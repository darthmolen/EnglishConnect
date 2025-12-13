# EnglishConnect

**A billion people learning, not a billion dollars earned.**

Open source, non-profit agentic system to help Spanish-speaking learners practice English through voice interaction.

## Architecture

```
┌──────────┐     ┌───────────────┐     ┌─────────────┐     ┌──────────────────┐
│  User    │────▶│ faster-whisper│────▶│   Claude    │────▶│ VibeVoice-       │
│  (Mic)   │     │ (local GPU)   │     │   API       │     │ Realtime (GPU)   │
│          │◀────│  STT ~300ms   │◀────│             │◀────│ TTS ~300ms       │
└──────────┘     └───────────────┘     └─────────────┘     └──────────────────┘
```

## Tech Stack

| Component | Choice | Notes |
|-----------|--------|-------|
| **STT** | faster-whisper | Local GPU, `large-v3` model |
| **TTS** | VibeVoice-Realtime-0.5B | Open-source, 6 voices, RTF 0.51x |
| **LLM** | Claude API | Conversation partner |
| **Backend** | FastAPI | Async/WebSocket support |
| **Database** | PostgreSQL | Progress tracking |
| **Frontend** | HTMX + Alpine.js | Server-rendered |

## Project Structure

```
services/
├── stt/                    # Speech-to-Text service
│   ├── server.py           # faster-whisper HTTP/WebSocket API
│   └── Dockerfile          # CUDA container
├── tts-mcp/                # Text-to-Speech MCP server
│   ├── server.py           # VibeVoice with speak() tool
│   └── VibeVoice/          # Microsoft VibeVoice repo
└── conversation/           # Full voice pipeline (WIP)

planning/
├── overview.md             # Phase summary
├── in_progress/            # Current work
├── completed/              # Done phases
└── backlog/                # Future work

content/                    # Lesson markdown files
tools/                      # PDF conversion, ingestion
```

## Quick Start

### TTS (Text-to-Speech)

```bash
cd services/tts-mcp
source .venv/bin/activate
python test_streaming_playback.py --text "Hello, how are you?"
python test_streaming_playback.py --voice speaker_b  # Emma
```

### STT (Speech-to-Text)

```bash
cd services/stt
source .venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001
# POST /transcribe with audio file
```

## Development Status

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ | Foundation + Voice Stack |
| 2 | 🔄 | STT Streaming Harness |
| 3 | ⏳ | Conversation Partner |
| 4+ | ⏳ | Auth, UI, Production |

See [planning/](planning/) for detailed phase documentation.

## Voice Performance

**TTS (VibeVoice)**:
- RTF: 0.51x (real-time capable)
- First chunk: ~300ms
- Sample rate: 24kHz

**STT (faster-whisper)**:
- Model: `large-v3`
- Latency: ~200-400ms

## License

Open source for educational use.
