# ResearchFlo Integration Guide

**How to add Direct Messaging to ResearchFlo in 5 minutes**

---

## Recommended Approach: Separate Package ✅

Keep `DirectMessage` as a separate package that ResearchFlo depends on.

### Why This is Better:
- ✅ **Clean separation** - Direct messaging is its own service
- ✅ **Reusable** - Other apps can use it
- ✅ **Independent updates** - Update messaging without touching ResearchFlo
- ✅ **3-line integration** - Minimal code changes
- ✅ **Easier maintenance** - Clear boundaries

---

## Step 1: Add to ResearchFlo Requirements

### Option A: Install from GitHub (Recommended for Now)

```bash
# researchflo/requirements.txt

# Add this line:
git+https://github.com/jacobmr/DirectMessage.git@main#egg=hipaa-direct[fastapi]

# Note: [fastapi] installs FastAPI integration extras
```

### Option B: Install from Local Path (Development)

```bash
# For local development/testing
-e /path/to/DirectMessage[fastapi]
```

### Option C: Publish to PyPI (Future)

```bash
# After publishing to PyPI:
hipaa-direct[fastapi]>=1.0.0
```

---

## Step 2: Integrate into ResearchFlo

### In your main FastAPI app (e.g., `main.py` or `app.py`):

```python
from fastapi import FastAPI
from hipaa_direct.integrations.fastapi_unified import create_unified_router

app = FastAPI(
    title="ResearchFlo",
    # ... your existing config
)

# Add Direct messaging router
direct_router = create_unified_router(
    prefix="/api/direct",
    tags=["Direct Messaging"]
)
app.include_router(direct_router)

# ... rest of your routes
```

**That's it! 3 lines of code.**

---

## Step 3: Configure Environment Variables

### Local Development (`.env`)

```bash
# Backend Selection
DIRECT_RECEIVER_BACKEND=imap

# IMAP Configuration (HIXNY)
POP3_HOST=hixny.net
POP3_PORT=993
POP3_USER=resflo
POP3_PASSWORD=Hdnb63456Mookie!
POP3_USE_SSL=true

# phiMail Configuration (optional - for sending)
# PHIMAIL_API_URL=https://secure.phimail.net:8443/rest/v1/
# PHIMAIL_USERNAME=your_username
# PHIMAIL_PASSWORD=your_password

# Storage
DIRECT_STORAGE_DIR=./received_messages
DIRECT_LOG_DIR=./logs
```

### Production (Digital Ocean App Platform)

Set these environment variables in Digital Ocean:

```
DIRECT_RECEIVER_BACKEND=imap
POP3_HOST=hixny.net
POP3_PORT=993
POP3_USER=resflo
POP3_PASSWORD=<secret>
POP3_USE_SSL=true
DIRECT_STORAGE_DIR=/var/researchflo/direct_messages
DIRECT_LOG_DIR=/var/log/researchflo
```

---

## Step 4: Test Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run ResearchFlo
uvicorn main:app --reload

# Test Direct messaging endpoints
curl http://localhost:8000/api/direct/health
curl http://localhost:8000/api/direct/check
curl -X POST http://localhost:8000/api/direct/fetch
```

---

## Step 5: Deploy to Digital Ocean

```bash
# Commit changes
git add requirements.txt main.py
git commit -m "Add HIPAA Direct messaging integration"
git push origin main

# Digital Ocean auto-deploys

# Verify
curl https://researchflo.com/api/direct/health
```

---

## Available Endpoints

After integration, these endpoints are automatically available:

```bash
# Health check
GET /api/direct/health

# Check message count
GET /api/direct/check

# Fetch messages
POST /api/direct/fetch?limit=10

# Send message (phiMail only)
POST /api/direct/send

# Get config
GET /api/direct/config

# Statistics
GET /api/direct/stats

# API documentation
GET /docs  # FastAPI auto-generates docs
```

---

## Switching Backends

### Use IMAP (Current - Recommended)

```bash
export DIRECT_RECEIVER_BACKEND=imap
# Restart app
```

### Switch to phiMail (When Ready)

```bash
export DIRECT_RECEIVER_BACKEND=phimail
# Add phiMail credentials
export PHIMAIL_API_URL=https://secure.phimail.net:8443/rest/v1/
export PHIMAIL_USERNAME=your_username
export PHIMAIL_PASSWORD=your_password
# Restart app
```

**No code changes needed!**

---

## Custom Integration (If Needed)

If you need custom behavior, you can configure the router:

```python
from hipaa_direct.integrations.fastapi_unified import (
    create_unified_router,
    UnifiedConfig,
)

# Custom configuration
config = UnifiedConfig()
config.backend = "imap"
config.storage_dir = "/custom/path"

# Create router with custom config
direct_router = create_unified_router(
    config=config,
    prefix="/api/direct",
    tags=["Direct Messaging"]
)

app.include_router(direct_router)
```

---

## Using the Client Directly

If you need to use Direct messaging in your own code:

```python
from hipaa_direct.integrations.unified_receiver import UnifiedDirectReceiver

# Get receiver (automatically uses env vars)
receiver = UnifiedDirectReceiver.from_env()

