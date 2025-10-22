"""
Demo FastAPI app with Direct message receiving.

Shows how to integrate the Direct message receiver into ResearchFlo.

Run with:
    PYTHONPATH=src uvicorn examples.fastapi_receiver_demo:app --reload

Then test with:
    curl http://localhost:8000/api/direct/health
    curl http://localhost:8000/api/direct/check
    curl -X POST http://localhost:8000/api/direct/fetch
"""

from fastapi import FastAPI
from dotenv import load_dotenv
import sys
sys.path.insert(0, 'src')

from hipaa_direct.integrations.fastapi_receiver import create_direct_receiver_router

# Load environment
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="ResearchFlo with Direct Messaging",
    description="HIPAA-compliant Direct message receiving for clinical research",
    version="1.0.0",
)

# Add Direct messaging routes
direct_router = create_direct_receiver_router(
    prefix="/api/direct",
    tags=["Direct Messaging"]
)
app.include_router(direct_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "ResearchFlo Direct Messaging API",
        "status": "operational",
        "endpoints": {
            "health": "/api/direct/health",
            "check_messages": "/api/direct/check",
            "fetch_messages": "/api/direct/fetch",
            "statistics": "/api/direct/stats",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
