# Architecture

This document explains how EnglishConnect fits together. For a product overview see [README.md](README.md); for local setup see [HOW-TO-DEV.md](HOW-TO-DEV.md).

## System overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│                          React SPA (Vite)                              │
│   MobileApp  ( < 768px )              DesktopApp  ( ≥ 768px )           │
│   tab bar + action bar + cards        sidebar + content + drawer       │
└───────────────┬────────────────────────────────────────┬──────────────┘
                │  HTTPS / WebSocket  (/api, /ws)          │
                ▼                                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        FastAPI backend (:8000)                         │
│   routers/      UnifiedTeachingAgent      services/ (tool handlers)     │
│   ────────      ───────────────────       ─────────                    │
│   conversation  help | practice modes     speak, get_teaching_help,    │
│   audio, auth   Azure GPT-4o-mini         record_attempt, render_*     │
└───────┬───────────────────┬───────────────────────────┬───────────────┘
        │                   │                           │
        ▼                   ▼                           ▼
 ┌────────────┐     ┌───────────────┐          ┌──────────────────┐
 │ PostgreSQL │     │     Redis     │          │  Voice pipeline  │
 │  lessons,  │     │    cache /    │          │  (see below)     │
 │  progress  │     │   sessions    │          │                  │
 └────────────┘     └───────────────┘          └──────────────────┘
