# ResearchFlo Integration Guide

This guide explains how to integrate the HIPAA Direct Messaging framework into your ResearchFlo application at Digital Ocean.

## Current ResearchFlo Infrastructure

- **Location**: `/var/www/researchflo/`
- **App**: FastAPI application at `src/clinres/app:app`
- **Server**: Gunicorn with Uvicorn workers (4 workers on port 8000)
- **Dependencies**: Already has `cryptography==42.0.0` and `email-validator==2.1.0`

## Integration Steps

### 1. Deploy HIPAA Direct Messaging Framework

Copy the framework to the ResearchFlo server:

```bash
# From your local machine
cd "/Users/jmr/dev/HIPAA DIRECT MESSAGE TEST"

# Option A: Deploy as a subdirectory within clinres
scp -r src/hipaa_direct root@157.230.183.202:/var/www/researchflo/src/

# Option B: Deploy as a standalone package
rsync -avz --exclude='__pycache__' \
  src/hipaa_direct/ \
  root@157.230.183.202:/var/www/researchflo/src/hipaa_direct/
```

### 2. Install Dependencies on Server

SSH into the server and install additional dependencies:

```bash
ssh root@157.230.183.202

cd /var/www/researchflo
source venv/bin/activate

# Install additional dependencies (most are already present)
pip install pyOpenSSL>=23.0.0 python-dotenv>=1.0.0

# Verify installation
python -c "from hipaa_direct import DirectMessage, DirectMessageSender; print('✓ HIPAA Direct installed')"
```

### 3. Run SMTP Setup (Local First)

Before deploying, set up your SMTP credentials locally:

```bash
# On your local machine
cd "/Users/jmr/dev/HIPAA DIRECT MESSAGE TEST"
python scripts/setup_smtp.py
```

This script will:
- Prompt for both sender and recipient SMTP credentials
- Handle password change requirements interactively
- Test connections and save to `.env`

### 4. Generate Certificates (Local)

```bash
# On your local machine
python examples/generate_certificates.py
```

This creates test certificates in `certs/` directory.

### 5. Copy Configuration to Server

```bash
# Copy .env file
scp .env root@157.230.183.202:/var/www/researchflo/.env.direct

# Copy certificates
scp -r certs/ root@157.230.183.202:/var/www/researchflo/certs/
```

### 6. Integrate into ResearchFlo App

On the server, edit `/var/www/researchflo/src/clinres/app.py`:

```python
# Add at the top of app.py
from hipaa_direct.integrations.fastapi_service import create_direct_messaging_router

# After creating your FastAPI app instance
app = FastAPI()  # Your existing app initialization

# Add Direct messaging routes
direct_router = create_direct_messaging_router(
    prefix="/api/direct",
    tags=["Direct Messaging"]
)
app.include_router(direct_router)
```

### 7. Update Environment Configuration

Merge Direct messaging config into your main `.env`:

```bash
ssh root@157.230.183.202
cd /var/www/researchflo

# Append Direct config to main .env
cat .env.direct >> .env

# Or manually add to .env:
# SMTP_HOST=your-smtp-host
# SMTP_PORT=587
# SMTP_USER=your-username
# SMTP_PASSWORD=your-password
# SMTP_USE_TLS=true
# DIRECT_SENDER_EMAIL=sender@direct.example.com
# SENDER_CERT_PATH=certs/sender_at_direct_example_com.crt
# SENDER_KEY_PATH=certs/private/sender_at_direct_example_com.key
```

### 8. Restart Services

```bash
ssh root@157.230.183.202

# Restart Gunicorn (managed by supervisor)
supervisorctl restart clinres

# Or if using systemd:
systemctl restart researchflo
```

### 9. Test the Integration

```bash
# Check health endpoint
curl http://localhost:8000/api/direct/health

# Send a test message
curl -X POST http://localhost:8000/api/direct/send \
  -H "Content-Type: application/json" \
  -d '{
    "to_address": "recipient@direct.example.com",
    "subject": "Test Message",
    "body": "This is a test HIPAA Direct message from ResearchFlo."
  }'
```

