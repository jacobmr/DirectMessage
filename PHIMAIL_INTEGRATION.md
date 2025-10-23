# phiMail Direct Messaging Integration Guide

**For ResearchFlo Development Team**

## Executive Summary

This document describes the **phiMail REST API integration** for HIPAA-compliant Direct messaging in ResearchFlo. phiMail provides a superior alternative to POP3/IMAP-based messaging with:

- ✅ **Clean REST API** - No email protocol complexity
- ✅ **Both send AND receive** - Unlike HIXNY (receive-only)
- ✅ **Delivery status tracking** - Know when messages are delivered
- ✅ **Provider directory search** - Find Direct addresses
- ✅ **Queue-based messaging** - Reliable message processing
- ✅ **JSON in/out** - No MIME parsing required

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Integration Options](#integration-options)
4. [API Reference](#api-reference)
5. [Deployment](#deployment)
6. [Security & HIPAA Compliance](#security--hipaa-compliance)
7. [Testing](#testing)

---

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install package
pip install -e .
```

### Environment Configuration

Create a `.env` file:

```bash
# phiMail API Configuration
PHIMAIL_API_URL=https://sandbox.phimaildev.com:8443/rest/v1/
PHIMAIL_USERNAME=your_username
PHIMAIL_PASSWORD=your_password

# For production:
# PHIMAIL_API_URL=https://secure.phimail.net:8443/rest/v1/
```

### Test the Client

```bash
# Run demo script
PYTHONPATH=src python3 examples/phimail_demo.py
```

### Integrate into FastAPI

```python
from fastapi import FastAPI
from hipaa_direct.integrations.fastapi_phimail import create_phimail_router

app = FastAPI()

# Add phiMail routes
phimail_router = create_phimail_router(
    prefix="/api/direct",
    tags=["Direct Messaging"]
)
app.include_router(phimail_router)
```

**That's it!** You now have a complete Direct messaging API.

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                    ResearchFlo App                      │
│                  (FastAPI + Gunicorn)                   │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│          FastAPI phiMail Router                         │
│        (fastapi_phimail.py)                            │
│                                                         │
│  Routes:                                                │
│  • GET  /api/direct/inbox/check                        │
│  • POST /api/direct/inbox/fetch                        │
│  • POST /api/direct/outbox/send                        │
│  • GET  /api/direct/outbox/status/{id}                 │
│  • GET  /api/direct/directory/search                   │
│  • GET  /api/direct/health                             │
│  • GET  /api/direct/stats                              │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              PhiMailClient                              │
│           (phimail_client.py)                          │
│                                                         │
│  Methods:                                               │
│  • check_inbox()        - Get message list             │
│  • get_message()        - Get full message             │
│  • acknowledge_message()- Remove from queue            │
│  • send_message()       - Send Direct message          │
│  • get_outbox_status()  - Check delivery status        │
│  • search_directory()   - Find providers               │
│  • download_attachment()- Get attachments              │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              phiMail REST API                           │
│        (EMR Direct Interoperability Engine)             │
│                                                         │
│  Sandbox:    sandbox.phimaildev.com:8443                │
│  Production: secure.phimail.net:8443                    │
└─────────────────────────────────────────────────────────┘
```

### Message Flow

#### Receiving Messages

```
1. phiMail receives Direct message
   ↓
2. Message queued in inbox
   ↓
3. ResearchFlo polls: GET /api/direct/inbox/check
   ↓
4. ResearchFlo fetches: POST /api/direct/inbox/fetch
   ↓
5. Message saved to storage + processed
   ↓
6. Message acknowledged (removed from queue)
```

#### Sending Messages

```
1. ResearchFlo creates message
   ↓
2. POST /api/direct/outbox/send
   ↓
3. phiMail queues message for delivery
   ↓
4. phiMail sends via Direct protocol
   ↓
5. ResearchFlo polls: GET /api/direct/outbox/status/{id}
   ↓
6. Delivery notification received
```

---

## Integration Options

### Option 1: REST API Integration (Recommended)

**Best for:** Modern microservices architecture

Add phiMail router to existing ResearchFlo FastAPI app:

```python
# In your main.py or app.py
from hipaa_direct.integrations.fastapi_phimail import create_phimail_router

app = FastAPI()

# Add Direct messaging
phimail_router = create_phimail_router()
app.include_router(phimail_router)
```

**Endpoints available:**

```bash
# Health check
GET /api/direct/health

# Check for new messages (lightweight)
GET /api/direct/inbox/check?limit=50

# Fetch and process messages
POST /api/direct/inbox/fetch?acknowledge=true

# Send a message
POST /api/direct/outbox/send
{
  "sender": "resflo@hixny.net",
  "recipients": ["doctor@clinic.direct"],
  "subject": "Patient Report",
  "body": "Please review attached report",
  "attachments": [...]
}

# Check delivery status
GET /api/direct/outbox/status/{message_id}

# Search provider directory
GET /api/direct/directory/search?query=cardiology&limit=10

# Get statistics
GET /api/direct/stats
```

### Option 2: Background Worker with RQ

**Best for:** Periodic message checking without blocking web requests

```python
# worker.py
from hipaa_direct.clients.phimail_client import PhiMailClient
from rq import Queue
from redis import Redis

redis_conn = Redis()
queue = Queue('direct_messages', connection=redis_conn)

def check_and_process_messages():
    """Background job to check for new Direct messages."""
    client = PhiMailClient(
        api_base_url=os.getenv("PHIMAIL_API_URL"),
        username=os.getenv("PHIMAIL_USERNAME"),
        password=os.getenv("PHIMAIL_PASSWORD"),
    )

    # Check inbox
    messages = client.check_inbox(limit=50)

    for msg_summary in messages:
        # Get full message
        full_msg = client.get_message(msg_summary['id'])

        # Process message (save to DB, trigger workflows, etc.)
        process_direct_message(full_msg)

        # Acknowledge (remove from queue)
        client.acknowledge_message(msg_summary['id'])

    return len(messages)

# Schedule to run every 5 minutes
queue.enqueue(check_and_process_messages, ttl=300)
```

Start worker:
```bash
rq worker direct_messages
```

### Option 3: Direct Client Usage

**Best for:** Simple scripts, testing, or custom integrations

```python
from hipaa_direct.clients.phimail_client import PhiMailClient

client = PhiMailClient(
    api_base_url="https://sandbox.phimaildev.com:8443/rest/v1/",
    username="your_username",
    password="your_password",
)

# Check inbox
messages = client.check_inbox(limit=10)

# Process each message
for msg_summary in messages:
    full_msg = client.get_message(msg_summary['id'])

    # Your processing logic
    print(f"From: {full_msg['from']}")
    print(f"Subject: {full_msg['subject']}")

    # Save message
    client.save_message_to_file(full_msg, "received_messages/phimail")

    # Acknowledge
    client.acknowledge_message(msg_summary['id'])

# Send a message
send_response = client.send_message(
    sender="resflo@hixny.net",
    recipients=["test.resflo@hixny.net"],
    subject="Test Message",
    body="This is a test",
)

print(f"Sent! Message ID: {send_response['id']}")
```

---

## API Reference

### PhiMailClient

#### Constructor

```python
PhiMailClient(
    api_base_url: str,
    username: str,
    password: str,
    verify_ssl: bool = True,
    timeout: int = 30,
    audit_logger: Optional[AuditLogger] = None,
)
```

**Parameters:**
- `api_base_url`: phiMail API base URL
  - Sandbox: `https://sandbox.phimaildev.com:8443/rest/v1/`
  - Production: `https://secure.phimail.net:8443/rest/v1/`
- `username`: phiMail account username
- `password`: phiMail account password
- `verify_ssl`: Verify SSL certificates (default: True)
- `timeout`: Request timeout in seconds (default: 30)
- `audit_logger`: Optional HIPAA audit logger

#### Methods

##### check_inbox()

```python
messages = client.check_inbox(limit: Optional[int] = None) -> List[Dict]
```

Get list of messages in inbox queue (metadata only).

**Returns:** List of message summaries
```python
[
    {
        'id': 'queue-id-123',           # Use for get_message() and acknowledge_message()
        'messageId': '<abc@example>',   # RFC 822 Message-ID
        'from': 'sender@example.direct',
        'to': ['recipient@example.direct'],
        'subject': 'Patient Report',
        'receivedDate': '2025-10-23T10:30:00Z',
        'size': 54321,
        'hasAttachments': True,
    },
    # ...
]
```

##### get_message()

```python
message = client.get_message(message_id: str) -> Dict
```

Get full message content including body and attachments.

**Parameters:**
- `message_id`: Queue ID from `check_inbox()`

**Returns:** Complete message dictionary

##### acknowledge_message()

```python
client.acknowledge_message(message_id: str) -> Dict
```

Acknowledge and remove message from inbox queue.

**Important:** Once acknowledged, the message is deleted from the queue!

##### send_message()

```python
response = client.send_message(
    sender: str,
    recipients: List[str],
    subject: str,
    body: str,
    attachments: Optional[List[Dict]] = None,
    request_delivery_status: bool = True,
    request_read_receipt: bool = False,
) -> Dict
```

Send a Direct message.

**Attachments format:**
```python
attachments = [
    {
        'filename': 'report.pdf',
        'content_type': 'application/pdf',
        'content': base64_encoded_content,  # Or raw bytes
    }
]
```

**Returns:**
```python
{
    'id': 'outbox-id-456',
    'status': 'queued',
    'messageId': '<xyz@phimail>',
}
```

##### get_outbox_status()

```python
status = client.get_outbox_status(message_id: str) -> Dict
```

Check delivery status of sent message.

**Returns:**
```python
{
    'id': 'outbox-id-456',
    'status': 'delivered',  # Or: queued, sent, failed
    'statusDetails': 'Successfully delivered',
    'deliveryNotifications': [...]
}
```

##### search_directory()

```python
results = client.search_directory(
    query: Optional[str] = None,
    direct_address: Optional[str] = None,
    npi: Optional[str] = None,
    organization: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]
```

Search provider directory for Direct addresses.

**Example:**
```python
# Search by organization
results = client.search_directory(organization="Mayo Clinic")

# Search by NPI
results = client.search_directory(npi="1234567890")

# Free-text search
results = client.search_directory(query="cardiology new york")
```

##### download_attachment()

```python
content = client.download_attachment(
    message_id: str,
    attachment_id: str,
    output_path: Optional[str] = None,
) -> bytes
```

Download attachment from a message.

##### save_message_to_file()

```python
file_path = client.save_message_to_file(
    message_data: Dict,
    output_dir: str = "received_messages/phimail",
) -> str
```

Save message to file (JSON format) and download attachments.

##### health_check()

```python
health = client.health_check() -> Dict
```

Verify API connectivity.

**Returns:**
```python
{
    'status': 'healthy',  # Or: unhealthy
    'api_url': 'https://...',
    'username': 'your_username',
    'timestamp': '2025-10-23T10:30:00Z',
}
```

---

## Deployment

### Digital Ocean Deployment

#### 1. Environment Variables

Set these in Digital Ocean App Platform or Droplet:

```bash
# Required
PHIMAIL_API_URL=https://secure.phimail.net:8443/rest/v1/
PHIMAIL_USERNAME=your_production_username
PHIMAIL_PASSWORD=your_production_password

# Optional
PHIMAIL_STORAGE_DIR=/var/researchflo/direct_messages
PHIMAIL_LOG_DIR=/var/log/researchflo
```

#### 2. Update ResearchFlo App

```python
# In main.py
from hipaa_direct.integrations.fastapi_phimail import create_phimail_router

app = FastAPI()

# Add phiMail routes
phimail_router = create_phimail_router(
    prefix="/api/direct",
    tags=["Direct Messaging"]
)
app.include_router(phimail_router)
```

#### 3. Deploy

```bash
# Install dependencies
pip install -r requirements.txt

# Run with Gunicorn + Uvicorn
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

#### 4. Test Endpoints

```bash
# Health check
curl https://researchflo.com/api/direct/health

# Check inbox
curl https://researchflo.com/api/direct/inbox/check
```

### Background Worker Setup (Optional)

For automatic message processing:

```bash
# Install Redis
apt-get install redis-server

# Install RQ
pip install rq

# Create worker script (see Option 2 above)

# Start worker
rq worker direct_messages --url redis://localhost:6379

# Schedule periodic checks (crontab)
*/5 * * * * /usr/bin/python3 /path/to/schedule_check.py
```

---

## Security & HIPAA Compliance

### Encryption

- ✅ **TLS/SSL**: All API communication uses HTTPS
- ✅ **S/MIME**: Direct messages are encrypted end-to-end
- ✅ **At-rest**: Messages stored on phiMail servers are encrypted

### Authentication

- HTTP Basic Auth over TLS
- Credentials stored in environment variables (never in code)
- SSL certificate verification enabled by default

### Audit Logging

All operations are logged to HIPAA-compliant audit log:

```python
# Automatic audit logging via AuditLogger
{
  "timestamp": "2025-10-23T10:30:00.000Z",
  "operation": "MESSAGE_RECEIVED",
  "email": "sender@example.direct",
  "success": true,
  "user_agent": "phiMail-client/1.0",
  "ip_address": "10.0.1.5"
}
```

Logs location: `logs/hipaa_audit.log`

### Access Control

**Recommendations:**
1. Use environment-based credentials (production vs. sandbox)
2. Rotate passwords quarterly
3. Use SSL certificate pinning for production
4. Implement IP whitelisting if possible
5. Monitor audit logs for suspicious activity

### PHI Handling

**CRITICAL:** Messages contain PHI (Protected Health Information)

- ✅ Store messages in encrypted filesystem
- ✅ Use secure database with encryption at rest
- ✅ Implement access controls (role-based)
- ✅ Enable audit logging for all access
- ✅ Delete messages after processing (or archive securely)
- ✅ Never log message content (only metadata)

---

## Testing

### Unit Tests

```bash
# Run unit tests
pytest tests/test_phimail_client.py -v
```

### Integration Tests

```bash
# Test with sandbox environment
export PHIMAIL_API_URL=https://sandbox.phimaildev.com:8443/rest/v1/
export PHIMAIL_USERNAME=sandbox_user
export PHIMAIL_PASSWORD=sandbox_pass

PYTHONPATH=src python3 examples/phimail_demo.py
```

### Manual Testing

```bash
# Start demo FastAPI app
PYTHONPATH=src uvicorn examples.fastapi_phimail_demo:app --reload

# Check health
curl http://localhost:8000/api/direct/health

# Check inbox
curl http://localhost:8000/api/direct/inbox/check

# Fetch messages
curl -X POST http://localhost:8000/api/direct/inbox/fetch?limit=10

# Send test message
curl -X POST http://localhost:8000/api/direct/outbox/send \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "resflo@hixny.net",
    "recipients": ["test.resflo@hixny.net"],
    "subject": "Test Message",
    "body": "This is a test Direct message",
    "request_delivery_status": true
  }'

# Search directory
curl "http://localhost:8000/api/direct/directory/search?query=test&limit=10"
```

---

## Comparison: phiMail vs POP3/IMAP

| Feature | phiMail REST API | POP3/IMAP |
|---------|------------------|-----------|
| **Protocol** | REST (HTTPS) | Email protocols |
| **Sending** | ✅ Full support | ❌ HIXNY disabled |
| **Receiving** | ✅ Queue-based | ✅ Works |
| **Delivery Status** | ✅ Real-time tracking | ❌ Not available |
| **Directory Search** | ✅ Built-in | ❌ Not available |
| **Message Format** | JSON | MIME/RFC822 |
| **Acknowledgment** | ✅ Explicit ACK | Delete or mark read |
| **Complexity** | Low (HTTP requests) | High (email protocols) |
| **Reliability** | High (queue-based) | Medium (connection issues) |
| **HIPAA Compliance** | ✅ Built-in | ⚠️ Must implement |

**Recommendation:** Use **phiMail REST API** for production. It's simpler, more reliable, and supports both sending and receiving.

---

## Troubleshooting

### Connection Errors

```
Error: Connection refused
```

**Solution:** Check API URL and network connectivity
```bash
curl -v https://sandbox.phimaildev.com:8443/rest/v1/inbox
```

### Authentication Errors

```
Error: HTTP 401: Unauthorized
```

**Solution:** Verify credentials
```bash
export PHIMAIL_USERNAME=your_username
export PHIMAIL_PASSWORD=your_password
```

### SSL Certificate Errors

```
Error: SSL verification failed
```

**Solution:** For sandbox only, disable SSL verification:
```python
client = PhiMailClient(..., verify_ssl=False)
```

**WARNING:** Never disable SSL verification in production!

### Message Not Found

```
Error: HTTP 404: Message not found
```

**Solution:** Message may have been acknowledged already. Check inbox:
```python
messages = client.check_inbox()
print([msg['id'] for msg in messages])
```

---

## Support

### Documentation
- phiMail API docs: See PDF in project root
- ResearchFlo: Internal wiki

### Contact
- phiMail Support: support@emrdirect.com
- ResearchFlo Team: [Your contact info]

### Resources
- [Direct Trust](https://directtrust.org/)
- [ONC Direct Project](https://www.healthit.gov/topic/direct-project)

---

## Next Steps

1. ✅ **Review this document**
2. ✅ **Set up sandbox credentials** with phiMail
3. ✅ **Run demo script** to test connectivity
4. ✅ **Integrate into ResearchFlo** (3 lines of code!)
5. ✅ **Test in staging** environment
6. ✅ **Deploy to production** on Digital Ocean
7. ✅ **Set up monitoring** and audit logging
8. ✅ **Train team** on Direct messaging workflows

---

## Appendix

### Sample Message

```json
{
  "id": "queue-12345",
  "messageId": "<abc123@phimail>",
  "from": "sender@clinic.direct",
  "to": ["resflo@hixny.net"],
  "subject": "Patient Referral",
  "receivedDate": "2025-10-23T10:30:00Z",
  "size": 245678,
  "body": "Please see attached patient referral form...",
  "attachments": [
    {
      "id": "att-001",
      "filename": "referral.pdf",
      "content_type": "application/pdf",
      "size": 234567
    }
  ],
  "hasAttachments": true
}
```

### Sample Directory Entry

```json
{
  "directAddress": "doctor@clinic.direct",
  "name": "Dr. Jane Smith",
  "npi": "1234567890",
  "organization": "ABC Medical Clinic",
  "specialty": "Cardiology",
  "address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zip": "10001"
  }
}
```

---

**Document Version:** 1.0
**Last Updated:** 2025-10-23
**Author:** ResearchFlo Development Team
