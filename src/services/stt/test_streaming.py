#!/usr/bin/env python3
"""Test streaming STT with real-time transcription display.

Records from microphone and streams to STT service, showing transcription as it arrives.

Usage:
    cd services/stt
    source .venv/bin/activate

    # Start the server first (in another terminal):
    uvicorn server:app --host 0.0.0.0 --port 8001

    # Then run this test:
    python test_streaming.py
    python test_streaming.py --duration 10  # Record for 10 seconds
    python test_streaming.py --continuous   # VAD-based continuous listening (Ctrl+C to stop)
"""

import argparse
import io
import sys
import time
import threading
from queue import Queue

import numpy as np
import requests
import sounddevice as sd
import soundfile as sf

# VAD import (optional - only needed for --continuous mode)
try:
    from vad import VoiceActivityDetector
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False

# Configuration
SAMPLE_RATE = 16000  # Whisper expects 16kHz
CHANNELS = 1
STT_URL = "http://localhost:8001"


def record_and_transcribe(
    duration: float = 5.0,
    chunk_interval: float = 1.0,
    show_partial: bool = True,
):
    """Record audio and transcribe with streaming display.

    Args:
        duration: Total recording duration in seconds
        chunk_interval: How often to send chunks for partial transcription
        show_partial: Whether to show partial results during recording
    """
    print(f"\nRecording for {duration} seconds...")
    print(f"Chunk interval: {chunk_interval}s")
    print("-" * 50)

    # Record full audio
    print("🎤 Recording... Speak now!")
    audio_data = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype='float32',
    )

    # Show countdown while recording
    start_time = time.time()
    last_chunk_time = start_time
    chunks_sent = 0

    while time.time() - start_time < duration:
        elapsed = time.time() - start_time
        remaining = duration - elapsed
        print(f"\r  Recording: {elapsed:.1f}s / {duration}s (remaining: {remaining:.1f}s)", end="", flush=True)

        # Send partial chunk if interval passed
        if show_partial and (time.time() - last_chunk_time >= chunk_interval):
            samples_so_far = int(elapsed * SAMPLE_RATE)
            if samples_so_far > 0:
                partial_audio = audio_data[:samples_so_far].copy()
                sd.wait()  # Ensure recording is synced

                # Only send if we have actual audio data
                if not np.all(partial_audio == 0):
                    chunks_sent += 1
                    # Send partial in background to not block recording display
                    threading.Thread(
                        target=send_partial_chunk,
                        args=(partial_audio, chunks_sent),
                        daemon=True
                    ).start()

            last_chunk_time = time.time()

        time.sleep(0.1)

    sd.wait()  # Wait for recording to complete
    print("\n✓ Recording complete!")
    print("-" * 50)

    # Final transcription
    print("\n📝 Final transcription:")
    transcribe_audio(audio_data, is_final=True)


def send_partial_chunk(audio_data: np.ndarray, chunk_num: int):
    """Send partial audio chunk for transcription."""
    try:
        # Convert to WAV bytes
        buffer = io.BytesIO()
        sf.write(buffer, audio_data, SAMPLE_RATE, format='WAV')
        buffer.seek(0)

        response = requests.post(
            f"{STT_URL}/transcribe/stream",
            files={"file": ("chunk.wav", buffer, "audio/wav")},
            params={"is_final": False},
            timeout=10,
        )

        if response.ok:
            result = response.json()
            text = result.get("text", "").strip()
            if text:
                print(f"\n  [Partial {chunk_num}]: {text}")
    except Exception as e:
        pass  # Ignore errors for partial chunks


def transcribe_audio(audio_data: np.ndarray, is_final: bool = True, language: str = None):
    """Send audio to STT service and display result."""
    start_time = time.time()

    # Convert to WAV bytes
    buffer = io.BytesIO()
    sf.write(buffer, audio_data, SAMPLE_RATE, format='WAV')
    buffer.seek(0)

    try:
        params = {}
        if language:
            params["language"] = language

        response = requests.post(
            f"{STT_URL}/transcribe",
            files={"file": ("recording.wav", buffer, "audio/wav")},
            params=params,
            timeout=30,
        )

        latency = (time.time() - start_time) * 1000

        if response.ok:
            result = response.json()
            print(f"\n  Text: {result['text']}")
            print(f"  Language: {result['language']} (confidence: {result['confidence']:.2%})")
            print(f"  Latency: {latency:.0f}ms")

            if result.get('segments'):
                print(f"  Segments: {len(result['segments'])}")
                for seg in result['segments'][:3]:  # Show first 3 segments
                    print(f"    [{seg['start']:.1f}s - {seg['end']:.1f}s]: {seg['text']}")
                if len(result['segments']) > 3:
                    print(f"    ... and {len(result['segments']) - 3} more segments")
        else:
            print(f"  Error: {response.status_code} - {response.text}")

    except requests.exceptions.ConnectionError:
        print("  Error: Cannot connect to STT server")
        print(f"  Make sure server is running: uvicorn server:app --port 8001")
    except Exception as e:
        print(f"  Error: {e}")


def test_connection():
    """Test connection to STT server."""
    try:
        response = requests.get(f"{STT_URL}/health", timeout=5)
        if response.ok:
            info = response.json()
            print(f"✓ Connected to STT server")
            print(f"  Model: {info.get('model', 'unknown')}")
            print(f"  Device: {info.get('device', 'unknown')}")
            return True
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to STT server")
        print(f"  Start the server: cd services/stt && uvicorn server:app --port 8001")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def list_audio_devices():
    """List available audio devices."""
    print("\nAudio Devices:")
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        marker = "*" if i == sd.default.device[0] else " "
        if d['max_input_channels'] > 0:
            print(f"  {marker} [{i}] {d['name']} (in: {d['max_input_channels']})")


