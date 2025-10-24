"""Unified FastAPI router supporting multiple Direct messaging backends.

This provides a single API that works with IMAP, POP3, or phiMail.
Switch backends by changing environment variable - no code changes needed.

Perfect for hybrid deployments where you want to easily migrate between backends.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
from datetime import datetime

from hipaa_direct.integrations.unified_receiver import (
    UnifiedDirectReceiver,
    ReceiverBackend,
)
from hipaa_direct.clients.phimail_client import PhiMailClient
from hipaa_direct.utils.logging import AuditLogger


# Pydantic models
class MessageSummary(BaseModel):
    """Summary of a Direct message."""
    backend: str
    message_id: str
    from_address: str
    to_address: str
    subject: str
    date: str
    size: int
    has_attachments: bool


class CheckMessagesResponse(BaseModel):
    """Response for message count check."""
    message_count: int
    backend: str
    account: str
    timestamp: str


class FetchMessagesResponse(BaseModel):
    """Response for fetch operation."""
    messages_fetched: int
    backend: str
    messages: List[Dict[str, Any]]
    timestamp: str


class BackendStatus(BaseModel):
    """Backend health status."""
    backend: str
    status: str
    details: Optional[Dict[str, Any]] = None


class SendMessageRequest(BaseModel):
    """Request to send a message (phiMail only)."""
    sender: str
    recipients: List[str]
    subject: str
    body: str
    attachments: Optional[List[Dict[str, Any]]] = None


# Configuration
class UnifiedConfig:
    """Configuration for unified receiver."""

    def __init__(self):
        """Initialize from environment variables."""
        # Backend selection
        self.backend = self._parse_backend()

        # Receiving config (IMAP/POP3)
        self.host = os.getenv('POP3_HOST')
        self.port = int(os.getenv('POP3_PORT', '993' if self.backend == 'imap' else '995'))
        self.user = os.getenv('POP3_USER')
        self.password = os.getenv('POP3_PASSWORD')
        self.use_ssl = os.getenv('POP3_USE_SSL', 'true').lower() == 'true'

        # Sending config (phiMail)
        self.phimail_api_url = os.getenv('PHIMAIL_API_URL')
        self.phimail_username = os.getenv('PHIMAIL_USERNAME')
        self.phimail_password = os.getenv('PHIMAIL_PASSWORD')

        # Storage
        self.storage_dir = os.getenv('DIRECT_STORAGE_DIR', 'received_messages')
        self.log_dir = os.getenv('DIRECT_LOG_DIR', 'logs')

    def _parse_backend(self) -> str:
        """Parse backend from environment."""
        backend = os.getenv('DIRECT_RECEIVER_BACKEND', 'imap').lower()
        if backend not in ['imap', 'pop3', 'phimail']:
            backend = 'imap'  # Default to IMAP
        return backend

    def get_receiver_backend(self) -> ReceiverBackend:
        """Get ReceiverBackend enum."""
        backend_map = {
            'imap': ReceiverBackend.IMAP,
            'pop3': ReceiverBackend.POP3,
            'phimail': ReceiverBackend.PHIMAIL,
        }
        return backend_map[self.backend]


def create_unified_router(
    config: Optional[UnifiedConfig] = None,
    prefix: str = "/api/direct",
    tags: Optional[List[str]] = None,
) -> APIRouter:
    """
    Create unified FastAPI router for Direct messaging.

    This router automatically uses the backend specified in environment variables.
    Switch between IMAP, POP3, or phiMail without code changes!

    Environment Variables:
        DIRECT_RECEIVER_BACKEND=imap|pop3|phimail  (default: imap)

        # For IMAP/POP3:
        POP3_HOST=hixny.net
        POP3_PORT=993
        POP3_USER=resflo
        POP3_PASSWORD=your_password

        # For phiMail:
        PHIMAIL_API_URL=https://secure.phimail.net:8443/rest/v1/
        PHIMAIL_USERNAME=your_username
        PHIMAIL_PASSWORD=your_password

    Example:
        ```python
        from fastapi import FastAPI
        from hipaa_direct.integrations.fastapi_unified import create_unified_router

        app = FastAPI()

        # Automatically uses backend from env var
        unified_router = create_unified_router()
        app.include_router(unified_router)

        # To switch backends, just change env var:
        # export DIRECT_RECEIVER_BACKEND=imap    # Use IMAP (default)
        # export DIRECT_RECEIVER_BACKEND=phimail # Use phiMail
        ```

    Args:
        config: Optional UnifiedConfig (reads from env if None)
        prefix: URL prefix for router
        tags: OpenAPI tags

    Returns:
        Configured APIRouter
    """
    # Initialize configuration
    if config is None:
        config = UnifiedConfig()

    # Initialize components
    audit_logger = AuditLogger(log_dir=config.log_dir)

    # Create router
    router = APIRouter(prefix=prefix, tags=tags or ["direct-messaging"])

    def _get_receiver() -> UnifiedDirectReceiver:
        """Get configured receiver."""
        return UnifiedDirectReceiver(
            backend=config.get_receiver_backend(),
            audit_logger=audit_logger,
        )

    def _get_phimail_sender() -> Optional[PhiMailClient]:
        """Get phiMail client for sending (if configured)."""
        if not config.phimail_api_url or not config.phimail_username:
            return None

        return PhiMailClient(
            api_base_url=config.phimail_api_url,
            username=config.phimail_username,
            password=config.phimail_password,
            audit_logger=audit_logger,
        )

    # =========================================================================
    # RECEIVING ENDPOINTS (All Backends)
    # =========================================================================

    @router.get("/check", response_model=CheckMessagesResponse)
    async def check_messages():
        """
        Check how many Direct messages are available.

        Works with all backends (IMAP, POP3, phiMail).
        The backend used is determined by DIRECT_RECEIVER_BACKEND env var.

        Returns:
            Message count and backend info
        """
        try:
            receiver = _get_receiver()
            msg_count = receiver.get_message_count()

            return CheckMessagesResponse(
                message_count=msg_count,
                backend=config.backend,
                account=config.user or config.phimail_username,
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error checking messages: {str(e)}"
            )

    @router.post("/fetch", response_model=FetchMessagesResponse)
    async def fetch_messages(
        limit: Optional[int] = Query(None, description="Max messages to fetch"),
        folder: str = Query("INBOX", description="Folder (IMAP only)"),
        mark_as_read: bool = Query(False, description="Mark as read (IMAP only)"),
        delete_after_fetch: bool = Query(False, description="Delete after fetch (POP3 only)"),
        acknowledge: bool = Query(True, description="Acknowledge/remove (phiMail only)"),
    ):
        """
        Fetch Direct messages from backend.

        This endpoint works with all backends:
        - **IMAP**: Fetches from specified folder, optionally marks as read
        - **POP3**: Fetches all messages, optionally deletes
        - **phiMail**: Fetches from inbox queue, optionally acknowledges

        The backend is automatically selected based on DIRECT_RECEIVER_BACKEND env var.

        Args:
            limit: Maximum messages to fetch (None = all available)
            folder: Folder name (IMAP only)
            mark_as_read: Mark messages as read (IMAP only)
            delete_after_fetch: Delete from server (POP3 only)
            acknowledge: Remove from queue (phiMail only)

        Returns:
            Fetched messages in standardized format
        """
        try:
            receiver = _get_receiver()

            # Fetch messages
            messages = receiver.fetch_messages(
                limit=limit,
                folder=folder,
                mark_as_read=mark_as_read,
                delete_after_fetch=delete_after_fetch,
                acknowledge=acknowledge,
            )

            # Save messages to storage
            from pathlib import Path
            storage_path = Path(config.storage_dir)
            storage_path.mkdir(parents=True, exist_ok=True)

            for msg in messages:
                receiver.save_message(msg, str(storage_path))

            return FetchMessagesResponse(
                messages_fetched=len(messages),
                backend=config.backend,
                messages=messages,
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching messages: {str(e)}"
            )

    # =========================================================================
    # SENDING ENDPOINTS (phiMail Only)
    # =========================================================================

    @router.post("/send")
    async def send_message(request: SendMessageRequest):
        """
        Send a Direct message via phiMail.

        Note: Sending is only available when phiMail is configured.
        HIXNY IMAP/POP3 does not support sending.

        Returns:
            Send response with message ID and status

        Raises:
            HTTPException: If phiMail is not configured
        """
        sender = _get_phimail_sender()

        if sender is None:
            raise HTTPException(
                status_code=503,
                detail="Sending not configured. Please configure phiMail (PHIMAIL_API_URL, PHIMAIL_USERNAME, PHIMAIL_PASSWORD)"
            )

        try:
            response = sender.send_message(
                sender=request.sender,
                recipients=request.recipients,
                subject=request.subject,
                body=request.body,
                attachments=request.attachments,
            )

            return {
                "status": "sent",
                "backend": "phimail",
                "message_id": response.get('id'),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error sending message: {str(e)}"
            )

    @router.get("/send/status/{message_id}")
    async def get_send_status(message_id: str):
        """
        Get delivery status of sent message (phiMail only).

        Args:
            message_id: Message ID from send response

        Returns:
            Delivery status information
        """
        sender = _get_phimail_sender()

        if sender is None:
            raise HTTPException(
                status_code=503,
                detail="Sending not configured"
            )

        try:
            status = sender.get_outbox_status(message_id)
            return status

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting status: {str(e)}"
            )

    # =========================================================================
    # DIRECTORY ENDPOINTS (phiMail Only)
    # =========================================================================

    @router.get("/directory/search")
    async def search_directory(
        query: Optional[str] = Query(None, description="Search query"),
        direct_address: Optional[str] = Query(None, description="Direct address"),
        npi: Optional[str] = Query(None, description="NPI"),
        organization: Optional[str] = Query(None, description="Organization"),
        limit: int = Query(50, description="Max results"),
    ):
        """
        Search provider directory (phiMail only).

        Returns:
            List of matching providers
        """
        sender = _get_phimail_sender()

        if sender is None:
            raise HTTPException(
                status_code=503,
                detail="Directory search not available. Configure phiMail to enable."
            )

        try:
            results = sender.search_directory(
                query=query,
                direct_address=direct_address,
                npi=npi,
                organization=organization,
                limit=limit,
            )

            return {
                "results_count": len(results),
                "entries": results,
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error searching directory: {str(e)}"
            )

    # =========================================================================
    # UTILITY ENDPOINTS
    # =========================================================================

    @router.get("/health", response_model=BackendStatus)
    async def health_check():
        """
        Health check for Direct messaging service.

        Returns current backend status and configuration.
        """
        try:
            receiver = _get_receiver()
            health = receiver.health_check()

            # Check if phiMail sending is available
            sender_available = _get_phimail_sender() is not None

            return BackendStatus(
                backend=config.backend,
                status=health.get('status', 'unknown'),
                details={
                    "receiving": {
                        "enabled": True,
                        "backend": config.backend,
                        "account": config.user or config.phimail_username,
                    },
                    "sending": {
                        "enabled": sender_available,
                        "backend": "phimail" if sender_available else "none",
                    },
                    "health": health,
                }
            )

        except Exception as e:
            return BackendStatus(
                backend=config.backend,
                status="unhealthy",
                details={"error": str(e)}
            )

    @router.get("/config")
    async def get_config():
        """
        Get current configuration (non-sensitive info only).

        Returns:
            Current backend and configuration info
        """
        return {
            "receiving": {
                "backend": config.backend,
                "host": config.host if config.backend != 'phimail' else None,
                "port": config.port if config.backend != 'phimail' else None,
                "user": config.user if config.backend != 'phimail' else None,
            },
            "sending": {
                "enabled": _get_phimail_sender() is not None,
                "backend": "phimail" if _get_phimail_sender() else "none",
            },
            "storage": {
                "directory": config.storage_dir,
            },
            "switch_backend": {
                "how_to": "Set DIRECT_RECEIVER_BACKEND environment variable",
                "options": ["imap", "pop3", "phimail"],
                "current": config.backend,
            }
        }

    @router.get("/stats")
    async def get_stats():
        """Get message statistics from storage."""
        try:
            from pathlib import Path

            storage_path = Path(config.storage_dir)

            if not storage_path.exists():
                return {
                    "total_messages": 0,
                    "total_attachments": 0,
                    "storage_size_bytes": 0,
                }

            # Count messages
            message_files = list(storage_path.glob("**/*.eml")) + list(storage_path.glob("**/*.json"))
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
                "backend": config.backend,
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting stats: {str(e)}"
            )

    return router
