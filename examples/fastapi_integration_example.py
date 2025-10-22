"""
Example: How to integrate HIPAA Direct Messaging into a FastAPI app (like ResearchFlo).

This shows how to add the Direct messaging router to an existing FastAPI application.
"""

from fastapi import FastAPI
from hipaa_direct.integrations.fastapi_service import create_direct_messaging_router, DirectMessageConfig

# Example 1: Basic integration with environment variables
app = FastAPI(title="ResearchFlo with Direct Messaging")

# Add Direct messaging routes (uses .env configuration)
direct_router = create_direct_messaging_router()
app.include_router(direct_router)


# Example 2: Integration with custom configuration
def create_app_with_custom_config():
    """Create app with custom Direct messaging configuration."""
    app = FastAPI(title="ResearchFlo with Direct Messaging")

    # Custom configuration
    config = DirectMessageConfig(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="sender@direct.example.com",
        smtp_password="password",
        smtp_use_tls=True,
        sender_email="sender@direct.example.com",
        sender_cert_path="certs/sender.crt",
        sender_key_path="certs/private/sender.key",
        cert_dir="certs",
        log_dir="logs",
    )

    # Add Direct messaging routes with custom config
    direct_router = create_direct_messaging_router(
        config=config,
        prefix="/api/v1/direct",  # Custom prefix
        tags=["HIPAA Direct Messaging"]
    )

    app.include_router(direct_router)

    return app


# Example 3: Integration into existing ResearchFlo app structure
# This is how you would add it to /var/www/researchflo/src/clinres/app.py
"""
# In your existing ResearchFlo app.py:

from fastapi import FastAPI
from hipaa_direct.integrations.fastapi_service import create_direct_messaging_router

# Your existing app
app = FastAPI()

# ... your existing routes ...

# Add Direct messaging
direct_router = create_direct_messaging_router(
    prefix="/api/direct",
    tags=["Direct Messaging"]
)
app.include_router(direct_router)
"""


if __name__ == "__main__":
    import uvicorn

    # Run the example app
    uvicorn.run(app, host="0.0.0.0", port=8000)
