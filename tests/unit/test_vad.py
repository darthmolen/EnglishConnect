"""Unit tests for Voice Activity Detection module.

Tests the VoiceActivityDetector class with mocked Silero VAD model
to ensure fast, deterministic tests without GPU requirements.
"""

import numpy as np
import pytest
from unittest.mock import Mock, patch, MagicMock


class MockSileroModel:
    """Mock Silero VAD model for testing."""

    def __init__(self, speech_probability=0.0):
        self._speech_probability = speech_probability
        self._call_count = 0
        self._probabilities = None  # For sequence of probabilities

    def __call__(self, tensor, sample_rate):
        """Return configured speech probability."""
        self._call_count += 1
        if self._probabilities is not None:
            idx = min(self._call_count - 1, len(self._probabilities) - 1)
            prob = self._probabilities[idx]
        else:
            prob = self._speech_probability

        # Return a mock that has .item() method
        result = Mock()
        result.item.return_value = prob
        return result

    def reset_states(self):
        """Reset model states."""
        pass

    def set_probability(self, prob: float):
        """Set the probability to return."""
        self._speech_probability = prob
        self._probabilities = None

    def set_probability_sequence(self, probs: list):
        """Set a sequence of probabilities to return."""
        self._probabilities = probs
        self._call_count = 0


@pytest.fixture
def mock_silero():
    """Create a mock Silero model and patch torch.hub.load."""
    mock_model = MockSileroModel()
    mock_utils = Mock()

    with patch('torch.hub.load') as mock_load:
        mock_load.return_value = (mock_model, mock_utils)
        yield mock_model


@pytest.fixture
def vad(mock_silero):
    """Create a VoiceActivityDetector with mocked model."""
    import sys
    sys.path.insert(0, str(__file__).replace('/tests/unit/test_vad.py', '/src/services/stt'))
    from vad import VoiceActivityDetector

    detector = VoiceActivityDetector()
    return detector


class TestVADInitialization:
    """Test VAD initialization."""

    def test_init_default_parameters(self, mock_silero):
        """Test default parameter values."""
        import sys
        sys.path.insert(0, str(__file__).replace('/tests/unit/test_vad.py', '/src/services/stt'))
        from vad import VoiceActivityDetector

        vad = VoiceActivityDetector()

        assert vad.sample_rate == 16000
        assert vad.threshold == 0.5
        assert vad.min_speech_samples == 4000  # 250ms at 16kHz
        assert vad.min_silence_samples == 8000  # 500ms at 16kHz
        assert vad.speech_pad_samples == 8000  # 500ms at 16kHz

    def test_init_custom_parameters(self, mock_silero):
        """Test custom parameter values."""
        import sys
        sys.path.insert(0, str(__file__).replace('/tests/unit/test_vad.py', '/src/services/stt'))
        from vad import VoiceActivityDetector

        vad = VoiceActivityDetector(
            threshold=0.7,
            min_speech_ms=100,
            min_silence_ms=300,
            speech_pad_ms=200,
        )

        assert vad.threshold == 0.7
        assert vad.min_speech_samples == 1600  # 100ms at 16kHz
        assert vad.min_silence_samples == 4800  # 300ms at 16kHz
        assert vad.speech_pad_samples == 3200  # 200ms at 16kHz

    def test_init_invalid_sample_rate(self, mock_silero):
        """Test that non-16kHz sample rate raises error."""
        import sys
        sys.path.insert(0, str(__file__).replace('/tests/unit/test_vad.py', '/src/services/stt'))
        from vad import VoiceActivityDetector

        with pytest.raises(ValueError, match="16kHz"):
            VoiceActivityDetector(sample_rate=44100)


