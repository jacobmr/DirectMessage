"""FastAPI integration for HIPAA Direct Messaging.

This module provides a FastAPI router that can be integrated into existing
FastAPI applications like ResearchFlo's clinres app.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
import os
from pathlib import Path

from hipaa_direct.core.message import DirectMessage
from hipaa_direct.core.sender import DirectMessageSender
from hipaa_direct.certs.manager import CertificateManager
from hipaa_direct.utils.logging import AuditLogger


# Pydantic models for API
class AttachmentModel(BaseModel):
    """Attachment data model."""
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


class DirectMessageRequest(BaseModel):
    """Request model for sending Direct messages."""
    to_address: EmailStr
    subject: str = Field(..., min_length=1, max_length=998)
    body: str = Field(..., min_length=1)
    body_html: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "to_address": "recipient@direct.example.com",
                "subject": "Patient Record Transfer",
                "body": "Please find the attached patient record.",
                "attachments": [
                    {
                        "filename": "patient_123.pdf",
                        "content": "base64_encoded_content_here",
                        "content_type": "application/pdf"
                    }
                ]
            }
        }


class DirectMessageResponse(BaseModel):
    """Response model for Direct message operations."""
    success: bool
    message_id: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None


class CertificateInfoResponse(BaseModel):
    """Response model for certificate information."""
    email: str
    subject: str
    issuer: str
    serial_number: int
    not_valid_before: str
    not_valid_after: str
    is_valid: bool


# Configuration
class DirectMessageConfig:
    """Configuration for Direct messaging service."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_use_tls: bool = True,
        sender_email: Optional[str] = None,
        sender_cert_path: Optional[str] = None,
        sender_key_path: Optional[str] = None,
        cert_dir: str = "certs",
        log_dir: str = "logs",
    ):
        """Initialize configuration from parameters or environment variables."""
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.smtp_use_tls = smtp_use_tls if smtp_use_tls is not None else os.getenv("SMTP_USE_TLS", "true").lower() == "true"

        self.sender_email = sender_email or os.getenv("DIRECT_SENDER_EMAIL") or self.smtp_user
        self.sender_cert_path = sender_cert_path or os.getenv("SENDER_CERT_PATH")
        self.sender_key_path = sender_key_path or os.getenv("SENDER_KEY_PATH")

        self.cert_dir = cert_dir
        self.log_dir = log_dir

        # Validate required configuration
        self._validate()

    def _validate(self):
        """Validate that required configuration is present."""
        if not self.smtp_host:
            raise ValueError("SMTP_HOST not configured")
        if not self.sender_email:
            raise ValueError("DIRECT_SENDER_EMAIL not configured")
        if not self.sender_cert_path:
            raise ValueError("SENDER_CERT_PATH not configured")
        if not self.sender_key_path:
            raise ValueError("SENDER_KEY_PATH not configured")


# Create router
def create_direct_messaging_router(
    config: Optional[DirectMessageConfig] = None,
    prefix: str = "/api/direct",
    tags: Optional[List[str]] = None,
) -> APIRouter:
    """
    Create a FastAPI router for Direct messaging.

    Args:
        config: DirectMessageConfig instance (uses env vars if None)
        prefix: URL prefix for the router
        tags: OpenAPI tags

    Returns:
        APIRouter instance ready to be included in FastAPI app

    Example:
        ```python
        from fastapi import FastAPI
        from hipaa_direct.integrations.fastapi_service import create_direct_messaging_router

        app = FastAPI()
        direct_router = create_direct_messaging_router()
        app.include_router(direct_router)
        ```
    """
    # Initialize configuration
    if config is None:
        config = DirectMessageConfig()

    # Initialize components
    cert_manager = CertificateManager(cert_dir=config.cert_dir)
    audit_logger = AuditLogger(log_dir=config.log_dir)

    # Create router
    router = APIRouter(prefix=prefix, tags=tags or ["direct-messaging"])

    @router.post("/send", response_model=DirectMessageResponse)
    async def send_direct_message(
        request: DirectMessageRequest,
        background_tasks: BackgroundTasks,
    ):
        """
        Send a HIPAA-compliant Direct message with S/MIME encryption.

        This endpoint:
        1. Validates the message
        2. Encrypts it with S/MIME using sender and recipient certificates
        3. Sends via SMTP
        4. Logs the operation for HIPAA compliance
        """
        try:
            # Create Direct message
            message = DirectMessage(
                from_address=config.sender_email,
                to_address=request.to_address,
                subject=request.subject,
                body=request.body,
                body_html=request.body_html,
                attachments=request.attachments,
            )

            # Validate message
            message.validate()

            # Determine recipient certificate path
            # In production, this would use DNS/LDAP discovery
            recipient_email_safe = request.to_address.replace("@", "_at_").replace(".", "_")
            recipient_cert_path = Path(config.cert_dir) / f"{recipient_email_safe}.crt"

            if not recipient_cert_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Recipient certificate not found for {request.to_address}"
                )

            # Initialize sender
            sender = DirectMessageSender(
                smtp_host=config.smtp_host,
                smtp_port=config.smtp_port,
                smtp_user=config.smtp_user,
                smtp_password=config.smtp_password,
                use_tls=config.smtp_use_tls,
                audit_logger=audit_logger,
            )

            # Send message
            success = sender.send(
                message=message,
                sender_cert_path=config.sender_cert_path,
                sender_key_path=config.sender_key_path,
                recipient_cert_path=str(recipient_cert_path),
            )

            if success:
                return DirectMessageResponse(
                    success=True,
                    message_id=message.message_id,
                    message="Message sent successfully",
                    details={
                        "from": config.sender_email,
                        "to": request.to_address,
                        "timestamp": message.timestamp.isoformat(),
                    }
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to send message")

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            audit_logger.log_send(
                message_id=message.message_id if 'message' in locals() else "unknown",
                from_address=config.sender_email,
                to_address=request.to_address,
                success=False,
                error=str(e),
            )
            raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")

    @router.get("/certificates/{email}", response_model=CertificateInfoResponse)
    async def get_certificate_info(email: str):
        """
        Get information about a certificate for a given email address.

        Useful for verifying certificate validity before sending messages.
        """
        try:
            email_safe = email.replace("@", "_at_").replace(".", "_")
            cert_path = Path(config.cert_dir) / f"{email_safe}.crt"

            if not cert_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Certificate not found for {email}"
                )

            info = cert_manager.get_certificate_info(str(cert_path))

            return CertificateInfoResponse(**info)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving certificate: {str(e)}")

    @router.get("/health")
    async def health_check():
        """
        Health check endpoint.

        Returns:
            Status of the Direct messaging service
        """
        checks = {
            "smtp_configured": bool(config.smtp_host),
            "sender_configured": bool(config.sender_email),
            "sender_cert_exists": Path(config.sender_cert_path).exists() if config.sender_cert_path else False,
            "sender_key_exists": Path(config.sender_key_path).exists() if config.sender_key_path else False,
        }

        all_healthy = all(checks.values())

        return {
            "status": "healthy" if all_healthy else "degraded",
            "checks": checks,
            "service": "HIPAA Direct Messaging",
        }

    return router
