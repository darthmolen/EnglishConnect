"""Integration tests for TTS (Text-to-Speech) MCP service.

These tests require:
- VibeVoice to be installed with voice presets
- GPU with CUDA (or will use placeholder TTS)

Tests can run in two modes:
1. With real VibeVoice model - tests full audio generation
2. With placeholder - tests API/tool structure only
"""

import base64
import json
import sys
from pathlib import Path

import pytest

# Add TTS service to path
TTS_SERVICE_PATH = Path(__file__).parent.parent.parent / "src" / "services" / "tts-mcp"
sys.path.insert(0, str(TTS_SERVICE_PATH))


def check_vibevoice_available():
    """Check if VibeVoice is importable."""
    try:
        from vibevoice.modular.modeling_vibevoice_streaming_inference import (
            VibeVoiceStreamingForConditionalGenerationInference,
        )
        return True
    except ImportError:
        return False


def check_voice_presets_available():
    """Check if voice preset files exist."""
    voices_dir = TTS_SERVICE_PATH / "VibeVoice" / "demo" / "voices" / "streaming_model"
    if not voices_dir.exists():
        return False
    # Check for at least one preset file
    preset_files = list(voices_dir.glob("*.pt"))
    return len(preset_files) > 0


# Mark for tests that require full VibeVoice
requires_vibevoice = pytest.mark.skipif(
    not check_vibevoice_available(),
    reason="VibeVoice not available"
)

requires_voice_presets = pytest.mark.skipif(
    not check_voice_presets_available(),
    reason="Voice preset files not found"
)


class TestTTSVoiceConfig:
    """Test TTS voice configuration."""

    def test_voices_dict_structure(self):
        """Test that VOICES dict has correct structure."""
        from server import VOICES

        assert len(VOICES) == 6  # speaker_a through speaker_f

        for voice_id, config in VOICES.items():
            assert "name" in config
            assert "file" in config
            assert "description" in config
            assert voice_id.startswith("speaker_")

    def test_voice_ids(self):
        """Test expected voice IDs exist."""
        from server import VOICES

        expected = ["speaker_a", "speaker_b", "speaker_c", "speaker_d", "speaker_e", "speaker_f"]
        assert set(VOICES.keys()) == set(expected)


class TestTTSTools:
    """Test TTS MCP tools."""

    @pytest.mark.asyncio
    async def test_list_voices_tool(self):
        """Test list_voices tool returns valid JSON."""
        from server import list_voices

        result = await list_voices()
        voices = json.loads(result)

        assert isinstance(voices, list)
        assert len(voices) == 6

        for voice in voices:
            assert "id" in voice
            assert "name" in voice
            assert "description" in voice

    @pytest.mark.asyncio
    async def test_speak_invalid_voice(self):
        """Test speak tool handles invalid voice."""
        from server import speak

        result = await speak("Hello", voice="invalid_voice")
        data = json.loads(result)

        assert "error" in data
        assert "invalid_voice" in data["error"]

    @pytest.mark.asyncio
    async def test_speak_base64_invalid_voice(self):
        """Test speak_base64 tool handles invalid voice."""
        from server import speak_base64

        result = await speak_base64("Hello", voice="invalid_voice")
        data = json.loads(result)

        assert "error" in data
        assert "invalid_voice" in data["error"]

    @pytest.mark.asyncio
    async def test_speak_dialogue_invalid_json(self):
        """Test speak_dialogue handles invalid JSON."""
        from server import speak_dialogue

        result = await speak_dialogue("not valid json")
        data = json.loads(result)

        assert "error" in data
        assert "JSON" in data["error"]


