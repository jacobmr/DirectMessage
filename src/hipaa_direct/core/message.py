"""Direct message construction and validation."""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class DirectMessage:
    """Represents a HIPAA Direct message."""

    def __init__(
        self,
        from_address: str,
        to_address: str,
        subject: str,
        body: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize a Direct message.

        Args:
            from_address: Sender's Direct address
            to_address: Recipient's Direct address
            subject: Message subject
            body: Plain text message body
            body_html: Optional HTML message body
            attachments: Optional list of attachments [{"filename": str, "content": bytes, "content_type": str}]
        """
        self.from_address = from_address
        self.to_address = to_address
        self.subject = subject
        self.body = body
        self.body_html = body_html
        self.attachments = attachments or []
        self.message_id = self._generate_message_id()
        self.timestamp = datetime.utcnow()

    def _generate_message_id(self) -> str:
        """Generate a unique message ID."""
        domain = self.from_address.split("@")[1] if "@" in self.from_address else "localhost"
        return f"<{uuid.uuid4()}@{domain}>"

    def to_mime(self) -> MIMEMultipart:
        """
        Convert the message to MIME format.

        Returns:
            MIMEMultipart message ready for S/MIME encryption
        """
        # Create multipart message
        if self.body_html:
            msg = MIMEMultipart("alternative")
        elif self.attachments:
            msg = MIMEMultipart("mixed")
        else:
            msg = MIMEMultipart()

        # Set headers
        msg["From"] = self.from_address
        msg["To"] = self.to_address
        msg["Subject"] = self.subject
        msg["Message-ID"] = self.message_id
        msg["Date"] = self.timestamp.strftime("%a, %d %b %Y %H:%M:%S +0000")

        # Add body
        if self.body_html:
            # Multipart alternative: plain text and HTML
            msg.attach(MIMEText(self.body, "plain"))
            msg.attach(MIMEText(self.body_html, "html"))
        else:
            msg.attach(MIMEText(self.body, "plain"))

        # Add attachments
        for attachment in self.attachments:
            part = MIMEApplication(
                attachment["content"], Name=attachment["filename"]
            )
            part["Content-Disposition"] = f'attachment; filename="{attachment["filename"]}"'
            if "content_type" in attachment:
                part.set_type(attachment["content_type"])
            msg.attach(part)

        return msg

    def validate(self) -> bool:
        """
        Validate the message meets Direct messaging requirements.

        Returns:
            True if valid, raises ValueError otherwise
        """
        if not self.from_address or "@" not in self.from_address:
            raise ValueError("Invalid from_address")
        if not self.to_address or "@" not in self.to_address:
            raise ValueError("Invalid to_address")
        if not self.subject:
            raise ValueError("Subject is required")
        if not self.body:
            raise ValueError("Message body is required")
        return True
