"""Unit tests for HelpingPhraseService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.helping_phrase_service import HelpingPhraseService
from app.schemas.helping_phrase import HelpingPhraseSchema


def create_mock_phrase(phrase_key: str, phrase_text: str, english_meaning: str, usage_context: str = None) -> MagicMock:
    """Create a mock HelpingPhrase object."""
    mock = MagicMock()
    mock.phrase_key = phrase_key
    mock.phrase_text = phrase_text
    mock.english_meaning = english_meaning
    mock.usage_context = usage_context
    return mock


class TestGetPhrasesForLanguage:
    """Tests for get_phrases_for_language method."""

    @pytest.mark.asyncio
    async def test_returns_spanish_phrases(self):
        """Should return Spanish phrases when language_code is 'es'."""
        # Arrange
        mock_db = AsyncMock()
        mock_phrases = [
            create_mock_phrase("repeat", "Repite, por favor", "Please repeat"),
            create_mock_phrase("dont_understand", "No entiendo", "I don't understand"),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_phrases
        mock_db.execute.return_value = mock_result
        
        service = HelpingPhraseService(mock_db)
        
        # Act
        result = await service.get_phrases_for_language("es")
        
        # Assert
        assert len(result) == 2
        assert result[0].phrase_key == "repeat"
        assert result[0].phrase_text == "Repite, por favor"
        assert result[1].phrase_key == "dont_understand"

    @pytest.mark.asyncio
    async def test_returns_english_phrases(self):
        """Should return English phrases when language_code is 'en'."""
        # Arrange
        mock_db = AsyncMock()
        mock_phrases = [
            create_mock_phrase("repeat", "Please repeat", "Please repeat"),
            create_mock_phrase("dont_understand", "I don't understand", "I don't understand"),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_phrases
        mock_db.execute.return_value = mock_result
        
        service = HelpingPhraseService(mock_db)
        
        # Act
        result = await service.get_phrases_for_language("en")
        
        # Assert
        assert len(result) == 2
        assert result[0].phrase_text == "Please repeat"

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_unknown_language(self):
        """Should return empty list for unknown language code."""
        # Arrange
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        service = HelpingPhraseService(mock_db)
        
        # Act
        result = await service.get_phrases_for_language("xx")
        
        # Assert
        assert result == []


class TestMatchHelpRequest:
    """Tests for match_help_request method."""

    @pytest.mark.asyncio
    async def test_exact_match(self):
        """Should match exact phrase."""
        # Arrange
        mock_db = AsyncMock()
        service = HelpingPhraseService(mock_db)
        
        # Mock get_phrases_for_language
        with patch.object(service, 'get_phrases_for_language') as mock_get:
            mock_get.return_value = [
                HelpingPhraseSchema(
                    phrase_key="repeat",
                    phrase_text="Repite, por favor",
                    english_meaning="Please repeat"
                ),
                HelpingPhraseSchema(
                    phrase_key="dont_understand",
                    phrase_text="No entiendo",
                    english_meaning="I don't understand"
                ),
            ]
            
            # Act
            result = await service.match_help_request("No entiendo", "es")
            
            # Assert
            assert result is not None
            assert result.phrase_key == "dont_understand"

    @pytest.mark.asyncio
    async def test_fuzzy_match_handles_stt_errors(self):
        """Should match phrases with STT errors like 'no en tiendo'."""
        # Arrange
        mock_db = AsyncMock()
        service = HelpingPhraseService(mock_db)
        
        with patch.object(service, 'get_phrases_for_language') as mock_get:
            mock_get.return_value = [
                HelpingPhraseSchema(
                    phrase_key="dont_understand",
                    phrase_text="No entiendo",
                    english_meaning="I don't understand"
                ),
            ]
            
            # Act - STT might add extra spaces
            result = await service.match_help_request("no en tiendo", "es")
            
            # Assert - should still match with fuzzy matching
            # Note: this depends on threshold - "no en tiendo" vs "no entiendo" has ~0.9 similarity
            assert result is not None
            assert result.phrase_key == "dont_understand"

    @pytest.mark.asyncio
    async def test_substring_match(self):
        """Should match when phrase is contained in longer input."""
        # Arrange
        mock_db = AsyncMock()
        service = HelpingPhraseService(mock_db)
        
        with patch.object(service, 'get_phrases_for_language') as mock_get:
            mock_get.return_value = [
                HelpingPhraseSchema(
                    phrase_key="repeat",
                    phrase_text="Repite, por favor",
                    english_meaning="Please repeat"
                ),
            ]
            
            # Act - phrase embedded in longer sentence
            result = await service.match_help_request("Repite, por favor, más despacio", "es")
            
            # Assert
            assert result is not None
            assert result.phrase_key == "repeat"

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_input(self):
        """Should return None for empty input."""
        # Arrange
        mock_db = AsyncMock()
        service = HelpingPhraseService(mock_db)
        
        # Act
        result = await service.match_help_request("", "es")
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_no_match(self):
        """Should return None when no phrase matches."""
        # Arrange
        mock_db = AsyncMock()
        service = HelpingPhraseService(mock_db)
        
        with patch.object(service, 'get_phrases_for_language') as mock_get:
            mock_get.return_value = [
                HelpingPhraseSchema(
                    phrase_key="repeat",
                    phrase_text="Repite, por favor",
                    english_meaning="Please repeat"
                ),
            ]
            
            # Act - completely unrelated text
            result = await service.match_help_request("I like pizza", "es")
            
            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self):
        """Should match regardless of case."""
        # Arrange
        mock_db = AsyncMock()
        service = HelpingPhraseService(mock_db)
        
        with patch.object(service, 'get_phrases_for_language') as mock_get:
            mock_get.return_value = [
                HelpingPhraseSchema(
                    phrase_key="dont_understand",
                    phrase_text="No entiendo",
                    english_meaning="I don't understand"
                ),
            ]
            
            # Act - uppercase input
            result = await service.match_help_request("NO ENTIENDO", "es")
            
            # Assert
            assert result is not None
            assert result.phrase_key == "dont_understand"


class TestNormalize:
    """Tests for _normalize helper method."""

    def test_lowercases_text(self):
        """Should lowercase all text."""
        service = HelpingPhraseService(None)
        assert service._normalize("HELLO WORLD") == "hello world"

    def test_removes_punctuation(self):
        """Should remove punctuation."""
        service = HelpingPhraseService(None)
        assert service._normalize("Hello, world!") == "hello world"

    def test_collapses_whitespace(self):
        """Should collapse multiple spaces."""
        service = HelpingPhraseService(None)
        assert service._normalize("hello   world") == "hello world"

    def test_handles_special_characters(self):
        """Should handle Spanish special characters."""
        service = HelpingPhraseService(None)
        # Should keep accented letters but remove punctuation
        result = service._normalize("¿No entiendo?")
        assert "no" in result
        assert "entiendo" in result
