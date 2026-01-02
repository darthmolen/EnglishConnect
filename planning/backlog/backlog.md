# Phases 4-13: Future Work

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

**Implementation:**
- New `LessonBasedTeacherAgent` class with phase tracking
- Session state stores current phase and progress
- Phase-specific system prompts guide behavior
- Frontend displays phase progress

### Phase 5B: Agent Test Harness ✅ Complete

Built comprehensive test infrastructure for agents without voice layer:

**Test Harness Features:**
- `AgentTestHarness` class in `tests/integration/agents/teacher/harness.py`
- Mock TTS service for testing without voice layer
- Tool call tracking and verification
- External prompt file loading with placeholder substitution

**Test Coverage (20 integration tests):**
- Green path scenarios (intro, vocabulary, patterns, practice, wrap-up)
- Skip-ahead detection when student demonstrates mastery
- Bilingual support (Spanish explanations when requested)
- Semantic behavior validation

**Deferred (original 5B concept):**
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

## Phase 6: UI Content Reorganization ✅ Complete

See `planning/completed/phase-06*.md` for details.

## Phase 7: Demo Agent ✅ Complete

Demo dialogue generator implemented with TTS audio generation.

**Implemented:**

- `src/tools/demo-generator/generate_demos.py` - CLI tool for generating demo audio
- Content MCP tools: `list_demo_audio()`, `get_demo_audio()`
- Backend audio streaming: `GET /api/audio/demos/{course_id}`, `GET /api/audio/stream/{path}`
- 19 demo audio files generated (5.3MB) with Grace (teacher) + Davis (student) voices

**Usage:**

```bash
python src/tools/demo-generator/generate_demos.py --lesson 5 --single
python src/tools/demo-generator/generate_demos.py --all
```

**Known Issue - Missing Example Sentences:**
Lessons 1-4, 6-7, 10-13, 15, 18-21, 24-25 have no example sentences in the database. Their Q&A patterns were not extracted with concrete examples during content ingestion. This should be addressed by improving the content ingestion regex patterns or manually adding examples.

### Phase 7D: Vocabulary Audio ✅ Complete

Vocabulary audio generation with play buttons in UI.

**Implemented:**

- `src/tools/vocab-generator/generate_vocab.py` - CLI tool for generating vocab audio
- Backend audio endpoint: `GET /api/audio/vocab/{course_id}?lesson_number=N`
- Frontend play buttons in VocabularyView component
- 487 vocab audio files generated (60MB) with Emma (speaker_b) voice

**Usage:**

```bash
python src/tools/vocab-generator/generate_vocab.py --lesson 5
python src/tools/vocab-generator/generate_vocab.py --all
```

### Phase 7E: Vocabulary Audio Quality (Backlog)

**Problem:** VibeVoice is optimized for sentences, not single-word pronunciations. Issues observed:

- Variable voice frequency as TTS tries to sound "organic"
- Some files have unexpected background music
- Some pronunciations are garbled or unclear
- Inconsistent quality across different words

**Potential Solutions:**

1. **Settings fix** - Find VibeVoice configuration to disable prosody variation
2. **Prompt workaround** - Add punctuation (e.g., "book." instead of "book") to signal complete utterance
3. **Alternative TTS** - Evaluate other TTS options for single-word pronunciation:
   - Azure Neural TTS (cloud)
   - Bark (local)
   - Piper (local, lightweight)
   - gpt-4o-mini-tts (cloud)

**Verification Pipeline (Future):**

- Create STT script to transcribe generated vocab audio
- Compare transcription to expected pronunciation text
- Build agent to review mismatches and suggest regeneration
- Automated loop: generate → verify → flag issues → regenerate

**Example problematic file:**

- `content/samples/vocab/noun-06-b37c25c1.wav`
- Input: "brother... brothers"
- Voice: speaker_b (Emma)

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

1. **TTS Consistency** - Agent calls speak() tool every time in a 3-turn conversation
2. **Spanish Explanation** - Agent explains in Spanish when student asks for clarification
3. **Grammar Quality** - Agent responses are grammatically correct
4. **Vocabulary Adherence** - Agent stays within lesson vocabulary and patterns

**Implementation:**

- Create test harness for automated agent behavior testing
- Define evaluation criteria for each test case
- Build prompt iteration workflow
- Track prompt versions and their test results

## Phase 12: Azure Cloud Deployment

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

## Backlog: TTS Streaming Investigation

**Context**: When agent responds in multiple languages (Spanish + English), TTS generates full WAV files sequentially. Current implementation waits for all TTS calls to complete before playing first audio.

**Opportunity**: VibeVoice uses `VibeVoiceStreamingForConditionalGenerationInference` which supports streaming inference. Streaming would:
- Reduce time to first audio (user hears first words while rest generates)
- More natural conversation pacing
- Lower perceived latency

**Investigation Needed**:
1. Can VibeVoice streaming be exposed via WebSocket or SSE?
2. How to stream audio chunks to frontend incrementally?
3. Frontend changes to play audio as chunks arrive
4. Latency measurements to validate improvement

**Priority**: Low (current queue-based playback works, streaming is optimization)

## Backlog: Spanish Translations for Patterns

**Context**: The EC1 books have all content in Spanish, but pattern Q&A templates and examples are in English only. Adding Spanish translations would help students with exploration and comprehension.

**Problem**: Students can see patterns like:
- Q: What is your name?
- A: My name is _____.

But have no Spanish translation to help them understand what they're practicing.

**Proposed Solution**:

1. Add `question_template_es` and `answer_template_es` fields to the QAPattern model
2. Update content ingestion to extract Spanish translations (if available in source PDFs)
3. Update PatternsView to display Spanish under each Q/A line in parentheses
4. Example display:
   ```
   Q: What is your name?
      (¿Cómo te llamas?)
   A: My name is _____.
      (Mi nombre es _____.)
   ```

**Scope**:
- Database migration to add new columns
- Content ingestion regex updates
- Frontend component updates
- Manual review/entry if translations not in source PDFs

**Priority**: Medium - Enhances comprehension but not blocking core functionality

## Backlog: TTS Abstraction & Cloud Migration

**Context**: Currently using VibeVoice (local GPU) for agent TTS and Piper (local CPU) for static vocabulary audio. Neither is deployable to cloud without significant infrastructure.

**Goal**: Create abstraction layer enabling seamless switch between local and cloud TTS providers.

**Target Provider**: `gpt-4o-mini-tts` (Azure AI Foundry)
- 70% cheaper than gpt-realtime
- 35% fewer word errors in multilingual
- Native Spanish and English support
- HD voice quality with emotion detection

**Implementation Steps**:
1. Create `TTSProvider` interface with `synthesize(text, language, voice_style)`
2. Implement `VibeVoiceTTS` (current local provider)
3. Implement `AzureTTS` using gpt-4o-mini-tts API
4. Add provider selection via environment config (`TTS_PROVIDER=vibevoice|azure`)
5. Test bilingual quality parity with current Piper static audio

**Timing**: After customer cloud provider preferences are known, before Phase 12 cloud deployment.

**Dependencies**: Phase 12 infrastructure decisions

**Priority**: Medium - Required for cloud deployment but not blocking local development

## Phase 13: Notifications (Stretch)

- Celery + Redis for task scheduling
- Reminder scheduling with timezone support
- Practice streak tracking