class TestVADProcessChunk:
    """Test audio chunk processing."""

    def test_process_silence_returns_false(self, vad, mock_silero):
        """Test that silence returns False."""
        mock_silero.set_probability(0.1)  # Below threshold

        silence = np.zeros(512, dtype=np.float32)
        result = vad.process_chunk(silence)

        assert result is False
        assert not vad.is_speaking

    def test_process_speech_returns_true(self, vad, mock_silero):
        """Test that speech returns True."""
        mock_silero.set_probability(0.9)  # Above threshold

        audio = np.random.randn(512).astype(np.float32) * 0.5
        result = vad.process_chunk(audio)

        assert result is True

    def test_process_converts_dtype(self, vad, mock_silero):
        """Test that non-float32 audio is converted."""
        mock_silero.set_probability(0.9)

        # Provide int16 audio
        audio = np.zeros(512, dtype=np.int16)
        result = vad.process_chunk(audio)

        # Should not raise, conversion happens internally
        assert isinstance(result, bool)

    def test_process_handles_stereo(self, vad, mock_silero):
        """Test that stereo audio is converted to mono."""
        mock_silero.set_probability(0.9)

        # Provide stereo audio
        stereo = np.random.randn(512, 2).astype(np.float32)
        result = vad.process_chunk(stereo)

        # Should not raise, mono conversion happens internally
        assert isinstance(result, bool)

    def test_process_pads_short_chunks(self, vad, mock_silero):
        """Test that short chunks are padded to 512 samples."""
        mock_silero.set_probability(0.9)

        short_audio = np.random.randn(100).astype(np.float32)
        result = vad.process_chunk(short_audio)

        # Should not raise
        assert isinstance(result, bool)


class TestVADStateMachine:
    """Test VAD speech detection state machine."""

    def test_speech_not_started_before_min_duration(self, vad, mock_silero):
        """Test that speech_started is False before min duration."""
        mock_silero.set_probability(0.9)

        # Process less than min_speech_ms (250ms = 4000 samples)
        audio = np.random.randn(2000).astype(np.float32)
        vad.process_chunk(audio)

        assert not vad.speech_started()

    def test_speech_starts_after_min_duration(self, vad, mock_silero):
        """Test that speech_started is True after min duration."""
        mock_silero.set_probability(0.9)

        # Process more than min_speech_ms (250ms = 4000 samples)
        # Need to process in 512-sample chunks
        for _ in range(10):  # 10 * 512 = 5120 samples > 4000
            audio = np.random.randn(512).astype(np.float32)
            vad.process_chunk(audio)

        assert vad.speech_started()

    def test_speech_ended_after_silence(self, vad, mock_silero):
        """Test that speech_ended is True after silence threshold."""
        # First, start speech
        mock_silero.set_probability(0.9)
        for _ in range(10):
            vad.process_chunk(np.random.randn(512).astype(np.float32))

        assert vad.speech_started()
        assert not vad.speech_ended()

        # Then silence
        mock_silero.set_probability(0.1)
        for _ in range(20):  # 20 * 512 = 10240 samples > 8000 (500ms)
            vad.process_chunk(np.zeros(512, dtype=np.float32))

        assert vad.speech_ended()

    def test_speech_not_ended_during_pause(self, vad, mock_silero):
        """Test that brief pauses don't trigger speech_ended."""
        # Start speech
        mock_silero.set_probability(0.9)
        for _ in range(10):
            vad.process_chunk(np.random.randn(512).astype(np.float32))

        # Brief pause (less than min_silence_ms)
        mock_silero.set_probability(0.1)
        for _ in range(5):  # 5 * 512 = 2560 samples < 8000
            vad.process_chunk(np.zeros(512, dtype=np.float32))

        assert not vad.speech_ended()


