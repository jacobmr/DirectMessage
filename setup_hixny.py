#!/usr/bin/env python3
"""
HIXNY SMTP Setup Script
Configures both sender and recipient accounts with automatic server discovery
"""

import smtplib
import getpass
from pathlib import Path

# Credentials provided
SENDER_EMAIL = "resflo@hixny.net"
SENDER_USER = "hixnycolo\\resflo"
SENDER_PASSWORD = "T1m3ZL1k3tH33se$"

RECIPIENT_EMAIL = "test.resflo@hixny.net"
RECIPIENT_USER = "hixnycolo\\test.resflo"
RECIPIENT_PASSWORD = "Th3M0nST3rma$Hed"

# Common Exchange server hostnames to try
# MX record shows direct.hixny.net as the mail server
POSSIBLE_HOSTS = [
    "direct.hixny.net",  # From MX record
    "smtp.hixny.net",
    "mail.hixny.net",
    "hixny.net",
]

PORTS = [
    (587, True, "TLS/STARTTLS"),
    (465, False, "SSL"),
    (995, False, "SSL (Secure)"),
    (993, False, "SSL (IMAP)"),
    (2525, True, "TLS/STARTTLS (alternate)"),
    (25, True, "TLS/STARTTLS (legacy)"),
]


def test_smtp_connection(host, port, username, password, use_starttls=True):
    """Test SMTP connection and return result."""
    try:
        print(f"  Trying {host}:{port} {'with STARTTLS' if use_starttls else 'with SSL'}...", end=" ")

        if port == 465:
            # Use SMTP_SSL for port 465
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            if use_starttls:
                server.starttls()

        server.login(username, password)
        server.quit()
        print("✅ SUCCESS")
        return True, "Connection successful"
    except smtplib.SMTPAuthenticationError as e:
        error_msg = str(e)
        print(f"❌ Auth Error")
        if "password" in error_msg.lower() and "change" in error_msg.lower():
            return False, "PASSWORD_CHANGE_REQUIRED"
        return False, f"Authentication failed: {error_msg}"
    except Exception as e:
        print(f"❌ {type(e).__name__}")
        return False, str(e)


def find_smtp_server(email, username, password):
    """Try to discover the working SMTP server."""
    print(f"\n🔍 Discovering SMTP server for {email}...")

    for host in POSSIBLE_HOSTS:
        print(f"\nTrying {host}:")
        for port, use_starttls, desc in PORTS:
            success, message = test_smtp_connection(host, port, username, password, use_starttls)
            if success:
                return host, port, use_starttls
            elif message == "PASSWORD_CHANGE_REQUIRED":
                print(f"\n⚠️  Password change required for {email}")
                return host, port, use_starttls, "PASSWORD_CHANGE_REQUIRED"

    return None, None, None


