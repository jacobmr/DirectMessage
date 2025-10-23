#!/usr/bin/env python3
"""
Demo script for phiMail Direct Messaging client.

This demonstrates how to use the phiMail REST API for sending and
receiving HIPAA Direct messages.

Setup:
    1. Set environment variables:
       export PHIMAIL_API_URL="https://sandbox.phimaildev.com:8443/rest/v1/"
       export PHIMAIL_USERNAME="your_username"
       export PHIMAIL_PASSWORD="your_password"

    2. Run:
       PYTHONPATH=src python3 examples/phimail_demo.py
"""

import sys
sys.path.insert(0, 'src')

import os
from dotenv import load_dotenv
from hipaa_direct.clients.phimail_client import PhiMailClient

load_dotenv()


def main():
    print("="*60)
    print("phiMail Direct Messaging Demo")
    print("="*60)

    # Initialize client
    client = PhiMailClient(
        api_base_url=os.getenv("PHIMAIL_API_URL", "https://sandbox.phimaildev.com:8443/rest/v1/"),
        username=os.getenv("PHIMAIL_USERNAME"),
        password=os.getenv("PHIMAIL_PASSWORD"),
    )

    # Health check
    print("\n1. Health Check")
    print("-" * 60)
    health = client.health_check()
    print(f"Status: {health['status']}")
    print(f"API URL: {health['api_url']}")

    # Check inbox
    print("\n2. Check Inbox")
    print("-" * 60)
    messages = client.check_inbox(limit=10)
    print(f"📬 Messages in inbox: {len(messages)}")

    if messages:
        print("\nMessage summaries:")
        for i, msg in enumerate(messages, 1):
            print(f"\n  Message {i}:")
            print(f"    ID: {msg['id']}")
            print(f"    From: {msg.get('from', 'N/A')}")
            print(f"    Subject: {msg.get('subject', 'N/A')}")
            print(f"    Date: {msg.get('receivedDate', 'N/A')}")
            print(f"    Size: {msg.get('size', 0)} bytes")
            print(f"    Attachments: {msg.get('hasAttachments', False)}")

        # Get first message in detail
        print("\n3. Retrieve Full Message")
        print("-" * 60)
        first_msg = client.get_message(messages[0]['id'])
        print(f"Message ID: {first_msg.get('messageId', 'N/A')}")
        print(f"Body preview: {first_msg.get('body', '')[:200]}...")

        # Save message
        print("\n4. Save Message to File")
        print("-" * 60)
        file_path = client.save_message_to_file(first_msg)
        print(f"💾 Saved to: {file_path}")

        # Acknowledge message
        print("\n5. Acknowledge Message")
        print("-" * 60)
        response = client.acknowledge_message(messages[0]['id'])
        print(f"✅ Message acknowledged and removed from queue")

    # Search directory
    print("\n6. Search Provider Directory")
    print("-" * 60)
    # Example search (customize as needed)
    results = client.search_directory(query="test", limit=5)
    print(f"Found {len(results)} directory entries")

    if results:
        for i, entry in enumerate(results[:3], 1):
            print(f"\n  Entry {i}:")
            print(f"    Direct Address: {entry.get('directAddress', 'N/A')}")
            print(f"    Name: {entry.get('name', 'N/A')}")
            print(f"    Organization: {entry.get('organization', 'N/A')}")

    # Send a test message (commented out - uncomment to test sending)
    # print("\n7. Send Test Message")
    # print("-" * 60)
    # send_response = client.send_message(
    #     sender="your-sender@example.direct",
    #     recipients=["recipient@example.direct"],
    #     subject="Test Direct Message",
    #     body="This is a test message from phiMail client",
    # )
    # print(f"✅ Message sent!")
    # print(f"   Message ID: {send_response['id']}")
    # print(f"   Status: {send_response['status']}")

    print("\n" + "="*60)
    print("✅ Demo completed successfully!")
    print("="*60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
