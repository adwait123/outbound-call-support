from .common import logger


async def write_trace(
        occurred_at: str, conversation_id: str, message_type: str, message: dict,
        should_redact: bool = False, is_unit_test=False, trace_id: int = None
):
    """
    Simple trace logging for outbound calls - direct logging without queue processing.
    """
    # For minimal memory usage, just log essential information directly
    logger.info(f"Trace: {conversation_id} | {message_type} | {occurred_at}")


async def init_trace_system():
    """Initialize minimal trace system - no background processing needed."""
    logger.info("Minimal trace system initialized")


async def shutdown_trace_system():
    """Shutdown minimal trace system - no cleanup needed."""
    logger.info("Minimal trace system shutdown complete")