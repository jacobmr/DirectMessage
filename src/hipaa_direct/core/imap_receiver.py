"""Direct message receiving with IMAP (when enabled by HIXNY).

This module provides IMAP-based message receiving, which is superior to POP3 for production use.
Benefits:
- Messages stay on server
- Folder organization (INBOX, Processed, etc.)
- Mark messages as read/unread
- Better for multiple workers/instances
- Sync across devices
"""

import imaplib
import ssl
import email
from email import policy
from email.parser import BytesParser
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

from hipaa_direct.utils.logging import AuditLogger


class IMAPDirectMessageReceiver:
    """Handles receiving Direct messages via IMAP."""

    def __init__(
        self,
        imap_host: str,
        imap_port: int = 993,
        imap_user: str = None,
        imap_password: str = None,
        use_ssl: bool = True,
        cert_path: Optional[str] = None,
        key_path: Optional[str] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """
        Initialize the IMAP Direct message receiver.

        Args:
            imap_host: IMAP server hostname
            imap_port: IMAP server port (default: 993 for SSL)
            imap_user: IMAP username
            imap_password: IMAP password
            use_ssl: Whether to use SSL (default: True)
            cert_path: Path to certificate for S/MIME decryption (optional)
            key_path: Path to private key for S/MIME decryption (optional)
            audit_logger: Optional audit logger for HIPAA compliance
        """
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.imap_user = imap_user
        self.imap_password = imap_password
        self.use_ssl = use_ssl
        self.cert_path = cert_path
        self.key_path = key_path
        self.audit_logger = audit_logger or AuditLogger()
        self.connection = None

    def connect(self) -> imaplib.IMAP4_SSL:
        """
        Connect to IMAP server and authenticate.

        Returns:
            IMAP4_SSL connection object

        Raises:
            Exception: If connection or authentication fails
        """
        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                self.connection = imaplib.IMAP4_SSL(
                    self.imap_host, self.imap_port, ssl_context=context
                )
            else:
                self.connection = imaplib.IMAP4(self.imap_host, self.imap_port)

            # Authenticate
            self.connection.login(self.imap_user, self.imap_password)

            self.audit_logger.log_certificate_operation(
                operation="IMAP_CONNECT",
                email=self.imap_user,
                success=True,
            )

            return self.connection

        except Exception as e:
            self.audit_logger.log_certificate_operation(
                operation="IMAP_CONNECT",
                email=self.imap_user,
                success=False,
                error=str(e),
            )
            raise

    def disconnect(self):
        """Close IMAP connection."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except:
                pass
            self.connection = None

    def list_folders(self) -> List[str]:
        """
        List all available IMAP folders.

        Returns:
            List of folder names
        """
        if not self.connection:
            self.connect()

        status, folders = self.connection.list()
        if status != 'OK':
            raise Exception("Failed to list folders")

        folder_names = []
        for folder in folders:
            # Parse folder name from IMAP response
            # Format: b'(\\HasNoChildren) "/" "INBOX"'
            parts = folder.decode().split('"')
            if len(parts) >= 3:
                folder_names.append(parts[-2])

        return folder_names

    def select_folder(self, folder: str = "INBOX") -> Tuple[str, int]:
        """
        Select an IMAP folder.

        Args:
            folder: Folder name (default: INBOX)

        Returns:
            Tuple of (status, message_count)
        """
        if not self.connection:
            self.connect()

        status, data = self.connection.select(folder)
        if status != 'OK':
            raise Exception(f"Failed to select folder: {folder}")

        message_count = int(data[0])
        return status, message_count

    def get_message_count(self, folder: str = "INBOX") -> int:
        """
        Get the number of messages in a folder.

        Args:
            folder: Folder name (default: INBOX)

        Returns:
            Number of messages
        """
        try:
            if not self.connection:
                self.connect()

            status, msg_count = self.select_folder(folder)
            return msg_count

        finally:
            self.disconnect()

    def search_messages(
        self,
        criteria: str = "ALL",
        folder: str = "INBOX"
    ) -> List[bytes]:
        """
        Search for messages matching criteria.

        Args:
            criteria: IMAP search criteria (default: ALL)
                     Examples: "ALL", "UNSEEN", "SINCE 01-Jan-2025"
            folder: Folder to search (default: INBOX)

        Returns:
            List of message IDs
        """
        if not self.connection:
            self.connect()

        self.select_folder(folder)

        status, messages = self.connection.search(None, criteria)
        if status != 'OK':
            raise Exception(f"Search failed for criteria: {criteria}")

        # Parse message IDs
        message_ids = messages[0].split() if messages[0] else []
        return message_ids

    def fetch_message(self, message_id: bytes, mark_as_read: bool = False) -> Dict[str, Any]:
        """
        Fetch a single message by ID.

        Args:
            message_id: IMAP message ID
            mark_as_read: If True, mark message as seen

        Returns:
            Dictionary with message data
        """
        try:
            # Fetch message
            fetch_flag = "(RFC822)" if mark_as_read else "(BODY.PEEK[])"
            status, msg_data = self.connection.fetch(message_id, fetch_flag)

            if status != 'OK':
                raise Exception(f"Failed to fetch message {message_id}")

            # Parse email
            msg_bytes = msg_data[0][1]
            msg = BytesParser(policy=policy.default).parsebytes(msg_bytes)

            # Extract message details
            message_data = {
                'imap_id': message_id.decode(),
                'message_id': msg.get('Message-ID', ''),
                'from': msg.get('From', ''),
                'to': msg.get('To', ''),
                'subject': msg.get('Subject', ''),
                'date': msg.get('Date', ''),
                'received_at': datetime.utcnow().isoformat(),
                'size': len(msg_bytes),
                'raw_message': msg_bytes,
                'parsed_message': msg,
                'is_encrypted': self._is_smime_encrypted(msg),
                'attachments': [],
            }

            # Extract body and attachments
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
                email=self.imap_user,
                success=False,
                error=str(e),
            )
            raise

    def _is_smime_encrypted(self, msg: email.message.EmailMessage) -> bool:
        """Check if message is S/MIME encrypted."""
        content_type = msg.get_content_type()
        return content_type in [
            'application/pkcs7-mime',
            'application/x-pkcs7-mime',
        ]

    def fetch_all_messages(
        self,
        folder: str = "INBOX",
        criteria: str = "ALL",
        mark_as_read: bool = False,
        move_to_folder: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all messages from a folder.

        Args:
            folder: Folder to fetch from (default: INBOX)
            criteria: IMAP search criteria (default: ALL)
            mark_as_read: If True, mark messages as seen
            move_to_folder: If specified, move messages to this folder after fetching

        Returns:
            List of message dictionaries
        """
        try:
            if not self.connection:
                self.connect()

            # Search for messages
            message_ids = self.search_messages(criteria, folder)

            self.audit_logger.log_certificate_operation(
                operation="FETCH_ALL_START",
                email=self.imap_user,
                success=True,
                error=f"Fetching {len(message_ids)} messages from {folder}",
            )

            messages = []

            for msg_id in message_ids:
                try:
                    message_data = self.fetch_message(msg_id, mark_as_read)
                    messages.append(message_data)

                    # Move message if requested
                    if move_to_folder:
                        self.move_message(msg_id, move_to_folder)

                    self.audit_logger.log_certificate_operation(
                        operation="MESSAGE_RECEIVED",
                        email=message_data.get('from', 'unknown'),
                        success=True,
                    )

                except Exception as e:
                    self.audit_logger.log_certificate_operation(
                        operation="MESSAGE_FETCH_ERROR",
                        email=self.imap_user,
                        success=False,
                        error=f"Message {msg_id}: {str(e)}",
                    )
                    continue

            return messages

        finally:
            self.disconnect()

    def move_message(self, message_id: bytes, destination_folder: str):
        """
        Move a message to a different folder.

        Args:
            message_id: IMAP message ID
            destination_folder: Destination folder name
        """
        if not self.connection:
            raise Exception("Not connected to IMAP server")

        # Copy message to destination
        self.connection.copy(message_id, destination_folder)

        # Mark original as deleted
        self.connection.store(message_id, '+FLAGS', '\\Deleted')

        # Expunge deleted messages
        self.connection.expunge()

    def mark_as_read(self, message_id: bytes):
        """Mark a message as read."""
        if not self.connection:
            raise Exception("Not connected to IMAP server")

        self.connection.store(message_id, '+FLAGS', '\\Seen')

    def mark_as_unread(self, message_id: bytes):
        """Mark a message as unread."""
        if not self.connection:
            raise Exception("Not connected to IMAP server")

        self.connection.store(message_id, '-FLAGS', '\\Seen')

    def delete_message(self, message_id: bytes):
        """
        Delete a message.

        Args:
            message_id: IMAP message ID
        """
        if not self.connection:
            raise Exception("Not connected to IMAP server")

        self.connection.store(message_id, '+FLAGS', '\\Deleted')
        self.connection.expunge()

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
