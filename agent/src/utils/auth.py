import os
from .common import logger

# Backend API configuration
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
AGENT_API_KEY = os.environ.get("AGENT_API_KEY", "agent-key-change-this-in-production")


def get_auth_headers():
    """Get authentication headers with API key"""
    return {"X-API-Key": AGENT_API_KEY}