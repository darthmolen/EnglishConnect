# EnglishConnect Architecture

**Last Updated**: Phase 2 Complete (STT + VAD)

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Device                                     │
│  ┌─────────────┐                                          ┌─────────────┐   │
│  │ Microphone  │──────────────────────────────────────────│   Speaker   │   │
│  └──────┬──────┘                                          └──────▲──────┘   │
└─────────┼────────────────────────────────────────────────────────┼──────────┘
          │ Audio In                                         Audio Out
          ▼                                                        │
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Voice Pipeline (Local GPU)                        │
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │     VAD     │───▶│     STT     │───▶│  Azure AI   │───▶│     TTS     │   │
│  │ (silero)    │    │  (whisper)  │    │ (GPT-4o-m)  │    │ (VibeVoice) │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘   │
│   Endpoint           Speech-to-        Response            Text-to-         │
│   Detection          Text              Generation          Speech           │
│                                                                              │
│   ~0ms latency       ~800ms            ~variable           ~300ms TTFA      │
│                      RTF 0.32x                             RTF 0.51x        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Text-to-Speech (TTS) - VibeVoice

**Location**: `services/tts-mcp/`

**Technology**: Microsoft VibeVoice-Realtime-0.5B (MIT License)

**Performance**:
| Metric | Value |
|--------|-------|
| Time to First Audio (TTFA) | ~300ms |
| Real-Time Factor (RTF) | 0.51x |
| Sample Rate | 24kHz |
| Streaming | Yes (chunk-based) |

**Available Voices**:
| ID | Name | Gender |
|----|------|--------|
| speaker_a | Carter | Male |
| speaker_b | Emma | Female |
| speaker_c | Davis | Male |
| speaker_d | Grace | Female |
| speaker_e | Frank | Male |
| speaker_f | Mike | Male |

**Test Harness**: `services/tts-mcp/test_streaming_playback.py`

```bash
cd services/tts-mcp
source .venv/bin/activate
python test_streaming_playback.py --text "Hello, how are you?" --voice speaker_b
```

**CLI Options**:
| Flag | Default | Description |
|------|---------|-------------|
| `--text` | "Hello..." | Text to synthesize |
| `--voice` | speaker_a | Voice ID (speaker_a through speaker_f) |
| `--output` | None | Save to WAV file instead of playing |

**Files**:
- `server.py` - MCP server (for agent tool use)
- `test_streaming_playback.py` - Standalone test harness
- `requirements.txt` - Dependencies

---

### 2. Speech-to-Text (STT) - faster-whisper

**Location**: `services/stt/`

**Technology**: faster-whisper (ctranslate2-optimized Whisper)

**Performance**:
| Metric | Value |
|--------|-------|
| Model | medium |
| Latency (5s audio) | ~800ms |
| Real-Time Factor (RTF) | 0.32x |
| Sample Rate | 16kHz |
| Compute Type | float16 |

**API Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with model info |
| `/transcribe` | POST | Transcribe audio file |
| `/transcribe/stream` | POST | Transcribe streaming chunk |
| `/ws/transcribe` | WebSocket | Real-time streaming transcription |

**HTTP Example**:
```bash
curl -X POST http://localhost:8001/transcribe \
  -F "file=@audio.wav" \
  -F "language=en"
```

**Response**:
```json
{
  "text": "Hello, how are you?",
  "language": "en",
  "confidence": 0.98,
  "segments": [...]
}
```

**Configuration** (via environment or `.env`):
| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL_SIZE` | medium | Model size (tiny, base, small, medium, large-v3) |
| `WHISPER_DEVICE` | cuda | Device (cuda, cpu) |
| `WHISPER_COMPUTE_TYPE` | float16 | Precision (float16, int8, float32) |

**Files**:
- `server.py` - FastAPI HTTP/WebSocket server
- `test_streaming.py` - Test harness with VAD integration
- `vad.py` - Voice Activity Detection module
- `start.sh` - Convenience startup script
- `.env` - Configuration
- `requirements.txt` - Dependencies

---

### 3. Voice Activity Detection (VAD) - silero-vad

**Location**: `services/stt/vad.py`

**Technology**: Silero VAD (PyTorch)

**Purpose**: Automatically detect speech boundaries for natural turn-taking.

**Features**:
- Speech start detection (voice activity begins)
- Speech end detection (silence after speaking)
- Pre-speech buffering (captures word onsets)
- Configurable thresholds

**Parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `threshold` | 0.5 | Speech probability threshold (0.0-1.0) |
| `min_speech_ms` | 250 | Minimum speech duration to trigger |
| `min_silence_ms` | 500 | Silence duration to mark endpoint |
| `speech_pad_ms` | 500 | Pre-speech buffer for word onsets |

**Test Harness**: `services/stt/test_streaming.py --continuous`

```bash
cd services/stt
source .venv/bin/activate

