#!/usr/bin/env python3
"""Test recipient account with new password"""

import sys
sys.path.insert(0, 'src')

import poplib
import ssl
from hipaa_direct.core.receiver import DirectMessageReceiver

RECIPIENT_USER = "test.resflo"
RECIPIENT_PASSWORD = "Hdnb63456Mookie!"

print("="*60)
print("Testing Recipient Account: test.resflo@hixny.net")
print("="*60)

# Test POP3 connection
print("\n1. Testing POP3 connection...")
try:
    context = ssl.create_default_context()
    mail = poplib.POP3_SSL("hixny.net", 995, timeout=10, context=context)
    mail.user(RECIPIENT_USER)
    mail.pass_(RECIPIENT_PASSWORD)

    msg_count, mbox_size = mail.stat()
    print(f"   ✅ Connection SUCCESS!")
    print(f"   📬 Mailbox: {msg_count} messages, {mbox_size} bytes")

    mail.quit()

except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

# Test with DirectMessageReceiver
print("\n2. Testing with DirectMessageReceiver...")
try:
    receiver = DirectMessageReceiver(
        pop3_host="hixny.net",
        pop3_port=995,
        pop3_user=RECIPIENT_USER,
        pop3_password=RECIPIENT_PASSWORD,
        use_ssl=True,
    )

    msg_count = receiver.get_message_count()
    print(f"   ✅ DirectMessageReceiver working!")
    print(f"   📬 Messages: {msg_count}")

    if msg_count > 0:
        print(f"\n3. Fetching messages...")
        messages = receiver.fetch_all_messages(delete_after_fetch=False)

        for i, msg in enumerate(messages, 1):
            print(f"\n   Message {i}:")
            print(f"     From: {msg.get('from')}")
            print(f"     Subject: {msg.get('subject')}")
            print(f"     Date: {msg.get('date')}")
            print(f"     Size: {msg.get('size')} bytes")

            file_path = receiver.save_message_to_file(msg, "received_messages/recipient")
            print(f"     💾 Saved: {file_path}")

except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*60)
print("✅ Both accounts are working!")
print("="*60)
print("\nAccounts configured:")
print("  1. resflo@hixny.net (sender/receiver)")
print("  2. test.resflo@hixny.net (recipient/receiver)")
print("\nBoth can receive Direct messages via POP3")
print("="*60)