@requires_vibevoice
@requires_voice_presets
class TestTTSSynthesis:
    """Test actual TTS synthesis. Requires VibeVoice and voice presets."""

    @pytest.mark.asyncio
    async def test_speak_generates_audio_file(self):
        """Test speak tool generates audio file."""
        from server import speak

        result = await speak("Hello, this is a test.", voice="speaker_a")
        data = json.loads(result)

        assert data.get("status") == "success"
        assert "audio_path" in data
        assert data["voice"] == "speaker_a"
        assert data["format"] == "wav"

        # Verify file exists
        audio_path = Path(data["audio_path"])
        assert audio_path.exists()

        # Cleanup
        audio_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_speak_base64_returns_audio(self):
        """Test speak_base64 returns base64-encoded audio."""
        from server import speak_base64

        result = await speak_base64("Hello world", voice="speaker_b")
        data = json.loads(result)

        assert data.get("status") == "success"
        assert "audio_base64" in data

        # Verify it's valid base64
        audio_bytes = base64.b64decode(data["audio_base64"])
        assert len(audio_bytes) > 0

        # Check WAV header (RIFF)
        assert audio_bytes[:4] == b"RIFF"

    @pytest.mark.asyncio
    async def test_speak_dialogue_generates_combined_audio(self):
        """Test speak_dialogue generates combined audio file."""
        from server import speak_dialogue

        exchanges = json.dumps([
            {"speaker": "speaker_a", "text": "Hello"},
            {"speaker": "speaker_b", "text": "Hi there"},
        ])

        result = await speak_dialogue(exchanges)
        data = json.loads(result)

        assert data.get("status") == "success"
        assert "audio_path" in data
        assert data["turns"] == 2
        assert data["format"] == "wav"

        # Verify file exists
        audio_path = Path(data["audio_path"])
        assert audio_path.exists()

        # Cleanup
        audio_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_all_voices_work(self):
        """Test all voices can generate audio."""
        from server import speak, VOICES

        for voice_id in VOICES.keys():
            result = await speak("Test", voice=voice_id)
            data = json.loads(result)

            assert data.get("status") == "success", f"Voice {voice_id} failed: {data}"
            assert data["voice"] == voice_id

            # Cleanup
            audio_path = Path(data["audio_path"])
            audio_path.unlink(missing_ok=True)


class TestTTSPlaceholder:
    """Test TTS placeholder mode (when VibeVoice not available)."""

    @pytest.mark.asyncio
    async def test_placeholder_generates_silence(self):
        """Test placeholder TTS generates silent audio."""
        from server import get_model, _synthesize_sync

        model, processor = get_model()

        # This will work even without VibeVoice - uses placeholder
        if model == "placeholder":
            audio_bytes = _synthesize_sync("Hello test", "speaker_a")

            assert len(audio_bytes) > 0
            # Check WAV header
            assert audio_bytes[:4] == b"RIFF"


class TestTTSCoreFunction:
    """Test TTS core synthesis function."""

    def test_synthesize_sync_exists(self):
        """Test _synthesize_sync function exists."""
        from server import _synthesize_sync

        assert callable(_synthesize_sync)

    @pytest.mark.asyncio
    async def test_synthesize_with_vibevoice_async(self):
        """Test async synthesize wrapper exists."""
        from server import synthesize_with_vibevoice

        assert callable(synthesize_with_vibevoice)


class TestTTSAudioConcatenation:
    """Test audio concatenation utilities."""

    @pytest.mark.asyncio
    async def test_concatenate_audio(self):
        """Test audio concatenation function."""
        import io

        import numpy as np
        import soundfile as sf

        from server import concatenate_audio, _sample_rate

        # Create two test audio segments
        duration = 0.1  # 100ms each
        samples = int(_sample_rate * duration)
        audio1 = np.sin(np.linspace(0, 10, samples)).astype(np.float32)
        audio2 = np.sin(np.linspace(0, 20, samples)).astype(np.float32)

        # Convert to WAV bytes
        def to_wav(audio):
            buf = io.BytesIO()
            sf.write(buf, audio, _sample_rate, format="WAV")
            buf.seek(0)
            return buf.read()

        wav1 = to_wav(audio1)
        wav2 = to_wav(audio2)

        # Concatenate with 100ms pause
        combined = await concatenate_audio([wav1, wav2], pause_seconds=0.1)

        # Verify result is valid WAV
        assert combined[:4] == b"RIFF"

        # Read back and check length
        buf = io.BytesIO(combined)
        combined_audio, sr = sf.read(buf)

        # Should be: audio1 + pause + audio2 + pause
        expected_samples = samples * 2 + int(_sample_rate * 0.1) * 2
        assert len(combined_audio) == expected_samples
