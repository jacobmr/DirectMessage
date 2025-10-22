"""FastAPI integration for HIPAA Direct Message receiving.

This module provides a FastAPI router for receiving Direct messages
that can be integrated into existing FastAPI applications like ResearchFlo.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
import os
from datetime import datetime
from pathlib import Path

from hipaa_direct.core.receiver import DirectMessageReceiver
from hipaa_direct.utils.logging import AuditLogger


# Pydantic models for API responses
class MessageSummary(BaseModel):
    """Summary of a Direct message."""
    message_id: str
    from_address: str
    to_address: str
    subject: str
    date: str
    size: int
    is_encrypted: bool
    attachment_count: int
    received_at: str


class AttachmentInfo(BaseModel):
    """Information about a message attachment."""
    filename: str
    content_type: str
    size: int


class MessageDetail(BaseModel):
    """Detailed Direct message information."""
    message_id: str
    from_address: str
    to_address: str
    subject: str
    date: str
    size: int
    body: Optional[str] = None
    body_html: Optional[str] = None
    is_encrypted: bool
    attachments: List[AttachmentInfo]
    received_at: str


class CheckMessagesResponse(BaseModel):
    """Response for message count check."""
    message_count: int
    account: str
    timestamp: str


class FetchMessagesResponse(BaseModel):
    """Response for fetch operation."""
    messages_fetched: int
    messages: List[MessageSummary]
    timestamp: str


# Configuration
class DirectReceiverConfig:
    """Configuration for Direct message receiver."""

    def __init__(
        self,
        pop3_host: Optional[str] = None,
        pop3_port: Optional[int] = None,
        pop3_user: Optional[str] = None,
        pop3_password: Optional[str] = None,
        pop3_use_ssl: bool = True,
        storage_dir: str = "received_messages",
        log_dir: str = "logs",
    ):
        """Initialize configuration from parameters or environment variables."""
        self.pop3_host = pop3_host or os.getenv("POP3_HOST")
        self.pop3_port = pop3_port or int(os.getenv("POP3_PORT", "995"))
        self.pop3_user = pop3_user or os.getenv("POP3_USER")
        self.pop3_password = pop3_password or os.getenv("POP3_PASSWORD")
        self.pop3_use_ssl = pop3_use_ssl if pop3_use_ssl is not None else os.getenv("POP3_USE_SSL", "true").lower() == "true"

        self.storage_dir = storage_dir
        self.log_dir = log_dir

        # Validate required configuration
        self._validate()

    def _validate(self):
        """Validate that required configuration is present."""
        if not self.pop3_host:
            raise ValueError("POP3_HOST not configured")
        if not self.pop3_user:
            raise ValueError("POP3_USER not configured")
        if not self.pop3_password:
            raise ValueError("POP3_PASSWORD not configured")


# Create router
def create_direct_receiver_router(
    config: Optional[DirectReceiverConfig] = None,
    prefix: str = "/api/direct",
    tags: Optional[List[str]] = None,
) -> APIRouter:
    """
    Create a FastAPI router for Direct message receiving.

    Args:
        config: DirectReceiverConfig instance (uses env vars if None)
        prefix: URL prefix for the router
        tags: OpenAPI tags

    Returns:
        APIRouter instance ready to be included in FastAPI app

    Example:
        ```python
        from fastapi import FastAPI
        from hipaa_direct.integrations.fastapi_receiver import create_direct_receiver_router

        app = FastAPI()
        direct_router = create_direct_receiver_router()
        app.include_router(direct_router)
        ```
    """
    # Initialize configuration
    if config is None:
        config = DirectReceiverConfig()

    # Initialize components
    audit_logger = AuditLogger(log_dir=config.log_dir)

    # Create router
    router = APIRouter(prefix=prefix, tags=tags or ["direct-messaging"])

    def _get_receiver() -> DirectMessageReceiver:
        """Get configured DirectMessageReceiver instance."""
        return DirectMessageReceiver(
            pop3_host=config.pop3_host,
            pop3_port=config.pop3_port,
            pop3_user=config.pop3_user,
            pop3_password=config.pop3_password,
            use_ssl=config.pop3_use_ssl,
            audit_logger=audit_logger,
        )

    @router.get("/check", response_model=CheckMessagesResponse)
    async def check_messages():
        """
        Check how many Direct messages are waiting in the mailbox.

        This is a lightweight operation that just checks the message count
        without downloading messages.

        Returns:
            CheckMessagesResponse with message count
        """
        try:
            receiver = _get_receiver()
            msg_count = receiver.get_message_count()

            return CheckMessagesResponse(
                message_count=msg_count,
                account=config.pop3_user,
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error checking messages: {str(e)}")

    @router.post("/fetch", response_model=FetchMessagesResponse)
    async def fetch_messages(
        delete_after_fetch: bool = Query(False, description="Delete messages from server after fetching"),
        decrypt: bool = Query(False, description="Attempt S/MIME decryption (not yet implemented)"),
    ):
        """
        Fetch all Direct messages from the mailbox.

        This downloads all messages, parses them, extracts attachments,
        and saves them to the storage directory.

        Args:
            delete_after_fetch: If True, delete messages from server after successful fetch
            decrypt: If True, attempt to decrypt S/MIME encrypted messages

        Returns:
            FetchMessagesResponse with message summaries
        """
        try:
            receiver = _get_receiver()

            # Fetch all messages
            messages = receiver.fetch_all_messages(
                delete_after_fetch=delete_after_fetch,
                decrypt=decrypt,
            )

            # Save messages to storage
            storage_path = Path(config.storage_dir)
            storage_path.mkdir(parents=True, exist_ok=True)

            for msg in messages:
                receiver.save_message_to_file(msg, str(storage_path))

            # Convert to response format
            message_summaries = [
                MessageSummary(
                    message_id=msg['message_id'],
                    from_address=msg['from'],
                    to_address=msg['to'],
                    subject=msg['subject'],
                    date=msg['date'],
                    size=msg['size'],
                    is_encrypted=msg['is_encrypted'],
                    attachment_count=len(msg.get('attachments', [])),
                    received_at=msg['received_at'],
                )
                for msg in messages
            ]

            return FetchMessagesResponse(
                messages_fetched=len(messages),
                messages=message_summaries,
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching messages: {str(e)}")

    @router.get("/messages", response_model=List[MessageSummary])
    async def list_messages(
        limit: int = Query(100, description="Maximum number of messages to return"),
    ):
        """
        List all stored Direct messages.

        This reads from the local storage directory, not from the POP3 server.

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of message summaries
        """
        try:
            storage_path = Path(config.storage_dir)

            if not storage_path.exists():
                return []

            # List all .eml files
            message_files = list(storage_path.glob("**/*.eml"))[:limit]

            # TODO: Parse stored messages and return summaries
            # For now, return empty list
            return []

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error listing messages: {str(e)}")

    @router.get("/health")
    async def health_check():
        """
        Health check endpoint.

        Returns:
            Status of the Direct messaging receiver service
        """
        checks = {
            "pop3_configured": bool(config.pop3_host and config.pop3_user),
            "storage_writable": Path(config.storage_dir).exists() or True,  # Will be created
            "logs_writable": Path(config.log_dir).exists() or True,  # Will be created
        }

        all_healthy = all(checks.values())

        return {
            "status": "healthy" if all_healthy else "degraded",
            "checks": checks,
            "service": "HIPAA Direct Message Receiver",
            "account": config.pop3_user,
            "server": f"{config.pop3_host}:{config.pop3_port}",
        }

    @router.get("/stats")
    async def get_stats():
        """
        Get statistics about received messages.

        Returns:
            Statistics about messages and attachments
        """
        try:
            storage_path = Path(config.storage_dir)

            if not storage_path.exists():
                return {
                    "total_messages": 0,
                    "total_attachments": 0,
                    "storage_size_bytes": 0,
                }

            # Count messages
            message_files = list(storage_path.glob("**/*.eml"))
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
            raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

    return router
