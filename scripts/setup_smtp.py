"""Interactive SMTP setup with password change support."""

import getpass
import smtplib
from pathlib import Path
from email.mime.text import MIMEText


def test_smtp_connection(host: str, port: int, username: str, password: str, use_tls: bool = True) -> tuple[bool, str]:
    """
    Test SMTP connection with provided credentials.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            if use_tls:
                server.starttls()

            server.login(username, password)
            return True, "Connection successful!"
    except smtplib.SMTPAuthenticationError as e:
        error_msg = str(e)
        if "password change" in error_msg.lower() or "must change" in error_msg.lower():
            return False, "PASSWORD_CHANGE_REQUIRED"
        return False, f"Authentication failed: {error_msg}"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


def change_smtp_password(host: str, port: int, username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """
    Attempt to change SMTP password.

    Note: This is a placeholder - actual password change mechanism depends on your SMTP provider.
    Some providers require web-based password change, others support SMTP commands.

    Returns:
        Tuple of (success: bool, message: str)
    """
    # TODO: Implement based on your specific SMTP provider's password change mechanism
    # This might require:
    # 1. Web-based password change (open browser, return instructions)
    # 2. SMTP extension commands (if supported)
    # 3. API calls to provider

    print("\n⚠️  Password change mechanism depends on your SMTP provider.")
    print("Common approaches:")
    print("1. Web-based: Login to your provider's web portal to change password")
    print("2. Email link: Check your email for password reset link")
    print("3. Provider API: Some providers offer API-based password changes")

    return False, "Manual password change required via provider's portal"


def save_to_env(env_path: Path, smtp_config: dict):
    """Save SMTP configuration to .env file."""
    env_content = []

    # Read existing .env if it exists
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip existing SMTP settings
                if not line.startswith(('SMTP_', '#SMTP', 'DIRECT_')):
                    env_content.append(line)

    # Add SMTP configuration
    env_content.extend([
        "",
        "# HIPAA Direct Message SMTP Configuration",
        f"SMTP_HOST={smtp_config['host']}",
        f"SMTP_PORT={smtp_config['port']}",
        f"SMTP_USER={smtp_config['username']}",
        f"SMTP_PASSWORD={smtp_config['password']}",
        f"SMTP_USE_TLS={smtp_config['use_tls']}",
        "",
        "# Direct Messaging Sender",
        f"DIRECT_SENDER_EMAIL={smtp_config.get('sender_email', smtp_config['username'])}",
    ])

    with open(env_path, 'w') as f:
        f.write('\n'.join(env_content))

    print(f"\n✅ Configuration saved to {env_path}")


def setup_smtp_account(account_name: str, env_path: Path) -> dict:
    """
    Interactive setup for a single SMTP account.

    Args:
        account_name: Name of the account (e.g., "Sender", "Recipient")
        env_path: Path to .env file

    Returns:
        Dictionary with SMTP configuration
    """
    print(f"\n{'='*60}")
    print(f"Setting up {account_name} Account")
    print('='*60)

    # Collect connection details
    host = input(f"\n{account_name} SMTP Host (e.g., smtp.example.com): ").strip()
    port = int(input(f"{account_name} SMTP Port (usually 587 for TLS, 465 for SSL): ").strip() or "587")
    use_tls_input = input(f"Use TLS? (y/n, default: y): ").strip().lower()
    use_tls = use_tls_input != 'n'

    # Collect credentials
    username = input(f"\n{account_name} Username/Email: ").strip()
    password = getpass.getpass(f"{account_name} Password: ")

    # Test connection
    print(f"\nTesting connection to {host}:{port}...")
    success, message = test_smtp_connection(host, port, username, password, use_tls)

    if success:
        print(f"✅ {message}")
        return {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'use_tls': use_tls,
            'sender_email': username,
        }

    # Handle password change requirement
    if message == "PASSWORD_CHANGE_REQUIRED":
        print(f"\n⚠️  Password change required for {account_name} account!")
        print("You must change your password on first login.")

        change_method = input("\nHow do you want to change the password?\n"
                            "1. Via web portal (I'll change it manually)\n"
                            "2. Try automated change (if supported)\n"
                            "Choice (1/2): ").strip()

        if change_method == "1":
            print("\nPlease:")
            print(f"1. Open your SMTP provider's web portal")
            print(f"2. Login with username: {username}")
            print(f"3. Change your password")
            print(f"4. Return here when done\n")
            input("Press Enter when you've changed the password...")

            # Get new password
            new_password = getpass.getpass(f"\nEnter your NEW password: ")

            # Test with new password
            print(f"\nTesting connection with new password...")
            success, message = test_smtp_connection(host, port, username, new_password, use_tls)

            if success:
                print(f"✅ {message}")
                return {
                    'host': host,
                    'port': port,
                    'username': username,
                    'password': new_password,
                    'use_tls': use_tls,
                    'sender_email': username,
                }
            else:
                print(f"❌ Still failed: {message}")
                retry = input("Try again? (y/n): ").strip().lower()
                if retry == 'y':
                    return setup_smtp_account(account_name, env_path)
                return None
        else:
            print("\n❌ Automated password change not yet implemented.")
            print("Please change your password via your provider's web portal and run this setup again.")
            return None

    # Other errors
    print(f"❌ {message}")
    retry = input("Try again? (y/n): ").strip().lower()
    if retry == 'y':
        return setup_smtp_account(account_name, env_path)
    return None


def main():
    """Main setup workflow."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  HIPAA Direct Message SMTP Setup                            ║
