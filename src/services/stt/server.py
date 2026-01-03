#!/usr/bin/env python3
"""Speech-to-Text service using faster-whisper.

Provides HTTP and WebSocket APIs for transcribing audio.

Usage:
    uvicorn server:app --host 0.0.0.0 --port 8001
"""

import asyncio
import io
import logging
import os
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import numpy as np
import soundfile as sf
from dotenv import load_dotenv
from fastapi import FastAPI, File, Header, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

# Configure timing logger
timing_logger = logging.getLogger("timing")


def log_stt_timing(point: str, label: str, request_id: str = "unknown", **extra) -> float:
    """Log STT timing point."""
    ts = time.time()
    extra_str = " ".join(f"{k}={v}" for k, v in extra.items())
    timing_logger.info(
        f"[TIMING] request_id={request_id} "
        f"point={point} ts={ts:.3f} label={label!r}"
        + (f" {extra_str}" if extra_str else "")
    )
    return ts

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "large-v3")
DEVICE = os.getenv("WHISPER_DEVICE", "cuda")  # 'cuda' or 'cpu'
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float16")  # 'float16', 'int8', etc.

# Global model instance
_model = None


def get_model():
    """Get or initialize the Whisper model."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        print(f"Loading Whisper model: {MODEL_SIZE} on {DEVICE}...")
        _model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        print("Model loaded successfully!")
    return _model


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup."""
    get_model()
    yield


app = FastAPI(
    title="EnglishConnect STT Service",
    description="Speech-to-text using faster-whisper",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranscriptionResult(BaseModel):
    """Transcription result model."""
    text: str
    language: str
    confidence: float
    segments: list[dict]


class TranscriptionRequest(BaseModel):
    """Request model for transcription settings."""
    language: Optional[str] = None  # Auto-detect if not specified
    task: str = "transcribe"  # 'transcribe' or 'translate'


@app.get("/")
async def root():
    """Health check."""
    return {"status": "ok", "service": "stt", "model": MODEL_SIZE}


@app.get("/health")
async def health():
    """Detailed health check."""
    model = get_model()
    return {
        "status": "healthy",
        "model": MODEL_SIZE,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
    }


def get_file_extension(content_type: str, filename: str) -> str:
    """Determine the correct file extension based on content type or filename."""
    # Map content types to extensions
    content_type_map = {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/mp3": ".mp3",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/wave": ".wav",
        "audio/x-wav": ".wav",
        "audio/flac": ".flac",
        "audio/m4a": ".m4a",
        "audio/mp4": ".m4a",
    }

    # Try content type first
    if content_type and content_type.lower() in content_type_map:
        return content_type_map[content_type.lower()]

    # Fall back to filename extension
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
        if ext in [".webm", ".ogg", ".mp3", ".wav", ".flac", ".m4a", ".mp4"]:
            return ext

    # Default to webm (common for browser MediaRecorder)
    return ".webm"


@app.post("/transcribe", response_model=TranscriptionResult)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = None,
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
):
    """Transcribe an audio file.

    Args:
        file: Audio file (WAV, MP3, webm, etc.)
        language: Optional language code (e.g., 'en', 'es'). Auto-detects if not specified.
        x_request_id: Optional request ID for timing correlation.

    Returns:
        Transcription result with text, language, and confidence.
    """
    # Use provided request ID or generate one
    req_id = x_request_id or str(uuid.uuid4())[:8]

    # S2: Request received
    s2_ts = log_stt_timing("S2", "request_received", req_id)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Read audio file
    audio_bytes = await file.read()

    # Log incoming request details
    logger.info(
        f"Transcribe request: filename={file.filename}, "
        f"content_type={file.content_type}, size={len(audio_bytes)} bytes"
    )

    if len(audio_bytes) == 0:
        logger.warning("Received empty audio file")
        return TranscriptionResult(
            text="",
            language="unknown",
            confidence=0.0,
            segments=[],
        )

    # Determine correct file extension (important for faster-whisper/ffmpeg)
    ext = get_file_extension(file.content_type, file.filename)
    logger.info(f"Using file extension: {ext}")

    # Save to temp file (faster-whisper requires file path or numpy array)
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        model = get_model()

        # S3: Transcription start
        s3_ts = log_stt_timing("S3", "transcription_start", req_id, audio_bytes=len(audio_bytes))

        # Transcribe
        logger.info(f"Transcribing {tmp_path}...")
        segments, info = model.transcribe(
            tmp_path,
            language=language,
            beam_size=5,
            vad_filter=True,
        )

        # Collect segments
        segment_list = []
        full_text = []
        for segment in segments:
            segment_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "confidence": segment.avg_logprob,
            })
            full_text.append(segment.text)

        result_text = " ".join(full_text).strip()

        # S4: Transcription complete
        delta_ms = (time.time() - s3_ts) * 1000
        log_stt_timing("S4", "transcription_complete", req_id, text_len=len(result_text), delta_ms=f"{delta_ms:.1f}")

        logger.info(
            f"Transcription complete: language={info.language}, "
            f"confidence={info.language_probability:.2f}, text_length={len(result_text)}"
        )

        if not result_text:
            logger.info("No speech detected in audio")

        return TranscriptionResult(
            text=result_text,
            language=info.language,
            confidence=info.language_probability,
            segments=segment_list,
        )

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    finally:
        # Clean up temp file
        os.unlink(tmp_path)


