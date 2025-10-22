"""Unit tests for DirectMessage class."""

import pytest
from hipaa_direct.core.message import DirectMessage


def test_message_creation():
    """Test basic message creation."""
    message = DirectMessage(
        from_address="sender@example.com",
        to_address="recipient@example.com",
        subject="Test Subject",
        body="Test body content",
    )

    assert message.from_address == "sender@example.com"
    assert message.to_address == "recipient@example.com"
    assert message.subject == "Test Subject"
    assert message.body == "Test body content"
    assert message.message_id is not None


def test_message_validation_valid():
    """Test validation of valid message."""
    message = DirectMessage(
        from_address="sender@example.com",
        to_address="recipient@example.com",
        subject="Test",
        body="Body",
    )

    assert message.validate() is True


def test_message_validation_invalid_from():
    """Test validation fails with invalid from address."""
    message = DirectMessage(
        from_address="invalid",
        to_address="recipient@example.com",
        subject="Test",
        body="Body",
    )

    with pytest.raises(ValueError, match="Invalid from_address"):
        message.validate()


def test_message_validation_invalid_to():
    """Test validation fails with invalid to address."""
    message = DirectMessage(
        from_address="sender@example.com",
        to_address="invalid",
        subject="Test",
        body="Body",
    )

    with pytest.raises(ValueError, match="Invalid to_address"):
        message.validate()


def test_message_validation_missing_subject():
    """Test validation fails with missing subject."""
    message = DirectMessage(
        from_address="sender@example.com",
        to_address="recipient@example.com",
        subject="",
        body="Body",
    )

    with pytest.raises(ValueError, match="Subject is required"):
        message.validate()


def test_message_validation_missing_body():
    """Test validation fails with missing body."""
    message = DirectMessage(
        from_address="sender@example.com",
        to_address="recipient@example.com",
        subject="Test",
        body="",
    )

    with pytest.raises(ValueError, match="Message body is required"):
        message.validate()


def test_message_with_attachments():
    """Test message creation with attachments."""
    attachments = [
        {
            "filename": "test.txt",
            "content": b"test content",
            "content_type": "text/plain",
        }
    ]

    message = DirectMessage(
        from_address="sender@example.com",
        to_address="recipient@example.com",
        subject="Test",
        body="Body",
        attachments=attachments,
    )

    assert len(message.attachments) == 1
    assert message.attachments[0]["filename"] == "test.txt"


def test_message_to_mime():
    """Test MIME conversion."""
    message = DirectMessage(
        from_address="sender@example.com",
        to_address="recipient@example.com",
        subject="Test Subject",
        body="Test body",
    )

    mime = message.to_mime()

    assert mime["From"] == "sender@example.com"
    assert mime["To"] == "recipient@example.com"
    assert mime["Subject"] == "Test Subject"
    assert mime["Message-ID"] is not None
