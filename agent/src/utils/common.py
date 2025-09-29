import os
import sys
import uuid
import logging
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+
from dotenv import load_dotenv

load_dotenv()

logger: logging.Logger = logging.getLogger(os.getenv("AGENT_NAME"))

# Message type constants to align with backend API
MESSAGE_TYPE_USER = "user"
MESSAGE_TYPE_AGENT = "agent"
MESSAGE_TYPE_REASONING_TOOL_CALL = "reasoning:tool_call"
MESSAGE_TYPE_REASONING_USER_RESPONSE = "reasoning:user_response"
MESSAGE_TYPE_TOOL = "tool"

# Role constants for LiveKit conversation items
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"


def is_console_mode():
    """Check if running in console mode (not connected to LiveKit)"""
    return len(sys.argv) > 1 and sys.argv[1] in {"console", "dev"}


def get_timestamp_iso_berlin():
    """Get current timestamp in ISO format for Berlin timezone"""
    berlin_tz = ZoneInfo("Europe/Berlin")
    now_berlin = datetime.now(tz=berlin_tz)
    return now_berlin.isoformat()


def generate_session_id():
    """Generate a custom session ID (do this ONCE per session)"""
    return str(uuid.uuid4())