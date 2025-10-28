"""Unit tests for DeepL plugin functions."""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from deepl.exceptions import AuthorizationException, QuotaExceededException, DeepLException

from app.integrations.simple_plugins.deepl_plugin import (
    _normalize_language_code,
    _get_deepl_api_key,
    translate_text_handler,
    auto_translate_handler,
    detect_language_handler,
)
from app.models.area import Area
from app.models.service_connection import ServiceConnection
from app.integrations.simple_plugins.exceptions import (
    DeepLAPIError,
    DeepLAuthError,
    DeepLConnectionError,
)


class TestDeepLPlugin:

    @pytest.fixture
    def area(self):
        """Create a mock area object for testing."""
        import uuid
        area = Area()
        area.id = uuid.uuid4()
        area.name = "Test DeepL Area"
        area.user_id = uuid.uuid4()
        return area

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock(spec=Session)

    @pytest.fixture
    def mock_service_connection(self):
        """Create a mock service connection."""
        connection = ServiceConnection()
        connection.encrypted_access_token = "encrypted_deepl_key"
        return connection

    # ========================
    # Language Code Normalization Tests
    # ========================

    def test_normalize_language_code_en_to_en_us(self):
        """Test EN normalization to EN-US."""
        assert _normalize_language_code("EN") == "EN-US"
        assert _normalize_language_code("en") == "EN-US"

    def test_normalize_language_code_pt_to_pt_pt(self):
        """Test PT normalization to PT-PT."""
        assert _normalize_language_code("PT") == "PT-PT"
        assert _normalize_language_code("pt") == "PT-PT"

    def test_normalize_language_code_other_languages(self):
        """Test other language codes remain unchanged."""
        assert _normalize_language_code("FR") == "FR"
        assert _normalize_language_code("de") == "DE"
        assert _normalize_language_code("ES") == "ES"
        assert _normalize_language_code("ja") == "JA"

    # ========================
    # API Key Retrieval Tests
    # ========================

    def test_get_deepl_api_key_success(self, area, mock_db, mock_service_connection):
        """Test successful retrieval of DeepL API key."""
        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_service_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_deepl_key:fx"):

            api_key = _get_deepl_api_key(area, mock_db)

            assert api_key == "test_deepl_key:fx"

    def test_get_deepl_api_key_no_connection(self, area, mock_db):
        """Test failure when no service connection exists."""
        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=None):

            with pytest.raises(DeepLConnectionError, match="DeepL service connection not found"):
                _get_deepl_api_key(area, mock_db)

    def test_get_deepl_api_key_invalid_key(self, area, mock_db, mock_service_connection):
        """Test failure when API key is invalid."""
        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_service_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value=""):

            with pytest.raises(DeepLConnectionError, match="DeepL API key not available or invalid"):
                _get_deepl_api_key(area, mock_db)

    # ========================
    # Translate Text Handler Tests
    # ========================

    def test_translate_text_handler_success(self, area, mock_db):
        """Test successful text translation with specified source and target languages."""
        params = {
            "source_lang": "EN",
            "target_lang": "FR",
            "text": "Hello, world!"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        # Mock translation result
        mock_result = MagicMock()
        mock_result.text = "Bonjour le monde!"
        mock_result.detected_source_lang = "EN"

        # Mock translator
        mock_translator = MagicMock()
        mock_translator.translate_text.return_value = mock_result

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_api_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            # Call the handler
            translate_text_handler(area, params, event, mock_db)

            # Verify event data
            assert event["deepl.translated_text"] == "Bonjour le monde!"
            assert event["deepl.source_language"] == "EN-US"
            assert event["deepl.target_language"] == "FR"
            assert event["deepl.detected_source_language"] == "EN"
            assert event["deepl.detected_language"] == "EN"
            assert event["deepl.original_text"] == "Hello, world!"

            # Verify deepl_data structure
            assert "deepl_data" in event
            assert event["deepl_data"]["translated_text"] == "Bonjour le monde!"
            assert event["deepl_data"]["character_count"] == 13

            # Verify translator was called correctly
            mock_translator.translate_text.assert_called_once_with(
                "Hello, world!",
                source_lang="EN-US",
                target_lang="FR"
            )

    def test_translate_text_handler_missing_source_lang(self, area, mock_db):
        """Test error when source_lang parameter is missing."""
        params = {
            "target_lang": "FR",
            "text": "Hello, world!"
        }
        event = {}

        with pytest.raises(ValueError, match="'source_lang' parameter is required"):
            translate_text_handler(area, params, event, mock_db)

    def test_translate_text_handler_missing_target_lang(self, area, mock_db):
        """Test error when target_lang parameter is missing."""
        params = {
            "source_lang": "EN",
            "text": "Hello, world!"
        }
        event = {}

        with pytest.raises(ValueError, match="'target_lang' parameter is required"):
            translate_text_handler(area, params, event, mock_db)

    def test_translate_text_handler_missing_text(self, area, mock_db):
        """Test error when text parameter is missing."""
        params = {
            "source_lang": "EN",
            "target_lang": "FR"
        }
        event = {}

        with pytest.raises(ValueError, match="'text' parameter is required"):
            translate_text_handler(area, params, event, mock_db)

    def test_translate_text_handler_auth_error(self, area, mock_db):
        """Test handling of authentication error."""
        params = {
            "source_lang": "EN",
            "target_lang": "FR",
            "text": "Hello, world!"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        # Mock translator that raises AuthorizationException
        mock_translator = MagicMock()
        mock_translator.translate_text.side_effect = AuthorizationException("Invalid API key")

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="invalid_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            with pytest.raises(DeepLAuthError, match="DeepL API key is invalid"):
                translate_text_handler(area, params, event, mock_db)

    def test_translate_text_handler_quota_exceeded(self, area, mock_db):
        """Test handling of quota exceeded error."""
        params = {
            "source_lang": "EN",
            "target_lang": "FR",
            "text": "Hello, world!"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        # Mock translator that raises QuotaExceededException
        mock_translator = MagicMock()
        mock_translator.translate_text.side_effect = QuotaExceededException("Quota exceeded")

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            with pytest.raises(DeepLAPIError, match="DeepL API quota exceeded"):
                translate_text_handler(area, params, event, mock_db)

    def test_translate_text_handler_deepl_exception(self, area, mock_db):
        """Test handling of generic DeepL exception."""
        params = {
            "source_lang": "EN",
            "target_lang": "FR",
            "text": "Hello, world!"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        # Mock translator that raises DeepLException
        mock_translator = MagicMock()
        mock_translator.translate_text.side_effect = DeepLException("Service unavailable")

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            with pytest.raises(DeepLAPIError, match="DeepL API error"):
                translate_text_handler(area, params, event, mock_db)

    def test_translate_text_handler_connection_error(self, area, mock_db):
        """Test handling of connection error."""
        params = {
            "source_lang": "EN",
            "target_lang": "FR",
            "text": "Hello, world!"
        }
        event = {}

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=None):

            with pytest.raises(DeepLConnectionError, match="DeepL service connection not found"):
                translate_text_handler(area, params, event, mock_db)

    # ========================
    # Auto Translate Handler Tests
    # ========================

    def test_auto_translate_handler_success(self, area, mock_db):
        """Test successful auto-translation with language detection."""
        params = {
            "target_lang": "FR",
            "text": "Hello, world!"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        # Mock translation result
        mock_result = MagicMock()
        mock_result.text = "Bonjour le monde!"
        mock_result.detected_source_lang = "EN"

        # Mock translator
        mock_translator = MagicMock()
        mock_translator.translate_text.return_value = mock_result

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_api_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            # Call the handler
            auto_translate_handler(area, params, event, mock_db)

            # Verify event data
            assert event["deepl.translated_text"] == "Bonjour le monde!"
            assert event["deepl.detected_source_language"] == "EN"
            assert event["deepl.detected_language"] == "EN"
            assert event["deepl.target_language"] == "FR"
            assert event["deepl.original_text"] == "Hello, world!"

            # Verify deepl_data structure
            assert "deepl_data" in event
            assert event["deepl_data"]["translated_text"] == "Bonjour le monde!"
            assert event["deepl_data"]["detected_source_language"] == "EN"

            # Verify translator was called without source_lang
            mock_translator.translate_text.assert_called_once_with(
                "Hello, world!",
                target_lang="FR"
            )

    def test_auto_translate_handler_missing_target_lang(self, area, mock_db):
        """Test error when target_lang parameter is missing."""
        params = {
            "text": "Hello, world!"
        }
        event = {}

        with pytest.raises(ValueError, match="'target_lang' parameter is required"):
            auto_translate_handler(area, params, event, mock_db)

    def test_auto_translate_handler_missing_text(self, area, mock_db):
        """Test error when text parameter is missing."""
        params = {
            "target_lang": "FR"
        }
        event = {}

        with pytest.raises(ValueError, match="'text' parameter is required"):
            auto_translate_handler(area, params, event, mock_db)

    def test_auto_translate_handler_auth_error(self, area, mock_db):
        """Test handling of authentication error in auto-translate."""
        params = {
            "target_lang": "FR",
            "text": "Hello, world!"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        # Mock translator that raises AuthorizationException
        mock_translator = MagicMock()
        mock_translator.translate_text.side_effect = AuthorizationException("Invalid API key")

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="invalid_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            with pytest.raises(DeepLAuthError, match="DeepL API key is invalid"):
                auto_translate_handler(area, params, event, mock_db)

    def test_auto_translate_handler_quota_exceeded(self, area, mock_db):
        """Test handling of quota exceeded in auto-translate."""
        params = {
            "target_lang": "FR",
            "text": "Hello, world!"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        # Mock translator that raises QuotaExceededException
        mock_translator = MagicMock()
        mock_translator.translate_text.side_effect = QuotaExceededException("Quota exceeded")

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            with pytest.raises(DeepLAPIError, match="DeepL API quota exceeded"):
                auto_translate_handler(area, params, event, mock_db)

    # ========================
    # Detect Language Handler Tests
    # ========================

    def test_detect_language_handler_success(self, area, mock_db):
        """Test successful language detection."""
        params = {
            "text": "Bonjour le monde!"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        # Mock translation result
        mock_result = MagicMock()
        mock_result.text = "Hello world!"  # Discarded
        mock_result.detected_source_lang = "FR"

        # Mock translator
        mock_translator = MagicMock()
        mock_translator.translate_text.return_value = mock_result

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_api_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            # Call the handler
            detect_language_handler(area, params, event, mock_db)

            # Verify event data
            assert event["deepl.detected_language"] == "FR"
            assert event["deepl.detected_source_language"] == "FR"
            assert event["deepl.original_text"] == "Bonjour le monde!"
            assert event["deepl.sample_used"] == "Bonjour le monde!"

            # Verify deepl_data structure
            assert "deepl_data" in event
            assert event["deepl_data"]["detected_language"] == "FR"

            # Verify translator was called with sample
            mock_translator.translate_text.assert_called_once_with(
                "Bonjour le monde!",
                target_lang="EN-US"
            )

    def test_detect_language_handler_with_sample_length(self, area, mock_db):
        """Test language detection with custom sample length."""
        long_text = "Bonjour le monde! " * 20  # Long text
        params = {
            "text": long_text,
            "sample_length": 50
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        # Mock translation result
        mock_result = MagicMock()
        mock_result.text = "Hello world!"
        mock_result.detected_source_lang = "FR"

        # Mock translator
        mock_translator = MagicMock()
        mock_translator.translate_text.return_value = mock_result

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_api_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            # Call the handler
            detect_language_handler(area, params, event, mock_db)

            # Verify event data
            assert event["deepl.detected_language"] == "FR"
            assert event["deepl_data"]["sample_length"] == 50

            # Verify only first 50 characters were used
            call_args = mock_translator.translate_text.call_args[0]
            assert len(call_args[0]) == 50
            assert call_args[0] == long_text[:50]

    def test_detect_language_handler_missing_text(self, area, mock_db):
        """Test error when text parameter is missing."""
        params = {}
        event = {}

        with pytest.raises(ValueError, match="'text' parameter is required"):
            detect_language_handler(area, params, event, mock_db)

    def test_detect_language_handler_invalid_sample_length(self, area, mock_db):
        """Test error when sample_length is invalid."""
        params = {
            "text": "Hello",
            "sample_length": -1
        }
        event = {}

        with pytest.raises(ValueError, match="'sample_length' must be a positive integer"):
            detect_language_handler(area, params, event, mock_db)

    def test_detect_language_handler_non_integer_sample_length(self, area, mock_db):
        """Test error when sample_length is not an integer."""
        params = {
            "text": "Hello",
            "sample_length": "invalid"
        }
        event = {}

        with pytest.raises(ValueError, match="'sample_length' must be a positive integer"):
            detect_language_handler(area, params, event, mock_db)

    def test_detect_language_handler_auth_error(self, area, mock_db):
        """Test handling of authentication error in language detection."""
        params = {
            "text": "Bonjour!"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        # Mock translator that raises AuthorizationException
        mock_translator = MagicMock()
        mock_translator.translate_text.side_effect = AuthorizationException("Invalid API key")

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="invalid_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            with pytest.raises(DeepLAuthError, match="DeepL API key is invalid"):
                detect_language_handler(area, params, event, mock_db)

    def test_detect_language_handler_quota_exceeded(self, area, mock_db):
        """Test handling of quota exceeded in language detection."""
        params = {
            "text": "Bonjour!"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        # Mock translator that raises QuotaExceededException
        mock_translator = MagicMock()
        mock_translator.translate_text.side_effect = QuotaExceededException("Quota exceeded")

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            with pytest.raises(DeepLAPIError, match="DeepL API quota exceeded"):
                detect_language_handler(area, params, event, mock_db)

    # ========================
    # Event Data Propagation Tests
    # ========================

    def test_event_data_propagation_translate(self, area, mock_db):
        """Test that translation data is properly propagated in event."""
        params = {
            "source_lang": "EN",
            "target_lang": "FR",
            "text": "Hello"
        }
        event = {"existing_key": "existing_value"}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        mock_result = MagicMock()
        mock_result.text = "Bonjour"
        mock_result.detected_source_lang = "EN"

        mock_translator = MagicMock()
        mock_translator.translate_text.return_value = mock_result

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_api_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            translate_text_handler(area, params, event, mock_db)

            # Verify existing event data is preserved
            assert event["existing_key"] == "existing_value"

            # Verify new data is added
            assert "deepl.translated_text" in event
            assert "deepl_data" in event

    def test_event_data_propagation_auto_translate(self, area, mock_db):
        """Test that auto-translation data is properly propagated in event."""
        params = {
            "target_lang": "FR",
            "text": "Hello"
        }
        event = {"trigger_data": "some_value"}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        mock_result = MagicMock()
        mock_result.text = "Bonjour"
        mock_result.detected_source_lang = "EN"

        mock_translator = MagicMock()
        mock_translator.translate_text.return_value = mock_result

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_api_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            auto_translate_handler(area, params, event, mock_db)

            # Verify existing event data is preserved
            assert event["trigger_data"] == "some_value"

            # Verify new data is added
            assert "deepl.translated_text" in event
            assert "deepl.detected_language" in event

    def test_event_data_propagation_detect_language(self, area, mock_db):
        """Test that detection data is properly propagated in event."""
        params = {
            "text": "Bonjour"
        }
        event = {"previous_step": "data"}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        mock_result = MagicMock()
        mock_result.text = "Hello"
        mock_result.detected_source_lang = "FR"

        mock_translator = MagicMock()
        mock_translator.translate_text.return_value = mock_result

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_api_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            detect_language_handler(area, params, event, mock_db)

            # Verify existing event data is preserved
            assert event["previous_step"] == "data"

            # Verify new data is added
            assert "deepl.detected_language" in event
            assert "deepl_data" in event

    # ========================
    # Integration/Edge Case Tests
    # ========================

    def test_translate_text_handler_with_long_text(self, area, mock_db):
        """Test translation with long text (>100 chars) for character counting."""
        long_text = "This is a very long text that exceeds one hundred characters. " * 3
        params = {
            "source_lang": "EN",
            "target_lang": "FR",
            "text": long_text
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        mock_result = MagicMock()
        mock_result.text = "French translation..."
        mock_result.detected_source_lang = "EN"

        mock_translator = MagicMock()
        mock_translator.translate_text.return_value = mock_result

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_api_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            translate_text_handler(area, params, event, mock_db)

            # Verify character count in deepl_data
            assert event["deepl_data"]["character_count"] == len(long_text)
            # Verify original_text is truncated in deepl_data
            assert "..." in event["deepl_data"]["original_text"]
            assert len(event["deepl_data"]["original_text"]) <= 103  # 100 chars + "..."

    def test_auto_translate_handler_japanese_to_english(self, area, mock_db):
        """Test auto-translation from Japanese to English."""
        params = {
            "target_lang": "EN",
            "text": "こんにちは世界"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        mock_result = MagicMock()
        mock_result.text = "Hello world"
        mock_result.detected_source_lang = "JA"

        mock_translator = MagicMock()
        mock_translator.translate_text.return_value = mock_result

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_api_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            auto_translate_handler(area, params, event, mock_db)

            # Verify Japanese was detected
            assert event["deepl.detected_language"] == "JA"
            assert event["deepl.target_language"] == "EN-US"

    def test_detect_language_handler_with_long_text_sample(self, area, mock_db):
        """Test language detection truncates text correctly with long input."""
        # Create text longer than default sample length
        long_text = "This is a very long English text. " * 10  # ~350 chars
        params = {
            "text": long_text,
            "sample_length": 100
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        mock_result = MagicMock()
        mock_result.text = "Translation"
        mock_result.detected_source_lang = "EN"

        mock_translator = MagicMock()
        mock_translator.translate_text.return_value = mock_result

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_api_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            detect_language_handler(area, params, event, mock_db)

            # Verify sample was used
            assert len(event["deepl.sample_used"]) == 100
            assert event["deepl.sample_used"] == long_text[:100]
            # Verify original text is preserved
            assert event["deepl.original_text"] == long_text

    def test_translate_text_handler_network_error(self, area, mock_db):
        """Test handling of generic exceptions (e.g., network errors)."""
        params = {
            "source_lang": "EN",
            "target_lang": "FR",
            "text": "Hello"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        # Mock translator that raises generic Exception
        mock_translator = MagicMock()
        mock_translator.translate_text.side_effect = Exception("Network connection lost")

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            with pytest.raises(DeepLAPIError, match="DeepL translation failed"):
                translate_text_handler(area, params, event, mock_db)

    def test_auto_translate_handler_generic_exception(self, area, mock_db):
        """Test handling of generic exceptions in auto-translate."""
        params = {
            "target_lang": "FR",
            "text": "Hello"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        # Mock translator that raises generic Exception
        mock_translator = MagicMock()
        mock_translator.translate_text.side_effect = Exception("Unexpected error")

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            with pytest.raises(DeepLAPIError, match="DeepL auto-translation failed"):
                auto_translate_handler(area, params, event, mock_db)

    def test_detect_language_handler_generic_exception(self, area, mock_db):
        """Test handling of generic exceptions in language detection."""
        params = {
            "text": "Bonjour"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        # Mock translator that raises generic Exception
        mock_translator = MagicMock()
        mock_translator.translate_text.side_effect = Exception("API unavailable")

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            with pytest.raises(DeepLAPIError, match="DeepL language detection failed"):
                detect_language_handler(area, params, event, mock_db)

    def test_normalize_language_code_lowercase_variants(self):
        """Test normalization handles lowercase input correctly."""
        assert _normalize_language_code("en") == "EN-US"
        assert _normalize_language_code("pt") == "PT-PT"
        assert _normalize_language_code("fr") == "FR"
        assert _normalize_language_code("de") == "DE"

    def test_translate_text_handler_pt_language_normalization(self, area, mock_db):
        """Test that PT language code is normalized to PT-PT."""
        params = {
            "source_lang": "PT",
            "target_lang": "EN",
            "text": "Olá mundo"
        }
        event = {}

        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"

        mock_result = MagicMock()
        mock_result.text = "Hello world"
        mock_result.detected_source_lang = "PT"

        mock_translator = MagicMock()
        mock_translator.translate_text.return_value = mock_result

        with patch('app.integrations.simple_plugins.deepl_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_connection), \
             patch('app.integrations.simple_plugins.deepl_plugin.decrypt_token',
                   return_value="test_api_key:fx"), \
             patch('app.integrations.simple_plugins.deepl_plugin.deepl.Translator',
                   return_value=mock_translator):

            translate_text_handler(area, params, event, mock_db)

            # Verify PT was normalized to PT-PT
            mock_translator.translate_text.assert_called_once_with(
                "Olá mundo",
                source_lang="PT-PT",
                target_lang="EN-US"
            )

    def test_detect_language_handler_zero_sample_length(self, area, mock_db):
        """Test that zero sample_length raises ValueError."""
        params = {
            "text": "Hello",
            "sample_length": 0
        }
        event = {}

        with pytest.raises(ValueError, match="'sample_length' must be a positive integer"):
            detect_language_handler(area, params, event, mock_db)
