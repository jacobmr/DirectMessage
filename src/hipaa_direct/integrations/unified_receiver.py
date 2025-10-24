"""Unified Direct Message receiver supporting multiple backends.

This module provides a unified interface for receiving Direct messages
from different backends (IMAP, POP3, phiMail) with a simple configuration
switch.

Perfect for hybrid deployments where you want to start with one backend
and easily switch to another later.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
import os

from hipaa_direct.core.receiver import DirectMessageReceiver
from hipaa_direct.core.imap_receiver import IMAPDirectMessageReceiver
from hipaa_direct.clients.phimail_client import PhiMailClient
from hipaa_direct.utils.logging import AuditLogger


class ReceiverBackend(Enum):
    """Available receiver backends."""
    IMAP = "imap"
    POP3 = "pop3"
    PHIMAIL = "phimail"


class UnifiedDirectReceiver:
    """
    Unified receiver that supports multiple backends.

    Switch between IMAP, POP3, or phiMail with a simple configuration change.
    All backends expose the same interface for easy migration.

    Example:
        ```python
        # Use IMAP (recommended for HIXNY)
        receiver = UnifiedDirectReceiver(backend=ReceiverBackend.IMAP)
        messages = receiver.fetch_messages()

        # Switch to phiMail by changing one parameter
        receiver = UnifiedDirectReceiver(backend=ReceiverBackend.PHIMAIL)
        messages = receiver.fetch_messages()
        ```
    """

    def __init__(
        self,
        backend: ReceiverBackend = ReceiverBackend.IMAP,
        config: Optional[Dict[str, Any]] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """
        Initialize unified receiver with specified backend.

        Args:
            backend: Backend to use (IMAP, POP3, or PHIMAIL)
            config: Optional configuration dict. If None, reads from env vars.
            audit_logger: Optional audit logger

        Environment Variables:
            # For IMAP/POP3:
            POP3_HOST, POP3_PORT, POP3_USER, POP3_PASSWORD, POP3_USE_SSL

            # For phiMail:
            PHIMAIL_API_URL, PHIMAIL_USERNAME, PHIMAIL_PASSWORD

            # Backend selection (optional):
            DIRECT_RECEIVER_BACKEND=imap|pop3|phimail
        """
        self.backend = backend
        self.config = config or {}
        self.audit_logger = audit_logger or AuditLogger()
        self.client = None

        # Initialize appropriate backend
        self._initialize_backend()

    def _initialize_backend(self):
        """Initialize the selected backend."""
        if self.backend == ReceiverBackend.IMAP:
            self._init_imap()
        elif self.backend == ReceiverBackend.POP3:
            self._init_pop3()
        elif self.backend == ReceiverBackend.PHIMAIL:
            self._init_phimail()
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def _init_imap(self):
        """Initialize IMAP receiver."""
        # Get port with proper default
        port = self.config.get('port') if 'port' in self.config else None
        if port is None:
            port = int(os.getenv('POP3_PORT', '993'))

        self.client = IMAPDirectMessageReceiver(
            imap_host=self.config.get('host') or os.getenv('POP3_HOST'),
            imap_port=port,
            imap_user=self.config.get('user') or os.getenv('POP3_USER'),
            imap_password=self.config.get('password') or os.getenv('POP3_PASSWORD'),
            use_ssl=self.config.get('use_ssl') if 'use_ssl' in self.config else (os.getenv('POP3_USE_SSL', 'true').lower() == 'true'),
            audit_logger=self.audit_logger,
        )

    def _init_pop3(self):
        """Initialize POP3 receiver."""
        self.client = DirectMessageReceiver(
            pop3_host=self.config.get('host') or os.getenv('POP3_HOST'),
            pop3_port=self.config.get('port') or int(os.getenv('POP3_PORT', '995')),
            pop3_user=self.config.get('user') or os.getenv('POP3_USER'),
            pop3_password=self.config.get('password') or os.getenv('POP3_PASSWORD'),
            use_ssl=self.config.get('use_ssl', True),
            audit_logger=self.audit_logger,
        )

    def _init_phimail(self):
        """Initialize phiMail client."""
        self.client = PhiMailClient(
            api_base_url=self.config.get('api_url') or os.getenv('PHIMAIL_API_URL'),
            username=self.config.get('username') or os.getenv('PHIMAIL_USERNAME'),
            password=self.config.get('password') or os.getenv('PHIMAIL_PASSWORD'),
            verify_ssl=self.config.get('verify_ssl', True),
            audit_logger=self.audit_logger,
        )

    def get_message_count(self, folder: str = "INBOX") -> int:
        """
        Get number of messages.

        Args:
            folder: Folder name (IMAP only, ignored for others)

        Returns:
            Number of messages
        """
        if self.backend == ReceiverBackend.IMAP:
            # For IMAP, need to manually handle connection
            try:
                if not self.client.connection:
                    self.client.connect()

                status, msg_count = self.client.select_folder(folder)
                return msg_count
            except Exception as e:
                raise Exception(f"IMAP get_message_count error: {e}")

        elif self.backend == ReceiverBackend.POP3:
            return self.client.get_message_count()

        elif self.backend == ReceiverBackend.PHIMAIL:
            messages = self.client.check_inbox()
            return len(messages)

    def fetch_messages(
        self,
        limit: Optional[int] = None,
        folder: str = "INBOX",
        mark_as_read: bool = False,
        delete_after_fetch: bool = False,
        acknowledge: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages from backend.

        This provides a unified interface across all backends.

        Args:
            limit: Maximum messages to fetch (None = all)
            folder: Folder name (IMAP only)
            mark_as_read: Mark as read after fetching (IMAP only)
            delete_after_fetch: Delete after fetching (POP3 only)
            acknowledge: Remove from queue (phiMail only)

        Returns:
            List of message dictionaries with standardized format:
            {
                'message_id': str,
                'from': str,
                'to': str or list,
                'subject': str,
                'date': str,
                'body': str,
                'attachments': list,
                'size': int,
                'received_at': str,
            }
        """
        if self.backend == ReceiverBackend.IMAP:
            return self._fetch_imap(limit, folder, mark_as_read)

        elif self.backend == ReceiverBackend.POP3:
            return self._fetch_pop3(delete_after_fetch)

        elif self.backend == ReceiverBackend.PHIMAIL:
            return self._fetch_phimail(limit, acknowledge)

    def _fetch_imap(
        self,
        limit: Optional[int],
        folder: str,
        mark_as_read: bool,
    ) -> List[Dict[str, Any]]:
        """Fetch messages via IMAP."""
        # Determine criteria based on mark_as_read
        criteria = "ALL" if mark_as_read else "UNSEEN"

        messages = self.client.fetch_all_messages(
            folder=folder,
            criteria=criteria,
            mark_as_read=mark_as_read,
        )

        # Apply limit if specified
        if limit and len(messages) > limit:
            messages = messages[:limit]

        # Normalize message format
        return [self._normalize_message(msg, 'imap') for msg in messages]

    def _fetch_pop3(self, delete_after_fetch: bool) -> List[Dict[str, Any]]:
        """Fetch messages via POP3."""
        messages = self.client.fetch_all_messages(
            delete_after_fetch=delete_after_fetch
        )

        return [self._normalize_message(msg, 'pop3') for msg in messages]

    def _fetch_phimail(
        self,
        limit: Optional[int],
        acknowledge: bool,
    ) -> List[Dict[str, Any]]:
        """Fetch messages via phiMail."""
        # Check inbox
        message_list = self.client.check_inbox(limit=limit)

        messages = []
        for msg_summary in message_list:
            # Get full message
            full_msg = self.client.get_message(msg_summary['id'])
            messages.append(self._normalize_message(full_msg, 'phimail'))

            # Acknowledge if requested
            if acknowledge:
                self.client.acknowledge_message(msg_summary['id'])

        return messages

    def _normalize_message(
        self,
        msg: Dict[str, Any],
        source: str,
    ) -> Dict[str, Any]:
        """
        Normalize message format across backends.

        Ensures all messages have the same structure regardless of backend.
        """
        # Base format
        normalized = {
            'backend': source,
            'message_id': '',
            'from': '',
            'to': '',
            'subject': '',
            'date': '',
            'body': '',
            'attachments': [],
            'size': 0,
            'received_at': '',
        }

        # Map fields from source
        if source == 'imap':
            normalized.update({
                'message_id': msg.get('message_id', ''),
                'from': msg.get('from', ''),
                'to': msg.get('to', ''),
                'subject': msg.get('subject', ''),
                'date': msg.get('date', ''),
                'body': msg.get('body', ''),
                'attachments': msg.get('attachments', []),
                'size': msg.get('size', 0),
                'received_at': msg.get('received_at', ''),
                'imap_id': msg.get('imap_id'),
            })

        elif source == 'pop3':
            normalized.update({
                'message_id': msg.get('message_id', ''),
                'from': msg.get('from', ''),
                'to': msg.get('to', ''),
                'subject': msg.get('subject', ''),
                'date': msg.get('date', ''),
                'body': msg.get('body', ''),
                'attachments': msg.get('attachments', []),
                'size': msg.get('size', 0),
                'received_at': msg.get('received_at', ''),
            })

        elif source == 'phimail':
            # phiMail uses slightly different field names
            to_addresses = msg.get('to', [])
            if isinstance(to_addresses, list):
                to_str = ', '.join(to_addresses)
            else:
                to_str = str(to_addresses)

            normalized.update({
                'message_id': msg.get('messageId', ''),
                'from': msg.get('from', ''),
                'to': to_str,
                'subject': msg.get('subject', ''),
                'date': msg.get('receivedDate', ''),
                'body': msg.get('body', ''),
                'attachments': msg.get('attachments', []),
                'size': msg.get('size', 0),
                'received_at': msg.get('receivedDate', ''),
                'phimail_id': msg.get('id'),
            })

        return normalized

    def save_message(
        self,
        message: Dict[str, Any],
        output_dir: str = "received_messages",
    ) -> str:
        """
        Save message to file.

        Args:
            message: Message dictionary
            output_dir: Directory to save messages

        Returns:
            Path to saved file
        """
        # Delegate to appropriate backend
        if self.backend == ReceiverBackend.PHIMAIL:
            return self.client.save_message_to_file(message, output_dir)
        else:
            # IMAP and POP3 use same save method
            return self.client.save_message_to_file(message, output_dir)

    def health_check(self) -> Dict[str, Any]:
        """
        Check backend health.

        Returns:
            Health status dictionary
        """
        try:
            if self.backend == ReceiverBackend.PHIMAIL:
                return self.client.health_check()
            else:
                # For IMAP/POP3, try to get message count
                count = self.get_message_count()
                return {
                    'status': 'healthy',
                    'backend': self.backend.value,
                    'message_count': count,
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'backend': self.backend.value,
                'error': str(e),
            }

    @staticmethod
    def from_env() -> 'UnifiedDirectReceiver':
        """
        Create receiver from environment variables.

        Reads DIRECT_RECEIVER_BACKEND env var to select backend.
        Defaults to IMAP if not specified.

        Example:
            ```bash
            export DIRECT_RECEIVER_BACKEND=imap
            # or
            export DIRECT_RECEIVER_BACKEND=phimail
            ```

        Returns:
            Configured UnifiedDirectReceiver
        """
        backend_str = os.getenv('DIRECT_RECEIVER_BACKEND', 'imap').lower()

        backend_map = {
            'imap': ReceiverBackend.IMAP,
            'pop3': ReceiverBackend.POP3,
            'phimail': ReceiverBackend.PHIMAIL,
        }

        backend = backend_map.get(backend_str, ReceiverBackend.IMAP)

        return UnifiedDirectReceiver(backend=backend)
