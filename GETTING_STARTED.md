# Getting Started - HIPAA Direct Messaging

Quick start guide for setting up and testing the HIPAA Direct Messaging framework.

## Prerequisites

- Python 3.8+
- SMTP credentials for Direct messaging (2 accounts recommended for testing)
- SSH access to ResearchFlo server (for deployment)

## Step-by-Step Setup

### 1. Install Dependencies

```bash
cd "/Users/jmr/dev/HIPAA DIRECT MESSAGE TEST"
pip install -r requirements.txt
```

### 2. Configure SMTP (Interactive - Handles Password Change)

```bash
python scripts/setup_smtp.py
```

This will:
- ✅ Prompt for sender SMTP credentials
- ✅ Prompt for recipient SMTP credentials (optional, for testing)
- ✅ Detect and handle password change requirements
- ✅ Test connections
- ✅ Generate `.env` file automatically

**Important**: If your SMTP provider requires password change on first login, the script will guide you through it.

### 3. Generate Test Certificates

```bash
python examples/generate_certificates.py
```

This creates self-signed certificates in `certs/` directory.

**Note**: These are for TESTING only. Production requires certificates from a trusted HISP CA.

### 4. Test Sending a Message

```bash
python examples/send_message.py
```

Expected output:
```
Message sent successfully! Message ID: <unique-id@domain>
```

### 5. Test with Attachment

```bash
python examples/send_with_attachment.py
```

## Verify Setup

Check that everything is working:

```bash
# Check audit logs were created
ls -la logs/

# View audit log
cat logs/audit_$(date +%Y%m%d).log

# Verify certificates
ls -la certs/
ls -la certs/private/
```

## Integration with ResearchFlo

### Option 1: Deploy to Digital Ocean Server

See detailed instructions in `deployment/researchflo_integration.md`

Quick summary:
```bash
# 1. Copy framework to server
rsync -avz --exclude='__pycache__' \
  src/hipaa_direct/ \
  root@157.230.183.202:/var/www/researchflo/src/hipaa_direct/

# 2. Copy config and certs
scp .env root@157.230.183.202:/var/www/researchflo/.env.direct
scp -r certs/ root@157.230.183.202:/var/www/researchflo/certs/

# 3. SSH to server and integrate
ssh root@157.230.183.202
cd /var/www/researchflo
source venv/bin/activate

# Install dependencies
pip install pyOpenSSL>=23.0.0 python-dotenv>=1.0.0

# Edit src/clinres/app.py and add:
# from hipaa_direct.integrations.fastapi_service import create_direct_messaging_router
# direct_router = create_direct_messaging_router(prefix="/api/direct")
# app.include_router(direct_router)

# Restart service
supervisorctl restart clinres
```

### Option 2: Test Locally with FastAPI

```bash
python examples/fastapi_integration_example.py
```

Then test the API:
```bash
curl http://localhost:8000/api/direct/health

curl -X POST http://localhost:8000/api/direct/send \
  -H "Content-Type: application/json" \
  -d '{
    "to_address": "recipient@direct.example.com",
    "subject": "Test",
    "body": "Test message"
  }'
```

## Common Issues

### SMTP Authentication Fails

**Problem**: "Authentication failed"

**Solution**:
1. Run `python scripts/setup_smtp.py` again
2. Verify credentials are correct
3. Check if password change is required

### Certificate Not Found

**Problem**: "Recipient certificate not found"

**Solution**:
1. Run `python examples/generate_certificates.py`
2. Verify `certs/` directory exists
3. Check certificate filenames match email addresses

### Import Errors

**Problem**: "ModuleNotFoundError: No module named 'hipaa_direct'"

**Solution**:
```bash
pip install -e .
```

## Next Steps

1. **Test with real SMTP credentials**: Use your actual Direct messaging provider
2. **Generate production certificates**: Contact your HISP to obtain trusted certificates
3. **Deploy to ResearchFlo**: Follow `deployment/researchflo_integration.md`
4. **Complete S/MIME encryption**: Implement full encryption in `src/hipaa_direct/core/sender.py:42`

## Support

- Review `CLAUDE.md` for architecture and development guidance
- Check `README.md` for detailed API documentation
- See `deployment/researchflo_integration.md` for deployment details

## Security Reminders

- ✅ Never commit `.env` files
- ✅ Never commit certificates or private keys
- ✅ Use `certs/private/` for all private keys
- ✅ Self-signed certificates are for TESTING only
- ✅ Review audit logs regularly: `logs/audit_*.log`
