# HIPAA Direct Messaging Framework

A complete Python framework for HIPAA-compliant Direct messaging with **both POP3/IMAP and phiMail REST API** support.

## 🎯 Key Features

- **✅ Receive messages** via POP3 (working with HIXNY)
- **✅ Receive messages** via phiMail REST API (recommended)
- **✅ Send messages** via phiMail REST API
- **✅ FastAPI integration** - 3 lines of code
- **✅ S/MIME encryption** support
- **✅ HIPAA audit logging**
- **✅ Provider directory search**
- **✅ Delivery status tracking**
- **✅ Attachment handling**

## 🚀 Quick Start (phiMail REST API - Recommended)

### Installation

```bash
git clone https://github.com/jacobmr/DirectMessage.git
cd DirectMessage
pip install -r requirements.txt
```

### Configure phiMail

Create `.env` file:

```bash
# phiMail Configuration
PHIMAIL_API_URL=https://sandbox.phimaildev.com:8443/rest/v1/
PHIMAIL_USERNAME=your_username
PHIMAIL_PASSWORD=your_password
```

### Test Client

```bash
PYTHONPATH=src python3 examples/phimail_demo.py
```

### Integrate into FastAPI

```python
from fastapi import FastAPI
from hipaa_direct.integrations.fastapi_phimail import create_phimail_router

app = FastAPI()

# Add Direct messaging (just 3 lines!)
phimail_router = create_phimail_router()
app.include_router(phimail_router)
```

### Use REST API

```bash
# Check inbox
GET /api/direct/inbox/check

# Fetch messages
POST /api/direct/inbox/fetch

# Send message
POST /api/direct/outbox/send

# Search directory
GET /api/direct/directory/search?query=cardiology
```

**See [PHIMAIL_INTEGRATION.md](./PHIMAIL_INTEGRATION.md) for complete documentation.**

---

## 📨 POP3 Receiving (HIXNY)

### Configure POP3

```bash
# HIXNY Configuration
POP3_HOST=hixny.net
POP3_PORT=995
POP3_USER=resflo
POP3_PASSWORD=your_password
POP3_USE_SSL=true
```

### Receive Messages

```bash
PYTHONPATH=src python3 examples/receive_messages.py
```

**See [RESEARCHFLO_INTEGRATION.md](./RESEARCHFLO_INTEGRATION.md) for POP3 documentation.**

---

## 📚 Documentation

- **[PHIMAIL_INTEGRATION.md](./PHIMAIL_INTEGRATION.md)** - Complete phiMail REST API guide
- **[RESEARCHFLO_INTEGRATION.md](./RESEARCHFLO_INTEGRATION.md)** - POP3/IMAP receiving guide
- **Examples:**
  - `examples/phimail_demo.py` - phiMail client demo
  - `examples/fastapi_phimail_demo.py` - FastAPI integration demo
  - `examples/receive_messages.py` - POP3 receiving demo
  - `examples/fastapi_receiver_demo.py` - FastAPI POP3 integration

---

## 🔧 Usage Examples

### phiMail Client

```python
from hipaa_direct.clients.phimail_client import PhiMailClient

client = PhiMailClient(
    api_base_url="https://sandbox.phimaildev.com:8443/rest/v1/",
    username="your_username",
    password="your_password",
)

# Check inbox
messages = client.check_inbox(limit=10)

# Get full message
for msg in messages:
    full_msg = client.get_message(msg['id'])
    client.save_message_to_file(full_msg)
    client.acknowledge_message(msg['id'])

# Send message
response = client.send_message(
    sender="sender@example.direct",
    recipients=["recipient@example.direct"],
    subject="Test Message",
    body="This is a test",
)
```

### POP3 Receiver

```python
from hipaa_direct.core.receiver import DirectMessageReceiver

receiver = DirectMessageReceiver(
    pop3_host="hixny.net",
    pop3_port=995,
    pop3_user="resflo",
    pop3_password="password",
    use_ssl=True,
)

# Fetch all messages
messages = receiver.fetch_all_messages(delete_after_fetch=False)

for msg in messages:
    print(f"From: {msg['from']}")
    print(f"Subject: {msg['subject']}")
    print(f"Attachments: {len(msg['attachments'])}")

    # Save message
    receiver.save_message_to_file(msg)
```

