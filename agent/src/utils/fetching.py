from livekit import agents



async def fetch_device_and_app_logs(context: agents.RunContext, device_id: str, mock_log_guidance: dict | None) -> str:
    """Fetch device and application logs for diagnostics"""
    # Placeholder function - not used for outbound sales calls
    return "No device logs available for outbound calls"


def fetch_user_info(user_id: str) -> dict:
    """Fetch user information from database"""
    # For outbound sales calls, return basic structure
    return {
        "all_devices": {},
        "country": "US",
        "app_version": "outbound_sales"
    }


def fetch_user_id_from_phone_number(user_phone_number) -> str:
    return f"lead_{user_phone_number.replace('+', '').replace('-', '')}"


def fetch_business_rules() -> str:
    """Fetch business rules and policies"""
    return "Focus on scheduling appointments efficiently and professionally for Floor Covering International."