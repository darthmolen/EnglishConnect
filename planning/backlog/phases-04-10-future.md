# Phases 4-10: Future Work

## Phase 4: Auth + Memory + Progress Tracking

**Authentication:**
- Microsoft Identity Platform (Microsoft Entra ID) with MSAL
- OAuth 2.0 with authorization code flow + PKCE
- Support both Microsoft AND Google identity providers
- FastAPI integration with python-jose for JWT validation

**Conversation Memory (Memori):**
- Open-source Memori library (uses existing PostgreSQL)
- Store user-specific conversation histories
- Enable context recall across sessions
- Fact/preference extraction from conversations

**Progress Tracking:**
- Lesson completion status per user
- Track conversation quality metrics
- Store pronunciation/grammar feedback history

## Phase 5: Teacher Agent (Multi-Part)

### Phase 5A: LessonBasedTeacherAgent (In Progress)

Structured lesson flow with linear phases:

| Phase | Agent Behavior |
|-------|---------------|
| **1. Intro** | Greet, state lesson topic and objective |
| **2. Vocabulary** | Present each word, have student repeat, confirm |
| **3. Patterns** | Explain each Q&A pattern with examples |
| **4. Practice** | Ask pattern questions, student answers using vocabulary |
| **5. Wrap-up** | Summary, encouragement, offer to continue or end |

**Implementation:**
- New `LessonBasedTeacherAgent` class with phase tracking
- Session state stores current phase and progress
- Phase-specific system prompts guide behavior
- Frontend displays phase progress

### Phase 5B: Agentic Tutor (Future)

Monitoring agent that interjects with help when student struggles:
- Detects confusion, hesitation, errors
- Offers hints, Spanish explanations, encouragement
- Can pause lesson flow to provide support
- Evaluates when to move forward vs. review

### Phase 5C: Conversational Weaving (Future)

More organic introduction of vocabulary during practice:
- Vocabulary woven into natural conversation
- Less rigid phase separation
- Context-appropriate word introduction
- Student-led topic exploration within lesson bounds

### Phase 5D: Student-Driven with Checkpoints (Future)

Free practice with prompts for uncovered content:
- Student leads the conversation
- Agent tracks which vocabulary/patterns practiced
- Gentle prompts for uncovered material
- End-of-session coverage report

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

## Phase 11: Prompt Engineering & Agent Testing

**Goal**: Systematic testing and refinement of agent behavior through prompt engineering.

**Test Cases:**

1. **TTS Consistency** - Agent calls speak() tool every time in a 3-turn conversation
2. **Spanish Explanation** - Agent explains in Spanish when student asks for clarification
3. **Grammar Quality** - Agent responses are grammatically correct
4. **Vocabulary Adherence** - Agent stays within lesson vocabulary and patterns

**Implementation:**

- Create test harness for automated agent behavior testing
- Define evaluation criteria for each test case
- Build prompt iteration workflow
- Track prompt versions and their test results
