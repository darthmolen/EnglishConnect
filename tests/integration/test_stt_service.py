"""Integration tests for STT (Speech-to-Text) service.

These tests require the STT service to be running:
    cd src/services/stt && source .venv/bin/activate
    uvicorn server:app --host 0.0.0.0 --port 8001
"""

import io
import socket
import wave

import numpy as np
import pytest

# Skip all tests if STT service is not running
STT_HOST = "127.0.0.1"
STT_PORT = 8001
STT_BASE_URL = f"http://{STT_HOST}:{STT_PORT}"


def check_stt_available():
    """Check if STT service is available."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        result = sock.connect_ex((STT_HOST, STT_PORT))
        return result == 0
    except Exception:
        return False
    finally:
        sock.close()


# Skip module if STT service not running
pytestmark = pytest.mark.skipif(
    not check_stt_available(),
    reason=f"STT service not available at {STT_BASE_URL}. Start with: cd src/services/stt && uvicorn server:app --port 8001"
)


def create_test_audio_wav(duration_seconds: float = 1.0, frequency: int = 440) -> bytes:
    """Create a test WAV audio file with a sine wave tone.

    Args:
        duration_seconds: Duration of the audio
        frequency: Frequency of the sine wave in Hz

    Returns:
        WAV file as bytes
    """
    sample_rate = 16000
    num_samples = int(sample_rate * duration_seconds)

    # Generate sine wave
    t = np.linspace(0, duration_seconds, num_samples, dtype=np.float32)
    audio = (np.sin(2 * np.pi * frequency * t) * 0.5).astype(np.float32)

    # Convert to 16-bit PCM
    audio_int16 = (audio * 32767).astype(np.int16)

    # Create WAV in memory
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        wav.writeframes(audio_int16.tobytes())

    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def test_audio():
    """Provide test audio as WAV bytes."""
    return create_test_audio_wav(duration_seconds=2.0)


class TestSTTHealthEndpoints:
    """Test STT service health endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint returns service info."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{STT_BASE_URL}/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "stt"
        assert "model" in data

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health endpoint returns detailed status."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{STT_BASE_URL}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "model" in data
        assert "device" in data
        assert "compute_type" in data


class TestSTTTranscription:
    """Test STT transcription endpoints."""

    @pytest.mark.asyncio
    async def test_transcribe_audio_file(self, test_audio):
        """Test transcribing an audio file via POST."""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": ("test.wav", test_audio, "audio/wav")}
            response = await client.post(f"{STT_BASE_URL}/transcribe", files=files)

        assert response.status_code == 200
        data = response.json()

        # Response should have expected fields
        assert "text" in data
        assert "language" in data
        assert "confidence" in data
        assert "segments" in data

    @pytest.mark.asyncio
    async def test_transcribe_with_language_hint(self, test_audio):
        """Test transcribing with language hint."""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": ("test.wav", test_audio, "audio/wav")}
            response = await client.post(
                f"{STT_BASE_URL}/transcribe",
                files=files,
                params={"language": "en"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data

    @pytest.mark.asyncio
    async def test_transcribe_no_file_error(self):
        """Test error when no file provided."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{STT_BASE_URL}/transcribe")

        # Should return 422 (Unprocessable Entity) for missing required file
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_transcribe_stream_chunk(self, test_audio):
        """Test streaming transcription endpoint."""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": ("chunk.wav", test_audio, "audio/wav")}
            response = await client.post(
                f"{STT_BASE_URL}/transcribe/stream",
                files=files,
                params={"is_final": True}
            )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "is_final" in data
        assert data["is_final"] is True


class TestSTTWebSocket:
    """Test STT WebSocket endpoint."""

    @pytest.mark.asyncio
    async def test_websocket_transcription(self, test_audio):
        """Test WebSocket transcription flow."""
        import websockets

        ws_url = f"ws://{STT_HOST}:{STT_PORT}/ws/transcribe"

        async with websockets.connect(ws_url) as ws:
            # Send audio data
            await ws.send(test_audio)

            # Request transcription
            await ws.send("END")

            # Receive result
            import json
            result = await ws.recv()
            data = json.loads(result)

            assert "text" in data or "error" in data

            # Close connection
            await ws.send("CLOSE")

    @pytest.mark.asyncio
    async def test_websocket_clear_command(self, test_audio):
        """Test WebSocket CLEAR command."""
        import websockets

        ws_url = f"ws://{STT_HOST}:{STT_PORT}/ws/transcribe"

        async with websockets.connect(ws_url) as ws:
            # Send some audio
            await ws.send(test_audio)

            # Clear without transcribing
            await ws.send("CLEAR")

            # Close connection
            await ws.send("CLOSE")

    @pytest.mark.asyncio
    async def test_websocket_empty_audio_error(self):
        """Test WebSocket handles empty audio gracefully."""
        import json

        import websockets

        ws_url = f"ws://{STT_HOST}:{STT_PORT}/ws/transcribe"

        async with websockets.connect(ws_url) as ws:
            # Request transcription without sending audio
            await ws.send("END")

            # Should receive error
            result = await ws.recv()
            data = json.loads(result)

            assert "error" in data

            # Close
            await ws.send("CLOSE")

    @pytest.mark.asyncio
    async def test_websocket_multiple_utterances(self, test_audio):
        """Test multiple transcriptions in one session."""
        import json

        import websockets

        ws_url = f"ws://{STT_HOST}:{STT_PORT}/ws/transcribe"

        async with websockets.connect(ws_url) as ws:
            # First utterance
            await ws.send(test_audio)
            await ws.send("END")
            result1 = json.loads(await ws.recv())
            assert "text" in result1 or "error" in result1

            # Second utterance
            await ws.send(test_audio)
            await ws.send("END")
            result2 = json.loads(await ws.recv())
            assert "text" in result2 or "error" in result2

            await ws.send("CLOSE")
