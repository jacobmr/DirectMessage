"""Example: Receive Direct messages via POP3."""

import os
from dotenv import load_dotenv
from hipaa_direct.core.receiver import DirectMessageReceiver
import json

# Load environment variables
load_dotenv()


def main():
    print("="*60)
    print("HIPAA Direct Message Receiver")
    print("="*60)

    # Initialize receiver
    receiver = DirectMessageReceiver(
        pop3_host=os.getenv("POP3_HOST"),
        pop3_port=int(os.getenv("POP3_PORT", 995)),
        pop3_user=os.getenv("POP3_USER"),
        pop3_password=os.getenv("POP3_PASSWORD"),
        use_ssl=os.getenv("POP3_USE_SSL", "true").lower() == "true",
    )

    print(f"\nConnecting to: {receiver.pop3_host}:{receiver.pop3_port}")
    print(f"Username: {receiver.pop3_user}")

    # Check message count
    try:
        msg_count = receiver.get_message_count()
        print(f"\n📬 Messages in mailbox: {msg_count}")

        if msg_count == 0:
            print("\nNo messages to fetch.")
            print("\nTo test:")
            print("1. Send a test email to resflo@hixny.net")
            print("2. Run this script again")
            return

        # Fetch all messages
        print(f"\nFetching {msg_count} message(s)...")
        messages = receiver.fetch_all_messages(
            delete_after_fetch=False,  # Set True to delete after fetching
            decrypt=False,  # S/MIME decryption not yet implemented
        )

        print(f"\n✅ Successfully fetched {len(messages)} message(s)")

        # Display message details
        for i, msg in enumerate(messages, 1):
            print(f"\n" + "="*60)
            print(f"Message {i}/{len(messages)}")
            print("="*60)
            print(f"  Message ID: {msg.get('message_id')}")
            print(f"  From: {msg.get('from')}")
            print(f"  To: {msg.get('to')}")
            print(f"  Subject: {msg.get('subject')}")
            print(f"  Date: {msg.get('date')}")
            print(f"  Size: {msg.get('size')} bytes")
            print(f"  Encrypted: {msg.get('is_encrypted')}")
            print(f"  Attachments: {len(msg.get('attachments', []))}")

            if msg.get('body'):
                print(f"\n  Body Preview:")
                body_preview = msg.get('body', '')[:200]
                print(f"  {body_preview}...")

            # Save message to file
            file_path = receiver.save_message_to_file(msg)
            print(f"\n  💾 Saved to: {file_path}")

            # Show attachment details
            if msg.get('attachments'):
                print(f"\n  📎 Attachments:")
                for att in msg['attachments']:
                    print(f"    - {att['filename']} ({att['content_type']}, {att['size']} bytes)")

        print(f"\n" + "="*60)
        print(f"All messages saved to: received_messages/")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
