"""TTS API router for text-to-speech synthesis."""

from fastapi import APIRouter

from app.schemas.tts import TTSRequest, TTSResponse

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.post("", response_model=TTSResponse)
async def synthesize_speech(request: TTSRequest):
    """Synthesize speech from text using TTS service.

    Args:
        request: TTSRequest with text and optional voice parameter

    Returns:
        TTSResponse with base64-encoded audio data
    """
    # TODO: Integrate TTS MCP server for actual synthesis
    # For now, return placeholder response
    return TTSResponse(
        audio_base64="",  # Placeholder - will be actual base64 audio
        format="wav",
        sample_rate=24000,
    )
