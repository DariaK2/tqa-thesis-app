import openai
import logging
from config import YANDEX_CLOUD_FOLDER, YANDEX_API_KEY, YANDEX_CLOUD_MODEL

logger = logging.getLogger(__name__)

client = openai.OpenAI(
    api_key=YANDEX_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_CLOUD_FOLDER
)


def call_llm(messages, temperature=0, max_tokens=4000, response_format=None):
    """
    Call Yandex Cloud LLM with the given messages.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        temperature: Sampling temperature (0 for deterministic)
        max_tokens: Maximum output tokens
        response_format: Optional response format dict (e.g., {"type": "json_object"})
    
    Returns:
        str: Model response text
    """
    model_uri = f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}"
    
    try:
        kwargs = {
            "model": model_uri,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        
        logger.debug(f"LLM response length: {len(content)} characters")
        return content
        
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise
