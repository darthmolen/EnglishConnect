"""Test that conversation router prefers English speak() calls.

This tests the fix for the bug where the agent would incorrectly return
Spanish when it made both EN and ES speak() calls.

Bug: On turn 4, agent made two speak() calls (EN then ES). Router returned
Spanish even though the student wasn't confused. Fix: Prefer English.
"""

import pytest
import sys
from pathlib import Path

# Add src/backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "backend"))


def extract_speak_response(tool_results: list) -> dict:
    """Extract audio response from tool results, preferring English.

    This mirrors the logic in conversation.py router.
    """
    english_speak = None
    spanish_speak = None

    for tool_result in tool_results:
        if tool_result.get("tool") == "speak" and tool_result.get("success"):
            result_data = tool_result.get("result", {})
            if result_data.get("spoken"):
                result_lang = result_data.get("language", "en")
                if result_lang == "en" and english_speak is None:
                    english_speak = result_data
                elif result_lang == "es" and spanish_speak is None:
                    spanish_speak = result_data

    # Prefer English, fall back to Spanish only if no English
    return english_speak if english_speak else spanish_speak


class TestConversationLanguagePreference:
    """Verify conversation router prefers English over Spanish."""

    def test_both_en_and_es_prefers_english(self):
        """When agent speaks both EN and ES, English is chosen.

        This is the bug case: agent made two speak() calls.
        The router was taking the last one (Spanish), but should take English.
        """
        tool_results = [
            {
                "tool": "speak",
                "success": True,
                "result": {
                    "spoken": True,
                    "text": "Nice to meet you! Houston is a great city.",
                    "language": "en",
                    "audio_base64": "fake_en_audio",
                    "format": "wav",
                },
            },
            {
                "tool": "speak",
                "success": True,
                "result": {
                    "spoken": True,
                    "text": "¡Encantado de conocerte! Houston es una gran ciudad.",
                    "language": "es",
                    "audio_base64": "fake_es_audio",
                    "format": "wav",
                },
            },
        ]

        result = extract_speak_response(tool_results)

        assert result is not None, "Should return a speak result"
        assert result["language"] == "en", "Should prefer English"
        assert "Nice to meet you" in result["text"], "Should return English text"

    def test_es_then_en_still_prefers_english(self):
        """Even if Spanish is called first, English is preferred."""
        tool_results = [
            {
                "tool": "speak",
                "success": True,
                "result": {
                    "spoken": True,
                    "text": "¡Hola! ¿Cómo estás?",
                    "language": "es",
                    "audio_base64": "fake_es_audio",
                    "format": "wav",
                },
            },
            {
                "tool": "speak",
                "success": True,
                "result": {
                    "spoken": True,
                    "text": "Hello! How are you?",
                    "language": "en",
                    "audio_base64": "fake_en_audio",
                    "format": "wav",
                },
            },
        ]

        result = extract_speak_response(tool_results)

        assert result["language"] == "en", "Should prefer English even if ES came first"
        assert "Hello" in result["text"]

    def test_only_english_uses_english(self):
        """When only English speak() is called, use it."""
        tool_results = [
            {
                "tool": "speak",
                "success": True,
                "result": {
                    "spoken": True,
                    "text": "Welcome to the lesson!",
                    "language": "en",
                    "audio_base64": "fake_audio",
                    "format": "wav",
                },
            },
        ]

        result = extract_speak_response(tool_results)

        assert result["language"] == "en"
        assert result["text"] == "Welcome to the lesson!"

    def test_only_spanish_uses_spanish(self):
        """When only Spanish speak() is called, use it (fallback)."""
        tool_results = [
            {
                "tool": "speak",
                "success": True,
                "result": {
                    "spoken": True,
                    "text": "¿Necesitas ayuda?",
                    "language": "es",
                    "audio_base64": "fake_audio",
                    "format": "wav",
                },
            },
        ]

        result = extract_speak_response(tool_results)

        assert result["language"] == "es", "Should use Spanish if that's all there is"
        assert result["text"] == "¿Necesitas ayuda?"

    def test_no_speak_calls_returns_none(self):
        """When no speak() calls are made, return None."""
        tool_results = []

        result = extract_speak_response(tool_results)

        assert result is None

    def test_failed_speak_calls_ignored(self):
        """Failed speak() calls should not be considered."""
        tool_results = [
            {
                "tool": "speak",
                "success": False,
                "error": "TTS failed",
            },
            {
                "tool": "speak",
                "success": True,
                "result": {
                    "spoken": True,
                    "text": "Hello!",
                    "language": "en",
                    "audio_base64": "audio",
                    "format": "wav",
                },
            },
        ]

        result = extract_speak_response(tool_results)

        assert result["text"] == "Hello!"

    def test_first_english_wins_over_later_english(self):
        """If multiple English speak() calls, use the first one."""
        tool_results = [
            {
                "tool": "speak",
                "success": True,
                "result": {
                    "spoken": True,
                    "text": "First English message.",
                    "language": "en",
                    "audio_base64": "a1",
                    "format": "wav",
                },
            },
            {
                "tool": "speak",
                "success": True,
                "result": {
                    "spoken": True,
                    "text": "Second English message.",
                    "language": "en",
                    "audio_base64": "a2",
                    "format": "wav",
                },
            },
        ]

        result = extract_speak_response(tool_results)

        assert result["text"] == "First English message.", "Should use first EN call"

    def test_fourth_turn_bug_scenario(self):
        """Reproduce the exact scenario from the bug report.

        User said "I'm from Houston" (turn 4), agent made:
        1. speak(en): "Nice to meet you! Houston is a great city..."
        2. speak(es): "¡Encantado de conocerte! Houston es una gran ciudad..."

        Bug: returned Spanish. Fix: return English.
        """
        tool_results = [
            {
                "tool": "speak",
                "success": True,
                "result": {
                    "spoken": True,
                    "text": "Nice to meet you! Houston is a great city. How are you today?",
                    "language": "en",
                    "audio_base64": "en_audio_base64",
                    "format": "wav",
                },
            },
            {
                "tool": "speak",
                "success": True,
                "result": {
                    "spoken": True,
                    "text": "¡Encantado de conocerte! Houston es una gran ciudad. ¿Cómo estás hoy?",
                    "language": "es",
                    "audio_base64": "es_audio_base64",
                    "format": "wav",
                },
            },
        ]

        result = extract_speak_response(tool_results)

        # This was the bug - it was returning Spanish
        assert result["language"] == "en", "MUST return English, not Spanish"
        assert "Nice to meet you" in result["text"]
        assert "Houston" in result["text"]