def continuous_listen(
    threshold: float = 0.5,
    min_speech_ms: int = 250,
    min_silence_ms: int = 500,
    speech_pad_ms: int = 500,
    language: str = None,
):
    """Continuously listen and transcribe using VAD for endpoint detection.

    Listens to microphone, detects speech boundaries using VAD, and transcribes
    each utterance automatically.

    Args:
        threshold: VAD speech probability threshold (0.0-1.0)
        min_speech_ms: Minimum speech duration to trigger transcription
        min_silence_ms: Silence duration to mark speech endpoint
        speech_pad_ms: Pre-speech padding to capture word onsets
        language: Force language code (e.g., 'en', 'es') or None for auto-detect
    """
    if not VAD_AVAILABLE:
        print("Error: VAD not available. Install torch and torchaudio:")
        print("  pip install torch torchaudio")
        return

    print("\n" + "=" * 50)
    print("Continuous Listening Mode (VAD)")
    print("=" * 50)
    print(f"  Threshold: {threshold}")
    print(f"  Min speech: {min_speech_ms}ms")
    print(f"  Min silence: {min_silence_ms}ms (endpoint detection)")
    print(f"  Speech pad: {speech_pad_ms}ms (pre-speech buffer)")
    print(f"  Language: {language or 'auto-detect'}")
    print("\nPress Ctrl+C to stop")
    print("-" * 50)

    # Initialize VAD
    print("Loading VAD model...")
    vad = VoiceActivityDetector(
        threshold=threshold,
        min_speech_ms=min_speech_ms,
        min_silence_ms=min_silence_ms,
        speech_pad_ms=speech_pad_ms,
    )
    print("VAD ready!")

    # Audio callback for streaming
    audio_queue = Queue()

    def audio_callback(indata, frames, time_info, status):
        if status:
            print(f"  [Audio status: {status}]", file=sys.stderr)
        audio_queue.put(indata.copy())

    # Stats tracking
    utterance_count = 0
    total_duration = 0.0

    try:
        print("\n🎤 Listening... (speak to transcribe)")

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='float32',
            blocksize=1600,  # 100ms chunks
            callback=audio_callback,
        ):
            while True:
                # Get audio chunk
                chunk = audio_queue.get()
                chunk = chunk.flatten()

                # Process through VAD
                is_speech = vad.process_chunk(chunk)

                # Show status
                if vad.speech_started() and not vad.speech_ended():
                    duration = vad.get_speech_duration()
                    print(f"\r  🔴 Recording... {duration:.1f}s", end="", flush=True)

                # Check if speech ended
                if vad.speech_ended():
                    print()  # New line after recording status

                    # Get speech audio and transcribe
                    audio = vad.get_speech_audio()
                    duration = vad.get_speech_duration()

                    if duration > 0.1:  # Skip very short utterances
                        utterance_count += 1
                        total_duration += duration
                        print(f"\n📝 Utterance #{utterance_count} ({duration:.1f}s):")
                        transcribe_audio(audio, language=language)

                    # Reset for next utterance
                    vad.reset()
                    print("\n🎤 Listening...")

    except KeyboardInterrupt:
        print("\n\n" + "=" * 50)
        print("Session Summary")
        print("=" * 50)
        print(f"  Utterances: {utterance_count}")
        print(f"  Total speech: {total_duration:.1f}s")
        print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Test streaming STT")
    parser.add_argument(
        "--duration",
        type=float,
        default=5.0,
        help="Recording duration in seconds (default: 5)"
    )
    parser.add_argument(
        "--chunk-interval",
        type=float,
        default=2.0,
        help="Interval between partial transcriptions in seconds (default: 2)"
    )
    parser.add_argument(
        "--no-partial",
        action="store_true",
        help="Disable partial transcriptions during recording"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Enable continuous listening with VAD-based endpoint detection"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="VAD speech probability threshold (default: 0.5)"
    )
    parser.add_argument(
        "--min-speech",
        type=int,
        default=250,
        help="Minimum speech duration in ms (default: 250)"
    )
    parser.add_argument(
        "--min-silence",
        type=int,
        default=500,
        help="Silence duration for endpoint detection in ms (default: 500)"
    )
    parser.add_argument(
        "--speech-pad",
        type=int,
        default=500,
        help="Pre-speech padding to capture word onsets in ms (default: 500)"
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Force language code (e.g., 'en', 'es', 'de'). Default: auto-detect"
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List audio devices and exit"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8001",
        help="STT server URL (default: http://localhost:8001)"
    )
    args = parser.parse_args()

    global STT_URL
    STT_URL = args.url

    if args.list_devices:
        list_audio_devices()
        return

    print("=" * 50)
    print("STT Streaming Test")
    print("=" * 50)

    # Check server connection
    if not test_connection():
        return

    # Show audio device
    list_audio_devices()
    print()

    # Choose mode
    if args.continuous:
        # VAD-based continuous listening
        continuous_listen(
            threshold=args.threshold,
            min_speech_ms=args.min_speech,
            min_silence_ms=args.min_silence,
            speech_pad_ms=args.speech_pad,
            language=args.language,
        )
    else:
        # Fixed duration recording
        record_and_transcribe(
            duration=args.duration,
            chunk_interval=args.chunk_interval,
            show_partial=not args.no_partial,
        )

    print("\n" + "=" * 50)
    print("Done!")


if __name__ == "__main__":
    main()
