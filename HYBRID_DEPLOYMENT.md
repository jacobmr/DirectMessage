# Hybrid Direct Messaging Deployment Guide

**Switch Between IMAP and phiMail Without Code Changes**

## Overview

The hybrid architecture lets you:
- ✅ **Start with IMAP** (HIXNY) - Working now, zero cost
- ✅ **Switch to phiMail** later - Just change one environment variable
- ✅ **No code changes** required - Same API, different backend
- ✅ **Use both simultaneously** - IMAP for receiving, phiMail for sending

---

## Quick Start

### 1. Environment Configuration

Create `.env` file with both configurations:

```bash
# Backend Selection (change this to switch!)
DIRECT_RECEIVER_BACKEND=imap    # Options: imap, pop3, phimail

# IMAP/POP3 Configuration (HIXNY)
POP3_HOST=hixny.net
POP3_PORT=993
POP3_USER=resflo
POP3_PASSWORD=Hdnb63456Mookie!
POP3_USE_SSL=true

# phiMail Configuration (for when you're ready)
PHIMAIL_API_URL=https://secure.phimail.net:8443/rest/v1/
PHIMAIL_USERNAME=your_phimail_username
PHIMAIL_PASSWORD=your_phimail_password

# Storage
DIRECT_STORAGE_DIR=received_messages
DIRECT_LOG_DIR=logs
```

### 2. Integrate into ResearchFlo

```python
from fastapi import FastAPI
from hipaa_direct.integrations.fastapi_unified import create_unified_router

app = FastAPI()

# Add unified router - automatically uses correct backend
unified_router = create_unified_router()
app.include_router(unified_router)
```

**That's it!** The router automatically uses the backend specified in `DIRECT_RECEIVER_BACKEND`.

### 3. Switch Backends

```bash
# Use IMAP (current - recommended)
export DIRECT_RECEIVER_BACKEND=imap

# Switch to phiMail (when ready)
export DIRECT_RECEIVER_BACKEND=phimail

# Restart app - no code changes needed!
```

---

## Architecture

### Unified Interface

```
┌─────────────────────────────────────────────────────────┐
│                    ResearchFlo App                      │
│                  (FastAPI + Gunicorn)                   │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│          Unified Direct Messaging Router                │
│        (fastapi_unified.py)                            │
│                                                         │
│  Same API endpoints regardless of backend:              │
│  • GET  /api/direct/check                              │
│  • POST /api/direct/fetch                              │
│  • POST /api/direct/send (phiMail only)                │
│  • GET  /api/direct/health                             │
│  • GET  /api/direct/config                             │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌──────────────────┐        ┌──────────────────┐
│  IMAP Backend    │   OR   │  phiMail Backend │
│  (HIXNY)         │        │  (EMR Direct)    │
│                  │        │                  │
│  hixny.net:993   │        │  phimail.net     │
└──────────────────┘        └──────────────────┘
```

### Message Flow

All backends use the same interface:

```python
# Check messages
GET /api/direct/check
→ Returns: {"message_count": 5, "backend": "imap"}

# Fetch messages
POST /api/direct/fetch?limit=10
→ Returns: {"messages_fetched": 10, "backend": "imap", "messages": [...]}

# Backend automatically selected from env var
```

---

## API Reference

### Receiving Endpoints (All Backends)

#### Check Messages

```bash
GET /api/direct/check
```

**Response:**
```json
{
  "message_count": 5,
  "backend": "imap",
  "account": "resflo",
  "timestamp": "2025-10-23T10:30:00Z"
}
```

**Works with:** IMAP, POP3, phiMail

#### Fetch Messages

```bash
POST /api/direct/fetch?limit=10&mark_as_read=false
```

**Parameters:**
- `limit` - Max messages to fetch (optional)
- `folder` - Folder name (IMAP only, default: INBOX)
- `mark_as_read` - Mark as read (IMAP only, default: false)
- `delete_after_fetch` - Delete after fetch (POP3 only, default: false)
- `acknowledge` - Remove from queue (phiMail only, default: true)

