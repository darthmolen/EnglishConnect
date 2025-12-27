"""Shared tool handlers for agent responses."""

import logging

from app.services.tts_service import synthesize_speech

logger = logging.getLogger(__name__)


async def speak_tool_handler(
    text: str,
    language: str,
    voice: str = "speaker_b"
) -> dict:
    """Handle speak tool calls from agents.

    Calls TTS service to synthesize speech and returns audio data.

    Args:
        text: Text to speak
        language: Language code (en or es)
        voice: Voice ID (default: speaker_b)

    Returns:
        Dict with spoken status, text, language, and audio data on success.
        On failure, includes error message instead of audio data.
    """
    try:
        result = await synthesize_speech(text=text, voice=voice)
        return {
            "spoken": True,
            "text": text,
            "language": language,
            "audio_base64": result["audio_base64"],
            "format": result["format"],
            "sample_rate": result["sample_rate"],
        }
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        return {
            "spoken": False,
            "text": text,
            "language": language,
            "error": str(e),
        }
