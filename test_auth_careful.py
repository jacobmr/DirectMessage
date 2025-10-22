#!/usr/bin/env python3
"""Test authentication formats carefully with delays to avoid lockout"""

import poplib
import ssl
import time

SENDER_EMAIL = "resflo@hixny.net"
SENDER_PASSWORD = "T1m3ZL1k3tH33se$"

# More username format variants
USERNAME_FORMATS = [
    # Simple formats
    ("Full email", "resflo@hixny.net"),
    ("Username only", "resflo"),

    # Domain formats
    ("Domain\\User (backslash)", "hixnycolo\\resflo"),
    ("DOMAIN\\User (uppercase domain)", "HIXNYCOLO\\resflo"),
    ("Domain/User (forward slash)", "hixnycolo/resflo"),
    ("DOMAIN/User (uppercase)", "HIXNYCOLO/resflo"),

    # UPN formats (common for Exchange)
    ("UPN format", "resflo@hixnycolo"),
    ("UPN uppercase domain", "resflo@HIXNYCOLO"),

    # With domain prefix
    ("hixny\\user", "hixny\\resflo"),
    ("HIXNY\\user", "HIXNY\\resflo"),

    # Exchange Online style
    ("Username@domain.com", "resflo@hixnycolo.com"),

    # Just domain prefix variations
    ("domain.username", "hixnycolo.resflo"),
    ("DOMAIN.username", "HIXNYCOLO.resflo"),
]

print("="*60)
print(f"Testing POP3 authentication on hixny.net:995")
print(f"Email: {SENDER_EMAIL}")
print(f"Testing {len(USERNAME_FORMATS)} different username formats")
print(f"⏱️  Adding 3-second delay between attempts to avoid lockout")
print("="*60)

context = ssl.create_default_context()

for i, (description, username) in enumerate(USERNAME_FORMATS, 1):
    print(f"\n[{i}/{len(USERNAME_FORMATS)}] {description}")
    print(f"  Username: '{username}'")

    try:
        mail = poplib.POP3_SSL("hixny.net", 995, timeout=10, context=context)

        # Send USER command
        user_response = mail.user(username)
        print(f"  USER response: {user_response}")

        # Send PASS command
        pass_response = mail.pass_(SENDER_PASSWORD)

        print(f"  ✅ ✅ ✅ SUCCESS! Authentication worked!")
        print(f"  PASS response: {pass_response}")

        # Get stats
        msg_count, mbox_size = mail.stat()
        print(f"  📬 Mailbox stats: {msg_count} messages, {mbox_size} bytes")

        # List messages
        num_messages = len(mail.list()[1])
        print(f"  📧 Messages: {num_messages}")

        mail.quit()

        print(f"\n🎉 🎉 🎉 FOUND WORKING FORMAT!")
        print(f"  Description: {description}")
        print(f"  Username: '{username}'")
        print(f"  Server: hixny.net:995 (POP3-SSL)")

        # Now test recipient account
        print(f"\n" + "="*60)
        print("Testing RECIPIENT account with same format...")
        print("="*60)

        RECIPIENT_EMAIL = "test.resflo@hixny.net"
        RECIPIENT_PASSWORD = "Th3M0nST3rma$Hed"

        # Derive recipient username from working sender format
        if "@" in username:
            recipient_username = username.replace("resflo", "test.resflo")
        elif "\\" in username or "/" in username:
            separator = "\\" if "\\" in username else "/"
            parts = username.split(separator)
            parts[-1] = "test.resflo"
            recipient_username = separator.join(parts)
        elif "." in username:
            recipient_username = username.replace("resflo", "test.resflo")
        else:
            recipient_username = "test.resflo"

        print(f"Recipient username: '{recipient_username}'")
        time.sleep(3)  # Delay before trying recipient

        try:
            mail2 = poplib.POP3_SSL("hixny.net", 995, timeout=10, context=context)
            mail2.user(recipient_username)
            mail2.pass_(RECIPIENT_PASSWORD)

            msg_count2, mbox_size2 = mail2.stat()
            print(f"  ✅ Recipient auth SUCCESS!")
            print(f"  📬 Recipient mailbox: {msg_count2} messages, {mbox_size2} bytes")

            mail2.quit()

            print(f"\n✅ ✅ Both accounts working!")

        except Exception as e:
            print(f"  ⚠️  Recipient failed: {e}")
            print(f"  (But sender works!)")

        print(f"\n" + "="*60)
        print("SAVE THESE SETTINGS:")
        print(f"  Server: hixny.net")
        print(f"  Port: 995 (POP3-SSL)")
        print(f"  Sender Username: {username}")
        print(f"  Recipient Username: {recipient_username}")
        print("="*60)

        break

    except poplib.error_proto as e:
        error_msg = str(e)
        print(f"  ❌ Auth error: {error_msg}")
        if "locked" in error_msg.lower() or "disabled" in error_msg.lower():
            print(f"  ⚠️  WARNING: Account may be locked!")
            print(f"  Consider waiting before more attempts")
            break

    except Exception as e:
        print(f"  ❌ Error: {type(e).__name__}: {str(e)[:100]}")

    # Wait between attempts to avoid lockout
    if i < len(USERNAME_FORMATS):
        print(f"  ⏱️  Waiting 3 seconds before next attempt...")
        time.sleep(3)

else:
    print(f"\n❌ No working username format found")
    print(f"\nPossible issues:")
    print(f"  1. Account may be locked due to previous failed attempts")
    print(f"  2. Password may need to be changed on first login")
    print(f"  3. Account may not be activated yet")
    print(f"  4. Credentials may be incorrect")
    print(f"\nRecommendation: Contact HIXNY support to:")
    print(f"  - Verify account is active and not locked")
    print(f"  - Confirm correct username format")
    print(f"  - Check if password reset is needed")
