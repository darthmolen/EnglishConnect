"""Unit tests for TTS Pydantic schemas."""

import pytest


def test_tts_request_requires_text():
    """TTSRequest should require text field."""
    from app.schemas.tts import TTSRequest

    request = TTSRequest(text="Hello world")
    assert request.text == "Hello world"
    assert request.voice == "speaker_a"  # default


def test_tts_request_accepts_voice():
    """TTSRequest should accept optional voice parameter."""
    from app.schemas.tts import TTSRequest

    request = TTSRequest(text="Hello", voice="speaker_b")
    assert request.voice == "speaker_b"


def test_tts_response_has_audio_base64():
    """TTSResponse should have audio_base64 and format."""
    from app.schemas.tts import TTSResponse

    response = TTSResponse(
        audio_base64="SGVsbG8gV29ybGQ=",
        format="wav",
        sample_rate=24000
    )
    assert response.audio_base64 == "SGVsbG8gV29ybGQ="
    assert response.format == "wav"
    assert response.sample_rate == 24000


def test_tts_response_default_values():
    """TTSResponse should have sensible defaults."""
    from app.schemas.tts import TTSResponse

    response = TTSResponse(audio_base64="test")
    assert response.format == "wav"
    assert response.sample_rate == 24000