### 10. Verify External Access

```bash
# From your local machine
curl https://researchflo.com/api/direct/health
```

## Directory Structure After Integration

```
/var/www/researchflo/
├── src/
│   ├── clinres/
│   │   ├── app.py              # Modified to include Direct router
│   │   ├── core/
│   │   ├── api/
│   │   └── ...
│   └── hipaa_direct/           # New Direct messaging framework
│       ├── core/
│       ├── certs/
│       ├── utils/
│       └── integrations/
├── certs/                      # New certificate directory
│   ├── *.crt                   # Public certificates
│   └── private/
│       └── *.key               # Private keys
├── logs/                       # Existing + new audit logs
│   └── audit_*.log             # HIPAA audit logs
├── .env                        # Updated with Direct config
└── venv/                       # Existing virtualenv
```

## API Endpoints Available

After integration, ResearchFlo will have these new endpoints:

- `POST /api/direct/send` - Send a Direct message
- `GET /api/direct/certificates/{email}` - Get certificate info
- `GET /api/direct/health` - Health check

## Security Considerations

1. **Certificates**: Ensure `certs/private/` has restricted permissions
   ```bash
   chmod 700 /var/www/researchflo/certs/private
   chmod 600 /var/www/researchflo/certs/private/*.key
   ```

2. **Environment Variables**: Never commit `.env` to git
   ```bash
   # Verify .env is in .gitignore
   cd /var/www/researchflo
   git check-ignore .env  # Should output: .env
   ```

3. **Audit Logs**: Ensure logs directory has proper permissions
   ```bash
   chown -R www-data:www-data /var/www/researchflo/logs
   ```

4. **HTTPS**: Ensure Direct messaging endpoints are only accessible via HTTPS in production

## Monitoring

Check audit logs for HIPAA compliance:

```bash
# View today's audit log
tail -f /var/www/researchflo/logs/audit_$(date +%Y%m%d).log

# Search for specific message
grep "MESSAGE_SENT" /var/www/researchflo/logs/audit_*.log

# Check for errors
grep "success\":false" /var/www/researchflo/logs/audit_*.log
```

## Troubleshooting

### Service won't start
```bash
# Check Gunicorn logs
tail -f /var/www/researchflo/data/logs/api-error.log

# Test app manually
cd /var/www/researchflo
source venv/bin/activate
python -c "from src.clinres.app import app; print('App loaded successfully')"
```

### Import errors
```bash
# Verify package installed
cd /var/www/researchflo
source venv/bin/activate
python -c "from hipaa_direct import DirectMessage; print('OK')"

# Check sys.path
python -c "import sys; print('\n'.join(sys.path))"
```

### SMTP connection errors
```bash
# Test SMTP connection manually
python -c "
import smtplib
server = smtplib.SMTP('your-smtp-host', 587)
server.starttls()
server.login('username', 'password')
print('SMTP OK')
"
```

## Production Readiness Checklist

- [ ] SMTP credentials configured and tested
- [ ] Production certificates obtained (not self-signed)
- [ ] Certificates deployed with proper permissions
- [ ] Environment variables configured
- [ ] Service restarted and health check passes
- [ ] Audit logging verified
- [ ] HTTPS enforced for API endpoints
- [ ] Rate limiting configured (if needed)
- [ ] Monitoring/alerting set up for failed sends
- [ ] Backup strategy for certificates and logs

## Next Steps

1. **Complete S/MIME Implementation**: The current implementation in `sender.py:encrypt_message()` is a placeholder
2. **Add Recipient Certificate Discovery**: Implement DNS/LDAP lookup for recipient certificates
3. **Implement Message Receiving**: Add IMAP receiver to handle incoming Direct messages
4. **Add to ResearchFlo UI**: Create frontend interface for sending Direct messages from the app
