#!/usr/bin/env python3
"""
Test IMAP receiver once HIXNY enables it.

Run this when HIXNY support confirms IMAP is enabled.
"""

import sys
sys.path.insert(0, 'src')

import os
from dotenv import load_dotenv
from hipaa_direct.core.imap_receiver import IMAPDirectMessageReceiver

load_dotenv()

def main():
    print("="*60)
    print("Testing IMAP Direct Message Receiver")
    print("="*60)

    # Get credentials from environment
    imap_host = os.getenv("POP3_HOST", "hixny.net")  # Same host, different protocol
    imap_user = os.getenv("POP3_USER")
    imap_password = os.getenv("POP3_PASSWORD")

    print(f"\nConnecting to: {imap_host}:993 (IMAP-SSL)")
    print(f"Username: {imap_user}")

    try:
        # Initialize IMAP receiver
        receiver = IMAPDirectMessageReceiver(
            imap_host=imap_host,
            imap_port=993,
            imap_user=imap_user,
            imap_password=imap_password,
            use_ssl=True,
        )

        # Connect
        print("\nConnecting...")
        receiver.connect()
        print("✅ Connected successfully!")

        # List folders
        print("\nListing folders...")
        folders = receiver.list_folders()
        print(f"Available folders: {folders}")

        # Check INBOX
        print("\nChecking INBOX...")
        msg_count = receiver.get_message_count("INBOX")
        print(f"📬 Messages in INBOX: {msg_count}")

        if msg_count > 0:
            print(f"\nFetching {msg_count} message(s)...")

            # Fetch unread messages only
            messages = receiver.fetch_all_messages(
                folder="INBOX",
                criteria="UNSEEN",  # Only unread messages
                mark_as_read=False,  # Don't mark as read yet
            )

            print(f"✅ Fetched {len(messages)} unread message(s)")

            for i, msg in enumerate(messages, 1):
                print(f"\n{'─'*60}")
                print(f"Message {i}/{len(messages)}")
                print(f"{'─'*60}")
                print(f"  From: {msg['from']}")
                print(f"  Subject: {msg['subject']}")
                print(f"  Date: {msg['date']}")
                print(f"  Attachments: {len(msg.get('attachments', []))}")

                # Save message
                file_path = receiver.save_message_to_file(msg, "received_messages/imap")
                print(f"  💾 Saved: {file_path}")

        receiver.disconnect()
        print("\n" + "="*60)
        print("✅ IMAP TEST SUCCESSFUL!")
        print("="*60)
        print("\nIMPA advantages over POP3:")
        print("  ✅ Messages stay on server")
        print("  ✅ Folder organization")
        print("  ✅ Mark as read/unread")
        print("  ✅ Better for multiple workers")
        print("="*60)

    except Exception as e:
        print(f"\n❌ IMAP Test Failed: {e}")
        print("\nIf you see 'Connection timeout' or 'Connection refused':")
        print("  → IMAP is not yet enabled by HIXNY")
        print("  → Continue using POP3 receiver until HIXNY enables IMAP")
        print("\nExpected errors until IMAP is enabled:")
        print("  - 'timed out'")
        print("  - 'Connection refused'")
        print("  - '[Errno 61] Connection refused'")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
