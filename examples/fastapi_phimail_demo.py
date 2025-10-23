"""
Demo FastAPI app with phiMail Direct messaging integration.

This shows how to integrate phiMail into ResearchFlo using the FastAPI router.

Run with:
    PYTHONPATH=src uvicorn examples.fastapi_phimail_demo:app --reload

Then test with:
    # Health check
    curl http://localhost:8000/api/direct/health

    # Check inbox
    curl http://localhost:8000/api/direct/inbox/check

    # Fetch messages
    curl -X POST http://localhost:8000/api/direct/inbox/fetch

    # Send message
    curl -X POST http://localhost:8000/api/direct/outbox/send \
      -H "Content-Type: application/json" \
      -d '{
        "sender": "your-sender@example.direct",
        "recipients": ["recipient@example.direct"],
        "subject": "Test Message",
        "body": "This is a test Direct message",
        "request_delivery_status": true
      }'

    # Search directory
    curl "http://localhost:8000/api/direct/directory/search?query=test&limit=10"

    # Get stats
    curl http://localhost:8000/api/direct/stats
"""

from fastapi import FastAPI
from dotenv import load_dotenv
import sys
sys.path.insert(0, 'src')

from hipaa_direct.integrations.fastapi_phimail import create_phimail_router

# Load environment
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="ResearchFlo with phiMail Direct Messaging",
    description="HIPAA-compliant Direct messaging via phiMail REST API",
    version="1.0.0",
)

# Add phiMail Direct messaging routes
phimail_router = create_phimail_router(
    prefix="/api/direct",
    tags=["phiMail Direct Messaging"]
)
app.include_router(phimail_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "ResearchFlo Direct Messaging API (phiMail)",
        "status": "operational",
        "endpoints": {
            "health": "/api/direct/health",
            "inbox_check": "/api/direct/inbox/check",
            "inbox_fetch": "/api/direct/inbox/fetch",
            "send_message": "/api/direct/outbox/send",
            "message_status": "/api/direct/outbox/status/{message_id}",
            "directory_search": "/api/direct/directory/search",
            "statistics": "/api/direct/stats",
            "docs": "/docs",
        },
        "advantages": [
            "Clean REST API (no email protocol complexity)",
            "Both send AND receive messages",
            "Delivery status tracking",
            "Provider directory search",
            "Queue-based with acknowledgment",
            "No MIME parsing required",
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
