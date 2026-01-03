"""TTS service for calling the TTS HTTP endpoint."""

import httpx

from app.config import get_settings
from app.utils.timing import request_id_var


async def synthesize_speech(text: str, voice: str = "speaker_a") -> dict:
    """Synthesize speech from text using TTS service.

    Args:
        text: Text to synthesize
        voice: Voice ID (speaker_a through speaker_f)

    Returns:
        Dict with audio_base64, voice, speaker_name, sample_rate, format

    Raises:
        httpx.HTTPError: If TTS service request fails
    """
    settings = get_settings()
    tts_url = settings.tts_mcp_url

    # Pass request_id to TTS service for timing correlation
    headers = {"X-Request-ID": request_id_var.get()}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{tts_url}/synthesize",
            json={"text": text, "voice": voice},
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


async def get_available_voices() -> list[dict]:
    """Get list of available TTS voices.

    Returns:
        List of voice dicts with id, name, description
    """
    settings = get_settings()
    tts_url = settings.tts_mcp_url

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{tts_url}/voices")
        response.raise_for_status()
        return response.json()