**Response:**
```json
{
  "messages_fetched": 10,
  "backend": "imap",
  "messages": [
    {
      "backend": "imap",
      "message_id": "<abc@example>",
      "from": "sender@example.direct",
      "to": "resflo@hixny.net",
      "subject": "Patient Report",
      "date": "2025-10-23T10:00:00Z",
      "body": "...",
      "attachments": [...],
      "size": 54321
    }
  ],
  "timestamp": "2025-10-23T10:30:00Z"
}
```

**Works with:** IMAP, POP3, phiMail

### Sending Endpoints (phiMail Only)

#### Send Message

```bash
POST /api/direct/send
```

**Request:**
```json
{
  "sender": "resflo@hixny.net",
  "recipients": ["doctor@clinic.direct"],
  "subject": "Patient Report",
  "body": "Please review attached report",
  "attachments": [
    {
      "filename": "report.pdf",
      "content_type": "application/pdf",
      "content": "base64-encoded-content"
    }
  ]
}
```

**Response:**
```json
{
  "status": "sent",
  "backend": "phimail",
  "message_id": "outbox-123",
  "timestamp": "2025-10-23T10:30:00Z"
}
```

**Note:** Returns HTTP 503 if phiMail not configured.

#### Check Send Status

```bash
GET /api/direct/send/status/{message_id}
```

**Response:**
```json
{
  "id": "outbox-123",
  "status": "delivered",
  "statusDetails": "Successfully delivered",
  "deliveryNotifications": [...]
}
```

### Utility Endpoints

#### Health Check

```bash
GET /api/direct/health
```

**Response:**
```json
{
  "backend": "imap",
  "status": "healthy",
  "details": {
    "receiving": {
      "enabled": true,
      "backend": "imap",
      "account": "resflo"
    },
    "sending": {
      "enabled": false,
      "backend": "none"
    }
  }
}
```

#### Configuration

```bash
GET /api/direct/config
```

**Response:**
```json
{
  "receiving": {
    "backend": "imap",
    "host": "hixny.net",
    "port": 993,
    "user": "resflo"
  },
  "sending": {
    "enabled": false,
    "backend": "none"
  },
  "switch_backend": {
    "how_to": "Set DIRECT_RECEIVER_BACKEND environment variable",
    "options": ["imap", "pop3", "phimail"],
    "current": "imap"
  }
}
```

---

## Deployment Scenarios

### Scenario 1: Start with IMAP (Recommended)

**Current State:**
- ✅ IMAP working with HIXNY
- ✅ Zero additional cost
- ✅ Production-ready

**Configuration:**
```bash
# .env
DIRECT_RECEIVER_BACKEND=imap
POP3_HOST=hixny.net
POP3_PORT=993
POP3_USER=resflo
POP3_PASSWORD=Hdnb63456Mookie!
```

**Features:**
- ✅ Receive messages
- ❌ Send messages (HIXNY SMTP disabled)
- ❌ Directory search
- ❌ Delivery tracking

**Deploy:**
```bash
# Digital Ocean
git push origin main  # Auto-deploy
```

---

### Scenario 2: Add phiMail for Sending

**When:** You need to send Direct messages

**Configuration:**
```bash
# .env
DIRECT_RECEIVER_BACKEND=imap  # Still use IMAP for receiving

# Add phiMail config for sending
PHIMAIL_API_URL=https://secure.phimail.net:8443/rest/v1/
PHIMAIL_USERNAME=your_username
PHIMAIL_PASSWORD=your_password
```

**Features:**
- ✅ Receive via IMAP (free)
- ✅ Send via phiMail (requires account)
- ✅ Directory search (phiMail)
- ✅ Delivery tracking (phiMail)

**How it works:**
- Receiving uses IMAP (HIXNY)
- Sending uses phiMail
- Best of both worlds!