# Fixed duration recording
python test_streaming.py --duration 5

# Continuous VAD-based listening
python test_streaming.py --continuous

# With tuning
python test_streaming.py --continuous --threshold 0.3 --min-silence 300 --language en
```

**CLI Options**:
| Flag | Default | Description |
|------|---------|-------------|
| `--continuous` | false | Enable VAD-based continuous listening |
| `--duration` | 5.0 | Recording duration (non-continuous mode) |
| `--threshold` | 0.5 | VAD speech probability threshold |
| `--min-speech` | 250 | Min speech duration (ms) |
| `--min-silence` | 500 | Silence for endpoint detection (ms) |
| `--speech-pad` | 500 | Pre-speech buffer (ms) |
| `--language` | auto | Force language (en, es, de, etc.) |
| `--url` | localhost:8001 | STT server URL |
| `--list-devices` | - | List audio input devices |

---

## Infrastructure

### Docker Services (`docker-compose.yml`)

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache / Task queue |

### Local Services (via `start.sh`)

| Service | Port | Description |
|---------|------|-------------|
| Backend API | 8000 | FastAPI main application |
| STT Service | 8001 | Speech-to-text (GPU) |
| Content MCP | - | Lesson content (MCP, no HTTP) |
| TTS MCP | - | Text-to-speech (MCP, no HTTP, GPU) |

### Startup Commands

```bash
# Start everything
./start.sh

# Start only infrastructure (postgres, redis)
./start.sh infra

# Start only services (assumes infra running)
./start.sh services

# Stop everything
./stop.sh
```

---

## Language Support

**STT (Whisper)**: Auto-detects language or can be forced via `--language` flag.

**Confidence Handling**:
- High confidence (>80%): Process normally
- Low confidence (<50%): Re-prompt user for clarification

**Supported Languages**: en, es, de, fr, it, pt, nl, pl, ja, ko, zh, and 90+ more

---

## File Structure

```
services/
├── stt/                          # Speech-to-Text
│   ├── server.py                 # FastAPI server
│   ├── vad.py                    # Voice Activity Detection
│   ├── test_streaming.py         # Test harness
│   ├── start.sh                  # Startup script
│   ├── .env                      # Configuration
│   ├── requirements.txt
│   └── Dockerfile
│
├── tts-mcp/                      # Text-to-Speech
│   ├── server.py                 # MCP server
│   ├── test_streaming_playback.py
│   ├── VibeVoice/                # Model files
│   ├── requirements.txt
│   └── Dockerfile
│
├── content-mcp/                  # Lesson Content
│   ├── server.py
│   └── requirements.txt
│
└── conversation/                 # (Phase 3 - Planned)
    ├── test_conversation.py
    └── requirements.txt
```

---

## Performance Summary

| Component | Latency | RTF | Notes |
|-----------|---------|-----|-------|
| VAD | ~0ms | - | Real-time detection |
| STT | ~800ms | 0.32x | For 5s audio |
| TTS | ~300ms TTFA | 0.51x | Streaming output |
| LLM (GPT-4o-mini) | Variable | - | Depends on response length |

**Estimated End-to-End**: ~1.5-2s from speech end to TTS start (excluding LLM response time)

---

## Next Steps (Phase 3)

Wire up the full conversation loop:
1. VAD detects speech end
2. STT transcribes utterance
3. LLM generates streaming response
4. TTS speaks response (streaming)
5. Loop continues

See: `planning/in_progress/phase-03-conversation-partner.md`
