"""Example: Send a Direct message with an attachment."""

import os
from dotenv import load_dotenv
from hipaa_direct import DirectMessage, DirectMessageSender

# Load environment variables
load_dotenv()


def main():
    # Read an example attachment (e.g., a medical record PDF)
    # For this example, we'll create a simple text file
    attachment_content = b"Sample medical record content"

    # Create a Direct message with attachment
    message = DirectMessage(
        from_address=os.getenv("SENDER_EMAIL"),
        to_address=os.getenv("RECIPIENT_EMAIL"),
        subject="Medical Record Transfer",
        body="Please find attached the patient medical record.",
        attachments=[
            {
                "filename": "patient_record.txt",
                "content": attachment_content,
                "content_type": "text/plain",
            }
        ],
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
            print(f"Message with attachment sent! Message ID: {message.message_id}")
    except Exception as e:
        print(f"Failed to send message: {e}")


if __name__ == "__main__":
    main()