**Deploy:**
```bash
# Just update environment variables in Digital Ocean
# No code changes needed
```

---

### Scenario 3: Switch Entirely to phiMail

**When:** You want full phiMail features

**Configuration:**
```bash
# .env
DIRECT_RECEIVER_BACKEND=phimail  # Switch to phiMail

PHIMAIL_API_URL=https://secure.phimail.net:8443/rest/v1/
PHIMAIL_USERNAME=your_username
PHIMAIL_PASSWORD=your_password
```

**Features:**
- ✅ Receive via phiMail
- ✅ Send via phiMail
- ✅ Directory search
- ✅ Delivery tracking
- ✅ Queue-based messaging

**Deploy:**
```bash
# Update environment variable in Digital Ocean
export DIRECT_RECEIVER_BACKEND=phimail

# Restart app - that's it!
```

---

## Migration Path

### Phase 1: IMAP Only (Current)

```bash
DIRECT_RECEIVER_BACKEND=imap
```

**Deployment:**
```python
# main.py (ResearchFlo)
from hipaa_direct.integrations.fastapi_unified import create_unified_router

app.include_router(create_unified_router())
```

**Available:**
- ✅ Receive messages via IMAP

### Phase 2: IMAP + phiMail Sending

```bash
DIRECT_RECEIVER_BACKEND=imap

# Add phiMail for sending
PHIMAIL_API_URL=...
PHIMAIL_USERNAME=...
PHIMAIL_PASSWORD=...
```

**No code changes needed!** The router automatically enables sending when phiMail is configured.

**Available:**
- ✅ Receive via IMAP
- ✅ Send via phiMail
- ✅ Directory search
- ✅ Delivery tracking

### Phase 3: Full phiMail (If Desired)

```bash
DIRECT_RECEIVER_BACKEND=phimail
```

**Available:**
- ✅ Receive via phiMail
- ✅ Send via phiMail
- ✅ Unified queue management

---

## Testing

### Test Current Backend

```bash
# Check which backend is active
curl http://localhost:8000/api/direct/config

# Health check
curl http://localhost:8000/api/direct/health

# Check messages
curl http://localhost:8000/api/direct/check
```

### Test Backend Switch

```bash
# Start with IMAP
export DIRECT_RECEIVER_BACKEND=imap
PYTHONPATH=src python3 examples/hybrid_demo.py

# Switch to phiMail
export DIRECT_RECEIVER_BACKEND=phimail
PYTHONPATH=src python3 examples/hybrid_demo.py
```

### Test Hybrid Mode (IMAP + phiMail)

```bash
# Configure both
export DIRECT_RECEIVER_BACKEND=imap
export PHIMAIL_API_URL=...
export PHIMAIL_USERNAME=...
export PHIMAIL_PASSWORD=...

# Start app
PYTHONPATH=src uvicorn examples.fastapi_hybrid_demo:app --reload

# Test receiving (uses IMAP)
curl http://localhost:8000/api/direct/fetch

# Test sending (uses phiMail)
curl -X POST http://localhost:8000/api/direct/send \
  -H "Content-Type: application/json" \
  -d '{"sender":"test@example.direct", "recipients":["dest@example.direct"], "subject":"Test", "body":"Test"}'
```

---

## Digital Ocean Deployment

### Environment Variables

Set in App Platform or Droplet:

```bash
# Backend selection
DIRECT_RECEIVER_BACKEND=imap

# IMAP (HIXNY)
POP3_HOST=hixny.net
POP3_PORT=993
POP3_USER=resflo
POP3_PASSWORD=<secret>

# phiMail (optional - for sending)
PHIMAIL_API_URL=https://secure.phimail.net:8443/rest/v1/
PHIMAIL_USERNAME=<secret>
PHIMAIL_PASSWORD=<secret>

# Storage
DIRECT_STORAGE_DIR=/var/researchflo/direct_messages
DIRECT_LOG_DIR=/var/log/researchflo
```

### Switching Backends in Production

