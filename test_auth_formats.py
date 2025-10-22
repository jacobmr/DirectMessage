#!/usr/bin/env python3
"""Test different authentication formats for HIXNY POP3"""

import poplib
import ssl

SENDER_EMAIL = "resflo@hixny.net"
SENDER_PASSWORD = "T1m3ZL1k3tH33se$"

# Different username formats to try
USERNAME_FORMATS = [
    "hixnycolo\\resflo",      # Domain\User (original)
    "hixnycolo/resflo",        # Domain/User
    "resflo@hixnycolo",        # User@Domain
    "resflo",                  # Just username
    "resflo@hixny.net",        # Full email
    "HIXNYCOLO\\resflo",       # Uppercase domain
    "HIXNYCOLO\\RESFLO",       # All uppercase
]

print("="*60)
print(f"Testing POP3 authentication on hixny.net:995")
print(f"Password: {SENDER_PASSWORD}")
print("="*60)

for username in USERNAME_FORMATS:
    print(f"\nTrying username: '{username}'...")
    try:
        context = ssl.create_default_context()
        mail = poplib.POP3_SSL("hixny.net", 995, timeout=10, context=context)

        mail.user(username)
        response = mail.pass_(SENDER_PASSWORD)

        print(f"  ✅ SUCCESS! Authentication worked!")
        print(f"  Response: {response}")

        # Get message count
        num_messages = len(mail.list()[1])
        print(f"  📬 Messages in mailbox: {num_messages}")

        mail.quit()

        print(f"\n🎉 FOUND WORKING FORMAT: '{username}'")
        print(f"\nNow testing with recipient account...")

        # Test recipient too
        RECIPIENT_PASSWORD = "Th3M0nST3rma$Hed"
        recipient_username = username.replace("resflo", "test.resflo")

        print(f"\nTrying recipient with: '{recipient_username}'...")
        try:
            mail2 = poplib.POP3_SSL("hixny.net", 995, timeout=10, context=context)
            mail2.user(recipient_username)
            mail2.pass_(RECIPIENT_PASSWORD)
            print(f"  ✅ Recipient authentication SUCCESS!")
            num_messages2 = len(mail2.list()[1])
            print(f"  📬 Recipient messages: {num_messages2}")
            mail2.quit()
        except Exception as e:
            print(f"  ❌ Recipient failed: {e}")

        break

    except poplib.error_proto as e:
        print(f"  ❌ Auth failed: {e}")
    except Exception as e:
        print(f"  ❌ Error: {type(e).__name__}: {e}")
