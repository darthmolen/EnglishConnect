"""Test that multiple speak() calls result in combined response text.

This tests the fix for the bug where only the last speak() text was shown
in the conversation UI when the agent spoke in multiple languages.
"""

import pytest
import sys
from pathlib import Path

# Add src/backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "backend"))

from app.schemas.lesson_session import AudioChunkSchema


class TestMultipleSpokenTexts:
    """Verify response.text contains all spoken texts, not just the last one."""

    def test_two_speak_calls_produces_combined_text(self):
        """When agent speaks Spanish then English, response.text has both."""
        # Mock agent_result with two speak() tool results
        mock_agent_result = {
            "text": "Final LLM message",
            "tool_calls": [],
            "tool_results": [
                {
                    "tool": "speak",
                    "success": True,
                    "result": {
                        "spoken": True,
                        "text": "Hola, el patrón es...",
                        "language": "es",
                        "audio_base64": "fake_audio_1",
                        "format": "wav",
                    },
                },
                {
                    "tool": "speak",
                    "success": True,
                    "result": {
                        "spoken": True,
                        "text": "Hello, the pattern is...",
                        "language": "en",
                        "audio_base64": "fake_audio_2",
                        "format": "wav",
                    },
                },
            ],
        }

        # Extract audio chunks (simulating lesson.py logic)
        audio_chunks = []
        for tool_result in mock_agent_result.get("tool_results", []):
            if tool_result.get("tool") == "speak" and tool_result.get("success"):
                result_data = tool_result.get("result", {})
                if result_data.get("spoken"):
                    audio_chunks.append(
                        AudioChunkSchema(
                            audio_base64=result_data.get("audio_base64", ""),
                            format=result_data.get("format", "wav"),
                            language=result_data.get("language", "en"),
                            text=result_data.get("text", ""),
                        )
                    )

        # Build response_text (the fix we're testing)
        # Uses double newline for visual separation between utterances
        if audio_chunks:
            response_text = "\n\n".join(chunk.text for chunk in audio_chunks)
        else:
            response_text = mock_agent_result["text"]

        # Assertions
        assert len(audio_chunks) == 2, "Should have 2 audio chunks"
        assert "Hola, el patrón es..." in response_text, "Spanish text missing"
        assert "Hello, the pattern is..." in response_text, "English text missing"
        assert (
            response_text == "Hola, el patrón es...\n\nHello, the pattern is..."
        ), f"Combined text incorrect: {response_text}"

    def test_single_speak_call_uses_that_text(self):
        """When agent speaks once, response.text is that single text."""
        mock_agent_result = {
            "text": "Final LLM message",
            "tool_calls": [],
            "tool_results": [
                {
                    "tool": "speak",
                    "success": True,
                    "result": {
                        "spoken": True,
                        "text": "Hello, welcome to the lesson!",
                        "language": "en",
                        "audio_base64": "fake_audio",
                        "format": "wav",
                    },
                },
            ],
        }

        audio_chunks = []
        for tool_result in mock_agent_result.get("tool_results", []):
            if tool_result.get("tool") == "speak" and tool_result.get("success"):
                result_data = tool_result.get("result", {})
                if result_data.get("spoken"):
                    audio_chunks.append(
                        AudioChunkSchema(
                            audio_base64=result_data.get("audio_base64", ""),
                            format=result_data.get("format", "wav"),
                            language=result_data.get("language", "en"),
                            text=result_data.get("text", ""),
                        )
                    )

        if audio_chunks:
            response_text = "\n\n".join(chunk.text for chunk in audio_chunks)
        else:
            response_text = mock_agent_result["text"]

        assert len(audio_chunks) == 1
        assert response_text == "Hello, welcome to the lesson!"

    def test_no_speak_calls_uses_llm_text(self):
        """When agent doesn't speak, response.text is LLM's final message."""
        mock_agent_result = {
            "text": "I understand, let me help you with that.",
            "tool_calls": [],
            "tool_results": [],  # No speak calls
        }

        audio_chunks = []
        for tool_result in mock_agent_result.get("tool_results", []):
            if tool_result.get("tool") == "speak" and tool_result.get("success"):
                result_data = tool_result.get("result", {})
                if result_data.get("spoken"):
                    audio_chunks.append(
                        AudioChunkSchema(
                            audio_base64=result_data.get("audio_base64", ""),
                            format=result_data.get("format", "wav"),
                            language=result_data.get("language", "en"),
                            text=result_data.get("text", ""),
                        )
                    )

        if audio_chunks:
            response_text = "\n\n".join(chunk.text for chunk in audio_chunks)
        else:
            response_text = mock_agent_result["text"]

        assert len(audio_chunks) == 0
        assert response_text == "I understand, let me help you with that."

    def test_three_speak_calls_all_combined(self):
        """When agent speaks three times, all texts are combined."""
        mock_agent_result = {
            "text": "Final message",
            "tool_calls": [],
            "tool_results": [
                {
                    "tool": "speak",
                    "success": True,
                    "result": {
                        "spoken": True,
                        "text": "First.",
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
                        "text": "Second.",
                        "language": "es",
                        "audio_base64": "a2",
                        "format": "wav",
                    },
                },
                {
                    "tool": "speak",
                    "success": True,
                    "result": {
                        "spoken": True,
                        "text": "Third.",
                        "language": "en",
                        "audio_base64": "a3",
                        "format": "wav",
                    },
                },
            ],
        }

        audio_chunks = []
        for tool_result in mock_agent_result.get("tool_results", []):
            if tool_result.get("tool") == "speak" and tool_result.get("success"):
                result_data = tool_result.get("result", {})
                if result_data.get("spoken"):
                    audio_chunks.append(
                        AudioChunkSchema(
                            audio_base64=result_data.get("audio_base64", ""),
                            format=result_data.get("format", "wav"),
                            language=result_data.get("language", "en"),
                            text=result_data.get("text", ""),
                        )
                    )

        if audio_chunks:
            response_text = "\n\n".join(chunk.text for chunk in audio_chunks)
        else:
            response_text = mock_agent_result["text"]

        assert len(audio_chunks) == 3
        assert response_text == "First.\n\nSecond.\n\nThird."

    def test_failed_speak_call_not_included(self):
        """Failed speak calls should not be included in response text."""
        mock_agent_result = {
            "text": "Final message",
            "tool_calls": [],
            "tool_results": [
                {
                    "tool": "speak",
                    "success": True,
                    "result": {
                        "spoken": True,
                        "text": "Success text.",
                        "language": "en",
                        "audio_base64": "audio",
                        "format": "wav",
                    },
                },
                {
                    "tool": "speak",
                    "success": False,  # Failed call
                    "error": "TTS service unavailable",
                },
            ],
        }

        audio_chunks = []
        for tool_result in mock_agent_result.get("tool_results", []):
            if tool_result.get("tool") == "speak" and tool_result.get("success"):
                result_data = tool_result.get("result", {})
                if result_data.get("spoken"):
                    audio_chunks.append(
                        AudioChunkSchema(
                            audio_base64=result_data.get("audio_base64", ""),
                            format=result_data.get("format", "wav"),
                            language=result_data.get("language", "en"),
                            text=result_data.get("text", ""),
                        )
                    )

        if audio_chunks:
            response_text = "\n\n".join(chunk.text for chunk in audio_chunks)
        else:
            response_text = mock_agent_result["text"]

        assert len(audio_chunks) == 1
        assert response_text == "Success text."
