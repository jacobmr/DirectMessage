#!/usr/bin/env python3
"""Test IMAP authentication with different username formats"""

import imaplib
import ssl
import os
from dotenv import load_dotenv

load_dotenv()

PASSWORD = os.getenv("POP3_PASSWORD")

# Username formats to try
USERNAME_FORMATS = [
    ("Just username", "resflo"),
    ("Full email", "resflo@hixny.net"),
    ("Domain\\User", "hixnycolo\\resflo"),
    ("DOMAIN\\User", "HIXNYCOLO\\resflo"),
    ("UPN format", "resflo@hixnycolo"),
]

print("="*60)
print("Testing IMAP Authentication on hixny.net:993")
print("="*60)

for description, username in USERNAME_FORMATS:
    print(f"\n{description}: '{username}'")
    try:
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL("hixny.net", 993, ssl_context=context)

        result = mail.login(username, PASSWORD)

        print(f"  ✅ ✅ ✅ LOGIN SUCCESS!")
        print(f"  Result: {result}")

        # List folders
        status, folders = mail.list()
        print(f"  Folders: {len(folders)} found")

        # Select INBOX
        status, data = mail.select('INBOX')
        msg_count = int(data[0])
        print(f"  📬 INBOX: {msg_count} messages")

        mail.logout()

        print(f"\n🎉 IMAP WORKING!")
        print(f"  Server: hixny.net:993")
        print(f"  Username: {username}")
        break

    except imaplib.IMAP4.error as e:
        print(f"  ❌ IMAP Error: {e}")
    except Exception as e:
        print(f"  ❌ Error: {type(e).__name__}: {str(e)[:80]}")

else:
    print(f"\n❌ No working username format found for IMAP")
    print(f"\nNote: POP3 uses 'resflo', but IMAP might need different format")
