"""HIPAA-compliant audit logging."""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


class AuditLogger:
    """HIPAA-compliant audit logger for Direct messaging operations."""

    def __init__(self, log_dir: str = "logs", log_level: int = logging.INFO):
        """
        Initialize the audit logger.

        Args:
            log_dir: Directory to store audit logs
            log_level: Logging level
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Set up logger
        self.logger = logging.getLogger("hipaa_direct.audit")
        self.logger.setLevel(log_level)

        # File handler for audit logs
        log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)

        # JSON formatter for structured logging
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        )
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def _log_event(self, event_type: str, **kwargs):
        """Log an audit event."""
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }
        self.logger.info(json.dumps(event))

    def log_encryption(self, message_id: str, from_address: str, to_address: str):
        """Log message encryption event."""
        self._log_event(
            "MESSAGE_ENCRYPTED",
            message_id=message_id,
            from_address=from_address,
            to_address=to_address,
        )

    def log_send(
        self,
        message_id: str,
        from_address: str,
        to_address: str,
        success: bool,
        error: Optional[str] = None,
    ):
        """Log message send event."""
        event_data = {
            "message_id": message_id,
            "from_address": from_address,
            "to_address": to_address,
            "success": success,
        }
        if error:
            event_data["error"] = error

        self._log_event("MESSAGE_SENT", **event_data)

    def log_certificate_operation(
        self, operation: str, email: str, success: bool, error: Optional[str] = None
    ):
        """Log certificate operation."""
        event_data = {
            "operation": operation,
            "email": email,
            "success": success,
        }
        if error:
            event_data["error"] = error

        self._log_event("CERTIFICATE_OPERATION", **event_data)
