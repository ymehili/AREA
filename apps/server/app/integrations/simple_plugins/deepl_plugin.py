"""DeepL plugin for AREA - Professional translation service integration.

This plugin integrates with DeepL API to provide:
- Text translation with specified source and target languages
- Automatic language detection with translation
- Language detection (translates small text sample to detect language)
- Support for 30+ languages with professional quality

Each user provides their own DeepL API key (free tier: 500,000 chars/month).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import deepl
from deepl.exceptions import DeepLException, AuthorizationException, QuotaExceededException

from app.models.area import Area
from app.services.service_connections import get_service_connection_by_user_and_service
from app.core.encryption import decrypt_token
from app.integrations.simple_plugins.exceptions import (
    DeepLAPIError,
    DeepLAuthError,
    DeepLConfigError,
    DeepLConnectionError,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger("area")


def _normalize_language_code(lang_code: str) -> str:
    """Normalize language codes to meet DeepL API requirements.
    
    DeepL has deprecated "EN" and now requires "EN-US" or "EN-GB".
    Similarly, "PT" is deprecated in favor of "PT-PT" or "PT-BR".
    
    Args:
        lang_code: Language code to normalize (e.g., "EN", "FR", "DE")
        
    Returns:
        Normalized language code compatible with DeepL API
    """
    lang_code = lang_code.upper()
    
    # Handle deprecated language codes
    if lang_code == "EN":
        return "EN-US"  # Default to US English
    elif lang_code == "PT":
        return "PT-PT"  # Default to European Portuguese
    
    return lang_code


def _get_deepl_api_key(area: Area, db: Session) -> str:
    """Get decrypted DeepL API key for a user.

    Args:
        area: The Area being executed (contains user_id)
        db: Database session

    Returns:
        Decrypted API key string

    Raises:
        DeepLConnectionError: If service connection not found or API key unavailable
    """
    # Get service connection for DeepL
    connection = get_service_connection_by_user_and_service(db, area.user_id, "deepl")
    if not connection:
        raise DeepLConnectionError("DeepL service connection not found. Please add your DeepL API key.")

    # Decrypt API key
    api_key = decrypt_token(connection.encrypted_access_token)
    if not api_key:
        raise DeepLConnectionError("DeepL API key not available or invalid.")

    return api_key


def translate_text_handler(area: Area, params: dict, event: dict, db: Session) -> None:
    """Translate text from source language to target language using DeepL.

    This action translates text with explicitly specified source and target languages.
    DeepL will still validate the source language and return the detected language.

    Args:
        area: The Area being executed
        params: Action parameters:
            - source_lang (str): Source language code (e.g., "EN", "FR", "DE", "ES", "IT", "JA")
            - target_lang (str): Target language code (e.g., "EN", "FR", "DE", "ES", "IT", "JA")
            - text (str): Text to translate
        event: Event data from trigger
        db: Database session (injected by dependency injection)

    Raises:
        ValueError: If required parameters are missing or invalid
        DeepLAPIError: If translation fails
        DeepLAuthError: If API key is invalid
        DeepLConnectionError: If API key is not configured

    Example params:
        {"source_lang": "EN", "target_lang": "FR", "text": "Hello, world!"}
        {"source_lang": "FR", "target_lang": "EN", "text": "Bonjour le monde!"}
    """
    # Validate and prepare parameters first before making database calls
    source_lang = params.get("source_lang")
    target_lang = params.get("target_lang")
    text = params.get("text")

    if not source_lang:
        raise ValueError("'source_lang' parameter is required (e.g., 'EN', 'FR', 'DE')")
    if not target_lang:
        raise ValueError("'target_lang' parameter is required (e.g., 'EN', 'FR', 'DE')")
    if not text:
        raise ValueError("'text' parameter is required")

    # Normalize language codes (handles deprecated codes like "EN" -> "EN-US")
    source_lang = _normalize_language_code(source_lang)
    target_lang = _normalize_language_code(target_lang)

    try:

        logger.info(
            "Starting DeepL translate action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "source_lang": source_lang,
                "target_lang": target_lang,
                "text_length": len(text),
            }
        )

        # Get API key
        api_key = _get_deepl_api_key(area, db)

        # Create DeepL translator
        translator = deepl.Translator(api_key)

        # Translate text
        result = translator.translate_text(
            text,
            source_lang=source_lang,
            target_lang=target_lang
        )

        # Extract results
        translated_text = result.text
        detected_lang = result.detected_source_lang

        logger.info(
            "DeepL translation successful",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "source_lang": source_lang,
                "target_lang": target_lang,
                "detected_lang": detected_lang,
                "original_length": len(text),
                "translated_length": len(translated_text),
            }
        )

        # Store translation results in event for potential chaining with other actions
        event["deepl.translated_text"] = translated_text
        event["deepl.source_language"] = source_lang
        event["deepl.target_language"] = target_lang
        event["deepl.detected_source_language"] = detected_lang
        event["deepl.detected_language"] = detected_lang  # Alias for consistency
        event["deepl.original_text"] = text

        # Store full data for display in execution logs
        event["deepl_data"] = {
            "translated_text": translated_text,
            "source_language": source_lang,
            "target_language": target_lang,
            "detected_source_language": detected_lang,
            "original_text": text[:100] + "..." if len(text) > 100 else text,
            "character_count": len(text),
        }

    except AuthorizationException as e:
        logger.error(
            "DeepL authentication failed",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise DeepLAuthError(f"DeepL API key is invalid: {str(e)}") from e
    except QuotaExceededException as e:
        logger.error(
            "DeepL quota exceeded",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise DeepLAPIError(f"DeepL API quota exceeded (500,000 chars/month for free tier): {str(e)}") from e
    except DeepLException as e:
        logger.error(
            "DeepL API error",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise DeepLAPIError(f"DeepL API error: {str(e)}") from e
    except DeepLConnectionError:
        # Re-raise connection errors as they are specific to this plugin
        raise
    except ValueError as e:
        logger.error(
            "Invalid parameters for DeepL translate",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            }
        )
        raise
    except Exception as e:
        logger.error(
            "Error during DeepL translation",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise DeepLAPIError(f"DeepL translation failed: {str(e)}") from e


def auto_translate_handler(area: Area, params: dict, event: dict, db: Session) -> None:
    """Automatically detect source language and translate to target language using DeepL.

    This action omits the source language parameter, letting DeepL automatically detect
    the source language before translating. Useful when you don't know the input language.

    Args:
        area: The Area being executed
        params: Action parameters:
            - target_lang (str): Target language code (e.g., "EN", "FR", "DE", "ES", "IT", "JA")
            - text (str): Text to translate (source language will be auto-detected)
        event: Event data from trigger
        db: Database session (injected by dependency injection)

    Raises:
        ValueError: If required parameters are missing or invalid
        DeepLAPIError: If translation fails
        DeepLAuthError: If API key is invalid
        DeepLConnectionError: If API key is not configured

    Example params:
        {"target_lang": "FR", "text": "Hello, world!"}  # EN detected -> FR
        {"target_lang": "EN", "text": "Bonjour le monde!"}  # FR detected -> EN
        {"target_lang": "EN", "text": "こんにちは"}  # JA detected -> EN
    """
    # Validate and prepare parameters first before making database calls
    target_lang = params.get("target_lang")
    text = params.get("text")

    if not target_lang:
        raise ValueError("'target_lang' parameter is required (e.g., 'EN', 'FR', 'DE')")
    if not text:
        raise ValueError("'text' parameter is required")

    # Normalize language code (handles deprecated codes like "EN" -> "EN-US")
    target_lang = _normalize_language_code(target_lang)

    try:

        logger.info(
            "Starting DeepL auto-translate action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "target_lang": target_lang,
                "text_length": len(text),
            }
        )

        # Get API key
        api_key = _get_deepl_api_key(area, db)

        # Create DeepL translator
        translator = deepl.Translator(api_key)

        # Translate text with automatic source language detection
        # Note: source_lang parameter is omitted
        result = translator.translate_text(text, target_lang=target_lang)

        # Extract results
        translated_text = result.text
        detected_lang = result.detected_source_lang

        logger.info(
            "DeepL auto-translation successful",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "detected_lang": detected_lang,
                "target_lang": target_lang,
                "original_length": len(text),
                "translated_length": len(translated_text),
            }
        )

        # Store translation results in event for potential chaining with other actions
        event["deepl.translated_text"] = translated_text
        event["deepl.detected_source_language"] = detected_lang
        event["deepl.detected_language"] = detected_lang  # Alias for consistency
        event["deepl.target_language"] = target_lang
        event["deepl.original_text"] = text

        # Store full data for display in execution logs
        event["deepl_data"] = {
            "translated_text": translated_text,
            "detected_source_language": detected_lang,
            "target_language": target_lang,
            "original_text": text[:100] + "..." if len(text) > 100 else text,
            "character_count": len(text),
        }

    except AuthorizationException as e:
        logger.error(
            "DeepL authentication failed",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise DeepLAuthError(f"DeepL API key is invalid: {str(e)}") from e
    except QuotaExceededException as e:
        logger.error(
            "DeepL quota exceeded",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise DeepLAPIError(f"DeepL API quota exceeded (500,000 chars/month for free tier): {str(e)}") from e
    except DeepLException as e:
        logger.error(
            "DeepL API error",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise DeepLAPIError(f"DeepL API error: {str(e)}") from e
    except DeepLConnectionError:
        # Re-raise connection errors as they are specific to this plugin
        raise
    except ValueError as e:
        logger.error(
            "Invalid parameters for DeepL auto-translate",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            }
        )
        raise
    except Exception as e:
        logger.error(
            "Error during DeepL auto-translation",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise DeepLAPIError(f"DeepL auto-translation failed: {str(e)}") from e


def detect_language_handler(area: Area, params: dict, event: dict, db: Session) -> None:
    """Detect the language of a text using DeepL.

    Note: DeepL does not provide a dedicated language detection endpoint. This handler
    works by translating a small portion of the text to English and extracting the
    detected source language from the response. The translated text is discarded,
    only the detected language is returned.

    Args:
        area: The Area being executed
        params: Action parameters:
            - text (str): Text to detect the language of
            - sample_length (int, optional): Number of characters to use for detection (default: 100)
        event: Event data from trigger
        db: Database session (injected by dependency injection)

    Raises:
        ValueError: If required parameters are missing or invalid
        DeepLAPIError: If language detection fails
        DeepLAuthError: If API key is invalid
        DeepLConnectionError: If API key is not configured

    Example params:
        {"text": "Bonjour le monde!"}  # Returns: FR
        {"text": "こんにちは世界！"}  # Returns: JA
        {"text": "Hello, world!", "sample_length": 50}  # Returns: EN
    """
    # Validate and prepare parameters first before making database calls
    text = params.get("text")
    sample_length = params.get("sample_length", 100)

    if not text:
        raise ValueError("'text' parameter is required")

    if not isinstance(sample_length, int) or sample_length <= 0:
        raise ValueError("'sample_length' must be a positive integer")

    # Use only a sample of the text for detection (to save API quota)
    text_sample = text[:sample_length]

    try:

        logger.info(
            "Starting DeepL detect language action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "text_length": len(text),
                "sample_length": len(text_sample),
            }
        )

        # Get API key
        api_key = _get_deepl_api_key(area, db)

        # Create DeepL translator
        translator = deepl.Translator(api_key)

        # Translate the text sample to English to detect the source language
        # We use EN-US as target because it's widely supported (EN is deprecated)
        # The translated text will be discarded, we only need the detected language
        result = translator.translate_text(text_sample, target_lang="EN-US")

        # Extract detected language
        detected_lang = result.detected_source_lang

        logger.info(
            "DeepL language detection successful",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "detected_language": detected_lang,
                "text_length": len(text),
                "sample_length": len(text_sample),
            }
        )

        # Store detection results in event for potential chaining with other actions
        event["deepl.detected_language"] = detected_lang
        event["deepl.detected_source_language"] = detected_lang  # Alias for consistency
        event["deepl.original_text"] = text
        event["deepl.sample_used"] = text_sample

        # Store full data for display in execution logs
        event["deepl_data"] = {
            "detected_language": detected_lang,
            "original_text": text[:100] + "..." if len(text) > 100 else text,
            "sample_length": len(text_sample),
            "character_count": len(text),
        }

    except AuthorizationException as e:
        logger.error(
            "DeepL authentication failed",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise DeepLAuthError(f"DeepL API key is invalid: {str(e)}") from e
    except QuotaExceededException as e:
        logger.error(
            "DeepL quota exceeded",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise DeepLAPIError(f"DeepL API quota exceeded (500,000 chars/month for free tier): {str(e)}") from e
    except DeepLException as e:
        logger.error(
            "DeepL API error",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise DeepLAPIError(f"DeepL API error: {str(e)}") from e
    except DeepLConnectionError:
        # Re-raise connection errors as they are specific to this plugin
        raise
    except ValueError as e:
        logger.error(
            "Invalid parameters for DeepL detect language",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            }
        )
        raise
    except Exception as e:
        logger.error(
            "Error during DeepL language detection",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise DeepLAPIError(f"DeepL language detection failed: {str(e)}") from e


__all__ = [
    "translate_text_handler",
    "auto_translate_handler",
    "detect_language_handler",
]
