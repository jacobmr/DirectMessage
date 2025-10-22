"""Example: Send a simple Direct message."""

import os
from dotenv import load_dotenv
from hipaa_direct import DirectMessage, DirectMessageSender

# Load environment variables
load_dotenv()


def main():
    # Create a Direct message
    message = DirectMessage(
        from_address=os.getenv("SENDER_EMAIL"),
        to_address=os.getenv("RECIPIENT_EMAIL"),
        subject="Test Direct Message",
        body="This is a test HIPAA Direct message with S/MIME encryption.",
    )

    # Initialize the sender
    sender = DirectMessageSender(
        smtp_host=os.getenv("SMTP_HOST"),
        smtp_port=int(os.getenv("SMTP_PORT", 587)),
        smtp_user=os.getenv("SMTP_USER"),
        smtp_password=os.getenv("SMTP_PASSWORD"),
        use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
    )

    # Send the message
    try:
        success = sender.send(
            message=message,
            sender_cert_path=os.getenv("SENDER_CERT_PATH"),
            sender_key_path=os.getenv("SENDER_KEY_PATH"),
            recipient_cert_path=os.getenv("RECIPIENT_CERT_PATH"),
        )
        if success:
            print(f"Message sent successfully! Message ID: {message.message_id}")
    except Exception as e:
        print(f"Failed to send message: {e}")


if __name__ == "__main__":
    main()
