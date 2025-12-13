# Phases 4-10: Future Work

## Phase 4: Auth + Progress Tracking

- Implement OAuth (Google) with authlib
- Build progress tracking API endpoints
- Store conversation history per user
- Track lesson completion status

## Phase 5: Teacher Agent + Polish

- Implement Teacher Agent with Azure AI Foundry (GPT-4o-mini)
- Build chat-based lesson guidance
- Add pronunciation/grammar feedback storage
- Conversation quality scoring

## Phase 6: Demo Agent (Optional)

*Can be done with static files, not as impressive as live conversation.*

- Build demo dialogue generator from lesson Q&A patterns
- Use TTS MCP to generate 2-voice audio files
- Pre-rendered examples for marketing/docs

## Phase 7: Notifications (Stretch)

- Celery + Redis for task scheduling
- Reminder scheduling with timezone support
- Practice streak tracking

## Phase 8: Azure Cloud Deployment

**Goal**: Move from local GPU to cloud-hosted voice pipeline.

### Current Local Stack (Phase 3)

| Component | Technology | Runs On |
|-----------|------------|---------|
| STT | faster-whisper (medium) | Local GPU |
| TTS | VibeVoice-Realtime-0.5B | Local GPU |
| VAD | Silero VAD | Local GPU |
| LLM | Azure AI Foundry | Cloud |

### Cloud Migration Options

#### Option A: Component-by-Component Migration

Replace each local service with cloud equivalent:

| Component | Cloud Alternative | Notes |
|-----------|-------------------|-------|
| STT | `gpt-4o-mini-transcribe` | Azure AI Foundry |
| TTS | `gpt-4o-mini-tts` | Azure AI Foundry |
| LLM | `gpt-4o-mini` | Already using |

**Pros**: Minimal architecture change, same data flow
**Cons**: Multiple API calls, higher latency

#### Option B: Azure Realtime API (Recommended for Cloud)

Replace entire voice pipeline with single WebSocket:

| Model | Capability |
|-------|------------|
| `gpt-4o-mini-realtime-preview` | STT + LLM + TTS in one connection |

**Features**:

- Single WebSocket handles entire conversation
- Built-in VAD (no separate service needed)
- Sub-second latency (~500ms)
- Natural interruption handling
- Streaming audio input/output

**Architecture Change**:

```text
Local:  Mic → VAD → STT → LLM → TTS → Speaker (4 services)
Cloud:  Mic → Realtime API → Speaker (1 service)
```

**Pros**: Simpler architecture, lower latency, less infrastructure
**Cons**: Per-minute billing, less voice customization, audio leaves device

#### Option C: Hybrid

- Keep local STT/TTS for development and low-cost testing
- Use Realtime API for production
- Feature flag to switch between modes

### Infrastructure

- Azure Container Apps for backend
- Azure Blob Storage for audio files
- Azure Database for PostgreSQL
- CI/CD via GitHub Actions

### Cost Considerations

| Service | Estimated Cost |
|---------|----------------|
| gpt-4o-mini (LLM) | ~$0.15/1M input tokens |
| gpt-4o-mini-realtime | ~$0.06/min audio |
| Container Apps | ~$50-100/month |
| PostgreSQL | ~$25/month |

For a non-profit learner app, budget ~$100-200/month at moderate usage.

## Phase 9: Full Agentic with A2A Support

- Agent-to-Agent protocol evaluation
- STT as MCP tool (if not using Realtime API)
- Multi-agent orchestration
- Teacher + Evaluator + Conversation agents

## Phase 10: Token/Compute Optimization

- Vector embeddings for patterns (pgvector)
- RAG pipeline for lesson context
- Tiered LLM strategy (local → GPT-4o-mini → GPT-4o)
- Conversation summarization for long sessions
- Caching frequent responses
