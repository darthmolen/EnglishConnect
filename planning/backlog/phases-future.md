# Future Phases Roadmap

Overview of planned development phases beyond current work.

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

### Phase 5A: LessonBasedTeacherAgent ✅ Complete

Structured lesson flow with linear phases:

| Phase | Agent Behavior |
|-------|---------------|
| **1. Intro** | Greet, state lesson topic and objective |
| **2. Vocabulary** | Present each word, have student repeat, confirm |
| **3. Patterns** | Explain each Q&A pattern with examples |
| **4. Practice** | Ask pattern questions, student answers using vocabulary |
| **5. Wrap-up** | Summary, encouragement, offer to continue or end |

### Phase 5B: Agent Test Harness ✅ Complete

Built comprehensive test infrastructure for agents without voice layer.

**Deferred (original 5B concept):**
Monitoring agent that interjects with help when student struggles.

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

## Phase 6: UI Content Reorganization ✅ Complete

See `planning/completed/phase-06*.md` for details.

## Phase 7: Demo Agent ✅ Complete

Demo dialogue generator implemented with TTS audio generation.

### Phase 7D: Vocabulary Audio ✅ Complete

Vocabulary audio generation with play buttons in UI.

## Phase 8: Evaluations

**Goal**: Systematic approach to measuring and improving agent quality over time.

- Define evaluation criteria and metrics
- Build evaluation harness for automated testing
- Track agent performance across versions
- A/B testing framework for prompt variations
- Quality regression detection

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
1. TTS Consistency - Agent calls speak() tool every time
2. Spanish Explanation - Agent explains in Spanish when requested
3. Grammar Quality - Agent responses are grammatically correct
4. Vocabulary Adherence - Agent stays within lesson vocabulary and patterns

## Phase 12: Azure Cloud Deployment

**Goal**: Move from local GPU to cloud-hosted voice pipeline.

See `planning/backlog/tts-abstraction-cloud.md` for TTS migration details.

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

## Phase 13: Notifications (Stretch)

- Celery + Redis for task scheduling
- Reminder scheduling with timezone support
- Practice streak tracking
