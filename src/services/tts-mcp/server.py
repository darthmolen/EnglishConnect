#!/usr/bin/env python3
"""Text-to-Speech MCP Server using VibeVoice-Realtime.

Provides MCP tools for agents to generate speech from text.
Also provides HTTP API for direct backend access.

Usage:
    # MCP mode (default)
    python server.py

    # HTTP mode (for backend access)
    python server.py --http

Note: Requires VibeVoice to be installed. See https://github.com/microsoft/VibeVoice
"""

import argparse
import asyncio
import base64
import copy
import io
import json
import os
import uuid
from pathlib import Path

import torch
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

load_dotenv()

# Configuration
MODEL_PATH = os.getenv("VIBEVOICE_MODEL_PATH", "microsoft/VibeVoice-Realtime-0.5B")
DEVICE = os.getenv("TTS_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
OUTPUT_DIR = Path(os.getenv("TTS_OUTPUT_DIR", "/tmp/tts_output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Voice presets directory (inside VibeVoice repo)
SCRIPT_DIR = Path(__file__).parent
VOICES_DIR = SCRIPT_DIR / "VibeVoice" / "demo" / "voices" / "streaming_model"

# Speaker voice configurations - maps to actual .pt preset files
# English speakers: Carter, Davis, Emma, Frank, Grace, Mike
VOICES = {
    "speaker_a": {"name": "Carter", "file": "en-Carter_man.pt", "description": "Male English speaker (clear, professional)"},
    "speaker_b": {"name": "Emma", "file": "en-Emma_woman.pt", "description": "Female English speaker (warm, friendly)"},
    "speaker_c": {"name": "Davis", "file": "en-Davis_man.pt", "description": "Male English speaker (conversational)"},
    "speaker_d": {"name": "Grace", "file": "en-Grace_woman.pt", "description": "Female English speaker (clear, articulate)"},
    "speaker_e": {"name": "Frank", "file": "en-Frank_man.pt", "description": "Male English speaker (authoritative)"},
    "speaker_f": {"name": "Mike", "file": "en-Mike_man.pt", "description": "Male English speaker (casual, friendly)"},
}

# Global model instance
_model = None
_processor = None
_voice_presets = {}  # Cache loaded voice presets
_sample_rate = 24000  # VibeVoice output sample rate


def load_voice_preset(voice_id: str) -> dict | None:
    """Load and cache a voice preset file."""
    global _voice_presets

    if voice_id in _voice_presets:
        return _voice_presets[voice_id]

    voice_config = VOICES.get(voice_id)
    if not voice_config:
        return None

    preset_path = VOICES_DIR / voice_config["file"]
    if not preset_path.exists():
        print(f"Warning: Voice preset file not found: {preset_path}")
        return None

    print(f"Loading voice preset: {preset_path}")
    preset = torch.load(preset_path, map_location=DEVICE, weights_only=False)
    _voice_presets[voice_id] = preset
    return preset


def get_model():
    """Get or initialize the VibeVoice model."""
    global _model, _processor

    if _model is None:
        print(f"Loading VibeVoice model: {MODEL_PATH} on {DEVICE}...")

        try:
            from vibevoice.modular.modeling_vibevoice_streaming_inference import (
                VibeVoiceStreamingForConditionalGenerationInference
            )
            from vibevoice.processor.vibevoice_streaming_processor import (
                VibeVoiceStreamingProcessor
            )

            # Determine dtype based on device
            # Use bfloat16 on CUDA to match the voice preset format
            if DEVICE == "cuda":
                load_dtype = torch.bfloat16
                attn_impl = "flash_attention_2"
            elif DEVICE == "mps":
                load_dtype = torch.float32
                attn_impl = "sdpa"
            else:
                load_dtype = torch.float32
                attn_impl = "sdpa"

            # Load processor and model
            _processor = VibeVoiceStreamingProcessor.from_pretrained(MODEL_PATH)

            try:
                _model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                    MODEL_PATH,
                    torch_dtype=load_dtype,
                    device_map=DEVICE,
                    attn_implementation=attn_impl
                )
            except Exception as e:
                # Fallback to sdpa if flash_attention_2 fails
                print(f"Flash attention failed ({e}), falling back to sdpa...")
                _model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                    MODEL_PATH,
                    torch_dtype=load_dtype,
                    device_map=DEVICE,
                    attn_implementation="sdpa"
                )

            _model.eval()
            _model.set_ddpm_inference_steps(num_steps=5)
            print("VibeVoice model loaded successfully!")

        except ImportError as e:
            print(f"VibeVoice import failed: {e}")
            print("Using placeholder TTS. Install VibeVoice for full functionality.")
            _model = "placeholder"
            _processor = None

    return _model, _processor


def _synthesize_sync(text: str, voice_id: str = "speaker_a") -> bytes:
    """Synchronous synthesis - runs in thread pool.

    Returns WAV audio bytes.
    """
    import numpy as np
    import soundfile as sf

    model, processor = get_model()

    if model == "placeholder" or processor is None:
        # Placeholder: Generate silence
        duration = len(text) * 0.05  # Rough estimate: 50ms per character
        samples = int(duration * _sample_rate)
        audio = np.zeros(samples, dtype=np.float32)

        buffer = io.BytesIO()
        sf.write(buffer, audio, _sample_rate, format="WAV")
        buffer.seek(0)
        return buffer.read()

    # Load voice preset (contains pre-computed KV cache for speaker)
    voice_preset = load_voice_preset(voice_id)
    if voice_preset is None:
        # Fall back to speaker_a if voice not found
        voice_preset = load_voice_preset("speaker_a")

    if voice_preset is None:
        raise RuntimeError("No voice presets available. Check VibeVoice installation.")

    # Clean up text for TTS
    full_script = text.replace("'", "'").replace('"', '"').replace('"', '"')

    # Process input with the cached voice prompt
    inputs = processor.process_input_with_cached_prompt(
        text=full_script,
        cached_prompt=voice_preset,
        padding=True,
        return_tensors="pt",
        return_attention_mask=True,
    )

    # Move inputs to device
    for k, v in inputs.items():
        if torch.is_tensor(v):
            inputs[k] = v.to(DEVICE)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=None,
            cfg_scale=1.5,
            tokenizer=processor.tokenizer,
            generation_config={'do_sample': False},
            verbose=False,
            show_progress_bar=False,
            all_prefilled_outputs=copy.deepcopy(voice_preset),
        )

    # Get audio from outputs
    if outputs.speech_outputs and outputs.speech_outputs[0] is not None:
        # Convert to float32 for numpy compatibility (bfloat16 not supported)
        # Shape is [1, samples] - squeeze to 1D for soundfile
        audio = outputs.speech_outputs[0].cpu().float().numpy().squeeze()
    else:
        raise RuntimeError("No audio output generated")

    # Write to bytes using WAV format with explicit subtype (needed for BytesIO)
    buffer = io.BytesIO()
    sf.write(buffer, audio, _sample_rate, format="WAV", subtype="FLOAT")
    buffer.seek(0)
    return buffer.read()


