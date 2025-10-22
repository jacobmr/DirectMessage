# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based HIPAA Direct Messaging framework for sending secure, encrypted healthcare messages using the Direct Protocol. The framework implements S/MIME encryption, certificate management, and HIPAA-compliant audit logging.

## Architecture

### Core Components

1. **hipaa_direct.core.message** (`src/hipaa_direct/core/message.py`)
   - `DirectMessage` class: Handles message construction, validation, and MIME conversion
   - Supports plain text, HTML, and attachments (medical records, images, etc.)
   - Automatically generates unique message IDs and timestamps
   - Key method: `to_mime()` converts message to MIME format for encryption

2. **hipaa_direct.core.sender** (`src/hipaa_direct/core/sender.py`)
   - `DirectMessageSender` class: Handles SMTP sending with S/MIME encryption
   - Key method: `encrypt_message()` - encrypts and signs messages using certificates
   - Key method: `send()` - orchestrates encryption and SMTP delivery
   - Integrates with AuditLogger for HIPAA compliance tracking
   - **Note**: Full S/MIME implementation is a TODO - currently placeholder

3. **hipaa_direct.certs.manager** (`src/hipaa_direct/certs/manager.py`)
   - `CertificateManager` class: X.509 certificate lifecycle management
   - Generates self-signed certificates for testing
   - Validates certificate expiration and integrity
   - Stores certificates in `certs/` and private keys in `certs/private/`

4. **hipaa_direct.utils.logging** (`src/hipaa_direct/utils/logging.py`)
   - `AuditLogger` class: HIPAA-compliant structured logging
   - Logs encryption, send, and certificate operations
   - JSON-formatted audit trail stored in `logs/audit_YYYYMMDD.log`

5. **hipaa_direct.integrations.fastapi_service** (`src/hipaa_direct/integrations/fastapi_service.py`)
   - `create_direct_messaging_router()`: Creates FastAPI router for Direct messaging
   - `DirectMessageConfig`: Configuration management with environment variable support
   - REST API endpoints for sending messages, checking certificates, and health checks
   - Designed for integration into existing FastAPI apps like ResearchFlo

### Data Flow

```
DirectMessage -> validate() -> to_mime() -> encrypt_message() -> SMTP send
                                                 ↓
                                          AuditLogger (all steps)
```

### FastAPI Integration Flow

```
FastAPI Request -> DirectMessageRequest (validation)
                -> DirectMessage (creation)
                -> DirectMessageSender (send)
                -> AuditLogger (log)
                -> DirectMessageResponse (return)
```

## Common Commands

### Setup and Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install development dependencies (includes pytest, black, flake8, mypy)
pip install -r requirements-dev.txt

# Install package in editable mode for development
pip install -e .
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=hipaa_direct --cov-report=html

# Run specific test file
pytest tests/unit/test_message.py

# Run specific test
pytest tests/unit/test_message.py::test_message_creation

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code with black
black src/

# Check formatting without changes
black --check src/

# Lint with flake8
flake8 src/

# Type checking with mypy
mypy src/
```

### Development Workflow

```bash
# Interactive SMTP setup with password change support (run this FIRST)
python scripts/setup_smtp.py

# Generate test certificates (required before sending messages)
python examples/generate_certificates.py

# Send a test message
python examples/send_message.py

# Send message with attachment
python examples/send_with_attachment.py
```

### Configuration

**Option 1: Interactive Setup (Recommended)**
```bash
python scripts/setup_smtp.py
```
This handles:
- SMTP credential collection for both sender and recipient
- Password change requirement on first login
- Connection testing
- Automatic `.env` file generation

**Option 2: Manual Setup**
1. Copy `.env.example` to `.env`
2. Update SMTP settings (host, port, credentials)
3. Update certificate paths after generating certificates

## Important Implementation Notes

### S/MIME Encryption (TODO)

The `encrypt_message()` method in `sender.py:42` is currently a placeholder. Full implementation requires:
1. Sign message with sender's private key using cryptography library
2. Encrypt signed message with recipient's public key
3. Return properly formatted S/MIME message

The current implementation logs the operation but returns unencrypted MIME bytes.

### Certificate Security

- Private keys are stored in `certs/private/` (gitignored)
- Self-signed certificates from `CertificateManager` are for **testing only**
- Production systems should use certificates from trusted HISP (Health Information Service Provider) CAs
- Never commit `.pem`, `.key`, `.crt`, `.p12`, or `.pfx` files

### HIPAA Compliance Features

- **Audit Logging**: All operations logged to `logs/` with timestamps
- **Encryption**: Messages encrypted with S/MIME (when fully implemented)
- **Access Control**: Certificate-based authentication
- **Integrity**: Digital signatures prevent tampering

### Testing Strategy

- Unit tests in `tests/unit/` for individual components
- Integration tests in `tests/integration/` for end-to-end workflows
- Use `temp_cert_dir` fixture for certificate tests to avoid polluting real cert directory
- Mock SMTP connections in sender tests to avoid actual email sending

## Key Design Decisions

1. **Separation of Concerns**: Message construction, encryption, and sending are separate classes for testability
2. **Certificate Directory Structure**: Public certs in `certs/`, private keys in `certs/private/` for security
3. **Audit Logging**: JSON format for easy parsing and integration with SIEM systems
4. **Environment Variables**: Sensitive config (SMTP credentials, cert paths) stored in `.env`

## Directory Structure

```
src/hipaa_direct/          # Main package
├── core/                  # Core messaging functionality
│   ├── message.py         # Message construction and MIME conversion
│   └── sender.py          # SMTP sending with S/MIME encryption
├── certs/                 # Certificate management
│   └── manager.py         # Generate, validate, inspect certificates
├── utils/                 # Utilities
│   └── logging.py         # HIPAA audit logging
└── integrations/          # Framework integrations
    └── fastapi_service.py # FastAPI router and config

