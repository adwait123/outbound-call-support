import json
import asyncio
import aiohttp
from dataclasses import dataclass, field
from typing import AsyncIterable, List, Dict
from enum import StrEnum
from pydantic import BaseModel, Field
from pydantic_core import from_json
from livekit import agents, rtc

from .common import logger, is_console_mode, get_timestamp_iso_berlin, MESSAGE_TYPE_REASONING_USER_RESPONSE, MESSAGE_TYPE_AGENT, MESSAGE_TYPE_USER, ROLE_ASSISTANT
from .auth import get_auth_headers, BACKEND_URL
from .tracing import write_trace


@dataclass
class DeviceInfo:
    device_id: str | None = None
    device_firmware_version: str | None = None


@dataclass
class MySessionInfo:
    conversation_id: str | None = "tonies-conversation"
    # tenant info
    tenant_id: str | None = None
    # user info
    user_id: str | None = "tonies-user"
    country: str | None = None
    app_version: str | None = None
    all_devices: Dict[str, DeviceInfo] = field(default_factory=dict)
    # session-related info
    consent_to_record: bool | None = None
    device_id: str | None = None
    figurine_name: str | None = None
    log_access_count: int = 0
    # mocking-related info
    mock_log_guidance: dict | None = None


class FrustrationLevel(StrEnum):
    low = 'low'
    medium = 'medium'
    high = 'high'


class ResponseFormat(BaseModel):
    user_frustration_level: FrustrationLevel = Field(..., description="The user's current frustration level.")
    number_of_attempts: int = Field(..., description="How many times the user has attempted to solve the problem.")
    response: str = Field(..., description="The assistant's response to the user.")


async def process_structured_output(text_stream: AsyncIterable[str]) -> AsyncIterable[str]:
    """Process structured LLM output for TTS streaming"""
    logger.info(f"inside process_structured_output: {text_stream}")

    last_response = ""
    acc_text = ""

    async for chunk in text_stream:
        acc_text += chunk
        try:
            resp: ResponseFormat = from_json(acc_text, allow_partial="trailing-strings")
        except ValueError:
            continue

        if not resp.get("response"):
            continue

        new_delta = resp["response"][len(last_response) :]
        if new_delta:
            yield new_delta
        last_response = resp["response"]


async def notify_session_end(userdata: MySessionInfo, is_unit_test: bool = False):
    """Notify the backend that the session ended"""
    logger.info(f"Inside notify_session_end")
    
    if is_unit_test:
        pass
    else:
        # Skip API call in console mode
        if is_console_mode():
            logger.info("Skipping session end notification in console mode")
            return

    try:
        # Prepare request data
        request_data = {
            "conversation_id": userdata.conversation_id,
            "tenant_id": userdata.tenant_id,
            "user_id": userdata.user_id,
            "device_id": userdata.device_id,
            "agent_id": "nuvu-agent-1",
            "product_id": None,  # Leave as None for now
            "total_tokens": None  # Leave as None for now
        }
        
        # Send to backend API using dedicated session
        headers = {
            **get_auth_headers(),
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/api/agent/conversations/end",
                json=request_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    logger.info(f"Session end notification sent successfully: {userdata.conversation_id}")
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to send session end notification: {response.status} - {error_text}")
                
    except Exception as e:
        logger.exception(f"Error in notify_session_end: {str(e)}")


async def send_ui_trigger(room: rtc.Room, action: str, data: dict = None):
    """Send UI trigger to frontend using the room reference"""
    try:
        message = {
            "type": "ui_trigger",
            "action": action
        }

        # Add additional data if provided
        if data:
            message.update(data)

        logger.info(f"📤 Attempting to send UI trigger: {action}")

        await room.local_participant.publish_data(
            json.dumps(message).encode('utf-8'),
            reliable=True
        )

        logger.info(f"📨 SUCCESS: Sent UI trigger via stored room: {action}")
    except Exception as e:
        logger.error(f"❌ Failed to send UI trigger: {e}")


async def on_shutdown():
    """Generic shutdown function for cleanup tasks."""
    from .tracing import shutdown_trace_system
    await shutdown_trace_system()


async def on_conversation_item_added(event: agents.ConversationItemAddedEvent, session: agents.AgentSession):
    """Handle conversation item added events for tracing"""
    logger.info(f"on_conversation_item_added: {event}")

    if session.userdata.consent_to_record:
        content = event.item.text_content

        if event.item.role == ROLE_ASSISTANT:  # write reasoning
            try:
                assistant_response = ResponseFormat(**from_json(content, allow_partial="trailing-strings"))
                reasoning = assistant_response.model_dump(exclude={"response"})
                content = assistant_response.response
            except Exception as e:
                logger.error(f"Failed to parse assistant response format: {e}")
                logger.error(f"Raw content: {content}")
                # Create fallback response with default values
                assistant_response = ResponseFormat(
                    user_frustration_level=FrustrationLevel.medium,
                    number_of_attempts=-1,
                    response="Can you say that again, please?"
                )
                reasoning = assistant_response.model_dump(exclude={"response"})
                content = assistant_response.response
            await write_trace(
                occurred_at=get_timestamp_iso_berlin(),
                conversation_id=session.userdata.conversation_id,
                message_type=MESSAGE_TYPE_REASONING_USER_RESPONSE,
                message=reasoning,
            )

        message_type = MESSAGE_TYPE_AGENT if event.item.role == ROLE_ASSISTANT else MESSAGE_TYPE_USER
        await write_trace(
            occurred_at=get_timestamp_iso_berlin(),
            conversation_id=session.userdata.conversation_id,
            message_type=message_type,
            message={"text": content},
            should_redact=True
        )