@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """WebSocket endpoint for streaming transcription.

    Protocol:
    1. Client sends binary audio chunks (raw bytes)
    2. Client sends text commands: "END" to transcribe, "CLOSE" to disconnect
    3. Server responds with JSON transcription results

    Example client usage:
        ws.send_bytes(audio_chunk)  # Send audio data
        ws.send_text("END")         # Request transcription
        # Receive JSON: {"text": "...", "language": "en", "confidence": 0.95}
    """
    await websocket.accept()

    model = get_model()
    audio_buffer = io.BytesIO()

    try:
        while True:
            # Receive message - check for bytes or text keys directly
            message = await websocket.receive()

            # Handle binary audio data
            if "bytes" in message:
                audio_buffer.write(message["bytes"])

            # Handle text commands
            elif "text" in message:
                command = message["text"].strip().upper()

                if command == "END":
                    # Transcribe accumulated audio
                    audio_buffer.seek(0)
                    audio_bytes = audio_buffer.read()

                    if len(audio_bytes) == 0:
                        await websocket.send_json({"error": "No audio data received"})
                        continue

                    # Save to temp file for transcription
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        tmp.write(audio_bytes)
                        tmp_path = tmp.name

                    try:
                        segments, info = model.transcribe(
                            tmp_path,
                            beam_size=5,
                            vad_filter=True,
                        )

                        full_text = []
                        for segment in segments:
                            full_text.append(segment.text)

                        await websocket.send_json({
                            "text": " ".join(full_text).strip(),
                            "language": info.language,
                            "confidence": info.language_probability,
                        })

                    finally:
                        os.unlink(tmp_path)

                    # Reset buffer for next utterance
                    audio_buffer = io.BytesIO()

                elif command == "CLOSE":
                    break

                elif command == "CLEAR":
                    # Clear buffer without transcribing
                    audio_buffer = io.BytesIO()

            # Handle disconnect
            elif message.get("type") == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass  # Already closed


@app.post("/transcribe/stream")
async def transcribe_stream_chunk(
    file: UploadFile = File(...),
    is_final: bool = False,
):
    """Transcribe a streaming audio chunk.

    For real-time transcription, send audio chunks and get partial results.

    Args:
        file: Audio chunk (WAV format recommended)
        is_final: Whether this is the final chunk

    Returns:
        Partial or final transcription result
    """
    audio_bytes = await file.read()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        model = get_model()

        segments, info = model.transcribe(
            tmp_path,
            beam_size=5 if is_final else 1,  # Faster for partial results
            vad_filter=True,
        )

        full_text = []
        for segment in segments:
            full_text.append(segment.text)

        return {
            "text": " ".join(full_text).strip(),
            "is_final": is_final,
            "language": info.language,
        }

    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
