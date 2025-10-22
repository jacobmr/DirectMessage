"""Certificate and key management utilities."""

from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


class CertificateManager:
    """Manages X.509 certificates for Direct messaging."""

    def __init__(self, cert_dir: str = "certs"):
        """
        Initialize the certificate manager.

        Args:
            cert_dir: Directory to store certificates
        """
        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        self.private_dir = self.cert_dir / "private"
        self.private_dir.mkdir(parents=True, exist_ok=True)

    def generate_self_signed_cert(
        self,
        email: str,
        common_name: Optional[str] = None,
        organization: Optional[str] = None,
        valid_days: int = 365,
        key_size: int = 2048,
    ) -> Tuple[str, str]:
        """
        Generate a self-signed certificate for testing.

        Args:
            email: Email address for the certificate
            common_name: Common name (defaults to email)
            organization: Organization name
            valid_days: Certificate validity period in days
            key_size: RSA key size in bits

        Returns:
            Tuple of (cert_path, key_path)
        """
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=key_size, backend=default_backend()
        )

        # Build certificate subject
        subject_attrs = [
            x509.NameAttribute(NameOID.EMAIL_ADDRESS, email),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name or email),
        ]
        if organization:
            subject_attrs.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization))

        subject = issuer = x509.Name(subject_attrs)

        # Create certificate
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=valid_days))
            .add_extension(
                x509.SubjectAlternativeName([x509.RFC822Name(email)]),
                critical=False,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(private_key, hashes.SHA256(), default_backend())
        )

        # Save certificate
        email_safe = email.replace("@", "_at_").replace(".", "_")
        cert_path = self.cert_dir / f"{email_safe}.crt"
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        # Save private key
        key_path = self.private_dir / f"{email_safe}.key"
        with open(key_path, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        return str(cert_path), str(key_path)

    def load_certificate(self, cert_path: str) -> x509.Certificate:
        """
        Load a certificate from file.

        Args:
            cert_path: Path to certificate file

        Returns:
            X.509 certificate object
        """
        with open(cert_path, "rb") as f:
            return x509.load_pem_x509_certificate(f.read(), default_backend())

    def verify_certificate(self, cert_path: str) -> bool:
        """
        Verify a certificate is valid and not expired.

        Args:
            cert_path: Path to certificate file

        Returns:
            True if valid and not expired
        """
        cert = self.load_certificate(cert_path)
        now = datetime.utcnow()

        # Check expiration
        if now < cert.not_valid_before or now > cert.not_valid_after:
            return False

        return True

    def get_certificate_info(self, cert_path: str) -> dict:
        """
        Get information about a certificate.

        Args:
            cert_path: Path to certificate file

        Returns:
            Dictionary with certificate information
        """
        cert = self.load_certificate(cert_path)

        subject = cert.subject
        info = {
            "subject": subject.rfc4514_string(),
            "issuer": cert.issuer.rfc4514_string(),
            "serial_number": cert.serial_number,
            "not_valid_before": cert.not_valid_before.isoformat(),
            "not_valid_after": cert.not_valid_after.isoformat(),
            "is_valid": self.verify_certificate(cert_path),
        }

        # Extract email if present
        try:
            email_attr = subject.get_attributes_for_oid(NameOID.EMAIL_ADDRESS)
            if email_attr:
                info["email"] = email_attr[0].value
        except Exception:
            pass

        return info
