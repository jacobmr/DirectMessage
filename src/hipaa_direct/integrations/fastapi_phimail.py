"""FastAPI integration for phiMail Direct Messaging REST API.

This module provides FastAPI routes for phiMail integration into ResearchFlo.
It offers a cleaner, more reliable alternative to POP3/IMAP-based receiving.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
import os
from datetime import datetime
from pathlib import Path

from hipaa_direct.clients.phimail_client import PhiMailClient
from hipaa_direct.utils.logging import AuditLogger


# Pydantic models for API responses
class MessageSummary(BaseModel):
    """Summary of a Direct message from phiMail."""
    id: str
    message_id: str
    from_address: str
    to_addresses: List[str]
    subject: str
    received_date: str
    size: int
    has_attachments: bool


class SendMessageRequest(BaseModel):
    """Request to send a Direct message."""
    sender: EmailStr
    recipients: List[EmailStr]
    subject: str
    body: str
    attachments: Optional[List[Dict[str, Any]]] = None
    request_delivery_status: bool = True


class SendMessageResponse(BaseModel):
    """Response from sending a message."""
    id: str
    status: str
    message_id: str
    timestamp: str


class DirectorySearchResponse(BaseModel):
    """Provider directory search result."""
    results_count: int
    entries: List[Dict[str, Any]]


class InboxCheckResponse(BaseModel):
    """Response from inbox check."""
    message_count: int
    messages: List[MessageSummary]
    timestamp: str


class FetchMessagesResponse(BaseModel):
    """Response from fetching and processing messages."""
    messages_fetched: int
    messages_acknowledged: int
    messages: List[Dict[str, Any]]
    timestamp: str


# Configuration
class PhiMailConfig:
    """Configuration for phiMail client."""

    def __init__(
        self,
        api_base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: bool = True,
        storage_dir: str = "received_messages/phimail",
        log_dir: str = "logs",
    ):
        """Initialize configuration from parameters or environment variables."""
        self.api_base_url = api_base_url or os.getenv(
            "PHIMAIL_API_URL",
            "https://sandbox.phimaildev.com:8443/rest/v1/"
        )
        self.username = username or os.getenv("PHIMAIL_USERNAME")
        self.password = password or os.getenv("PHIMAIL_PASSWORD")
        self.verify_ssl = verify_ssl
        self.storage_dir = storage_dir
        self.log_dir = log_dir

        # Validate required configuration
        self._validate()

    def _validate(self):
        """Validate that required configuration is present."""
        if not self.api_base_url:
            raise ValueError("PHIMAIL_API_URL not configured")
        if not self.username:
            raise ValueError("PHIMAIL_USERNAME not configured")
        if not self.password:
            raise ValueError("PHIMAIL_PASSWORD not configured")


# Create router
def create_phimail_router(
    config: Optional[PhiMailConfig] = None,
    prefix: str = "/api/direct",
    tags: Optional[List[str]] = None,
) -> APIRouter:
    """
    Create a FastAPI router for phiMail Direct messaging.

    This provides a complete REST API for Direct messaging that can be
    integrated into ResearchFlo or any FastAPI application.

    Args:
        config: PhiMailConfig instance (uses env vars if None)
        prefix: URL prefix for the router
        tags: OpenAPI tags

    Returns:
        APIRouter instance ready to be included in FastAPI app

    Example:
        ```python
        from fastapi import FastAPI
        from hipaa_direct.integrations.fastapi_phimail import create_phimail_router

        app = FastAPI()
        phimail_router = create_phimail_router()
        app.include_router(phimail_router)
        ```
    """
    # Initialize configuration
    if config is None:
        config = PhiMailConfig()

    # Initialize components
    audit_logger = AuditLogger(log_dir=config.log_dir)

    # Create router
    router = APIRouter(prefix=prefix, tags=tags or ["phimail-direct-messaging"])

    def _get_client() -> PhiMailClient:
        """Get configured PhiMailClient instance."""
        return PhiMailClient(
            api_base_url=config.api_base_url,
            username=config.username,
            password=config.password,
            verify_ssl=config.verify_ssl,
            audit_logger=audit_logger,
        )

    # =========================================================================
    # INBOX ENDPOINTS
    # =========================================================================

    @router.get("/inbox/check", response_model=InboxCheckResponse)
    async def check_inbox(
        limit: int = Query(50, description="Maximum messages to retrieve"),
    ):
        """
        Check inbox for new Direct messages.

        This retrieves message metadata without downloading full content.
        Messages remain in queue until acknowledged via /inbox/fetch.

        Returns:
            InboxCheckResponse with message summaries
        """
        try:
            client = _get_client()
            messages = client.check_inbox(limit=limit)

            summaries = [
                MessageSummary(
                    id=msg['id'],
                    message_id=msg.get('messageId', ''),
                    from_address=msg.get('from', ''),
                    to_addresses=msg.get('to', []),
                    subject=msg.get('subject', ''),
                    received_date=msg.get('receivedDate', ''),
                    size=msg.get('size', 0),
                    has_attachments=msg.get('hasAttachments', False),
                )
                for msg in messages
            ]

            return InboxCheckResponse(
                message_count=len(messages),
                messages=summaries,
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error checking inbox: {str(e)}"
            )

    @router.post("/inbox/fetch", response_model=FetchMessagesResponse)
    async def fetch_and_process_messages(
        limit: int = Query(50, description="Maximum messages to fetch"),
        acknowledge: bool = Query(True, description="Acknowledge (remove) messages after fetching"),
    ):
        """
        Fetch and process messages from inbox.

        This:
        1. Retrieves full message content with attachments
        2. Saves messages to storage directory
        3. Optionally acknowledges messages (removes from queue)

        Args:
            limit: Maximum messages to process
            acknowledge: If True, remove messages from queue after processing

        Returns:
            FetchMessagesResponse with processed messages
        """
        try:
            client = _get_client()

            # Check inbox
            message_list = client.check_inbox(limit=limit)

            fetched_messages = []
            acknowledged_count = 0

            # Process each message
            for msg_summary in message_list:
                try:
                    msg_id = msg_summary['id']

                    # Get full message
                    full_msg = client.get_message(msg_id)

                    # Save to storage
                    client.save_message_to_file(full_msg, config.storage_dir)

                    fetched_messages.append(full_msg)

                    # Acknowledge if requested
                    if acknowledge:
                        client.acknowledge_message(msg_id)
                        acknowledged_count += 1

                except Exception as e:
                    audit_logger.log_certificate_operation(
                        operation="MESSAGE_FETCH_ERROR",
                        email=config.username,
                        success=False,
                        error=f"Message {msg_summary.get('id')}: {str(e)}",
                    )
                    continue

            return FetchMessagesResponse(
                messages_fetched=len(fetched_messages),
                messages_acknowledged=acknowledged_count,
                messages=fetched_messages,
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching messages: {str(e)}"
            )

    # =========================================================================
    # OUTBOX ENDPOINTS (SENDING)
    # =========================================================================

    @router.post("/outbox/send", response_model=SendMessageResponse)
    async def send_message(request: SendMessageRequest):
        """
        Send a Direct message.

        This sends a message through phiMail with optional attachments
        and delivery status tracking.

        Example:
            ```json
            {
                "sender": "resflo@hixny.net",
                "recipients": ["test.resflo@hixny.net"],
                "subject": "Patient Report",
                "body": "Please see attached report",
                "attachments": [
                    {
                        "filename": "report.pdf",
                        "content_type": "application/pdf",
                        "content": "base64-encoded-content"
                    }
                ],
                "request_delivery_status": true
            }
            ```

        Returns:
            SendMessageResponse with message ID and status
        """
        try:
            client = _get_client()

            response = client.send_message(
                sender=request.sender,
                recipients=request.recipients,
                subject=request.subject,
                body=request.body,
                attachments=request.attachments,
                request_delivery_status=request.request_delivery_status,
            )

            return SendMessageResponse(
                id=response['id'],
                status=response.get('status', 'queued'),
                message_id=response.get('messageId', ''),
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error sending message: {str(e)}"
            )

    @router.get("/outbox/status/{message_id}")
    async def get_message_status(message_id: str):
        """
        Get delivery status of a sent message.

        Args:
            message_id: Outbox message ID from send response

        Returns:
            Status information including delivery notifications
        """
        try:
            client = _get_client()
            status = client.get_outbox_status(message_id)
            return status

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting status: {str(e)}"
            )

    # =========================================================================
    # DIRECTORY ENDPOINTS
    # =========================================================================

    @router.get("/directory/search", response_model=DirectorySearchResponse)
    async def search_directory(
        query: Optional[str] = Query(None, description="Free-text search query"),
        direct_address: Optional[str] = Query(None, description="Exact Direct address"),
        npi: Optional[str] = Query(None, description="National Provider Identifier"),
        organization: Optional[str] = Query(None, description="Organization name"),
        limit: int = Query(50, description="Maximum results"),
    ):
        """
        Search provider directory.

        Search by any combination of parameters to find Direct addresses
        for healthcare providers and organizations.

        Returns:
            DirectorySearchResponse with matching entries
        """
        try:
            client = _get_client()

            entries = client.search_directory(
                query=query,
                direct_address=direct_address,
                npi=npi,
                organization=organization,
                limit=limit,
            )

            return DirectorySearchResponse(
                results_count=len(entries),
                entries=entries,
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error searching directory: {str(e)}"
            )

    # =========================================================================
    # UTILITY ENDPOINTS
    # =========================================================================

    @router.get("/health")
    async def health_check():
        """
        Health check endpoint.

        Returns:
            Status of the phiMail Direct messaging service
        """
        try:
            client = _get_client()
            health = client.health_check()

            return {
                "status": health['status'],
                "service": "phiMail Direct Messaging",
                "api_url": config.api_base_url,
                "username": config.username,
                "ssl_verification": config.verify_ssl,
                "timestamp": health['timestamp'],
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "phiMail Direct Messaging",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    @router.get("/stats")
    async def get_stats():
        """
        Get statistics about received messages.

        Returns:
            Statistics about messages and attachments in storage
        """
        try:
            storage_path = Path(config.storage_dir)

            if not storage_path.exists():
                return {
                    "total_messages": 0,
                    "total_attachments": 0,
                    "storage_size_bytes": 0,
                }

            # Count messages (JSON files)
            message_files = list(storage_path.glob("**/*.json"))
            total_messages = len(message_files)

            # Count attachments
            attachment_path = storage_path / "attachments"
            total_attachments = len(list(attachment_path.glob("*"))) if attachment_path.exists() else 0

            # Calculate storage size
            total_size = sum(f.stat().st_size for f in storage_path.rglob("*") if f.is_file())

            return {
                "total_messages": total_messages,
                "total_attachments": total_attachments,
                "storage_size_bytes": total_size,
                "storage_size_mb": round(total_size / (1024 * 1024), 2),
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting stats: {str(e)}"
            )

    return router
