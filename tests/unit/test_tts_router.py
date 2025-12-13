"""Unit tests for TTS router endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport


class TestTTSRouter:
    """Test TTS API endpoints."""

    @pytest.mark.asyncio
    async def test_tts_returns_200(self):
        """POST /api/tts should return 200 with audio data."""
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/tts",
                json={"text": "Hello world"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "audio_base64" in data
        assert "format" in data
        assert data["format"] == "wav"

    @pytest.mark.asyncio
    async def test_tts_accepts_voice_parameter(self):
        """POST /api/tts should accept voice parameter."""
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/tts",
                json={"text": "Hello", "voice": "speaker_b"},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_tts_validates_request(self):
        """POST /api/tts should validate request body."""
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Missing text field
            response = await client.post(
                "/api/tts",
                json={},
            )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_tts_returns_sample_rate(self):
        """POST /api/tts should return sample rate."""
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/tts",
                json={"text": "Test audio"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "sample_rate" in data
        assert data["sample_rate"] == 24000
