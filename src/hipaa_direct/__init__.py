"""
HIPAA Direct Messaging Framework

A Python framework for sending HIPAA-compliant Direct messages with S/MIME encryption.
"""

__version__ = "0.1.0"

from hipaa_direct.core.message import DirectMessage
from hipaa_direct.core.sender import DirectMessageSender
from hipaa_direct.certs.manager import CertificateManager

__all__ = ["DirectMessage", "DirectMessageSender", "CertificateManager"]
