"""Unit tests for the audio streaming router.

Looping playback replays the same clips repeatedly, so /api/audio/stream
responses must be cacheable by the browser. Without Cache-Control the browser
falls back to heuristic caching, which is unreliable on mobile and would make
every loop pass re-download uncompressed WAV over a student's data plan.
"""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def audio_file(tmp_path, monkeypatch):
    """Point the audio router at a temp dir holding one real .wav file."""
    from app.routers import audio

    wav = tmp_path / "ec1" / "vocab" / "lesson-01"
    wav.mkdir(parents=True)
    clip = wav / "noun-01-deadbeef.wav"
    clip.write_bytes(b"RIFF....WAVEfmt ")

    monkeypatch.setattr(audio, "AUDIO_BASE", tmp_path)
    return "ec1/vocab/lesson-01/noun-01-deadbeef.wav"


class TestStreamAudioCaching:
    """Cache headers on GET /api/audio/stream/{file_path}."""

    @pytest.mark.asyncio
    async def test_stream_sets_immutable_cache_control(self, audio_file):
        """Clips are content-hashed, so they can be cached forever.

        This is what makes looping cheap: the second pass through a section
        should be served from disk cache with zero network requests.
        """
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/api/audio/stream/{audio_file}")

        assert response.status_code == 200
        assert response.headers["cache-control"] == "public, max-age=31536000, immutable"

    @pytest.mark.asyncio
    async def test_stream_still_supports_range_requests(self, audio_file):
        """Regression guard: adding cache headers must not drop Accept-Ranges."""
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/api/audio/stream/{audio_file}")

        assert response.status_code == 200
        assert response.headers["accept-ranges"] == "bytes"
