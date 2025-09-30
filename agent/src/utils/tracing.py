import asyncio
import aiohttp
import textwrap
from dataclasses import dataclass
from typing import List
from livekit import agents
from livekit.plugins import openai

from .common import logger, is_console_mode, MESSAGE_TYPE_USER, MESSAGE_TYPE_AGENT


# Global trace system infrastructure
trace_queue: asyncio.Queue = None
trace_session: aiohttp.ClientSession = None
trace_consumers: List[asyncio.Task] = []
N_WRITE_TRACE_CONSUMERS = 5


@dataclass
class TraceItem:
    occurred_at: str
    conversation_id: str
    message_type: str
    message: dict
    should_redact: bool = False
    is_unit_test: bool = False
    trace_id: int = None


async def write_trace(
        occurred_at: str, conversation_id: str, message_type: str, message: dict,
        should_redact: bool = False, is_unit_test=False, trace_id: int = None
):
    """
    Add a trace item to the queue for background processing.
    """
    global trace_queue
    
    if trace_queue is None:
        logger.error("Trace system not initialized. Call init_trace_system() first.")
        return
    
    item = TraceItem(
        occurred_at=occurred_at,
        conversation_id=conversation_id,
        message_type=message_type,
        message=message,
        should_redact=should_redact,
        is_unit_test=is_unit_test,
        trace_id=trace_id
    )
    
    try:
        await trace_queue.put(item)
    except asyncio.QueueFull:
        logger.error(f"Trace queue is full, dropping trace: {conversation_id}, {message_type}")
    except Exception as e:
        logger.error(f"Error adding trace to queue: {str(e)}")


async def redact(text_content: str):
    """Redact personally identifiable information from text content"""
    logger.info(f"Inside redact. Text content: {text_content}")

    system_prompt = textwrap.dedent("""
        Redact any personally identifiable information (PII) from the given text, replacing each PII token with a clear, bracketed label indicating its type (e.g., [Address], [Credit card], [Phone number], [Email], [Social Security Number], etc.). Ensure all forms of PII are identified and properly replaced. If multiple PII types appear, apply the relevant label for each. Reason step-by-step to identify and classify each PII instance before producing the redacted output. Persist until all objectives are met and the output text contains no remaining PII.
        
        Output Format:
        - Return the fully redacted text as a single string, with every PII instance replaced by its type in square brackets.
        
        Example:
        Input: "John Doe lives at 123 Main St., Springfield. His phone number is 555-123-4567 and his email is johndoe@email.com."
        Reasoning:  
        - Detect "John Doe" as a name → [Name]  
        - "123 Main St., Springfield" as an address → [Address]  
        - "555-123-4567" as a phone number → [Phone number]  
        - "johndoe@email.com" as an email → [Email]
        Output: "[Name] lives at [Address]. His phone number is [Phone number] and his email is [Email]."
        
        (For longer inputs, ensure every PII token is handled. Use clear placeholders based on PII type in every instance.)
        
        Important:  
        - Step-by-step reasoning to detect and classify PII before returning the redacted text.  
        - Output ONLY the single redacted text, no extra commentary or metadata.
        
        Important instructions and objective reminder:  
        Redact all PII in the text by replacing tokens with clearly bracketed PII-type labels; include every PII kind and reason step-by-step before final output. 
        
        Note: Don't output Reasoning. Only output the fully redacted string.
    """)

    chat_ctx = agents.ChatContext([
        agents.ChatMessage(
            type="message",
            role="system",
            content=[system_prompt]
        ),
        agents.ChatMessage(type="message", role="user", content=[f"""Redact this text: \n\n{text_content}"""])
    ])

    llm = openai.LLM(model="gpt-4.1-mini")

    response = ""
    try:
        async with llm.chat(chat_ctx=chat_ctx) as stream:
            async for chunk in stream:
                if not chunk:
                    continue
                content = getattr(chunk.delta, 'content', None) if hasattr(chunk, 'delta') else str(chunk)
                if content:
                    response += content
        logger.info(f"Redacted: {response}")

    except Exception as e:
        logger.error(f"Error inside redaction: {str(e)}")

    return response


async def trace_consumer():
    """Consumer function that processes trace items from the queue."""
    global trace_queue, trace_session
    
    while True:
        try:
            # Get trace item from queue
            item: TraceItem = await trace_queue.get()
            
            # Skip tracing in console mode
            if item.is_unit_test:
                pass  # if testing write_trace, continue, since write_trace is being tested
            else:
                if is_console_mode():  # if console mode, then skip writing trace
                    logger.info(f"Skipping trace in console mode: {item.conversation_id}, {item.message_type}")
                    trace_queue.task_done()
                    continue

            content = item.message
            if item.should_redact and item.message_type in {MESSAGE_TYPE_USER, MESSAGE_TYPE_AGENT}:
                try:
                    # Redact text content
                    # content["text"] = await redact(content["text"])
                    content["text"] = content["text"]  # no redaction for now
                except Exception as e:
                    logger.error(f"Failed to redact: {str(e)}")

            # For outbound sales calls, just log the trace locally
            logger.info(f"Trace: {item.conversation_id} | {item.message_type} | {item.occurred_at}")
            
            # Mark task as done
            trace_queue.task_done()
            
        except asyncio.CancelledError:
            logger.info("Trace consumer cancelled")
            break
        except Exception as e:
            logger.error(f"Unexpected error in trace_consumer: {str(e)}")
            # Continue running even if there's an error


async def init_trace_system():
    """Initialize the trace system with queue, session, and consumers."""
    global trace_queue, trace_session, trace_consumers
    
    # Create queue
    trace_queue = asyncio.Queue(maxsize=100)
    
    # Create shared HTTP session with proper configuration
    connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
    timeout = aiohttp.ClientTimeout(total=30)
    trace_session = aiohttp.ClientSession(
        connector=connector,
        timeout=timeout
    )
    
    # Start consumer tasks
    trace_consumers = []
    for i in range(N_WRITE_TRACE_CONSUMERS):
        task = asyncio.create_task(trace_consumer())
        task.set_name(f"trace_consumer_{i}")
        trace_consumers.append(task)
    
    logger.info(f"Trace system initialized with {N_WRITE_TRACE_CONSUMERS} consumers")


async def shutdown_trace_system():
    """Shutdown the trace system by cancelling consumers and closing session."""
    global trace_queue, trace_session, trace_consumers
    
    logger.info("Shutting down trace system...")
    
    # Cancel all consumer tasks
    for task in trace_consumers:
        task.cancel()
    
    # Wait for consumers to finish
    if trace_consumers:
        await asyncio.gather(*trace_consumers, return_exceptions=True)
    
    # Process any remaining items in queue (with timeout)
    if trace_queue:
        try:
            # Wait for queue to be empty, but with a timeout
            await asyncio.wait_for(trace_queue.join(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for trace queue to empty during shutdown")
    
    # Close HTTP session
    if trace_session:
        await trace_session.close()
    
    # Reset globals
    trace_consumers.clear()
    trace_queue = None
    trace_session = None
    
    logger.info("Trace system shutdown complete")