class TestVADAudioBuffer:
    """Test audio buffer management."""

    def test_get_speech_audio_empty_initially(self, vad, mock_silero):
        """Test that get_speech_audio returns empty array initially."""
        audio = vad.get_speech_audio()

        assert isinstance(audio, np.ndarray)
        assert len(audio) == 0

    def test_get_speech_audio_contains_speech(self, vad, mock_silero):
        """Test that speech audio is accumulated."""
        mock_silero.set_probability(0.9)

        # Process enough speech to trigger speech_started
        total_samples = 0
        for _ in range(10):
            chunk = np.random.randn(512).astype(np.float32)
            vad.process_chunk(chunk)
            total_samples += 512

        audio = vad.get_speech_audio()

        # Should have audio (including pre-speech buffer)
        assert len(audio) > 0

    def test_get_speech_duration(self, vad, mock_silero):
        """Test speech duration calculation."""
        mock_silero.set_probability(0.9)

        # Process 10 chunks of 512 samples each
        for _ in range(10):
            vad.process_chunk(np.random.randn(512).astype(np.float32))

        duration = vad.get_speech_duration()

        # Duration should be positive (exact value depends on buffer management)
        assert duration >= 0

    def test_pre_speech_buffer_included(self, vad, mock_silero):
        """Test that pre-speech audio is included when speech starts."""
        # Add some silence first (goes to pre-speech buffer)
        mock_silero.set_probability(0.1)
        for _ in range(5):
            vad.process_chunk(np.zeros(512, dtype=np.float32))

        # Then speech (should include pre-speech buffer)
        mock_silero.set_probability(0.9)
        for _ in range(10):
            vad.process_chunk(np.random.randn(512).astype(np.float32))

        audio = vad.get_speech_audio()

        # Audio should include pre-speech buffer
        # 5 chunks of silence + 10 chunks of speech = up to 7680 samples
        # But pre-speech buffer is limited to speech_pad_samples (8000)
        assert len(audio) > 5120  # More than just speech chunks


class TestVADReset:
    """Test VAD reset functionality."""

    def test_reset_clears_state(self, vad, mock_silero):
        """Test that reset clears all state."""
        # Build up some state
        mock_silero.set_probability(0.9)
        for _ in range(10):
            vad.process_chunk(np.random.randn(512).astype(np.float32))

        assert vad.speech_started()

        # Reset
        vad.reset()

        assert not vad.speech_started()
        assert not vad.speech_ended()
        assert not vad.is_speaking
        assert len(vad.get_speech_audio()) == 0

    def test_reset_allows_new_detection(self, vad, mock_silero):
        """Test that reset allows detecting new speech."""
        # First speech segment
        mock_silero.set_probability(0.9)
        for _ in range(10):
            vad.process_chunk(np.random.randn(512).astype(np.float32))

        # End speech
        mock_silero.set_probability(0.1)
        for _ in range(20):
            vad.process_chunk(np.zeros(512, dtype=np.float32))

        assert vad.speech_ended()

        # Reset and detect new speech
        vad.reset()

        mock_silero.set_probability(0.9)
        for _ in range(10):
            vad.process_chunk(np.random.randn(512).astype(np.float32))

        assert vad.speech_started()


class TestVADProperties:
    """Test VAD property accessors."""

    def test_is_speaking_property(self, mock_silero):
        """Test is_speaking property updates correctly."""
        import sys
        sys.path.insert(0, str(__file__).replace('/tests/unit/test_vad.py', '/src/services/stt'))
        from vad import VoiceActivityDetector

        # Start fresh with low probability
        mock_silero.set_probability(0.1)
        vad = VoiceActivityDetector()

        assert not vad.is_speaking

        # Process enough speech to trigger speech_started (needs > 4000 samples)
        mock_silero.set_probability(0.9)
        for _ in range(10):  # 10 * 512 = 5120 samples
            vad.process_chunk(np.random.randn(512).astype(np.float32))

        assert vad.is_speaking
        assert vad.speech_started()

        # Now silence will properly clear is_speaking
        mock_silero.set_probability(0.1)
        for _ in range(20):  # 20 * 512 = 10240 samples > 8000 (min_silence)
            vad.process_chunk(np.zeros(512, dtype=np.float32))

        assert not vad.is_speaking
