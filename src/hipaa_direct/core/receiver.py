"""Direct message receiving with POP3 and S/MIME decryption."""

import poplib
import ssl
import email
from email import policy
from email.parser import BytesParser
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from hipaa_direct.utils.logging import AuditLogger


class DirectMessageReceiver:
    """Handles receiving Direct messages via POP3."""

    def __init__(
        self,
        pop3_host: str,
        pop3_port: int = 995,
        pop3_user: str = None,
        pop3_password: str = None,
        use_ssl: bool = True,
        cert_path: Optional[str] = None,
        key_path: Optional[str] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """
        Initialize the Direct message receiver.

        Args:
            pop3_host: POP3 server hostname
            pop3_port: POP3 server port (default: 995 for SSL)
            pop3_user: POP3 username
            pop3_password: POP3 password
            use_ssl: Whether to use SSL (default: True)
            cert_path: Path to certificate for S/MIME decryption (optional)
            key_path: Path to private key for S/MIME decryption (optional)
            audit_logger: Optional audit logger for HIPAA compliance
        """
        self.pop3_host = pop3_host
        self.pop3_port = pop3_port
        self.pop3_user = pop3_user
        self.pop3_password = pop3_password
        self.use_ssl = use_ssl
        self.cert_path = cert_path
        self.key_path = key_path
        self.audit_logger = audit_logger or AuditLogger()

    def connect(self) -> poplib.POP3_SSL:
        """
        Connect to POP3 server and authenticate.

        Returns:
            POP3_SSL connection object

        Raises:
            Exception: If connection or authentication fails
        """
        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                connection = poplib.POP3_SSL(
                    self.pop3_host, self.pop3_port, timeout=30, context=context
                )
            else:
                connection = poplib.POP3(self.pop3_host, self.pop3_port, timeout=30)

            # Authenticate
            connection.user(self.pop3_user)
            connection.pass_(self.pop3_password)

            self.audit_logger.log_certificate_operation(
                operation="POP3_CONNECT",
                email=self.pop3_user,
                success=True,
            )

            return connection

        except Exception as e:
            self.audit_logger.log_certificate_operation(
                operation="POP3_CONNECT",
                email=self.pop3_user,
                success=False,
                error=str(e),
            )
            raise

    def get_message_count(self) -> int:
        """
        Get the number of messages in the mailbox.

        Returns:
            Number of messages
        """
        connection = self.connect()
        try:
            msg_count, mbox_size = connection.stat()
            return msg_count
        finally:
            connection.quit()

    def fetch_message(self, connection: poplib.POP3_SSL, msg_num: int) -> Dict[str, Any]:
        """
        Fetch a single message from the server.

        Args:
            connection: Active POP3 connection
            msg_num: Message number (1-indexed)

        Returns:
            Dictionary with message data
        """
        try:
            # Fetch message
            response, lines, octets = connection.retr(msg_num)

            # Parse email
            msg_bytes = b'\n'.join(lines)
            msg = BytesParser(policy=policy.default).parsebytes(msg_bytes)

            # Extract message details
            message_data = {
                'message_number': msg_num,
                'message_id': msg.get('Message-ID', ''),
                'from': msg.get('From', ''),
                'to': msg.get('To', ''),
                'subject': msg.get('Subject', ''),
                'date': msg.get('Date', ''),
                'received_at': datetime.utcnow().isoformat(),
                'size': octets,
                'raw_message': msg_bytes,
                'parsed_message': msg,
                'is_encrypted': self._is_smime_encrypted(msg),
                'attachments': [],
            }

            # Extract body
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))

                    # Get message body
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        message_data['body'] = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif content_type == "text/html" and "attachment" not in content_disposition:
                        message_data['body_html'] = part.get_payload(decode=True).decode('utf-8', errors='ignore')

                    # Get attachments
                    elif "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            message_data['attachments'].append({
                                'filename': filename,
                                'content_type': content_type,
                                'size': len(part.get_payload(decode=True)) if part.get_payload(decode=True) else 0,
                                'content': part.get_payload(decode=True),
                            })
            else:
                # Single part message
                message_data['body'] = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

            return message_data

        except Exception as e:
            self.audit_logger.log_certificate_operation(
                operation="FETCH_MESSAGE",
                email=self.pop3_user,
                success=False,
                error=str(e),
            )
            raise

    def _is_smime_encrypted(self, msg: email.message.EmailMessage) -> bool:
        """
        Check if message is S/MIME encrypted.

        Args:
            msg: Parsed email message

        Returns:
            True if message appears to be S/MIME encrypted
        """
        content_type = msg.get_content_type()
        return content_type in [
            'application/pkcs7-mime',
            'application/x-pkcs7-mime',
        ]

    def decrypt_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt S/MIME encrypted message.

        Args:
            message_data: Message data dictionary

        Returns:
            Updated message data with decrypted content

        Note:
            This is a placeholder. Full S/MIME decryption implementation needed.
        """
        if not message_data.get('is_encrypted'):
            return message_data

        if not self.cert_path or not self.key_path:
            raise ValueError("Certificate and key required for S/MIME decryption")

        # TODO: Implement full S/MIME decryption
        # This would use cryptography library to:
        # 1. Load recipient's private key
        # 2. Decrypt the message envelope
        # 3. Verify sender's signature
        # 4. Extract decrypted content

        self.audit_logger.log_certificate_operation(
            operation="DECRYPT_MESSAGE",
            email=self.pop3_user,
            success=False,
            error="S/MIME decryption not yet implemented",
        )

        message_data['decryption_note'] = "S/MIME decryption not yet implemented"
        return message_data

    def fetch_all_messages(
        self,
        delete_after_fetch: bool = False,
        decrypt: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all messages from the mailbox.

        Args:
            delete_after_fetch: Whether to delete messages after fetching
            decrypt: Whether to attempt S/MIME decryption

        Returns:
            List of message dictionaries
        """
        connection = self.connect()
        messages = []

        try:
            msg_count, mbox_size = connection.stat()

            self.audit_logger.log_certificate_operation(
                operation="FETCH_ALL_START",
                email=self.pop3_user,
                success=True,
                error=f"Fetching {msg_count} messages",
            )

            for msg_num in range(1, msg_count + 1):
                try:
                    message_data = self.fetch_message(connection, msg_num)

                    # Decrypt if requested and encrypted
                    if decrypt and message_data.get('is_encrypted'):
                        message_data = self.decrypt_message(message_data)

                    messages.append(message_data)

                    # Delete message if requested
                    if delete_after_fetch:
                        connection.dele(msg_num)

                    self.audit_logger.log_certificate_operation(
                        operation="MESSAGE_RECEIVED",
                        email=message_data.get('from', 'unknown'),
                        success=True,
                    )

                except Exception as e:
                    self.audit_logger.log_certificate_operation(
                        operation="MESSAGE_FETCH_ERROR",
                        email=self.pop3_user,
                        success=False,
                        error=f"Message {msg_num}: {str(e)}",
                    )
                    # Continue with other messages
                    continue

            return messages

        finally:
            connection.quit()

    def save_message_to_file(
        self,
        message_data: Dict[str, Any],
        output_dir: str = "received_messages",
    ) -> str:
        """
        Save message to file.

        Args:
            message_data: Message data dictionary
            output_dir: Directory to save messages

        Returns:
            Path to saved message file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename from message ID and date
        message_id = message_data.get('message_id', 'unknown').replace('<', '').replace('>', '').replace('/', '_')
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{message_id}.eml"

        file_path = output_path / filename

        # Save raw message
        with open(file_path, 'wb') as f:
            f.write(message_data['raw_message'])

        return str(file_path)
