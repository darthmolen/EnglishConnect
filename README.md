# EnglishConnect

**A billion people learning, not a billion dollars earned.**

Open source, non-profit agentic system to help Spanish-speaking learners practice English through voice interaction.

## Problem Statement

1. **Most curriculums are written, but students are learning a spoken language.** Reading and writing skills don't transfer directly to conversational fluency.

2. **Traditional audio production is prohibitive and can't adapt as fast as curriculum needs.** Professional voice recording is expensive and slow to update when lessons change.

3. **Even with embedded audio, flipping between languages disrupts learning flow.** Students who need clarification in their native language must break concentration to switch contexts.

4. **Immigrant families share the same challenge but prioritize differently, making practice partners hard to find.** Family members want to learn but at different paces and times, leaving everyone without a consistent conversation partner.

## Vision: Intelligent Conversation Partner

We are building an intelligent conversation partner agent that can:

- Help students practice conversation in their target language (English)
- Flip seamlessly between native language (Spanish) and target language to aid understanding
- Practice curriculum patterns with natural ad-lib that feels like real conversation
- Stay within the student's vocabulary level from their current lesson
- Feel like a helpful conversation partner, not a robotic response system

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        Conversation Partner Agent                             │
│                         (Azure GPT-4o-mini)                                   │
│                                                                               │
│   Capabilities:                    MCP Tools:                                 │
│   - Lesson context awareness       - speak(text, voice) → TTS                │
│   - Language flipping (EN/ES)      - get_lesson() → Content                  │
│   - Vocabulary-appropriate         - (future: show_image, highlight)         │
│     responses                                                                 │
└──────────────────────────────────────────────────────────────────────────────┘
                    ▲                                    │
                    │ transcribed text                   │ speak() tool call
                    │                                    ▼
┌──────────────────────────────────┐     ┌──────────────────────────────────┐
│        STT Service               │     │        TTS MCP Server            │
│        faster-whisper            │     │        VibeVoice-Realtime        │
│        (local GPU, ~300ms)       │     │        (local GPU, ~300ms)       │
└──────────────────────────────────┘     └──────────────────────────────────┘
                    ▲                                    │
                    │ audio                              │ audio
                    │                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              User (Browser)                                   │
│                     Mic input ────────────── Speaker output                  │
└──────────────────────────────────────────────────────────────────────────────┘
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
