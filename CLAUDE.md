# EnglishConnect

Open source, non-profit agentic system to help Spanish-speaking learners practice English through voice interaction.

## Required Skills

These skills MUST be invoked before writing any code. No exceptions.

- **`using-superpowers`** — Invoke at the start of every task to discover applicable skills
- **`test-driven-development`** — Invoke before implementing any feature or bugfix

## Guiding Principles

**Never implement anything that doesn't get us nearer to solving our problem.**

**Always use skills and test first.** Before implementing new features:

1. **Invoke `/using-superpowers`** - Check for applicable skills before writing code
2. **Write tests first** - Follow RED-GREEN-REFACTOR (see TDD section below)
3. **Verify before claiming done** - Run tests, check logs, confirm behavior

This prevents the "6 manual iterations" problem where bugs slip through because:

- Tool handler parameters don't match tool definitions
- Frontend components have wrong behavior
- Prompts don't guide the agent correctly

See `.claude/skills/` for available methodologies.

## TDD: RED-GREEN-REFACTOR

All code changes MUST follow the RED-GREEN-REFACTOR cycle:

1. **RED** — Write a failing test that describes the desired behavior. Run it. Confirm it fails.
2. **GREEN** — Write the minimum code to make the test pass. Nothing more.
3. **REFACTOR** — Clean up the implementation while keeping tests green.

This is not optional. Do not write implementation code without a failing test first.

- **Backend**: `python -m pytest tests/unit/ -v` (unit), `python -m pytest tests/integration/ -v` (integration)
- **Frontend**: `cd src/frontend && npm run test:run`
- **Single test**: `python -m pytest tests/unit/test_foo.py::test_bar -v`

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
│   └── app/
│       ├── agents/       # UnifiedTeachingAgent (single agent, two modes)
│       ├── prompts/agent/  # Agent prompts (base, mode_help, mode_practice, tools)
│       ├── routers/      # API endpoints (/api/practice/conversation)
│       └── services/     # Business logic, tool handlers
├── services/
│   ├── stt/              # Speech-to-Text (faster-whisper, port 8001)
│   ├── tts-mcp/          # Text-to-Speech MCP server (VibeVoice)
│   └── content-mcp/      # Lesson content MCP server
├── tools/                # PDF conversion, content ingestion
└── frontend/             # React SPA (Vite + shadcn/ui)

tests/                    # All tests
├── unit/                 # Unit tests
├── integration/          # Integration tests
└── e2e/                  # Playwright E2E tests

content/                  # Lesson content
├── refined/              # Processed markdown lessons
│   ├── ec1/              # EnglishConnect 1
│   └── ec2/              # EnglishConnect 2
├── audio/                # Generated audio (vocab, demos, intros)
│   ├── ec1/
│   └── ec2/
└── raw/                  # Source PDFs
    ├── ec1/
    └── ec2/

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
- Phase 2B: Test Infrastructure + TDD (complete)
- Phase 3: React SPA + Unified Teaching Agent (complete)
- Phase 4+: Auth, Progress Tracking, Production (backlog)

## Agent Architecture

Single `UnifiedTeachingAgent` with two modes (see ADR-005):

| Mode       | Page       | Behavior                                             |
|------------|------------|------------------------------------------------------|
| `help`     | Vocabulary | Answer questions only, use `get_teaching_help`       |
| `practice` | Practice   | Lead conversation, flip roles after 3-5 exchanges    |

**API Endpoint**: `POST /api/practice/conversation`

**Tools**: `speak`, `get_teaching_help`, `record_attempt`, `render_vocabulary`, `render_pattern`

## Key Files

- `src/backend/app/agents/unified_teaching_agent.py` - Single teaching agent
- `src/backend/app/routers/conversation.py` - Unified conversation endpoint
- `src/backend/app/prompts/agent/` - Agent prompts (base, modes, tools)
- `src/services/stt/server.py` - STT FastAPI server
- `src/services/tts-mcp/server.py` - TTS MCP server
- `documentation/ADR/ADR-005-unified-teaching-agent.md` - Architecture decision

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

## Deployed Environment

- **ACA URL**: <https://ca-ec-4fz3j4ag5rqtu.bluedesert-074435b9.southcentralus.azurecontainerapps.io>

## Content Pipeline

For ingesting new course content (PDF → database → audio), see:

- `documentation/CONTENT-INGESTION-PIPELINE.md` - Full pipeline runbook
- `documentation/HOW-TO-GENERATE-DEMO-SAMPLES.md` - Demo audio generation details
- `documentation/LOCAL-TTS-VOICES.md` - TTS voice configuration

## Architecture Decision Records

When making decisions that affect the architecture, consult and update:

- `documentation/ADR/` - Architecture Decision Records
- Create new ADR documents for significant architectural changes

## Planning Process

Phase-based development workflow:

1. **Start a phase:** Create `planning/in_progress/phase-XX-name.md` with goals and tasks
2. **Complete a phase:** Move file to `planning/completed/` when done
3. **Backlog items:** Add user-requested future work to `planning/backlog/backlog.md`

Current phases are tracked in `planning/backlog/backlog.md` with status indicators (✅ Complete, etc.).
