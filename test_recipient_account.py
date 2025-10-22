#!/usr/bin/env python3
"""Test the recipient account (test.resflo@hixny.net)"""

import poplib
import ssl
import time

RECIPIENT_EMAIL = "test.resflo@hixny.net"
RECIPIENT_PASSWORD = "Th3M0nST3rma$Hed"

# Username format variants for test.resflo
USERNAME_FORMATS = [
    ("Full email", "test.resflo@hixny.net"),
    ("Username only", "test.resflo"),
    ("Domain\\User", "hixnycolo\\test.resflo"),
    ("DOMAIN\\User", "HIXNYCOLO\\test.resflo"),
    ("Domain/User", "hixnycolo/test.resflo"),
    ("UPN format", "test.resflo@hixnycolo"),
    ("hixny\\user", "hixny\\test.resflo"),
]

print("="*60)
print(f"Testing RECIPIENT account on hixny.net:995")
print(f"Email: {RECIPIENT_EMAIL}")
print(f"Testing {len(USERNAME_FORMATS)} formats")
print("="*60)

context = ssl.create_default_context()

for i, (description, username) in enumerate(USERNAME_FORMATS, 1):
    print(f"\n[{i}/{len(USERNAME_FORMATS)}] {description}")
    print(f"  Username: '{username}'")

    try:
        mail = poplib.POP3_SSL("hixny.net", 995, timeout=10, context=context)

        user_response = mail.user(username)
        print(f"  USER: {user_response}")

        pass_response = mail.pass_(RECIPIENT_PASSWORD)

        print(f"  ✅ ✅ ✅ AUTHENTICATION SUCCESS!")
        print(f"  PASS: {pass_response}")

        msg_count, mbox_size = mail.stat()
        print(f"  📬 Mailbox: {msg_count} messages, {mbox_size} bytes")

        mail.quit()

        print(f"\n🎉 FOUND WORKING FORMAT!")
        print(f"  Username: '{username}'")
        print(f"  Server: hixny.net:995")

        break

    except poplib.error_proto as e:
        print(f"  ❌ Auth error: {e}")
        if "locked" in str(e).lower():
            print(f"  ⚠️  Account appears locked!")
            break

    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:80]}")

    if i < len(USERNAME_FORMATS):
        time.sleep(3)

else:
    print(f"\n❌ Recipient account also failed")
    print(f"Both accounts appear to have authentication issues")
    print(f"Likely need HIXNY support intervention")
