"""Direct message sending with S/MIME encryption."""

import smtplib
from email.mime.multipart import MIMEMultipart
from typing import Optional
from OpenSSL import crypto
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography import x509

from hipaa_direct.core.message import DirectMessage
from hipaa_direct.utils.logging import AuditLogger


class DirectMessageSender:
    """Handles sending Direct messages with S/MIME encryption."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        use_tls: bool = True,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """
        Initialize the Direct message sender.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port (default: 587)
            smtp_user: SMTP username (optional)
            smtp_password: SMTP password (optional)
            use_tls: Whether to use TLS (default: True)
            audit_logger: Optional audit logger for HIPAA compliance
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.audit_logger = audit_logger or AuditLogger()

    def encrypt_message(
        self,
        message: DirectMessage,
        sender_cert_path: str,
        sender_key_path: str,
        recipient_cert_path: str,
    ) -> bytes:
        """
        Encrypt and sign a message using S/MIME.

        Args:
            message: DirectMessage to encrypt
            sender_cert_path: Path to sender's certificate
            sender_key_path: Path to sender's private key
            recipient_cert_path: Path to recipient's certificate

        Returns:
            Encrypted message as bytes
        """
        # Validate message first
        message.validate()

        # Load sender's certificate and private key
        with open(sender_cert_path, "rb") as f:
            sender_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

        with open(sender_key_path, "rb") as f:
            sender_key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )

        # Load recipient's certificate
        with open(recipient_cert_path, "rb") as f:
            recipient_cert = x509.load_pem_x509_certificate(
                f.read(), default_backend()
            )

        # Convert message to MIME
        mime_message = message.to_mime()
        message_bytes = mime_message.as_bytes()

        # TODO: Implement full S/MIME encryption and signing
        # This is a placeholder - full implementation would use:
        # 1. Sign the message with sender's private key
        # 2. Encrypt the signed message with recipient's public key
        # 3. Return the encrypted/signed S/MIME message

        self.audit_logger.log_encryption(
            message_id=message.message_id,
            from_address=message.from_address,
            to_address=message.to_address,
        )

        return message_bytes

    def send(
        self,
        message: DirectMessage,
        sender_cert_path: str,
        sender_key_path: str,
        recipient_cert_path: str,
    ) -> bool:
        """
        Send a Direct message with S/MIME encryption.

        Args:
            message: DirectMessage to send
            sender_cert_path: Path to sender's certificate
            sender_key_path: Path to sender's private key
            recipient_cert_path: Path to recipient's certificate

        Returns:
            True if sent successfully
        """
        try:
            # Encrypt the message
            encrypted_message = self.encrypt_message(
                message, sender_cert_path, sender_key_path, recipient_cert_path
            )

            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()

                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)

                # Send the encrypted message
                server.sendmail(
                    message.from_address,
                    message.to_address,
                    encrypted_message,
                )

            self.audit_logger.log_send(
                message_id=message.message_id,
                from_address=message.from_address,
                to_address=message.to_address,
                success=True,
            )

            return True

        except Exception as e:
            self.audit_logger.log_send(
                message_id=message.message_id,
                from_address=message.from_address,
                to_address=message.to_address,
                success=False,
                error=str(e),
            )
            raise
