# Agent Architecture

The EnglishConnect teaching agent - a unified agent with mode-based behavior for vocabulary help and conversation practice.

## Design Philosophy

The agent is an **intelligent conversation partner**, not a pipeline. It controls TTS/STT as tools, deciding when to speak, what language to use, and how to pace responses. This enables language flipping, vocabulary-aware responses, and natural conversation flow.

**Key principle**: The agent makes decisions. It's not a text-in/audio-out pipeline.

## Unified Teaching Agent

A single `UnifiedTeachingAgent` with two behavioral modes:

| Mode | Page | Behavior |
|------|------|----------|
| `help` | Vocabulary | Answer questions only, use RAG for context |
| `practice` | Practice | Lead conversation, flip roles, track errors silently |

Both modes share the same tools and underlying capabilities. Mode determines behavioral instructions via prompt configuration.

### Why One Agent, Not Multiple

We evaluated multi-agent architectures (Orchestrator + Teacher + Partner) but chose unified because:

- **Context is small** (~2K tokens) - no isolation benefit from separate agents
- **No coordination overhead** - multi-agent adds ~15× token cost
- **All tools everywhere** - no "trapped functionality"
- **Simpler failure modes** - no supervisor bottleneck or "telephone game"

See ADR-005 for the full decision rationale.

## API

**Endpoint**: `POST /api/practice/conversation`

**Request**:
```json
{
  "message": "Hello, I want to practice",
  "lesson_id": 5,
  "mode": "practice",
  "exchange_count": 3
}
```

**Mode Selection**:
- Vocabulary page → `mode: "help"`
- Practice page → `mode: "practice"`

## Tools

The agent has access to these tools:

### speak

Output audio to the student via TTS.

```python
speak(text: str, language: str = "en", voice: str = "default")
```

- `language`: "en" for English, "es" for Spanish
- Agent decides when to speak - it's not automatic

### get_teaching_help

Agentic RAG for vocabulary, patterns, and examples.

```python
get_teaching_help(query: str) -> TeachingContext
```

Returns relevant vocabulary, example sentences, and explanations from the lesson content.

### record_attempt

Track student performance for progress analysis.

```python
record_attempt(item_type: str, correct: bool)
```

### render_vocabulary / render_pattern

Display interactive cards with audio in the UI.

```python
render_vocabulary(word: str)
render_pattern(pattern_number: int, lesson_number: int = None)
```

## Mode Behaviors

### Help Mode (Vocabulary Page)

The student studies vocabulary independently. Agent responds only when asked.

**Core behaviors**:
- Wait for questions - don't initiate
- Use `get_teaching_help` for explanations
- Render vocabulary cards with bilingual audio
- Keep answers concise
- Explain in student's preferred language

**Explicit correction**: Yes - this is teaching mode

### Practice Mode (Practice Page)

The student practices conversation patterns with the agent as partner.

**Conversation flow**:
1. **Exchanges 0-2**: Agent leads, asks questions using patterns
2. **Exchanges 3-5**: Prompt the flip - "Now you ask me!"
3. **Exchanges 5+**: Natural back-and-forth

**Core behaviors**:
- Lead first, then flip roles
- Stay within lesson vocabulary
- Use `get_teaching_help` when student struggles
- Redirect personal questions (agent is AI, not a person)

**Error handling**: Silent tracking with implicit correction (see below)

## Pedagogical Patterns

### Silent Error Tracking (Practice Mode)

During practice, the agent observes errors but doesn't explicitly correct. This preserves conversational fluency.

**Pattern**:
1. Student makes error
2. Agent does NOT say "Actually, you should say..."
3. Agent naturally models correct form in response
4. Error logged for later review

**Example**:
```
Student: "I go to church with family"
Agent: "That's great that you go to church with your family! Do you go every Sunday?"
        ↑ Models "your family" without explicit correction
```

**When to break the rule**:
- Same error type occurs 3+ times
- Student explicitly asks "Was that correct?"
- Error causes communication breakdown

### Native Language Awareness

The agent understands common interference patterns for Spanish speakers:

| Pattern | Example Error | Correct Form |
|---------|---------------|--------------|
| Article omission | "I go with family" | "I go with my family" |
| Adjective placement | "house big" | "big house" |
| Subject pronoun drop | "Is tall" | "He is tall" |
| False cognates | "actually" ≠ "actualmente" | Context-dependent |

This awareness enables:
- Anticipating likely errors
- Proactively modeling correct forms
- Understanding why errors occur

### Implicit Modeling

Rather than correcting, the agent demonstrates correct usage:

```
Student: "Yesterday I go to store"
Agent: "Oh nice! I went to the store yesterday too. What did you buy?"
        ↑ Models "went" and proper word order
```

## Prompt Structure

The agent prompt is assembled from modular components:

```
src/backend/app/prompts/agent/
├── base.md           # Core persona, lesson context
├── mode_help.md      # Help mode behaviors
├── mode_practice.md  # Practice mode behaviors
└── tools.md          # Tool usage instructions
```

**Assembly**:
```python
prompt = base_prompt + mode_prompt + tools_prompt
```

### Template Variables

| Variable | Source | Example |
|----------|--------|---------|
| `{lesson_number}` | Lesson | 5 |
| `{vocab_list}` | Lesson vocabulary | "family = familia\nchurch = iglesia" |
| `{patterns_list}` | Q&A patterns | "Q: What is your name?\nA: My name is ___." |
| `{exchange_count}` | Session state | 3 |
| `{instruction_language}` | User preference | "Spanish" |
| `{native_language_patterns}` | Default Spanish | "Omit articles..." |

## Session State

Tracked per conversation session:

| Field | Type | Purpose |
|-------|------|---------|
| `exchange_count` | int | Determines flip timing |
| `mode` | "help" \| "practice" | Behavioral mode |
| `lesson_id` | int | Current lesson |
| `performance_context` | object | Struggle signals |

**Performance context** tracks:
- `struggle_level`: 0-3 scale
- `consecutive_errors`: Count
- `needs_help`: Boolean flag

## Files

```
src/backend/app/
├── agents/
│   └── unified_teaching_agent.py   # Agent class
├── prompts/agent/
│   ├── base.md                     # Core persona
│   ├── mode_help.md                # Help behaviors
│   ├── mode_practice.md            # Practice behaviors
│   └── tools.md                    # Tool instructions
├── routers/
│   └── conversation.py             # API endpoint
├── services/
│   ├── azure_openai.py             # LLM with tool calling
│   └── tool_handlers.py            # Tool implementations
└── models/
    └── performance.py              # Performance tracking
```

## Related Documentation

- [Architecture](../ARCHITECTURE.md) - System overview, voice pipeline, services, infrastructure
- [ADR-005](ADR/ADR-005-UNIFIED-TEACHING-AGENT.md) - Architecture decision record
