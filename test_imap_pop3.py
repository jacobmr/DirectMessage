#!/usr/bin/env python3
"""Test IMAP and POP3 connections for HIXNY"""

import imaplib
import poplib
import ssl

# Credentials
SENDER_EMAIL = "resflo@hixny.net"
SENDER_USER = "hixnycolo\\resflo"
SENDER_PASSWORD = "T1m3ZL1k3tH33se$"

RECIPIENT_EMAIL = "test.resflo@hixny.net"
RECIPIENT_USER = "hixnycolo\\test.resflo"
RECIPIENT_PASSWORD = "Th3M0nST3rma$Hed"

HOSTS = ["direct.hixny.net", "mail.hixny.net", "hixny.net"]

print("="*60)
print("Testing IMAP (Port 993) for RECEIVING messages")
print("="*60)

for host in HOSTS:
    print(f"\nTrying {host}:993 (IMAP SSL)...")
    try:
        mail = imaplib.IMAP4_SSL(host, 993, timeout=10)
        print(f"  ✅ Connected to {host}")

        # Try to login with sender credentials
        print(f"  Logging in as {SENDER_USER}...")
        mail.login(SENDER_USER, SENDER_PASSWORD)
        print(f"  ✅ LOGIN SUCCESS for {SENDER_EMAIL}")

        # List mailboxes
        status, folders = mail.list()
        print(f"  Mailboxes: {len(folders)} found")

        mail.logout()
        print(f"\n🎉 IMAP WORKS on {host}:993")
        break

    except Exception as e:
        print(f"  ❌ Error: {type(e).__name__}: {str(e)[:100]}")

print("\n" + "="*60)
print("Testing POP3 (Port 995) for RECEIVING messages")
print("="*60)

for host in HOSTS:
    print(f"\nTrying {host}:995 (POP3 SSL)...")
    try:
        context = ssl.create_default_context()
        mail = poplib.POP3_SSL(host, 995, timeout=10, context=context)
        print(f"  ✅ Connected to {host}")

        # Try to login with sender credentials
        print(f"  Logging in as {SENDER_USER}...")
        mail.user(SENDER_USER)
        mail.pass_(SENDER_PASSWORD)
        print(f"  ✅ LOGIN SUCCESS for {SENDER_EMAIL}")

        # Get message count
        num_messages = len(mail.list()[1])
        print(f"  Messages in mailbox: {num_messages}")

        mail.quit()
        print(f"\n🎉 POP3 WORKS on {host}:995")
        break

    except Exception as e:
        print(f"  ❌ Error: {type(e).__name__}: {str(e)[:100]}")

print("\n" + "="*60)
print("Testing SMTP for SENDING (just to confirm)")
print("="*60)

import smtplib

for host in HOSTS:
    for port in [587, 465]:
        print(f"\nTrying {host}:{port} (SMTP)...")
        try:
            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=10)
            else:
                server = smtplib.SMTP(host, port, timeout=10)
                server.starttls()

            print(f"  ✅ Connected to {host}:{port}")
            server.login(SENDER_USER, SENDER_PASSWORD)
            print(f"  ✅ SMTP LOGIN SUCCESS on {host}:{port}")
            server.quit()
            break
        except Exception as e:
            print(f"  ❌ Error: {type(e).__name__}: {str(e)[:100]}")
