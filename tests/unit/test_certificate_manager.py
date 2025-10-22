"""Unit tests for CertificateManager class."""

import pytest
import tempfile
import shutil
from pathlib import Path
from hipaa_direct.certs.manager import CertificateManager


@pytest.fixture
def temp_cert_dir():
    """Create a temporary directory for certificates."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_certificate_manager_init(temp_cert_dir):
    """Test CertificateManager initialization."""
    manager = CertificateManager(cert_dir=temp_cert_dir)

    assert manager.cert_dir.exists()
    assert manager.private_dir.exists()


def test_generate_self_signed_cert(temp_cert_dir):
    """Test self-signed certificate generation."""
    manager = CertificateManager(cert_dir=temp_cert_dir)

    cert_path, key_path = manager.generate_self_signed_cert(
        email="test@example.com",
        organization="Test Org",
        valid_days=365,
    )

    assert Path(cert_path).exists()
    assert Path(key_path).exists()


def test_load_certificate(temp_cert_dir):
    """Test certificate loading."""
    manager = CertificateManager(cert_dir=temp_cert_dir)

    cert_path, _ = manager.generate_self_signed_cert(email="test@example.com")

    cert = manager.load_certificate(cert_path)

    assert cert is not None


def test_verify_certificate_valid(temp_cert_dir):
    """Test verification of valid certificate."""
    manager = CertificateManager(cert_dir=temp_cert_dir)

    cert_path, _ = manager.generate_self_signed_cert(
        email="test@example.com", valid_days=365
    )

    assert manager.verify_certificate(cert_path) is True


def test_get_certificate_info(temp_cert_dir):
    """Test getting certificate information."""
    manager = CertificateManager(cert_dir=temp_cert_dir)

    cert_path, _ = manager.generate_self_signed_cert(
        email="test@example.com", organization="Test Org"
    )

    info = manager.get_certificate_info(cert_path)

    assert "subject" in info
    assert "issuer" in info
    assert "serial_number" in info
    assert "not_valid_before" in info
    assert "not_valid_after" in info
    assert "is_valid" in info
    assert info["is_valid"] is True
    assert info["email"] == "test@example.com"
