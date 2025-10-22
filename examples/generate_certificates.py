"""Example: Generate self-signed certificates for testing."""

from hipaa_direct import CertificateManager


def main():
    # Initialize certificate manager
    cert_manager = CertificateManager(cert_dir="certs")

    # Generate certificate for sender
    print("Generating sender certificate...")
    sender_cert, sender_key = cert_manager.generate_self_signed_cert(
        email="sender@direct.example.com",
        organization="Example Healthcare Organization",
        valid_days=365,
    )
    print(f"  Certificate: {sender_cert}")
    print(f"  Private Key: {sender_key}")

    # Generate certificate for recipient
    print("\nGenerating recipient certificate...")
    recipient_cert, recipient_key = cert_manager.generate_self_signed_cert(
        email="recipient@direct.example.com",
        organization="Example Medical Practice",
        valid_days=365,
    )
    print(f"  Certificate: {recipient_cert}")
    print(f"  Private Key: {recipient_key}")

    # Display certificate information
    print("\nSender Certificate Info:")
    sender_info = cert_manager.get_certificate_info(sender_cert)
    for key, value in sender_info.items():
        print(f"  {key}: {value}")

    print("\nRecipient Certificate Info:")
    recipient_info = cert_manager.get_certificate_info(recipient_cert)
    for key, value in recipient_info.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