# Check messages
count = receiver.get_message_count()

# Fetch messages
messages = receiver.fetch_messages(limit=10)

# Process messages
for msg in messages:
    print(f"From: {msg['from']}")
    print(f"Subject: {msg['subject']}")

    # Save to custom location
    receiver.save_message(msg, "custom/path")
```

---

## Background Worker (Optional)

For periodic message checking without blocking web requests:

```python
# worker.py
from hipaa_direct.integrations.unified_receiver import UnifiedDirectReceiver
from rq import Queue
from redis import Redis

def check_messages():
    """Background job to check for new messages."""
    receiver = UnifiedDirectReceiver.from_env()
    messages = receiver.fetch_messages()

    for msg in messages:
        # Process message
        process_direct_message(msg)

    return len(messages)

# Schedule every 5 minutes
redis_conn = Redis()
queue = Queue('direct_messages', connection=redis_conn)
queue.enqueue(check_messages, ttl=300)
```

Start worker:
```bash
rq worker direct_messages
```

---

## Monitoring

### Health Checks

```python
# Add to ResearchFlo health check
@app.get("/health")
async def health():
    # Check Direct messaging
    direct_health = requests.get("http://localhost:8000/api/direct/health").json()

    return {
        "researchflo": "healthy",
        "direct_messaging": direct_health["status"],
    }
```

### Logging

All Direct messaging operations are automatically logged to:
```
{DIRECT_LOG_DIR}/hipaa_audit.log
```

Example log entry:
```json
{
  "timestamp": "2025-10-23T10:30:00.000Z",
  "operation": "MESSAGE_RECEIVED",
  "email": "sender@example.direct",
  "success": true,
  "user_agent": "DirectMessage/1.0",
  "ip_address": "10.0.1.5"
}
```

---

## Troubleshooting

### ImportError: No module named 'hipaa_direct'

```bash
# Make sure package is installed
pip install -r requirements.txt

# Or install directly
pip install git+https://github.com/jacobmr/DirectMessage.git#egg=hipaa-direct[fastapi]
```

### Connection Errors

```bash
# Check configuration
curl http://localhost:8000/api/direct/config

# Verify environment variables
echo $DIRECT_RECEIVER_BACKEND
echo $POP3_HOST
echo $POP3_USER
```

### Wrong Backend

```bash
# Check current backend
curl http://localhost:8000/api/direct/config

# Should show:
# {"receiving": {"backend": "imap", ...}}
```

---

## Updating DirectMessage

### Update to Latest Version

```bash
# ResearchFlo directory
pip install --upgrade git+https://github.com/jacobmr/DirectMessage.git#egg=hipaa-direct[fastapi]

# Or update requirements.txt to specific version:
git+https://github.com/jacobmr/DirectMessage.git@v1.1.0#egg=hipaa-direct[fastapi]
```

---

## Alternative: Merge into ResearchFlo (Not Recommended)

If you really want to merge the code into ResearchFlo instead:

### Steps:

1. **Copy source code:**
   ```bash
   cp -r DirectMessage/src/hipaa_direct researchflo/src/
   ```

2. **Update imports:**
   ```python
   # Instead of:
   from hipaa_direct.integrations.fastapi_unified import create_unified_router

   # Use:
   from src.hipaa_direct.integrations.fastapi_unified import create_unified_router
   ```

3. **Add dependencies to requirements.txt:**
   ```bash
   cryptography>=41.0.0
   pyOpenSSL>=23.0.0
   requests>=2.31.0
   # ... etc
   ```

**But I don't recommend this because:**
- ❌ Tight coupling
- ❌ Harder to update
- ❌ Can't reuse in other projects
- ❌ ResearchFlo repo gets larger

---

## Recommended Folder Structure

```
researchflo/                  # ResearchFlo main repo
├── requirements.txt          # Include: git+https://...DirectMessage.git
├── main.py                   # Import and use unified router
├── src/
│   ├── api/
│   ├── models/
│   └── ...
└── .env                      # DIRECT_RECEIVER_BACKEND=imap

DirectMessage/                # Separate repo (this one!)
├── src/hipaa_direct/
├── setup.py
└── ...
```

---

## Summary

### ✅ Recommended: Separate Package

1. Add to `requirements.txt`:
   ```
   git+https://github.com/jacobmr/DirectMessage.git#egg=hipaa-direct[fastapi]
   ```

2. Add to `main.py`:
   ```python
   from hipaa_direct.integrations.fastapi_unified import create_unified_router
   app.include_router(create_unified_router())
   ```

3. Set environment variables

4. Deploy!

### 🔄 Benefits:
- 3-line integration
- Independent versioning
- Easy updates
- Reusable across projects
- Clean architecture

---

**Questions? Check the main documentation:**
- DEPLOYMENT_RECOMMENDATION.md
- HYBRID_DEPLOYMENT.md
- PHIMAIL_INTEGRATION.md

**Repository:** https://github.com/jacobmr/DirectMessage

---

**Ready to integrate? Just add those 3 lines to ResearchFlo and deploy! 🚀**