def save_to_env(config):
    """Save configuration to .env file."""
    env_path = Path(__file__).parent / ".env"

    env_content = [
        "# HIPAA Direct Message SMTP Configuration",
        "# Generated automatically",
        "",
        "# Sender Account (resflo@hixny.net)",
        f"SMTP_HOST={config['sender']['host']}",
        f"SMTP_PORT={config['sender']['port']}",
        f"SMTP_USER={config['sender']['username']}",
        f"SMTP_PASSWORD={config['sender']['password']}",
        f"SMTP_USE_TLS={str(config['sender']['use_tls']).lower()}",
        "",
        f"DIRECT_SENDER_EMAIL={SENDER_EMAIL}",
        "",
        "# Recipient Account (test.resflo@hixny.net)",
        f"RECIPIENT_EMAIL={RECIPIENT_EMAIL}",
        f"RECIPIENT_SMTP_HOST={config['recipient']['host']}",
        f"RECIPIENT_SMTP_PORT={config['recipient']['port']}",
        f"RECIPIENT_SMTP_USER={config['recipient']['username']}",
        f"RECIPIENT_SMTP_PASSWORD={config['recipient']['password']}",
        "",
        "# Certificate paths (update after generating certificates)",
        f"SENDER_CERT_PATH=certs/resflo_at_hixny_net.crt",
        f"SENDER_KEY_PATH=certs/private/resflo_at_hixny_net.key",
        f"RECIPIENT_CERT_PATH=certs/test_resflo_at_hixny_net.crt",
    ]

    with open(env_path, 'w') as f:
        f.write('\n'.join(env_content) + '\n')

    print(f"\n✅ Configuration saved to {env_path}")


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║  HIXNY Direct Message SMTP Setup                            ║
║  Automated configuration for resflo@hixny.net               ║
╚══════════════════════════════════════════════════════════════╝
    """)

    config = {'sender': {}, 'recipient': {}}

    # Test sender account
    print("\n" + "="*60)
    print("SENDER ACCOUNT: resflo@hixny.net")
    print("="*60)

    result = find_smtp_server(SENDER_EMAIL, SENDER_USER, SENDER_PASSWORD)

    if len(result) == 4 and result[3] == "PASSWORD_CHANGE_REQUIRED":
        host, port, use_tls, _ = result
        print(f"\n⚠️  PASSWORD CHANGE REQUIRED for {SENDER_EMAIL}")
        print(f"\nPlease follow these steps:")
        print(f"1. Open your email client or webmail for {SENDER_EMAIL}")
        print(f"2. Login with username: {SENDER_USER}")
        print(f"3. You'll be prompted to change your password")
        print(f"4. Change it and come back here")
        print(f"\nFound server: {host}:{port}")

        input("\nPress Enter when you've changed the password...")

        new_password = getpass.getpass("Enter your NEW password for sender: ")

        print(f"\nTesting with new password...")
        success, message = test_smtp_connection(host, port, SENDER_USER, new_password, use_tls)

        if success:
            print(f"✅ Sender account configured successfully!")
            config['sender'] = {
                'host': host,
                'port': port,
                'username': SENDER_USER,
                'password': new_password,
                'use_tls': use_tls
            }
        else:
            print(f"❌ Failed: {message}")
            return
    elif result[0]:
        host, port, use_tls = result
        print(f"\n✅ Sender account configured successfully!")
        print(f"   Server: {host}:{port}")
        config['sender'] = {
            'host': host,
            'port': port,
            'username': SENDER_USER,
            'password': SENDER_PASSWORD,
            'use_tls': use_tls
        }
    else:
        print(f"\n❌ Could not find working SMTP server for sender")
        print("Please check credentials and try manually")
        return

    # Test recipient account
    print("\n" + "="*60)
    print("RECIPIENT ACCOUNT: test.resflo@hixny.net")
    print("="*60)

    result = find_smtp_server(RECIPIENT_EMAIL, RECIPIENT_USER, RECIPIENT_PASSWORD)

    if len(result) == 4 and result[3] == "PASSWORD_CHANGE_REQUIRED":
        host, port, use_tls, _ = result
        print(f"\n⚠️  PASSWORD CHANGE REQUIRED for {RECIPIENT_EMAIL}")
        print(f"\nPlease follow these steps:")
        print(f"1. Open your email client or webmail for {RECIPIENT_EMAIL}")
        print(f"2. Login with username: {RECIPIENT_USER}")
        print(f"3. You'll be prompted to change your password")
        print(f"4. Change it and come back here")
        print(f"\nFound server: {host}:{port}")

        input("\nPress Enter when you've changed the password...")

        new_password = getpass.getpass("Enter your NEW password for recipient: ")

        print(f"\nTesting with new password...")
        success, message = test_smtp_connection(host, port, RECIPIENT_USER, new_password, use_tls)

        if success:
            print(f"✅ Recipient account configured successfully!")
            config['recipient'] = {
                'host': host,
                'port': port,
                'username': RECIPIENT_USER,
                'password': new_password,
                'use_tls': use_tls
            }
        else:
            print(f"❌ Failed: {message}")
            return
    elif result[0]:
        host, port, use_tls = result
        print(f"\n✅ Recipient account configured successfully!")
        print(f"   Server: {host}:{port}")
        config['recipient'] = {
            'host': host,
            'port': port,
            'username': RECIPIENT_USER,
            'password': RECIPIENT_PASSWORD,
            'use_tls': use_tls
        }
    else:
        print(f"\n❌ Could not find working SMTP server for recipient")
        print("Please check credentials and try manually")
        return

    # Save configuration
    save_to_env(config)

    print("\n" + "="*60)
    print("✅ SETUP COMPLETE!")
    print("="*60)
    print("\nConfiguration Summary:")
    print(f"  Sender: {SENDER_EMAIL}")
    print(f"    Server: {config['sender']['host']}:{config['sender']['port']}")
    print(f"  Recipient: {RECIPIENT_EMAIL}")
    print(f"    Server: {config['recipient']['host']}:{config['recipient']['port']}")

    print("\n" + "="*60)
    print("Next steps:")
    print("1. Generate certificates: python examples/generate_certificates.py")
    print("2. Send test message: python examples/send_message.py")
    print("="*60)


if __name__ == "__main__":
    main()
