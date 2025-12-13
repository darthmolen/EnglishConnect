#!/usr/bin/env python3
"""Test streaming TTS with real-time metrics.

This script demonstrates real-time audio streaming from VibeVoice TTS.
Audio chunks are collected as they're generated, measuring latency and throughput.

If sounddevice/PortAudio is available, audio plays through speakers.
Otherwise, audio is saved to a file for playback elsewhere.

Usage:
    cd services/tts-mcp
    source .venv/bin/activate
    python test_streaming_playback.py --text "Hello, how are you today?"
    python test_streaming_playback.py --voice speaker_b  # Emma
    python test_streaming_playback.py --output /tmp/output.wav
"""

import argparse
import copy
import threading
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

# Try to import sounddevice for real-time playback
try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except (ImportError, OSError):
    AUDIO_AVAILABLE = False
    print("Note: sounddevice/PortAudio not available - will save to file instead")

# Configuration
MODEL_PATH = "microsoft/VibeVoice-Realtime-0.5B"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
SAMPLE_RATE = 24000

SCRIPT_DIR = Path(__file__).parent
VOICES_DIR = SCRIPT_DIR / "VibeVoice" / "demo" / "voices" / "streaming_model"

VOICES = {
    "speaker_a": {"name": "Carter", "file": "en-Carter_man.pt"},
    "speaker_b": {"name": "Emma", "file": "en-Emma_woman.pt"},
    "speaker_c": {"name": "Davis", "file": "en-Davis_man.pt"},
    "speaker_d": {"name": "Grace", "file": "en-Grace_woman.pt"},
    "speaker_e": {"name": "Frank", "file": "en-Frank_man.pt"},
    "speaker_f": {"name": "Mike", "file": "en-Mike_man.pt"},
}


def load_model():
    """Load VibeVoice model and processor."""
    from vibevoice.modular.modeling_vibevoice_streaming_inference import (
        VibeVoiceStreamingForConditionalGenerationInference
    )
    from vibevoice.processor.vibevoice_streaming_processor import (
        VibeVoiceStreamingProcessor
    )

    print(f"Loading VibeVoice model on {DEVICE}...")

    processor = VibeVoiceStreamingProcessor.from_pretrained(MODEL_PATH)

    try:
        model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.bfloat16,
            device_map=DEVICE,
            attn_implementation="flash_attention_2"
        )
    except Exception as e:
        print(f"Flash attention failed ({e}), using sdpa...")
        model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.bfloat16,
            device_map=DEVICE,
            attn_implementation="sdpa"
        )

    model.eval()
    model.set_ddpm_inference_steps(num_steps=5)
    print("Model loaded!")

    return model, processor