```

## The teaching agent

A single `UnifiedTeachingAgent` runs the conversation, with two modes selected by the page the learner is on (see [ADR-005](documentation/ADR/ADR-005-UNIFIED-TEACHING-AGENT.md)):

| Mode       | Page       | Behavior                                          |
|------------|------------|---------------------------------------------------|
| `help`     | Vocabulary | Answers questions only, via `get_teaching_help`   |
| `practice` | Practice   | Leads the conversation, flips roles after 3–5 exchanges |

The agent is not a pipeline that pushes text through TTS. It **decides** when to speak, which language to use, and how to pace a response, by calling tools — `speak`, `get_teaching_help`, `record_attempt`, `render_vocabulary`, `render_pattern`. The conversation endpoint is `POST /api/practice/conversation`.

For the full picture, see the deep dives: [agent-architecture.md](documentation/agent-architecture.md) (pedagogical patterns, prompt structure, session state), [general-agent-conversation-workflow.md](documentation/general-agent-conversation-workflow.md) (the end-to-end turn), and [agent-context-engineering.md](documentation/agent-context-engineering.md) (how prompts are assembled).

## Voice pipeline

Speech-to-text and text-to-speech run through one of two interchangeable paths.

**Azure Realtime API (default).** Development and production default to Azure's Realtime API (`USE_REALTIME_API=true`), which handles STT and TTS in the cloud. This keeps local setup light and avoids a GPU requirement.

**Local GPU stack (optional).** For fully local, offline voice, the repo also ships a self-hosted stack:

| Stage | Component | Notes |
|-------|-----------|-------|
| VAD | Silero VAD | Speech-endpoint detection (~0ms) |
| STT | faster-whisper (`medium`) | Local GPU, ~800ms for 5s of audio |
| TTS | VibeVoice-Realtime-0.5B | Local GPU, 6 voices, ~300ms to first audio |

These run as separate services (`src/services/stt`, `src/services/tts-mcp`) and are disabled by default in `start.sh`.

Vocabulary and example **demo audio** is pre-generated and served as static WAV files from `/api/audio/...` with a content-hashed filename and `Cache-Control: immutable`, so a clip is downloaded once and replayed from cache — which is what makes hands-free loop playback cheap on mobile data.

## Performance

Figures for the local voice stack:

| Component | Latency | RTF |
|-----------|---------|-----|
| VAD | ~0ms | — |
| STT (faster-whisper) | ~800ms for 5s of audio | 0.32× |
| TTS (VibeVoice) | ~300ms to first audio | 0.51× |
| LLM (GPT-4o-mini) | variable | — |

End to end: **~1.5–2s** from end of speech to first audio out, excluding LLM response time. For a per-stage breakdown and how to read the timing logs, see [frontend-timing-instrumentation.md](documentation/frontend-timing-instrumentation.md) and [latency-analysis-2026-01-03.md](documentation/latency-analysis-2026-01-03.md).

## Frontend

A React 19 single-page app built with Vite and shadcn/ui.

- **Two shells.** `App.tsx` renders `MobileApp` below 768px and `DesktopApp` at or above it, via the `useIsMobile` hook. The two are separate component trees, not one responsive layout (see [ADR-007](documentation/ADR/ADR-007-MOBILE-LAYOUT-V1.md)).
- **State.** Zustand stores (`authStore`, `conversationStore`) hold cross-cutting state; feature hooks (`useConversation`, `useVocabAudio`, `useDemoAudio`, `useSectionLoop`, `useLessons`) own their own slices.
- **Audio.** Each audio source owns its own `<audio>` element, so starting one silences the others. `buildLoopClips` derives loop order from lesson content, guaranteeing playback matches on-screen order.
- **i18n.** `i18next` drives a fully bilingual UI (`locales/en.json`, `locales/es.json`); see [internationalization.md](documentation/internationalization.md) for the language-control model and how to add a language.
- **Auth.** Azure AD via MSAL (`@azure/msal-react`).
- **Dev proxy.** Vite proxies `/api` and `/ws` to the backend on `:8000`.

## Backend

A FastAPI application (`src/backend/app`).

- **`routers/`** — HTTP and WebSocket endpoints (conversation, audio, auth).
- **`agents/`** — the `UnifiedTeachingAgent`.
- **`prompts/agent/`** — the agent's prompts (base, mode_help, mode_practice, tools).
- **`services/`** — business logic and tool handlers.

## Data

- **PostgreSQL** stores lessons, vocabulary, and learner progress. Schema is managed by **Alembic** migrations; in production the app runs migrations on startup and skips `create_all`.
- **Redis** backs caching and session state.

## Deployment

The app runs on **Azure Container Apps**. GitHub Actions ships it:

- `deploy.yml` — on push to `main`: `test → build-and-push → sync-audio → deploy-app`. Opening or updating a PR runs only the `test` job.
- `deploy-infra.yml` — on changes under `azure/**`: provisions infrastructure with Bicep.

Audio files are served from an Azure Files mount and synced by the `sync-audio` job. Database is Azure PostgreSQL Flexible Server.

## Project structure

```text
src/
├── backend/              # FastAPI app (:8000)
│   └── app/
│       ├── agents/       # UnifiedTeachingAgent
│       ├── prompts/agent/# Agent prompts
│       ├── routers/      # API + WebSocket endpoints
│       └── services/     # Tool handlers, business logic
├── services/
│   ├── stt/              # faster-whisper (optional, local GPU)
│   ├── tts-mcp/          # VibeVoice TTS MCP server (optional, local GPU)
│   └── content-mcp/      # Lesson content MCP server
├── tools/                # PDF conversion, content ingestion, QR codes
└── frontend/             # React SPA (Vite + shadcn/ui)

content/                  # Lesson content (refined markdown + generated audio)
documentation/            # Architecture docs and ADRs
planning/                 # Phase documentation
tests/                    # unit / integration / e2e
```

## Deep dives

This document is the map. The detail lives in [documentation/](documentation/):

### Agent & conversation

- [agent-architecture.md](documentation/agent-architecture.md) — pedagogical patterns, prompt structure, session state
- [general-agent-conversation-workflow.md](documentation/general-agent-conversation-workflow.md) — the end-to-end turn
- [agent-context-engineering.md](documentation/agent-context-engineering.md) — how prompts are assembled

### Voice & audio

- [LOCAL-TTS-VOICES.md](documentation/LOCAL-TTS-VOICES.md) — the local TTS service and its voices
- [CONTENT-INGESTION-PIPELINE.md](documentation/CONTENT-INGESTION-PIPELINE.md) — PDF → database → audio
- [HOW-TO-GENERATE-DEMO-SAMPLES.md](documentation/HOW-TO-GENERATE-DEMO-SAMPLES.md) — generating demo audio
- [frontend-timing-instrumentation.md](documentation/frontend-timing-instrumentation.md), [latency-analysis-2026-01-03.md](documentation/latency-analysis-2026-01-03.md) — latency

### Frontend & UX

- [internationalization.md](documentation/internationalization.md) — the bilingual UI

### Operations

- [AI-SAFETY-ADOPTION-AND-COMPLIANCE.md](documentation/AI-SAFETY-ADOPTION-AND-COMPLIANCE.md) — safety controls and compliance
- [ENGLISHCONNECT1-AZURE-COST-ESTIMATES.md](documentation/ENGLISHCONNECT1-AZURE-COST-ESTIMATES.md) — cost model

### Architecture Decision Records

The *why* behind the design lives in [documentation/ADR/](documentation/ADR/). Start with [ADR-005](documentation/ADR/ADR-005-UNIFIED-TEACHING-AGENT.md) (single-agent, two-mode) and [ADR-007](documentation/ADR/ADR-007-MOBILE-LAYOUT-V1.md) (the mobile/desktop split).
