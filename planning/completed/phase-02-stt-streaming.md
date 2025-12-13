# Phase 2: STT Integration + Streaming Harness

**Status**: ✅ Complete
**Goal**: Validate STT pipeline with visual streaming feedback

## Tasks

- [x] Create STT server (`services/stt/server.py`)
- [x] Create STT requirements.txt
- [x] Create STT Dockerfile (CUDA)
- [x] **Create STT streaming test harness** (`services/stt/test_streaming.py`)
- [x] Fix STT WebSocket protocol bug (line 180)
- [x] **Test the harness with live microphone** - 1.6s latency for 5s audio (0.32x RTF)
- [x] **Add VAD-based endpoint detection** - silero-vad for automatic speech boundary detection

## Deliverable

Terminal demo showing real-time transcription as you speak.

## Test Harness Requirements

`services/stt/test_streaming.py` should:
1. Record from microphone using `sounddevice`
2. Stream audio chunks to STT HTTP endpoint
3. Display partial transcriptions as they arrive
4. Show final transcription with timing metrics

Pattern: Similar to `services/tts-mcp/test_streaming_playback.py`

## WebSocket Bug (server.py:180) - FIXED

~~Current code has incorrect type checking~~ Fixed by checking for "bytes" and "text" keys directly:
```python
# Before (wrong)
if data.get("type") == "websocket.receive":
    if "bytes" in data: ...

# After (fixed)
message = await websocket.receive()
if "bytes" in message:
    audio_buffer.write(message["bytes"])
elif "text" in message:
    command = message["text"].strip().upper()
```

## Files Created/Modified

| File | Status |
|------|--------|
| `services/stt/test_streaming.py` | ✅ Created |
| `services/stt/server.py` | ✅ Fixed |
| `services/stt/vad.py` | ✅ Created |
| `services/stt/requirements.txt` | ✅ Updated (torch, torchaudio) |

## VAD-Based Endpoint Detection

Added `services/stt/vad.py` using silero-vad for automatic speech boundary detection:

- **Speech start**: Detects when user begins speaking (min 250ms of speech)
- **Speech end**: Triggers transcription after 500ms of silence
- **Continuous mode**: `python test_streaming.py --continuous`

## Testing Commands

```bash
# Terminal 1: Start STT server
cd services/stt
source .venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001

# Terminal 2: Fixed duration mode
python test_streaming.py --duration 5

# Terminal 2: Continuous listening (VAD)
python test_streaming.py --continuous

# Adjust VAD sensitivity
python test_streaming.py --continuous --threshold 0.3 --min-silence 300
```
