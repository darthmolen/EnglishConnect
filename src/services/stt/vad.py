"""Voice Activity Detection using Silero VAD.

Detects speech boundaries in audio streams for automatic endpoint detection.
This enables natural turn-taking without requiring fixed recording durations.

Usage:
    from vad import VoiceActivityDetector

    vad = VoiceActivityDetector()

    # Process audio chunks (16kHz, mono, float32)
    for chunk in audio_stream:
        is_speech = vad.process_chunk(chunk)
        if vad.speech_ended():
            # User stopped speaking, trigger transcription
            audio = vad.get_speech_audio()
            transcribe(audio)
            vad.reset()
"""

import numpy as np
import torch


class VoiceActivityDetector:
    """Wraps Silero VAD for real-time speech detection."""

    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        min_speech_ms: int = 250,
        min_silence_ms: int = 500,
        speech_pad_ms: int = 500,
    ):
        """Initialize VAD.

        Args:
            sample_rate: Audio sample rate (must be 16000 for Silero VAD)
            threshold: Speech probability threshold (0.0-1.0)
            min_speech_ms: Minimum speech duration to trigger detection
            min_silence_ms: Silence duration after speech to mark endpoint
            speech_pad_ms: Padding before speech start (default 500ms to capture word onsets)
        """
        if sample_rate != 16000:
            raise ValueError("Silero VAD requires 16kHz audio")

        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_speech_samples = int(min_speech_ms * sample_rate / 1000)
        self.min_silence_samples = int(min_silence_ms * sample_rate / 1000)
        self.speech_pad_samples = int(speech_pad_ms * sample_rate / 1000)

        # Load Silero VAD model
        self.model, self.utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False,
        )

        # State tracking
        self._reset_state()

        # Audio buffer for collecting speech
        self._audio_buffer = []
        self._pre_speech_buffer = []  # Keep last N samples before speech
        self._pre_speech_buffer_size = self.speech_pad_samples

    def _reset_state(self):
        """Reset internal state."""
        self.model.reset_states()
        self._is_speaking = False
        self._speech_samples = 0
        self._silence_samples = 0
        self._speech_started = False
        self._speech_ended = False

    def reset(self):
        """Reset VAD state and clear audio buffer."""
        self._reset_state()
        self._audio_buffer = []
        self._pre_speech_buffer = []

    def process_chunk(self, audio: np.ndarray) -> bool:
        """Process an audio chunk and detect speech.

        Args:
            audio: Audio samples (float32, mono, 16kHz)

        Returns:
            True if speech is detected in this chunk
        """
        # Convert to tensor
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Ensure mono
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        # Silero VAD expects chunks of specific sizes (512, 1024, or 1536 samples)
        # Process in 512-sample chunks for lowest latency
        chunk_size = 512
        results = []

        for i in range(0, len(audio), chunk_size):
            chunk = audio[i:i + chunk_size]
            if len(chunk) < chunk_size:
                # Pad last chunk if needed
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)))

            tensor = torch.from_numpy(chunk)
            speech_prob = self.model(tensor, self.sample_rate).item()
            is_speech = speech_prob >= self.threshold
            results.append(is_speech)

            self._update_state(is_speech, len(chunk))

        # Store audio in appropriate buffer
        if self._speech_started and not self._speech_ended:
            self._audio_buffer.append(audio.copy())
        else:
            # Keep pre-speech buffer for smooth start
            self._pre_speech_buffer.append(audio.copy())
            total_pre_samples = sum(len(a) for a in self._pre_speech_buffer)
            while total_pre_samples > self._pre_speech_buffer_size:
                if self._pre_speech_buffer:
                    removed = self._pre_speech_buffer.pop(0)
                    total_pre_samples -= len(removed)

        return any(results)

    def _update_state(self, is_speech: bool, num_samples: int):
        """Update speech/silence tracking state."""
        if is_speech:
            self._silence_samples = 0
            self._speech_samples += num_samples

            if not self._speech_started and self._speech_samples >= self.min_speech_samples:
                self._speech_started = True
                # Add pre-speech buffer to audio
                if self._pre_speech_buffer:
                    self._audio_buffer = self._pre_speech_buffer.copy() + self._audio_buffer
                    self._pre_speech_buffer = []

            self._is_speaking = True
        else:
            self._speech_samples = 0
            self._silence_samples += num_samples

            if self._speech_started and self._silence_samples >= self.min_silence_samples:
                self._speech_ended = True
                self._is_speaking = False

    @property
    def is_speaking(self) -> bool:
        """Whether speech is currently detected."""
        return self._is_speaking

    def speech_started(self) -> bool:
        """Whether speech has started (minimum duration reached)."""
        return self._speech_started

    def speech_ended(self) -> bool:
        """Whether speech has ended (silence threshold reached after speech)."""
        return self._speech_ended

    def get_speech_audio(self) -> np.ndarray:
        """Get the accumulated speech audio.

        Returns:
            Concatenated audio samples containing the speech
        """
        if not self._audio_buffer:
            return np.array([], dtype=np.float32)
        return np.concatenate(self._audio_buffer)

    def get_speech_duration(self) -> float:
        """Get duration of accumulated speech in seconds."""
        total_samples = sum(len(a) for a in self._audio_buffer)
        return total_samples / self.sample_rate


def test_vad():
    """Test VAD with a simple example."""
    print("Testing VAD...")

    vad = VoiceActivityDetector()

    # Generate test audio: silence, speech (sine wave), silence
    sr = 16000
    silence = np.zeros(sr, dtype=np.float32)  # 1 second silence
    speech = np.sin(2 * np.pi * 440 * np.arange(sr) / sr).astype(np.float32) * 0.5  # 1s tone

    test_audio = np.concatenate([silence, speech, silence])

    # Process in chunks
    chunk_size = 1600  # 100ms chunks
    for i in range(0, len(test_audio), chunk_size):
        chunk = test_audio[i:i + chunk_size]
        is_speech = vad.process_chunk(chunk)
        time_ms = i * 1000 // sr
        status = "SPEECH" if is_speech else "silence"
        print(f"  {time_ms:4d}ms: {status}")

        if vad.speech_ended():
            print(f"\n  Speech ended! Duration: {vad.get_speech_duration():.2f}s")
            break

    print("VAD test complete!")


if __name__ == "__main__":
    test_vad()