async def synthesize_with_vibevoice(text: str, voice_id: str = "speaker_a") -> bytes:
    """Async synthesis - offloads CPU/GPU work to thread pool.

    This prevents blocking other requests while model inference runs.
    """
    return await asyncio.to_thread(_synthesize_sync, text, voice_id)


def _concatenate_audio_sync(audio_segments: list[bytes], pause_seconds: float = 0.5) -> bytes:
    """Synchronous audio concatenation - runs in thread pool."""
    import numpy as np
    import soundfile as sf

    pause_samples = int(pause_seconds * _sample_rate)
    all_segments = []

    for audio_bytes in audio_segments:
        buffer = io.BytesIO(audio_bytes)
        audio_data, _ = sf.read(buffer)
        all_segments.append(audio_data)
        all_segments.append(np.zeros(pause_samples, dtype=np.float32))

    combined_audio = np.concatenate(all_segments)

    buffer = io.BytesIO()
    sf.write(buffer, combined_audio, _sample_rate, format="WAV")
    buffer.seek(0)
    return buffer.read()


async def concatenate_audio(audio_segments: list[bytes], pause_seconds: float = 0.5) -> bytes:
    """Async audio concatenation - offloads to thread pool."""
    return await asyncio.to_thread(_concatenate_audio_sync, audio_segments, pause_seconds)


# Create MCP server
mcp = FastMCP("tts")


@mcp.tool()
async def speak(text: str, voice: str = "speaker_a") -> str:
    """Generate speech audio from text.

    Args:
        text: The text to speak
        voice: Voice ID to use (speaker_a through speaker_f)

    Returns:
        JSON with audio file path and metadata
    """
    if voice not in VOICES:
        return json.dumps({
            "error": f"Unknown voice: {voice}. Available: {list(VOICES.keys())}"
        })

    voice_config = VOICES[voice]

    try:
        # Generate audio (runs in thread pool, doesn't block event loop)
        audio_bytes = await synthesize_with_vibevoice(text, voice)

        # Save to file
        filename = f"{uuid.uuid4()}.wav"
        filepath = OUTPUT_DIR / filename
        await asyncio.to_thread(filepath.write_bytes, audio_bytes)

        return json.dumps({
            "status": "success",
            "audio_path": str(filepath),
            "voice": voice,
            "speaker_name": voice_config["name"],
            "text": text,
            "sample_rate": _sample_rate,
            "format": "wav",
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
        })


