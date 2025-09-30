import os
import json
import textwrap
import asyncio
import aiohttp
from livekit import agents

from .common import logger


class Perplexity:
    """Internal Perplexity API client for support documentation search"""
    
    def __init__(self):
        self.system_prompt = textwrap.dedent("""
            Search the web for the issue and provide a concise answer. 
            Your answer will be used by a Tonies customer support agent, who helps Tonies' customers with set-up and troubleshooting.
            Keep your answers clear, concise and actionable.

            ALWAYS produce your response in this form:

            Confidence: low
            Some response for the Tonies' customer support agent.

            Different values for Confidence are {low, medium, high}.
        """)

        self.model = "sonar"
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}",
            "Content-Type": "application/json"
        }

    async def search(self, query):
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": query}
            ],
            "max_tokens": 500,
            "temperature": 0.1,  # Low temperature for consistent technical advice
            "search_domain_filter": [
                "tonies.com"
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                    self.base_url, headers=self.headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    citations = result['citations']
                    result_message = json.dumps({"content": content, "citations": citations})
                    return result_message
                else:
                    error_text = await response.text()
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=error_text
                    )


# Create a singleton instance for internal use
_perplexity = Perplexity()


async def fetch_support_documentation(query: str) -> str:
    """
    Fetch support documentation for a given query.
    
    This function abstracts the implementation details of how support documentation
    is retrieved. Currently uses Perplexity API to search tonies.com.
    
    Args:
        query: The support question or issue to search for
        
    Returns:
        JSON string containing the search result with content and citations
    """
    try:
        result = await _perplexity.search(query)
        logger.info(f"Successfully fetched support documentation for query: {query}")
        return result
    except Exception as e:
        logger.error(f"Error fetching support documentation: {str(e)}")
        # Return a fallback response
        fallback_response = {
            "content": "I'm having trouble accessing the support documentation right now. Please try again or contact support directly.",
            "citations": []
        }
        return json.dumps(fallback_response)


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