examples/                  # Usage examples
├── generate_certificates.py
├── send_message.py
├── send_with_attachment.py
└── fastapi_integration_example.py

scripts/                   # Setup and utility scripts
└── setup_smtp.py          # Interactive SMTP setup with password change

deployment/                # Deployment guides
└── researchflo_integration.md  # ResearchFlo integration guide

tests/                     # Test suite
├── unit/                  # Unit tests
└── integration/           # Integration tests

certs/                     # Certificate storage (gitignored)
├── *.crt                  # Public certificates
└── private/               # Private keys (gitignored)
    └── *.key

logs/                      # Audit logs (gitignored)
└── audit_*.log
```

## Adding New Features

### Adding a New Message Type

1. Extend `DirectMessage` class in `message.py`
2. Update `to_mime()` method to handle new format
3. Add validation in `validate()` method
4. Write unit tests in `tests/unit/test_message.py`

### Adding Certificate Features

1. Add methods to `CertificateManager` in `certs/manager.py`
2. Use `cryptography` library for certificate operations
3. Log operations with `audit_logger.log_certificate_operation()`
4. Write tests using `temp_cert_dir` fixture

### Enhancing Security

1. Complete S/MIME implementation in `sender.py:encrypt_message()`
2. Add certificate revocation checking (CRL/OCSP)
3. Implement recipient certificate discovery (DNS/LDAP)
4. Add message integrity verification on receive

## Troubleshooting

### Import Errors
- Ensure package is installed: `pip install -e .`
- Check PYTHONPATH includes project root

### Certificate Errors
- Verify certificates exist in `certs/` directory
- Check certificate validity: `python -c "from hipaa_direct import CertificateManager; cm = CertificateManager(); print(cm.verify_certificate('path/to/cert.crt'))"`
- Regenerate test certificates: `python examples/generate_certificates.py`

### SMTP Errors
- Verify `.env` configuration matches your SMTP server
- Check firewall/network allows SMTP ports (usually 587 or 465)
- Test SMTP credentials with basic telnet or openssl commands

## ResearchFlo Integration

This framework is designed to integrate into the ResearchFlo clinical research platform at Digital Ocean.

### Quick Integration

```python
# In /var/www/researchflo/src/clinres/app.py
from hipaa_direct.integrations.fastapi_service import create_direct_messaging_router

# Add to existing FastAPI app
direct_router = create_direct_messaging_router(
    prefix="/api/direct",
    tags=["Direct Messaging"]
)
app.include_router(direct_router)
```

### Deployment to ResearchFlo

See `deployment/researchflo_integration.md` for complete deployment guide including:
- File transfer to Digital Ocean server
- Dependency installation in existing venv
- Configuration merge with existing `.env`
- Service restart procedures
- Testing and verification

### ResearchFlo Infrastructure

- **Location**: `/var/www/researchflo/`
- **App**: FastAPI at `src/clinres/app:app`
- **Server**: Gunicorn + Uvicorn (4 workers on port 8000)
- **Supervisor**: Managed via supervisor/systemd
- **Already Has**: `cryptography==42.0.0`, `email-validator==2.1.0`

## First-Time SMTP Setup

### Password Change Requirement

Many SMTP providers require password change on first login. Use the interactive setup:

```bash
python scripts/setup_smtp.py
```

This script handles:
1. Initial credential collection
2. Connection testing
3. Password change detection
4. Guided password change workflow
5. Credential verification
6. `.env` file generation

The script supports:
- Single account setup (sender only)
- Dual account setup (sender + recipient for testing)
- Interactive password change prompts
- Connection retry on failure

## Next Steps for Production

1. **Complete S/MIME Implementation**: Implement full encryption/signing in `sender.py`
2. **Add Message Receiving**: Implement IMAP/POP3 receiver with decryption
3. **Certificate Discovery**: Implement DNS/LDAP lookup for recipient certificates
4. **Production Certificates**: Integrate with HISP CA for trusted certificates
5. **Message Disposition Notifications (MDN)**: Implement delivery/read receipts
6. **Error Handling**: Add retry logic and better error messages
7. **Performance**: Add connection pooling for SMTP
8. **ResearchFlo UI**: Build frontend interface for sending Direct messages
