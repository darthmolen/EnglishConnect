"""Pydantic schemas for TTS API endpoint."""

from pydantic import BaseModel


class TTSRequest(BaseModel):
    """Request body for POST /api/tts."""

    text: str
    voice: str = "speaker_a"


class TTSResponse(BaseModel):
    """Response body for TTS endpoint."""

    audio_base64: str
    format: str = "wav"
    sample_rate: int = 24000
