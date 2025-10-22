#!/usr/bin/env python3
"""Test with new password after web portal reset"""

import poplib
import imaplib
import ssl

SENDER_EMAIL = "resflo@hixny.net"
NEW_PASSWORD = "Hdnb63456Mookie!"

# Username format variants
USERNAME_FORMATS = [
    ("Full email", "resflo@hixny.net"),
    ("Username only", "resflo"),
    ("Domain\\User", "hixnycolo\\resflo"),
    ("DOMAIN\\User", "HIXNYCOLO\\resflo"),
    ("UPN format", "resflo@hixnycolo"),
]

print("="*60)
print(f"Testing with NEW PASSWORD: {NEW_PASSWORD}")
print(f"Account: {SENDER_EMAIL}")
print("="*60)

# Try POP3 first
print("\n### Testing POP3 (Port 995) ###")
context = ssl.create_default_context()

for description, username in USERNAME_FORMATS:
    print(f"\n{description}: '{username}'")
    try:
        mail = poplib.POP3_SSL("hixny.net", 995, timeout=10, context=context)
        mail.user(username)
        response = mail.pass_(NEW_PASSWORD)

        print(f"  ✅ ✅ ✅ POP3 SUCCESS!")
        print(f"  Response: {response}")

        msg_count, mbox_size = mail.stat()
        print(f"  📬 {msg_count} messages, {mbox_size} bytes")

        mail.quit()

        print(f"\n🎉 POP3 WORKING!")
        print(f"  Server: hixny.net:995")
        print(f"  Username: {username}")

        POP3_USERNAME = username
        break

    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:80]}")

# Try IMAP
print("\n### Testing IMAP (Port 993) ###")

for description, username in USERNAME_FORMATS:
    print(f"\n{description}: '{username}'")
    try:
        mail = imaplib.IMAP4_SSL("hixny.net", 993, timeout=10)
        response = mail.login(username, NEW_PASSWORD)

        print(f"  ✅ ✅ ✅ IMAP SUCCESS!")
        print(f"  Response: {response}")

        # List mailboxes
        status, folders = mail.list()
        print(f"  📁 {len(folders)} folders")

        # Select inbox
        mail.select('INBOX')
        status, messages = mail.search(None, 'ALL')
        msg_count = len(messages[0].split())
        print(f"  📧 {msg_count} messages in INBOX")

        mail.logout()

        print(f"\n🎉 IMAP WORKING!")
        print(f"  Server: hixny.net:993")
        print(f"  Username: {username}")

        IMAP_USERNAME = username
        break

    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:80]}")

# Try SMTP too
print("\n### Testing SMTP (Ports 587, 465) ###")

import smtplib

for port in [587, 465]:
    print(f"\nTrying port {port}...")
    for description, username in USERNAME_FORMATS[:3]:  # Just try top 3
        print(f"  {description}: '{username}'")
        try:
            if port == 465:
                server = smtplib.SMTP_SSL("hixny.net", port, timeout=10)
            else:
                server = smtplib.SMTP("hixny.net", port, timeout=10)
                server.starttls()

            server.login(username, NEW_PASSWORD)
            print(f"    ✅ SMTP {port} SUCCESS with {username}!")
            server.quit()
            break

        except Exception as e:
            print(f"    ❌ {type(e).__name__}")

print("\n" + "="*60)
print("TESTING COMPLETE")
print("="*60)
