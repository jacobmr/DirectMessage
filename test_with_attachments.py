#!/usr/bin/env python3
"""Test receiving messages with PDF attachments from both accounts"""

import sys
sys.path.insert(0, 'src')

from hipaa_direct.core.receiver import DirectMessageReceiver
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

def test_account(account_name, pop3_user, pop3_password):
    """Test receiving messages from an account."""
    print(f"\n{'='*60}")
    print(f"Testing Account: {account_name}")
    print(f"{'='*60}")

    receiver = DirectMessageReceiver(
        pop3_host="hixny.net",
        pop3_port=995,
        pop3_user=pop3_user,
        pop3_password=pop3_password,
        use_ssl=True,
    )

    # Get message count
    msg_count = receiver.get_message_count()
    print(f"\n📬 Messages in mailbox: {msg_count}")

    if msg_count == 0:
        print("   No messages to fetch.")
        return

    # Fetch all messages
    print(f"\nFetching {msg_count} message(s)...")
    messages = receiver.fetch_all_messages(delete_after_fetch=False)

    print(f"✅ Fetched {len(messages)} message(s)\n")

    # Process each message
    for i, msg in enumerate(messages, 1):
        print(f"\n{'─'*60}")
        print(f"Message {i}/{len(messages)}")
        print(f"{'─'*60}")
        print(f"  From: {msg.get('from')}")
        print(f"  To: {msg.get('to')}")
        print(f"  Subject: {msg.get('subject')}")
        print(f"  Date: {msg.get('date')}")
        print(f"  Size: {msg.get('size'):,} bytes")
        print(f"  Encrypted: {msg.get('is_encrypted')}")

        # Check for attachments
        attachments = msg.get('attachments', [])
        print(f"  Attachments: {len(attachments)}")

        if attachments:
            print(f"\n  📎 Attachment Details:")
            for j, att in enumerate(attachments, 1):
                print(f"     {j}. Filename: {att['filename']}")
                print(f"        Type: {att['content_type']}")
                print(f"        Size: {att['size']:,} bytes")

                # Save PDF attachments
                if att['content_type'] == 'application/pdf' or att['filename'].endswith('.pdf'):
                    output_dir = Path("received_messages") / "attachments"
                    output_dir.mkdir(parents=True, exist_ok=True)

                    pdf_path = output_dir / att['filename']
                    with open(pdf_path, 'wb') as f:
                        f.write(att['content'])

                    print(f"        💾 Saved PDF: {pdf_path}")
                    print(f"        ✅ PDF extraction successful!")

        # Show body preview
        body = msg.get('body', '')
        if body:
            preview = body[:150].replace('\n', ' ')
            print(f"\n  Body Preview: {preview}...")

        # Save message
        save_dir = f"received_messages/{pop3_user}"
        file_path = receiver.save_message_to_file(msg, save_dir)
        print(f"\n  💾 Message saved: {file_path}")

    return messages


def main():
    print("="*60)
    print("HIPAA Direct Message Test - With Attachments")
    print("="*60)

    # Test Account 1
    account1_messages = test_account(
        "resflo@hixny.net",
        os.getenv("POP3_USER"),
        os.getenv("POP3_PASSWORD")
    )

    # Test Account 2
    account2_messages = test_account(
        "test.resflo@hixny.net",
        os.getenv("RECIPIENT_POP3_USER"),
        os.getenv("RECIPIENT_POP3_PASSWORD")
    )

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    total_messages = len(account1_messages or []) + len(account2_messages or [])
    total_attachments = sum(len(msg.get('attachments', [])) for msg in (account1_messages or []) + (account2_messages or []))
    total_pdfs = sum(
        1 for msg in (account1_messages or []) + (account2_messages or [])
        for att in msg.get('attachments', [])
        if 'pdf' in att['content_type'].lower() or att['filename'].endswith('.pdf')
    )

    print(f"Total Messages: {total_messages}")
    print(f"Total Attachments: {total_attachments}")
    print(f"Total PDFs: {total_pdfs}")
    print(f"\nAll messages and attachments saved to: received_messages/")
    print(f"PDF attachments saved to: received_messages/attachments/")
    print("="*60)


if __name__ == "__main__":
    main()