def stream_and_play(text: str, voice_id: str, model, processor, output_path: str = None):
    """Generate TTS and stream audio (to speakers if available, or save to file)."""
    from vibevoice.modular.streamer import AudioStreamer

    # Load voice preset
    voice_config = VOICES[voice_id]
    preset_path = VOICES_DIR / voice_config["file"]
    print(f"Loading voice preset: {voice_config['name']} ({preset_path.name})")
    voice_preset = torch.load(preset_path, map_location=DEVICE, weights_only=False)

    # Clean up text
    full_script = text.replace("'", "'").replace('"', '"').replace('"', '"')

    # Process input
    inputs = processor.process_input_with_cached_prompt(
        text=full_script,
        cached_prompt=voice_preset,
        padding=True,
        return_tensors="pt",
        return_attention_mask=True,
    )

    # Move to device
    for k, v in inputs.items():
        if torch.is_tensor(v):
            inputs[k] = v.to(DEVICE)

    # Create audio streamer to receive chunks
    audio_streamer = AudioStreamer(batch_size=1, stop_signal=None)

    # Shared state for streaming
    all_chunks = []
    chunk_times = []
    first_chunk_time = [None]

    def collector_thread():
        """Thread that collects audio chunks (and plays if audio available)."""
        stream = None
        if AUDIO_AVAILABLE:
            try:
                stream = sd.OutputStream(
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype='float32',
                )
                stream.start()
                print("Playing through speakers...")
            except Exception as e:
                print(f"Could not open audio stream: {e}")
                stream = None

        chunk_count = 0
        try:
            for audio_chunk in audio_streamer.get_stream(0):
                chunk_time = time.time()
                if first_chunk_time[0] is None:
                    first_chunk_time[0] = chunk_time

                # Convert to float32 numpy
                audio_np = audio_chunk.float().numpy().squeeze()
                all_chunks.append(audio_np)
                chunk_times.append(chunk_time)

                # Play if available
                if stream:
                    stream.write(audio_np)

                chunk_count += 1
                # Print progress dots
                if chunk_count % 10 == 0:
                    print(".", end="", flush=True)

        except StopIteration:
            pass
        finally:
            if stream:
                stream.stop()
                stream.close()
            print(f"\nReceived {chunk_count} audio chunks")

    # Start collector/playback thread
    collector = threading.Thread(target=collector_thread, daemon=True)
    collector.start()

    # Run generation (this feeds audio_streamer)
    print(f"\nGenerating: \"{text}\"")
    print(f"Voice: {voice_config['name']}")
    print("-" * 50)

    start_time = time.time()

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=None,
            cfg_scale=1.5,
            tokenizer=processor.tokenizer,
            generation_config={'do_sample': False},
            verbose=False,
            show_progress_bar=True,
            audio_streamer=audio_streamer,
            all_prefilled_outputs=copy.deepcopy(voice_preset),
        )

    generation_time = time.time() - start_time

    # Wait for collector to finish
    collector.join(timeout=30)

    # Calculate metrics
    if all_chunks:
        total_samples = sum(len(c) for c in all_chunks)
        audio_duration = total_samples / SAMPLE_RATE
        rtf = generation_time / audio_duration if audio_duration > 0 else 0

        if first_chunk_time[0]:
            latency = (first_chunk_time[0] - start_time) * 1000  # ms
        else:
            latency = 0

        # Calculate inter-chunk timing
        if len(chunk_times) > 1:
            inter_chunk_times = [
                (chunk_times[i] - chunk_times[i-1]) * 1000
                for i in range(1, len(chunk_times))
            ]
            avg_chunk_interval = np.mean(inter_chunk_times)
            max_chunk_interval = np.max(inter_chunk_times)
        else:
            avg_chunk_interval = 0
            max_chunk_interval = 0

        print("-" * 50)
        print("STREAMING METRICS")
        print("-" * 50)
        print(f"First chunk latency:    {latency:.0f}ms")
        print(f"Total generation time:  {generation_time:.2f}s")
        print(f"Audio duration:         {audio_duration:.2f}s")
        print(f"RTF (Real Time Factor): {rtf:.2f}x")
        print(f"Chunks generated:       {len(all_chunks)}")
        print(f"Avg chunk interval:     {avg_chunk_interval:.1f}ms")
        print(f"Max chunk interval:     {max_chunk_interval:.1f}ms")
        print("-" * 50)

        if rtf < 1.0:
            print("✓ REAL-TIME CAPABLE (RTF < 1.0)")
        else:
            print("✗ NOT REAL-TIME (RTF >= 1.0)")

        # Save to file
        if output_path or not AUDIO_AVAILABLE:
            output_path = output_path or "/tmp/tts_streaming_output.wav"
            combined = np.concatenate(all_chunks)
            sf.write(output_path, combined, SAMPLE_RATE)
            print(f"\nSaved audio to: {output_path}")

            # Play with paplay (PulseAudio) since sounddevice doesn't have PulseAudio backend
            import subprocess
            import shutil
            if shutil.which("paplay"):
                print("Playing with paplay...")
                subprocess.run(["paplay", output_path], check=False)

    return all_chunks


def main():
    parser = argparse.ArgumentParser(description="Test streaming TTS playback")
    parser.add_argument(
        "--text",
        type=str,
        default="Hello! I am your English tutor. Let's practice some conversation today. How are you feeling?",
        help="Text to synthesize"
    )
    parser.add_argument(
        "--voice",
        type=str,
        default="speaker_a",
        choices=list(VOICES.keys()),
        help="Voice ID to use"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output WAV file path (auto-saves if no audio device)"
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available voices and exit"
    )
    args = parser.parse_args()

    if args.list_voices:
        print("\nAvailable voices:")
        for vid, config in VOICES.items():
            print(f"  {vid}: {config['name']} ({config['file']})")
        return

    # Load model
    model, processor = load_model()

    # Stream and play/save
    stream_and_play(args.text, args.voice, model, processor, args.output)

    print("\nDone!")


if __name__ == "__main__":
    main()
