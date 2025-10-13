"""OpenAI plugin for AREA - Implements OpenAI capabilities for text completion, chat, and image generation.

This plugin integrates with OpenAI API to provide:
- Text completion using models like GPT-3.5, GPT-4
- Chat completions for conversational AI
- Image generation using DALL-E
- Content moderation

Each user provides their own API key which is securely stored and retrieved.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict
import httpx

from app.models.area import Area
from app.db.session import SessionLocal
from app.services.service_connections import get_service_connection_by_user_and_service
from app.core.encryption import decrypt_token
from app.integrations.simple_plugins.exceptions import (
    OpenAIConnectionError,
    OpenAIAPIError,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger("area")


def _get_openai_api_key(area: Area, db: Session) -> str:
    """Get decrypted OpenAI API key for a user by retrieving and decrypting their API key.
    
    Args:
        area: The Area being executed (contains user_id)
        db: Database session
        
    Returns:
        Decrypted API key string
        
    Raises:
        OpenAIConnectionError: If service connection not found or API key unavailable
    """
    # Get service connection for OpenAI
    connection = get_service_connection_by_user_and_service(db, area.user_id, "openai")
    if not connection:
        raise OpenAIConnectionError("OpenAI service connection not found. Please add your OpenAI API key.")

    # Decrypt API key
    api_key = decrypt_token(connection.encrypted_access_token)
    if not api_key:
        raise OpenAIConnectionError("OpenAI API key not available or invalid.")

    return api_key


def chat_completion_handler(area: Area, params: dict, event: dict) -> None:
    """Generate chat completions using OpenAI's chat models (e.g., GPT-3.5, GPT-4).
    
    Args:
        area: The Area being executed
        params: Action parameters:
            - model (str, optional): Model to use (default: gpt-3.5-turbo)
            - messages (list, optional): Conversation history as list of message dicts
            - prompt (str, optional): Single message to send if messages not provided
            - temperature (float, optional): Sampling temperature (0.0-2.0)
            - max_tokens (int, optional): Maximum tokens to generate
            - system_prompt (str, optional): System role prompt
        event: Event data from trigger
        
    Raises:
        OpenAIConnectionError: If API key not found/invalid
        OpenAIAPIError: If API request fails
    """
    # Validate and prepare parameters first before making database calls
    model = params.get("model") or "gpt-3.5-turbo"
    temperature = params.get("temperature", 0.7)
    max_tokens = params.get("max_tokens", 500)
    system_prompt = params.get("system_prompt", "")
    
    # Build messages array
    messages = params.get("messages", [])
    
    # If no messages provided but prompt is given, create a simple message
    if not messages and "prompt" in params:
        messages = [{"role": "user", "content": params["prompt"]}]
    
    # If system prompt provided, add it at the beginning
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages
    
    if not messages:
        raise ValueError("Either 'messages' or 'prompt' parameter must be provided")
    
    # Only create DB session when we know params are valid
    try:
        db = SessionLocal()
        
        logger.info(
            "Starting OpenAI chat completion action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "params": {k: v for k, v in params.items() if k != "api_key"},
            },
        )
        
        # Get API key
        api_key = _get_openai_api_key(area, db)
        
        # Prepare request payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Make API request using a context manager
        with httpx.Client(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0  # 30 second timeout for OpenAI requests
        ) as client:
            response = client.post("https://api.openai.com/v1/chat/completions", json=payload)
        
        if response.status_code != 200:
            error_msg = f"OpenAI API error: {response.status_code} - {response.text}"
            logger.error(
                "OpenAI chat completion failed",
                extra={
                    "area_id": str(area.id),
                    "user_id": str(area.user_id),
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )
            raise OpenAIAPIError(error_msg)
        
        result = response.json()
        
        # Extract the assistant's reply
        if result.get("choices") and len(result["choices"]) > 0:
            assistant_message = result["choices"][0]["message"]["content"]
            finish_reason = result["choices"][0].get("finish_reason", "stop")
        else:
            raise OpenAIAPIError("No choices returned from OpenAI API")
        
        logger.info(
            "OpenAI chat completion successful",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "model": model,
                "input_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                "output_tokens": result.get("usage", {}).get("completion_tokens", 0),
                "finish_reason": finish_reason,
                "response_length": len(assistant_message),
            },
        )
        
        # Store response in event for potential chaining with other actions
        event["openai.response"] = assistant_message
        event["openai.finish_reason"] = finish_reason
        event["openai.model"] = model
        event["openai.input_tokens"] = result.get("usage", {}).get("prompt_tokens", 0)
        event["openai.output_tokens"] = result.get("usage", {}).get("completion_tokens", 0)
        event["openai.total_tokens"] = result.get("usage", {}).get("total_tokens", 0)
        
        # Store full response for display in execution logs
        event["openai_data"] = {
            "response": assistant_message,
            "model": model,
            "finish_reason": finish_reason,
            "usage": result.get("usage", {}),
            "full_response": result,
        }
        
    except OpenAIConnectionError:
        # Re-raise connection errors as they are specific to this plugin
        raise
    except ValueError as e:
        logger.error(
            "Invalid parameters for chat completion",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
        )
        raise
    except Exception as e:
        logger.error(
            "Error in OpenAI chat completion",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise OpenAIAPIError(f"OpenAI API request failed: {str(e)}") from e
    finally:
        db.close()


def text_completion_handler(area: Area, params: dict, event: dict) -> None:
    """Generate text completions using OpenAI's completion models.
    
    Args:
        area: The Area being executed
        params: Action parameters:
            - model (str, optional): Model to use (default: gpt-3.5-turbo-instruct)
            - prompt (str): Input text to complete
            - temperature (float, optional): Sampling temperature (0.0-1.0)
            - max_tokens (int, optional): Maximum tokens to generate
            - stop (str or list, optional): Stop sequences
        event: Event data from trigger
        
    Raises:
        OpenAIConnectionError: If API key not found/invalid
        OpenAIAPIError: If API request fails
    """
    # Validate required parameters first before making database calls
    prompt = params.get("prompt", "")
    if not prompt:
        raise ValueError("'prompt' parameter is required for text completion")
    
    # Only create DB session when we know params are valid
    try:
        db = SessionLocal()
        
        logger.info(
            "Starting OpenAI text completion action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "params": {k: v for k, v in params.items() if k != "api_key"},
            },
        )
        
        # Get API key
        api_key = _get_openai_api_key(area, db)
        
        # Prepare parameters
        model = params.get("model") or "gpt-3.5-turbo-instruct"
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 256)
        stop = params.get("stop", None)
        
        # Prepare request payload
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if stop:
            payload["stop"] = stop
        
        # Make API request using a context manager
        with httpx.Client(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0  # 30 second timeout for OpenAI requests
        ) as client:
            response = client.post("https://api.openai.com/v1/completions", json=payload)
        
        if response.status_code != 200:
            error_msg = f"OpenAI API error: {response.status_code} - {response.text}"
            logger.error(
                "OpenAI text completion failed",
                extra={
                    "area_id": str(area.id),
                    "user_id": str(area.user_id),
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )
            raise OpenAIAPIError(error_msg)
        
        result = response.json()
        
        # Extract the completion text
        if result.get("choices") and len(result["choices"]) > 0:
            completion_text = result["choices"][0]["text"]
            finish_reason = result["choices"][0].get("finish_reason", "stop")
        else:
            raise OpenAIAPIError("No choices returned from OpenAI API")
        
        logger.info(
            "OpenAI text completion successful",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "model": model,
                "input_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                "output_tokens": result.get("usage", {}).get("completion_tokens", 0),
                "finish_reason": finish_reason,
                "response_length": len(completion_text),
            },
        )
        
        # Store response in event for potential chaining with other actions
        event["openai.response"] = completion_text
        event["openai.finish_reason"] = finish_reason
        event["openai.model"] = model
        event["openai.input_tokens"] = result.get("usage", {}).get("prompt_tokens", 0)
        event["openai.output_tokens"] = result.get("usage", {}).get("completion_tokens", 0)
        event["openai.total_tokens"] = result.get("usage", {}).get("total_tokens", 0)
        
        # Store full response for display in execution logs
        event["openai_data"] = {
            "response": completion_text,
            "model": model,
            "finish_reason": finish_reason,
            "usage": result.get("usage", {}),
            "full_response": result,
        }
        
    except OpenAIConnectionError:
        # Re-raise connection errors as they are specific to this plugin
        raise
    except ValueError as e:
        logger.error(
            "Invalid parameters for text completion",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
        )
        raise
    except Exception as e:
        logger.error(
            "Error in OpenAI text completion",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise OpenAIAPIError(f"OpenAI API request failed: {str(e)}") from e
    finally:
        db.close()


def image_generation_handler(area: Area, params: dict, event: dict) -> None:
    """Generate images using OpenAI's DALL-E.
    
    Args:
        area: The Area being executed
        params: Action parameters:
            - prompt (str): Text description of the image to generate
            - n (int, optional): Number of images to generate (1-10, default: 1)
            - size (str, optional): Size of generated images (256x256, 512x512, 1024x1024, default: 1024x1024)
            - response_format (str, optional): Format of response (url or b64_json, default: url)
        event: Event data from trigger
        
    Raises:
        OpenAIConnectionError: If API key not found/invalid
        OpenAIAPIError: If API request fails
    """
    # Validate and prepare parameters first before making database calls
    prompt = params.get("prompt", "")
    n = params.get("n", 1)
    size = params.get("size", "1024x1024")
    response_format = params.get("response_format", "url")
    
    if not prompt:
        raise ValueError("'prompt' parameter is required for image generation")
    
    # Validate parameters
    if not (1 <= n <= 10):
        raise ValueError("'n' parameter must be between 1 and 10")
    
    valid_sizes = ["256x256", "512x512", "1024x1024"]
    if size not in valid_sizes:
        raise ValueError(f"'size' parameter must be one of: {valid_sizes}")
    
    valid_formats = ["url", "b64_json"]
    if response_format not in valid_formats:
        raise ValueError(f"'response_format' parameter must be one of: {valid_formats}")
    
    # Only create DB session when we know params are valid
    try:
        db = SessionLocal()
        
        logger.info(
            "Starting OpenAI image generation action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "params": {k: v for k, v in params.items() if k != "api_key"},
            },
        )
        
        # Get API key
        api_key = _get_openai_api_key(area, db)
        
        # Prepare request payload
        payload = {
            "prompt": prompt,
            "n": n,
            "size": size,
            "response_format": response_format,
        }
        
        # Make API request using a context manager
        with httpx.Client(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0  # 30 second timeout for OpenAI requests
        ) as client:
            response = client.post("https://api.openai.com/v1/images/generations", json=payload)
        
        if response.status_code != 200:
            error_msg = f"OpenAI API error: {response.status_code} - {response.text}"
            logger.error(
                "OpenAI image generation failed",
                extra={
                    "area_id": str(area.id),
                    "user_id": str(area.user_id),
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )
            raise OpenAIAPIError(error_msg)
        
        result = response.json()
        
        # Extract image URLs or base64 data
        if result.get("data"):
            image_data_list = []
            for img_data in result["data"]:
                if response_format == "url":
                    image_data_list.append(img_data["url"])
                else:  # b64_json
                    image_data_list.append(img_data["b64_json"])
        else:
            raise OpenAIAPIError("No image data returned from OpenAI API")
        
        logger.info(
            "OpenAI image generation successful",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "num_images": n,
                "size": size,
                "response_format": response_format,
                "image_count": len(image_data_list),
            },
        )
        
        # Store response in event for potential chaining with other actions
        event["openai.image_urls"] = image_data_list
        event["openai.num_images"] = n
        event["openai.image_size"] = size
        event["openai.response_format"] = response_format
        
        # Store full response for display in execution logs
        event["openai_data"] = {
            "image_urls": image_data_list,
            "num_images": n,
            "size": size,
            "response_format": response_format,
            "model": "dall-e-3",  # OpenAI's default image generation model
            "full_response": result,
        }
        
    except OpenAIConnectionError:
        # Re-raise connection errors as they are specific to this plugin
        raise
    except ValueError as e:
        logger.error(
            "Invalid parameters for image generation",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
        )
        raise
    except Exception as e:
        logger.error(
            "Error in OpenAI image generation",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise OpenAIAPIError(f"OpenAI API request failed: {str(e)}") from e
    finally:
        db.close()


def content_moderation_handler(area: Area, params: dict, event: dict) -> None:
    """Analyze content for potential policy violations using OpenAI's moderation API.
    
    Args:
        area: The Area being executed
        params: Action parameters:
            - input (str or list): Content to moderate
            - model (str, optional): Model to use for moderation (default: text-moderation-latest)
        event: Event data from trigger
        
    Raises:
        OpenAIConnectionError: If API key not found/invalid
        OpenAIAPIError: If API request fails
    """
    # Validate and prepare parameters first before making database calls
    input_content = params.get("input", "")
    model = params.get("model") or "text-moderation-latest"
    
    if not input_content:
        raise ValueError("'input' parameter is required for content moderation")
    
    # Only create DB session when we know params are valid
    try:
        db = SessionLocal()
        
        logger.info(
            "Starting OpenAI content moderation action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "params": {k: v for k, v in params.items() if k != "api_key"},
            },
        )
        
        # Get API key
        api_key = _get_openai_api_key(area, db)
        
        # Prepare request payload
        payload = {
            "input": input_content,
            "model": model,
        }
        
        # Make API request using a context manager
        with httpx.Client(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0  # 30 second timeout for OpenAI requests
        ) as client:
            response = client.post("https://api.openai.com/v1/moderations", json=payload)
        
        if response.status_code != 200:
            error_msg = f"OpenAI API error: {response.status_code} - {response.text}"
            logger.error(
                "OpenAI content moderation failed",
                extra={
                    "area_id": str(area.id),
                    "user_id": str(area.user_id),
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )
            raise OpenAIAPIError(error_msg)
        
        result = response.json()
        
        # Extract moderation results
        if result.get("results"):
            moderation_result = result["results"][0]
            categories = moderation_result.get("categories", {})
            category_scores = moderation_result.get("category_scores", {})
            flagged = moderation_result.get("flagged", False)
        else:
            raise OpenAIAPIError("No moderation results returned from OpenAI API")
        
        logger.info(
            "OpenAI content moderation completed",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "flagged": flagged,
                "categories": categories,
                "content_length": len(str(input_content)),
            },
        )
        
        # Store response in event for potential chaining with other actions
        event["openai.moderation.flagged"] = flagged
        event["openai.moderation.categories"] = categories
        event["openai.moderation.scores"] = category_scores
        event["openai.moderation.input"] = input_content
        
        # Store full response for display in execution logs
        event["openai_data"] = {
            "moderation_result": {
                "flagged": flagged,
                "categories": categories,
                "category_scores": category_scores,
            },
            "input": input_content,
            "model": model,
            "full_response": result,
        }
        
    except OpenAIConnectionError:
        # Re-raise connection errors as they are specific to this plugin
        raise
    except ValueError as e:
        logger.error(
            "Invalid parameters for content moderation",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
        )
        raise
    except Exception as e:
        logger.error(
            "Error in OpenAI content moderation",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise OpenAIAPIError(f"OpenAI API request failed: {str(e)}") from e
    finally:
        db.close()


__all__ = [
    "chat_completion_handler",
    "text_completion_handler",
    "image_generation_handler",
    "content_moderation_handler",
]