1. **Update environment variable** in Digital Ocean dashboard:
   ```bash
   DIRECT_RECEIVER_BACKEND=phimail  # Change from imap to phimail
   ```

2. **Restart app** (automatic in App Platform)

3. **Verify switch:**
   ```bash
   curl https://researchflo.com/api/direct/config
   ```

**No code deployment needed!**

---

## Advantages of Hybrid Architecture

### Flexibility
- ✅ Start simple (IMAP only)
- ✅ Add features incrementally
- ✅ Switch backends without code changes
- ✅ Use best tool for each job

### Cost Control
- ✅ Use free IMAP until sending needed
- ✅ Add phiMail only when required
- ✅ No upfront commitment

### Risk Mitigation
- ✅ Test phiMail in staging first
- ✅ Easy rollback (change env var)
- ✅ Gradual migration path

### Best of Both Worlds
- ✅ IMAP: Free receiving from HIXNY
- ✅ phiMail: Advanced sending features
- ✅ Combined: Full Direct messaging capability

---

## Comparison

| Feature | IMAP Only | IMAP + phiMail | phiMail Only |
|---------|-----------|----------------|--------------|
| **Receive** | ✅ IMAP | ✅ IMAP | ✅ phiMail |
| **Send** | ❌ | ✅ phiMail | ✅ phiMail |
| **Directory** | ❌ | ✅ phiMail | ✅ phiMail |
| **Tracking** | ❌ | ✅ phiMail | ✅ phiMail |
| **Cost** | Free | IMAP free + phiMail | phiMail only |
| **Code Changes** | None | None | None |
| **Recommendation** | **Now** | **When sending needed** | **Future option** |

---

## Troubleshooting

### Wrong Backend Active

```bash
# Check current backend
curl http://localhost:8000/api/direct/config

# Verify environment variable
echo $DIRECT_RECEIVER_BACKEND

# Update if needed
export DIRECT_RECEIVER_BACKEND=imap
```

### Sending Not Available

```
Error: Sending not configured
```

**Solution:** Configure phiMail:
```bash
export PHIMAIL_API_URL=https://secure.phimail.net:8443/rest/v1/
export PHIMAIL_USERNAME=your_username
export PHIMAIL_PASSWORD=your_password
```

### Backend Connection Failed

```bash
# Check backend-specific credentials
# For IMAP:
echo $POP3_HOST $POP3_PORT $POP3_USER

# For phiMail:
echo $PHIMAIL_API_URL $PHIMAIL_USERNAME
```

---

## Next Steps

### Current Recommendation: IMAP (Phase 1)

1. ✅ **Deploy with IMAP** - Already tested and working
2. ✅ **Set environment variable:**
   ```bash
   DIRECT_RECEIVER_BACKEND=imap
   ```
3. ✅ **Integrate into ResearchFlo:**
   ```python
   app.include_router(create_unified_router())
   ```
4. ✅ **Deploy to Digital Ocean**
5. ✅ **Monitor and use!**

### When You Need Sending (Phase 2)

1. Contact EMR Direct for phiMail account
2. Add phiMail credentials to environment
3. Test in staging
4. Deploy to production
5. Sending automatically enabled!

### Full Migration (Phase 3 - Optional)

1. When ready, change one variable:
   ```bash
   DIRECT_RECEIVER_BACKEND=phimail
   ```
2. Restart app
3. Done!

---

## Summary

The hybrid architecture gives you:

- ✅ **Start immediately** with IMAP (working now)
- ✅ **Add sending later** with phiMail (when needed)
- ✅ **Zero code changes** to switch backends
- ✅ **Best of both worlds** - use IMAP + phiMail together

**All the code is ready!** Just set one environment variable to choose your path.

---

**Document Version:** 1.0
**Last Updated:** 2025-10-23
**Status:** Production Ready
**Recommended:** IMAP (Phase 1) → IMAP + phiMail (Phase 2) → Full phiMail (Phase 3 - optional)