@mcp.tool()
async def speak_dialogue(exchanges: str) -> str:
    """Generate a multi-speaker dialogue audio.

    Args:
        exchanges: JSON array of dialogue turns, e.g.:
            [{"speaker": "speaker_a", "text": "Hello"}, {"speaker": "speaker_b", "text": "Hi there"}]

    Returns:
        JSON with combined audio file path
    """
    try:
        turns = json.loads(exchanges)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    audio_segments = []

    for turn in turns:
        voice_id = turn.get("speaker", "speaker_a")
        text = turn.get("text", "")

        if voice_id not in VOICES:
            voice_id = "speaker_a"

        # Generate audio for this turn (async, doesn't block)
        audio_bytes = await synthesize_with_vibevoice(text, voice_id)
        audio_segments.append(audio_bytes)

    # Concatenate all segments with pauses (async)
    combined_bytes = await concatenate_audio(audio_segments, pause_seconds=0.5)
    duration_seconds = len(combined_bytes) / (_sample_rate * 2)  # Approximate

    # Save to file
    filename = f"dialogue_{uuid.uuid4()}.wav"
    filepath = OUTPUT_DIR / filename
    await asyncio.to_thread(filepath.write_bytes, combined_bytes)

    return json.dumps({
        "status": "success",
        "audio_path": str(filepath),
        "turns": len(turns),
        "duration_seconds": duration_seconds,
        "format": "wav",
    })


@mcp.tool()
async def list_voices() -> str:
    """List available TTS voices.

    Returns:
        JSON array of available voices with their descriptions
    """
    return json.dumps([
        {"id": k, "name": v["name"], "description": v["description"]}
        for k, v in VOICES.items()
    ])


@mcp.tool()
async def speak_base64(text: str, voice: str = "speaker_a") -> str:
    """Generate speech and return as base64-encoded audio.

    Useful when you need the audio data directly without file I/O.

    Args:
        text: The text to speak
        voice: Voice ID to use (speaker_a through speaker_f)

    Returns:
        JSON with base64-encoded WAV audio
    """
    if voice not in VOICES:
        return json.dumps({
            "error": f"Unknown voice: {voice}. Available: {list(VOICES.keys())}"
        })

    voice_config = VOICES[voice]

    try:
        audio_bytes = await synthesize_with_vibevoice(text, voice)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return json.dumps({
            "status": "success",
            "audio_base64": audio_b64,
            "voice": voice,
            "speaker_name": voice_config["name"],
            "text": text,
            "sample_rate": _sample_rate,
            "format": "wav",
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
        })


# ============================================================================
# HTTP API (FastAPI) - for direct backend access
# ============================================================================

http_app = FastAPI(
    title="EnglishConnect TTS Service",
    description="Text-to-Speech using VibeVoice-Realtime",
    version="0.1.0",
)

http_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SynthesizeRequest(BaseModel):
    """Request body for /synthesize endpoint."""
    text: str
    voice: str = "speaker_a"


class SynthesizeResponse(BaseModel):
    """Response body for /synthesize endpoint."""
    audio_base64: str
    voice: str
    speaker_name: str
    text: str
    sample_rate: int
    format: str


@http_app.on_event("startup")
async def startup_event():
    """Load model on HTTP server startup."""
    get_model()


@http_app.get("/")
async def root():
    """Health check."""
    return {"status": "ok", "service": "tts", "voices": list(VOICES.keys())}


@http_app.get("/health")
async def health():
    """Detailed health check."""
    model, _ = get_model()
    return {
        "status": "healthy",
        "model": MODEL_PATH,
        "device": DEVICE,
        "model_loaded": model is not None,
    }


@http_app.get("/voices")
async def list_voices_http():
    """List available TTS voices."""
    return [
        {"id": k, "name": v["name"], "description": v["description"]}
        for k, v in VOICES.items()
    ]


@http_app.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize_http(request: SynthesizeRequest):
    """Synthesize speech from text.

    Args:
        request: SynthesizeRequest with text and optional voice

    Returns:
        SynthesizeResponse with base64-encoded WAV audio
    """
    if request.voice not in VOICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown voice: {request.voice}. Available: {list(VOICES.keys())}"
        )

    voice_config = VOICES[request.voice]

    try:
        audio_bytes = await synthesize_with_vibevoice(request.text, request.voice)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return SynthesizeResponse(
            audio_base64=audio_b64,
            voice=request.voice,
            speaker_name=voice_config["name"],
            text=request.text,
            sample_rate=_sample_rate,
            format="wav",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Main entry point
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TTS Server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run HTTP server instead of MCP server"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="HTTP server port (default: 8002)"
    )
    args = parser.parse_args()

    if args.http:
        # Run HTTP server
        import uvicorn
        print(f"Starting TTS HTTP server on port {args.port}...")
        uvicorn.run(http_app, host="0.0.0.0", port=args.port)
    else:
        # Run MCP server (default)
        get_model()
        mcp.run()