║  Interactive configuration with password change support     ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Determine .env path
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"

    print(f"Configuration will be saved to: {env_path}")

    # Ask how many accounts to configure
    print("\nHow many Direct messaging accounts do you need to configure?")
    print("1. Single account (sender only)")
    print("2. Two accounts (sender and recipient for testing)")

    choice = input("\nChoice (1/2, default: 2): ").strip() or "2"

    if choice == "1":
        # Single account setup
        config = setup_smtp_account("Sender", env_path)
        if config:
            save_to_env(env_path, config)
            print("\n✅ Setup complete!")
            print(f"\nYour Direct messaging sender is configured:")
            print(f"  Email: {config['sender_email']}")
            print(f"  SMTP: {config['host']}:{config['port']}")
        else:
            print("\n❌ Setup cancelled or failed.")
    else:
        # Two account setup
        print("\n📧 Setting up SENDER account...")
        sender_config = setup_smtp_account("Sender", env_path)

        if not sender_config:
            print("\n❌ Sender setup failed. Cannot continue.")
            return

        print("\n📧 Setting up RECIPIENT account...")
        recipient_config = setup_smtp_account("Recipient", env_path)

        if not recipient_config:
            print("\n⚠️  Recipient setup failed. Saving sender config only.")
            save_to_env(env_path, sender_config)
        else:
            # Save both configurations
            save_to_env(env_path, sender_config)

            # Append recipient config
            with open(env_path, 'a') as f:
                f.write(f"\n# Recipient Account (for testing)\n")
                f.write(f"RECIPIENT_EMAIL={recipient_config['sender_email']}\n")
                f.write(f"RECIPIENT_SMTP_HOST={recipient_config['host']}\n")
                f.write(f"RECIPIENT_SMTP_PORT={recipient_config['port']}\n")
                f.write(f"RECIPIENT_SMTP_USER={recipient_config['username']}\n")
                f.write(f"RECIPIENT_SMTP_PASSWORD={recipient_config['password']}\n")

            print("\n✅ Setup complete!")
            print(f"\nSender: {sender_config['sender_email']}")
            print(f"Recipient: {recipient_config['sender_email']}")

    print("\n" + "="*60)
    print("Next steps:")
    print("1. Generate certificates: python examples/generate_certificates.py")
    print("2. Send test message: python examples/send_message.py")
    print("="*60)


if __name__ == "__main__":
    main()
