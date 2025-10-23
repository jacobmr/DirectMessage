"""phiMail REST API client for HIPAA Direct Messaging.

This module provides a clean REST API interface to phiMail Direct messaging,
which is superior to POP3/IMAP for production use.

Benefits over POP3/IMAP:
- Clean REST API (no email protocol complexity)
- Both send AND receive messages
- Status notifications for delivery tracking
- Provider directory search
- Queue-based with acknowledgment
- JSON in/out, no MIME parsing needed

API Documentation: EMR Direct phiMail REST API
Sandbox: https://sandbox.phimaildev.com:8443/rest/v1/
Production: https://secure.phimail.net:8443/rest/v1/
"""

import requests
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import base64
from urllib.parse import urljoin

from hipaa_direct.utils.logging import AuditLogger


class PhiMailClient:
    """Client for phiMail Direct Messaging REST API."""

    def __init__(
        self,
        api_base_url: str,
        username: str,
        password: str,
        verify_ssl: bool = True,
        timeout: int = 30,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """
        Initialize phiMail API client.

        Args:
            api_base_url: Base URL for phiMail API
                         Sandbox: https://sandbox.phimaildev.com:8443/rest/v1/
                         Production: https://secure.phimail.net:8443/rest/v1/
            username: phiMail account username
            password: phiMail account password
            verify_ssl: Whether to verify SSL certificates (default: True)
            timeout: Request timeout in seconds (default: 30)
            audit_logger: Optional audit logger for HIPAA compliance
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.audit_logger = audit_logger or AuditLogger()

        # Setup session with HTTP Basic Auth
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.verify = verify_ssl
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })

    def _build_url(self, endpoint: str) -> str:
        """Build full URL for API endpoint."""
        return urljoin(self.api_base_url + '/', endpoint.lstrip('/'))

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to phiMail API.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path
            json_data: JSON request body (optional)
            params: Query parameters (optional)

        Returns:
            Response data as dictionary

        Raises:
            Exception: If request fails
        """
        url = self._build_url(endpoint)

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                timeout=self.timeout,
            )

            # Log request
            self.audit_logger.log_certificate_operation(
                operation=f"PHIMAIL_{method}_{endpoint}",
                email=self.username,
                success=response.status_code < 400,
                error=None if response.status_code < 400 else f"HTTP {response.status_code}",
            )

            # Handle errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                raise Exception(error_msg)

            # Return JSON response
            if response.content:
                return response.json()
            return {}

        except requests.exceptions.RequestException as e:
            self.audit_logger.log_certificate_operation(
                operation=f"PHIMAIL_{method}_{endpoint}",
                email=self.username,
                success=False,
                error=str(e),
            )
            raise

    # =========================================================================
    # INBOX OPERATIONS
    # =========================================================================

    def check_inbox(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve messages from inbox queue.

        This returns message metadata without downloading full message content.
        Messages remain in queue until acknowledged with acknowledge_message().

        Args:
            limit: Optional limit on number of messages to retrieve

        Returns:
            List of message metadata dictionaries containing:
            - id: Message queue ID (use for acknowledgment)
            - messageId: RFC 822 Message-ID
            - from: Sender Direct address
            - to: List of recipient Direct addresses
            - subject: Message subject
            - receivedDate: ISO timestamp
            - size: Message size in bytes
            - hasAttachments: Boolean indicating attachments

        Example:
            ```python
            client = PhiMailClient(api_base_url, username, password)
            messages = client.check_inbox(limit=10)
            for msg in messages:
                print(f"From: {msg['from']}, Subject: {msg['subject']}")
            ```
        """
        params = {'limit': limit} if limit else None
        response = self._request('GET', '/inbox', params=params)

        # Response is a list of message metadata
        messages = response if isinstance(response, list) else []

        self.audit_logger.log_certificate_operation(
            operation="INBOX_CHECK",
            email=self.username,
            success=True,
            error=f"Retrieved {len(messages)} messages",
        )

        return messages

    def get_message(self, message_id: str) -> Dict[str, Any]:
        """
        Retrieve full message content by queue ID.

        Args:
            message_id: Message queue ID from check_inbox()

        Returns:
            Complete message dictionary containing:
            - id: Message queue ID
            - messageId: RFC 822 Message-ID
            - from: Sender Direct address
            - to: List of recipient addresses
            - subject: Message subject
            - receivedDate: ISO timestamp
            - size: Message size in bytes
            - body: Message body (text or HTML)
            - attachments: List of attachment metadata
            - raw: Full MIME message (optional)

        Example:
            ```python
            messages = client.check_inbox()
            if messages:
                full_msg = client.get_message(messages[0]['id'])
                print(full_msg['body'])
            ```
        """
        response = self._request('GET', f'/inbox/{message_id}')

        self.audit_logger.log_certificate_operation(
            operation="MESSAGE_RETRIEVED",
            email=response.get('from', 'unknown'),
            success=True,
        )

        return response

    def acknowledge_message(self, message_id: str) -> Dict[str, Any]:
        """
        Acknowledge and remove message from inbox queue.

        Once acknowledged, the message is removed from the queue and
        will not appear in subsequent check_inbox() calls.

        Args:
            message_id: Message queue ID from check_inbox()

        Returns:
            Acknowledgment response

        Example:
            ```python
            messages = client.check_inbox()
            for msg in messages:
                # Process message...
                client.acknowledge_message(msg['id'])
            ```
        """
        response = self._request('DELETE', f'/inbox/{message_id}')

        self.audit_logger.log_certificate_operation(
            operation="MESSAGE_ACKNOWLEDGED",
            email=self.username,
            success=True,
            error=f"Message ID: {message_id}",
        )

        return response

    def download_attachment(
        self,
        message_id: str,
        attachment_id: str,
        output_path: Optional[str] = None,
    ) -> bytes:
        """
        Download attachment from a message.

        Args:
            message_id: Message queue ID
            attachment_id: Attachment ID from message metadata
            output_path: Optional path to save attachment

        Returns:
            Attachment content as bytes
        """
        url = self._build_url(f'/inbox/{message_id}/attachments/{attachment_id}')

        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()

        content = response.content

        # Save to file if path provided
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(content)

            self.audit_logger.log_certificate_operation(
                operation="ATTACHMENT_DOWNLOADED",
                email=self.username,
                success=True,
                error=f"Saved to {output_path}",
            )

        return content

    # =========================================================================
    # OUTBOX OPERATIONS (SENDING)
    # =========================================================================

    def send_message(
        self,
        sender: str,
        recipients: List[str],
        subject: str,
        body: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        request_delivery_status: bool = True,
        request_read_receipt: bool = False,
    ) -> Dict[str, Any]:
        """
        Send a Direct message.

        Args:
            sender: Sender Direct address (must be authorized for your account)
            recipients: List of recipient Direct addresses
            subject: Message subject
            body: Message body (plain text or HTML)
            attachments: Optional list of attachment dictionaries:
                - filename: Attachment filename
                - content_type: MIME type (e.g., 'application/pdf')
                - content: Base64-encoded content OR raw bytes
            request_delivery_status: Request delivery status notification (default: True)
            request_read_receipt: Request read receipt (default: False)

        Returns:
            Send response containing:
            - id: Outbox message ID for tracking
            - status: Initial status (typically 'queued')
            - messageId: RFC 822 Message-ID

        Example:
            ```python
            # Send simple text message
            response = client.send_message(
                sender='resflo@hixny.net',
                recipients=['test.resflo@hixny.net'],
                subject='Test Direct Message',
                body='This is a test message',
            )

            # Send with PDF attachment
            with open('report.pdf', 'rb') as f:
                pdf_content = base64.b64encode(f.read()).decode()

            response = client.send_message(
                sender='resflo@hixny.net',
                recipients=['doctor@clinic.direct'],
                subject='Patient Report',
                body='Please see attached report',
                attachments=[{
                    'filename': 'report.pdf',
                    'content_type': 'application/pdf',
                    'content': pdf_content,
                }],
            )
            ```
        """
        # Prepare message parts
        message_parts = [{
            'content': body,
            'content_type': 'text/plain',
        }]

        # Add attachments
        if attachments:
            for att in attachments:
                # Ensure content is base64-encoded
                content = att['content']
                if isinstance(content, bytes):
                    content = base64.b64encode(content).decode()

                message_parts.append({
                    'filename': att['filename'],
                    'content_type': att['content_type'],
                    'content': content,
                })

        # Build request payload
        payload = {
            'sender': sender,
            'recipients': recipients,
            'subject': subject,
            'messageParts': message_parts,
            'requestDeliveryStatus': request_delivery_status,
            'requestReadReceipt': request_read_receipt,
        }

        response = self._request('POST', '/outbox', json_data=payload)

        self.audit_logger.log_certificate_operation(
            operation="MESSAGE_SENT",
            email=sender,
            success=True,
            error=f"To: {', '.join(recipients)}",
        )

        return response

    def get_outbox_status(self, message_id: str) -> Dict[str, Any]:
        """
        Check delivery status of sent message.

        Args:
            message_id: Outbox message ID from send_message()

        Returns:
            Status dictionary containing:
            - id: Message ID
            - status: Current status (queued, sent, delivered, failed)
            - statusDetails: Human-readable status description
            - deliveryNotifications: List of delivery notifications

        Example:
            ```python
            send_response = client.send_message(...)
            message_id = send_response['id']

            # Check status later
            status = client.get_outbox_status(message_id)
            print(f"Status: {status['status']}")
            ```
        """
        response = self._request('GET', f'/outbox/{message_id}')
        return response

    # =========================================================================
    # DIRECTORY OPERATIONS
    # =========================================================================

    def search_directory(
        self,
        query: Optional[str] = None,
        direct_address: Optional[str] = None,
        npi: Optional[str] = None,
        organization: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search provider directory.

        Search by any combination of query text, Direct address, NPI, or organization.

        Args:
            query: Free-text search query (searches all fields)
            direct_address: Exact Direct address to find
            npi: National Provider Identifier
            organization: Organization name
            limit: Maximum results to return (default: 50)

        Returns:
            List of provider/organization records containing:
            - directAddress: Provider's Direct address
            - name: Provider/organization name
            - npi: National Provider Identifier (if available)
            - organization: Organization name
            - address: Physical address
            - specialties: List of specialties

        Example:
            ```python
            # Search by organization
            results = client.search_directory(organization='Mayo Clinic')

            # Search by NPI
            results = client.search_directory(npi='1234567890')

            # Find specific Direct address
            results = client.search_directory(
                direct_address='doctor@clinic.direct'
            )

            # Free-text search
            results = client.search_directory(query='cardiology new york')
            ```
        """
        params = {'limit': limit}

        if query:
            params['q'] = query
        if direct_address:
            params['directAddress'] = direct_address
        if npi:
            params['npi'] = npi
        if organization:
            params['organization'] = organization

        response = self._request('GET', '/directory', params=params)

        # Response is a list of directory entries
        entries = response if isinstance(response, list) else []

        self.audit_logger.log_certificate_operation(
            operation="DIRECTORY_SEARCH",
            email=self.username,
            success=True,
            error=f"Found {len(entries)} entries",
        )

        return entries

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def save_message_to_file(
        self,
        message_data: Dict[str, Any],
        output_dir: str = "received_messages/phimail",
    ) -> str:
        """
        Save message to file in standardized format.

        Args:
            message_data: Message dictionary from get_message()
            output_dir: Directory to save messages

        Returns:
            Path to saved message file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename
        message_id = message_data.get('messageId', 'unknown').replace('<', '').replace('>', '').replace('/', '_')
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{message_id}.json"

        file_path = output_path / filename

        # Save as JSON
        import json
        with open(file_path, 'w') as f:
            json.dump(message_data, f, indent=2)

        # Save attachments separately
        if message_data.get('attachments'):
            att_dir = output_path / 'attachments'
            att_dir.mkdir(exist_ok=True)

            for i, att in enumerate(message_data['attachments']):
                if 'id' in att:
                    # Download attachment
                    att_filename = att.get('filename', f'attachment_{i}')
                    att_path = att_dir / att_filename

                    self.download_attachment(
                        message_data['id'],
                        att['id'],
                        str(att_path),
                    )

        return str(file_path)

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on API connection.

        Returns:
            Health status dictionary

        Example:
            ```python
            client = PhiMailClient(api_base_url, username, password)
            health = client.health_check()
            print(f"Status: {health['status']}")
            ```
        """
        try:
            # Try to check inbox as health check
            self._request('GET', '/inbox', params={'limit': 1})

            return {
                'status': 'healthy',
                'api_url': self.api_base_url,
                'username': self.username,
                'ssl_verification': self.verify_ssl,
                'timestamp': datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'api_url': self.api_base_url,
                'username': self.username,
                'timestamp': datetime.utcnow().isoformat(),
            }
