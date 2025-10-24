"""
Hybrid FastAPI Demo - ResearchFlo Integration

This shows how to integrate the unified Direct messaging router into ResearchFlo.
The router automatically uses the backend specified in environment variables.

Run with:
    # Use IMAP (default - recommended for HIXNY)
    export DIRECT_RECEIVER_BACKEND=imap
    PYTHONPATH=src uvicorn examples.fastapi_hybrid_demo:app --reload

    # Switch to phiMail (when ready)
    export DIRECT_RECEIVER_BACKEND=phimail
    PYTHONPATH=src uvicorn examples.fastapi_hybrid_demo:app --reload

Then test:
    # Health check (shows current backend)
    curl http://localhost:8000/api/direct/health

    # Check configuration
    curl http://localhost:8000/api/direct/config

    # Check messages
    curl http://localhost:8000/api/direct/check

    # Fetch messages
    curl -X POST http://localhost:8000/api/direct/fetch?limit=5

    # Send message (phiMail only)
    curl -X POST http://localhost:8000/api/direct/send \
      -H "Content-Type: application/json" \
      -d '{
        "sender": "your-sender@example.direct",
        "recipients": ["recipient@example.direct"],
        "subject": "Test",
        "body": "Test message"
      }'
"""

from fastapi import FastAPI
from dotenv import load_dotenv
import sys
import os
sys.path.insert(0, 'src')

from hipaa_direct.integrations.fastapi_unified import create_unified_router

# Load environment
load_dotenv()

# Get current backend
backend = os.getenv('DIRECT_RECEIVER_BACKEND', 'imap').upper()

# Create FastAPI app
app = FastAPI(
    title=f"ResearchFlo Direct Messaging ({backend})",
    description=f"HIPAA-compliant Direct messaging - Currently using: {backend}",
    version="1.0.0",
)

# Add unified Direct messaging router
# This automatically uses the backend specified in DIRECT_RECEIVER_BACKEND env var
unified_router = create_unified_router(
    prefix="/api/direct",
    tags=["Direct Messaging"]
)
app.include_router(unified_router)


@app.get("/")
async def root():
    """Root endpoint showing current configuration."""
    return {
        "service": "ResearchFlo Direct Messaging API",
        "status": "operational",
        "current_backend": backend,
        "endpoints": {
            "health": "/api/direct/health",
            "config": "/api/direct/config",
            "check_messages": "/api/direct/check",
            "fetch_messages": "/api/direct/fetch",
            "send_message": "/api/direct/send (phiMail only)",
            "send_status": "/api/direct/send/status/{id} (phiMail only)",
            "directory_search": "/api/direct/directory/search (phiMail only)",
            "statistics": "/api/direct/stats",
            "docs": "/docs",
        },
        "features": {
            "receiving": {
                "enabled": True,
                "backend": backend,
            },
            "sending": {
                "enabled": backend == "PHIMAIL",
                "note": "Configure phiMail to enable sending",
            },
        },
        "how_to_switch": {
            "description": "Change backend by setting environment variable",
            "example": "export DIRECT_RECEIVER_BACKEND=imap|pop3|phimail",
            "no_code_changes": "✅ Router automatically adapts to new backend",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