---

## 📁 Project Structure

```
src/hipaa_direct/
├── clients/
│   └── phimail_client.py         # phiMail REST API client
├── core/
│   ├── receiver.py               # POP3 message receiver
│   ├── imap_receiver.py          # IMAP receiver (ready for HIXNY)
│   ├── message.py                # Message construction
│   └── sender.py                 # S/MIME message sending
├── integrations/
│   ├── fastapi_phimail.py        # FastAPI phiMail router
│   └── fastapi_receiver.py       # FastAPI POP3 router
├── certs/
│   └── manager.py                # Certificate management
└── utils/
    └── logging.py                # HIPAA audit logging

examples/
├── phimail_demo.py               # phiMail client demo
├── fastapi_phimail_demo.py       # phiMail FastAPI demo
├── receive_messages.py           # POP3 receiving demo
├── fastapi_receiver_demo.py      # POP3 FastAPI demo
└── test_imap_when_ready.py       # IMAP test (when enabled)

docs/
├── PHIMAIL_INTEGRATION.md        # phiMail complete guide
└── RESEARCHFLO_INTEGRATION.md    # POP3/IMAP guide
```

---

## 🔒 HIPAA Compliance

This framework provides:

- ✅ **Audit Logging** - All operations logged with timestamps
- ✅ **Encryption** - TLS/SSL for transport, S/MIME for messages
- ✅ **Access Control** - Certificate and password-based auth
- ✅ **Integrity** - Digital signatures prevent tampering
- ✅ **PHI Protection** - Secure message storage and handling

Audit logs: `logs/hipaa_audit.log` (JSON format)

### Security Best Practices

1. **Never commit credentials** to version control
2. **Use environment variables** for sensitive config
3. **Rotate passwords** quarterly
4. **Enable SSL verification** in production
5. **Store messages encrypted** at rest
6. **Implement access controls** (RBAC)
7. **Monitor audit logs** for suspicious activity

---

## 🧪 Testing

```bash
# Install dev dependencies
pip install pytest pytest-cov

# Run tests
pytest

# With coverage
pytest --cov=hipaa_direct --cov-report=html

# Test specific component
pytest tests/test_phimail_client.py -v
```

---

## 🌐 Deployment

### Digital Ocean (ResearchFlo)

1. **Set environment variables** in App Platform:
   ```bash
   PHIMAIL_API_URL=https://secure.phimail.net:8443/rest/v1/
   PHIMAIL_USERNAME=production_username
   PHIMAIL_PASSWORD=production_password
   ```

2. **Add to requirements.txt**:
   ```bash
   -e git+https://github.com/jacobmr/DirectMessage.git#egg=hipaa_direct
   ```

3. **Integrate into app**:
   ```python
   from hipaa_direct.integrations.fastapi_phimail import create_phimail_router
   app.include_router(create_phimail_router())
   ```

4. **Deploy**:
   ```bash
   git push origin main  # Triggers auto-deploy
   ```

---

## 📊 Comparison: phiMail vs POP3

| Feature | phiMail REST API | POP3/IMAP |
|---------|------------------|-----------|
| **Sending** | ✅ Full support | ❌ Disabled (HIXNY) |
| **Receiving** | ✅ Queue-based | ✅ Works |
| **Status Tracking** | ✅ Real-time | ❌ Not available |
| **Directory Search** | ✅ Built-in | ❌ Not available |
| **Complexity** | Low (HTTP) | High (email protocols) |
| **Reliability** | High | Medium |

**Recommendation:** Use **phiMail** for production. It's simpler, more reliable, and supports both sending and receiving.

---

## 📖 Additional Resources

- [Direct Trust](https://directtrust.org/)
- [ONC Direct Project](https://www.healthit.gov/topic/direct-project)
- [phiMail Documentation](./PHIMAIL_INTEGRATION.md)

---

## 📄 License

MIT License

---

## 🆘 Support

- **GitHub Issues**: [github.com/jacobmr/DirectMessage/issues](https://github.com/jacobmr/DirectMessage/issues)
- **Email**: Contact ResearchFlo team
- **Docs**: See PHIMAIL_INTEGRATION.md and RESEARCHFLO_INTEGRATION.md

---

**Built for ResearchFlo by JMR** | Last Updated: 2025-10-23
