#!/usr/bin/env python3
"""
Hybrid Direct Messaging Demo

This demonstrates the unified receiver that can switch between
IMAP, POP3, and phiMail with a simple environment variable change.

Run with:
    # Use IMAP (default - recommended for HIXNY)
    export DIRECT_RECEIVER_BACKEND=imap
    PYTHONPATH=src python3 examples/hybrid_demo.py

    # Switch to phiMail (when ready)
    export DIRECT_RECEIVER_BACKEND=phimail
    PYTHONPATH=src python3 examples/hybrid_demo.py
"""

import sys
sys.path.insert(0, 'src')

import os
from dotenv import load_dotenv
from hipaa_direct.integrations.unified_receiver import (
    UnifiedDirectReceiver,
    ReceiverBackend,
)

load_dotenv()


def main():
    print("="*60)
    print("Hybrid Direct Messaging Demo")
    print("="*60)

    # Get backend from environment (defaults to IMAP)
    backend_str = os.getenv('DIRECT_RECEIVER_BACKEND', 'imap').lower()
    print(f"\n📡 Using backend: {backend_str.upper()}")

    # Create receiver - automatically uses correct backend
    receiver = UnifiedDirectReceiver.from_env()

    # Health check
    print("\n1. Health Check")
    print("-" * 60)
    health = receiver.health_check()
    print(f"Status: {health['status']}")
    print(f"Backend: {health.get('backend', 'unknown')}")

    # Check message count
    print("\n2. Check Message Count")
    print("-" * 60)
    try:
        count = receiver.get_message_count()
        print(f"📬 Messages available: {count}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Fetch messages
    print("\n3. Fetch Messages")
    print("-" * 60)
    try:
        # Fetch up to 5 messages
        messages = receiver.fetch_messages(
            limit=5,
            mark_as_read=False,  # IMAP: don't mark as read
            acknowledge=False,   # phiMail: don't remove from queue
        )

        print(f"✅ Fetched {len(messages)} message(s)")

        if messages:
            print("\nMessage summaries:")
            for i, msg in enumerate(messages, 1):
                print(f"\n  Message {i}:")
                print(f"    Backend: {msg['backend']}")
                print(f"    From: {msg['from']}")
                print(f"    Subject: {msg['subject']}")
                print(f"    Date: {msg['date']}")
                print(f"    Attachments: {len(msg['attachments'])}")

                # Save message
                file_path = receiver.save_message(msg)
                print(f"    💾 Saved: {file_path}")

    except Exception as e:
        print(f"❌ Error fetching messages: {e}")

    print("\n" + "="*60)
    print("✅ Demo completed!")
    print("="*60)
    print("\n💡 To switch backends:")
    print("   export DIRECT_RECEIVER_BACKEND=imap     # Use IMAP (HIXNY)")
    print("   export DIRECT_RECEIVER_BACKEND=phimail  # Use phiMail")
    print("   export DIRECT_RECEIVER_BACKEND=pop3     # Use POP3 (HIXNY)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
