# EnglishConnect

Open source, non-profit agentic system to help Spanish-speaking learners practice English through voice interaction.

## Guiding Principle

**Never implement anything that doesn't get us nearer to solving our problem.**

## Vision: Intelligent Conversation Partner

We are building an intelligent conversation partner agent that can:

- Help students practice conversation in their target language (English)
- Flip between native language (Spanish) and target language (English) to aid understanding
- Practice curriculum patterns with natural ad-lib
- Stay within the student's vocabulary level
- Feel like a helpful conversation partner, not a robotic response system

The agent controls TTS/STT as tools - it decides when to speak, what language to use, and how to pace responses. This is NOT a pipeline where text automatically flows through TTS. The agent makes intelligent decisions about voice interaction.

## REQUIRED READING

Review available skills in `.claude/skills/` and apply relevant methodologies based on the task at hand. When uncertain which approach to take, start with `using-superpowers/SKILL.md`.

## Tech Stack

- **STT**: faster-whisper (local GPU, medium model)
- **TTS**: VibeVoice-Realtime-0.5B (local GPU, 6 voices)
- **VAD**: Silero VAD for speech endpoint detection
- **LLM**: Azure AI Foundry (GPT-4o-mini) via Microsoft Agent Framework
- **Backend**: FastAPI (async/WebSocket)
- **Database**: PostgreSQL
- **Cache**: Redis
- **Frontend**: React SPA (Vite + shadcn/ui)

## Project Structure

```
src/                      # All source code
├── backend/              # FastAPI main application (port 8000)
├── services/
│   ├── stt/              # Speech-to-Text (faster-whisper, port 8001)
│   ├── tts-mcp/          # Text-to-Speech MCP server (VibeVoice)
│   └── content-mcp/      # Lesson content MCP server
├── tools/                # PDF conversion, content ingestion
└── frontend/             # React SPA (planned)

tests/                    # All tests
├── unit/                 # Unit tests
├── integration/          # Integration tests
└── e2e/                  # Playwright E2E tests

content/                  # Lesson content
├── refined/              # Processed markdown lessons
│   └── ec1/              # EnglishConnect 1
└── raw/                  # Source PDFs
    └── ec1/

documentation/            # Architecture docs, ADRs
planning/                 # Phase documentation
```

## Common Commands

```bash
# Start all services
./start.sh

# Start infrastructure only (postgres, redis)
./start.sh infra

# Stop everything
./stop.sh

# TTS test
cd src/services/tts-mcp && source .venv/bin/activate
python test_streaming_playback.py --text "Hello" --voice speaker_b

# STT server
cd src/services/stt && source .venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001

# STT test with VAD
python test_streaming.py --continuous

# Run tests
python -m pytest tests/
```

## Development Status

- Phase 1: Foundation + Voice Stack (complete)
- Phase 2: STT Streaming Harness (complete)
- Phase 2B: Test Infrastructure + TDD (in progress)
- Phase 3: React SPA Conversation Partner (in progress)
- Phase 4+: Auth, Progress Tracking, Production (backlog)

## Key Files

- `src/services/stt/server.py` - STT FastAPI server
- `src/services/stt/vad.py` - Voice Activity Detection
- `src/services/tts-mcp/server.py` - TTS MCP server
- `documentation/architecture.md` - Full architecture details

## Performance Targets

| Component | Latency |
|-----------|---------|
| VAD | ~0ms |
| STT | ~800ms (5s audio) |
| TTS | ~300ms TTFA |
| End-to-end | ~1.5-2s (excluding LLM) |

## Environment

- GPU required for STT and TTS
- Python venvs per service (not shared)
- `.env` for API keys and config

## Architecture Decision Records

When making decisions that affect the architecture, consult and update:
- `documentation/ADR/` - Architecture Decision Records
- Create new ADR documents for significant architectural changes
