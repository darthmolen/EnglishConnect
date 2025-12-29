"""Piper TTS Service - CPU-based text-to-speech.

Wraps the Piper CLI for audio synthesis. No GPU required.
Returns audio as bytes, does not manage file storage.

Usage:
    from services.piper import PiperService

    service = PiperService()

    # Single language
    audio_bytes = service.synthesize("Hello", language="en")

    # Vocabulary (bilingual)
    audio_bytes = service.synthesize_vocabulary(
        english_parts=["book", "books"],
        spanish_parts=["libro", "libros"],
    )
"""

from dataclasses import dataclass
from pathlib import Path
import io
import json
import subprocess
import tempfile

import numpy as np
import soundfile as sf
from scipy import signal


@dataclass
class VoiceConfig:
    """Voice configuration for a Piper model."""

    model_path: Path
    language: str  # 'en' or 'es'
    sample_rate: int = 22050  # Piper default


class PiperService:
    """Piper TTS synthesis service.

    Wraps the Piper CLI to synthesize text to audio. Supports English and
    Spanish voices, with special support for vocabulary pronunciation that
    combines both languages with programmatic pauses.
    """

    # Default voices per language
    DEFAULT_VOICES = {
        "en": "en_US-lessac-medium",
        "es": "es_ES-davefx-medium",  # European Spanish (less stereotypical)
    }

    # Target sample rate for output (matches existing EnglishConnect audio)
    TARGET_SAMPLE_RATE = 24000

    def __init__(
        self,
        models_dir: Path | None = None,
        piper_executable: str = "piper",
    ):
        """Initialize Piper service.

        Args:
            models_dir: Directory containing ONNX model files.
                       Defaults to src/services/piper/models/
            piper_executable: Path to piper binary. Defaults to 'piper'
                            (assumes installed via pip in active venv)
        """
        self.models_dir = models_dir or (Path(__file__).parent / "models")
        self.piper_executable = piper_executable
        self._voice_configs: dict[str, VoiceConfig] = {}
        self._load_voice_configs()

    def _load_voice_configs(self) -> None:
        """Discover available voice models."""
        for lang, voice_name in self.DEFAULT_VOICES.items():
            model_path = self.models_dir / f"{voice_name}.onnx"
            if model_path.exists():
                # Parse sample rate from JSON config
                config_path = self.models_dir / f"{voice_name}.onnx.json"
                sample_rate = 22050  # default
                if config_path.exists():
                    try:
                        config = json.loads(config_path.read_text())
                        sample_rate = config.get("audio", {}).get("sample_rate", 22050)
                    except (json.JSONDecodeError, KeyError):
                        pass

                self._voice_configs[lang] = VoiceConfig(
                    model_path=model_path,
                    language=lang,
                    sample_rate=sample_rate,
                )

    def get_available_languages(self) -> list[str]:
        """Return list of available language codes."""
        return list(self._voice_configs.keys())

    def get_voice_info(self) -> dict[str, str]:
        """Return mapping of language to voice name."""
        return {
            lang: config.model_path.stem
            for lang, config in self._voice_configs.items()
        }

    def synthesize(
        self,
        text: str,
        language: str = "en",
        resample: bool = True,
    ) -> bytes:
        """Synthesize text to WAV audio bytes.

        Args:
            text: Text to synthesize
            language: Language code ('en' or 'es')
            resample: If True, resample to TARGET_SAMPLE_RATE (24000 Hz)

        Returns:
            WAV audio bytes

        Raises:
            ValueError: If language not available
            RuntimeError: If Piper execution fails
        """
        if language not in self._voice_configs:
            available = ", ".join(self._voice_configs.keys()) or "none (download models first)"
            raise ValueError(f"Language '{language}' not available. Have: {available}")

        voice = self._voice_configs[language]

        # Use temp file for output (Piper writes to file)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # Run Piper CLI
            cmd = [
                self.piper_executable,
                "-m",
                str(voice.model_path),
                "--output_file",
                str(tmp_path),
            ]

            result = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                error_msg = result.stderr.decode("utf-8", errors="replace")
                raise RuntimeError(f"Piper failed: {error_msg}")

            # Read audio
            audio_data, native_rate = sf.read(tmp_path)

            # Resample if needed
            if resample and native_rate != self.TARGET_SAMPLE_RATE:
                audio_data = self._resample(audio_data, native_rate, self.TARGET_SAMPLE_RATE)
                output_rate = self.TARGET_SAMPLE_RATE
            else:
                output_rate = native_rate

            # Write to bytes
            output = io.BytesIO()
            sf.write(output, audio_data.astype(np.float32), output_rate, format="WAV")
            output.seek(0)
            return output.read()

        finally:
            tmp_path.unlink(missing_ok=True)

    def synthesize_vocabulary(
        self,
        english_parts: list[str],
        spanish_parts: list[str],
        intra_pause: float = 0.5,
        inter_pause: float = 0.8,
        sample_rate: int = 24000,
    ) -> bytes:
        """Generate vocabulary pronunciation audio.

        Creates bilingual audio in this order:
        1. English parts (with intra_pause between each)
        2. Inter-language pause
        3. Spanish parts (with intra_pause between each)

        Example for ["book", "books"] and ["libro", "libros"]:
        "book" [0.5s] "books" [0.8s] "libro" [0.5s] "libros"

        Args:
            english_parts: English word forms (e.g., ["book", "books"])
            spanish_parts: Spanish translations (e.g., ["libro", "libros"])
            intra_pause: Pause between forms within same language (seconds)
            inter_pause: Pause between English and Spanish (seconds)
            sample_rate: Output sample rate

        Returns:
            Combined WAV audio bytes
        """
        segments: list[np.ndarray] = []

        # Generate English parts
        for i, text in enumerate(english_parts):
            audio_bytes = self.synthesize(text, language="en", resample=True)
            audio_data = self._bytes_to_array(audio_bytes)
            segments.append(audio_data)

            # Add intra-pause after each part except the last
            if i < len(english_parts) - 1:
                segments.append(self._silence(intra_pause, sample_rate))

        # Add inter-language pause
        if english_parts and spanish_parts:
            segments.append(self._silence(inter_pause, sample_rate))

        # Generate Spanish parts
        for i, text in enumerate(spanish_parts):
            audio_bytes = self.synthesize(text, language="es", resample=True)
            audio_data = self._bytes_to_array(audio_bytes)
            segments.append(audio_data)

            # Add intra-pause after each part except the last
            if i < len(spanish_parts) - 1:
                segments.append(self._silence(intra_pause, sample_rate))

        # Concatenate all segments
        if not segments:
            return b""

        combined = np.concatenate(segments)

        # Write to bytes
        output = io.BytesIO()
        sf.write(output, combined.astype(np.float32), sample_rate, format="WAV")
        output.seek(0)
        return output.read()

    def _resample(
        self, audio_data: np.ndarray, from_rate: int, to_rate: int
    ) -> np.ndarray:
        """Resample audio to a different sample rate."""
        if from_rate == to_rate:
            return audio_data

        # Calculate number of samples in output
        num_samples = int(len(audio_data) * to_rate / from_rate)
        resampled = signal.resample(audio_data, num_samples)
        return resampled.astype(np.float32)

    def _silence(self, duration: float, sample_rate: int) -> np.ndarray:
        """Generate silence of specified duration."""
        num_samples = int(sample_rate * duration)
        return np.zeros(num_samples, dtype=np.float32)

    def _bytes_to_array(self, wav_bytes: bytes) -> np.ndarray:
        """Convert WAV bytes to numpy array."""
        buffer = io.BytesIO(wav_bytes)
        audio_data, _ = sf.read(buffer)
        return audio_data.astype(np.float32)
