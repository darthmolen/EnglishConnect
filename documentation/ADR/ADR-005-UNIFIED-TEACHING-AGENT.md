# ADR-005: Unified Teaching Agent Architecture

**Status**: Accepted
**Date**: 2025-12-31
**Supersedes**: ADR-001-AI-AGENT-ARCHITECTURE, ADR-002-CONVERSATION-PARTNER-AGENT
**Decision Makers**: Project Team

## Context

EnglishConnect evolved through several agent architectures:

1. **Original design** (ADR-001): Dual architecture with local agents for real-time voice and Azure AI Agent Service for non-realtime tasks
2. **Agent vs pipeline** (ADR-002): Chose agent architecture where LLM controls TTS/STT as tools
3. **Multi-agent attempt**: Three separate agents (ConversationAgent, LessonBasedTeacherAgent, DemoAgent)

The multi-agent implementation revealed problems:

- **Trapped functionality**: TeachingHelpService (agentic RAG) was only available on the Vocabulary page via LessonBasedTeacherAgent
- **ConversationAgent lacked teaching tools**: Students on Practice page couldn't get help
- **DemoAgent redundancy**: Demo functionality not needed as a separate agent
- **Context overhead without benefit**: Three agents, but none approaching context limits

After reviewing multi-agent architecture patterns from context engineering research, we found: "Sub-agents exist primarily to isolate context, not to anthropomorphize role division."

Our lesson context is small (~20 vocabulary items + 5 patterns + 20 conversation exchanges), nowhere near context limits. The multi-agent split provided no context isolation benefit while introducing tool fragmentation.

## Decision

**Consolidate to a single UnifiedTeachingAgent with two modes: "help" and "practice".**

### Architecture

```text
UnifiedTeachingAgent
├── Mode: "help" (Vocabulary page)
│   └── Behavior: Answer questions only, use get_teaching_help
├── Mode: "practice" (Practice page)
│   └── Behavior: Lead conversation, flip roles, use get_teaching_help
├── Tools: speak, get_teaching_help, record_attempt
└── Endpoint: POST /api/conversation (mode parameter)
```

### Mode Behaviors

**Help Mode** (Vocabulary page)

- Student self-studies vocabulary with play buttons
- Agent waits for student questions
- Uses agentic RAG (get_teaching_help) to retrieve vocabulary, examples, explanations
- Does NOT initiate conversation
- Responds in student's preferred language

**Practice Mode** (Practice page)

- Student watches pre-recorded pattern demos for self-study
- When conversation starts, agent leads first 3-5 exchanges using patterns
- After 3-5 exchanges, prompts flip: "Now you ask me a question!"
- Natural conversation continues with role switching
- Uses get_teaching_help when student struggles

### Progress Tracking

Progress tracking is handled by a **background service**, not an agent:

```python
class ProgressService:
    async def record_page_visit(user_id, lesson_id, page)
    async def mark_practice_complete(user_id, lesson_id)
    async def get_lesson_progress(user_id, lesson_id) -> dict
```

This is deterministic bookkeeping, not requiring LLM reasoning.

## Rationale

### Why Single Agent Over Multi-Agent

From multi-agent architecture patterns research:

| Consideration | Multi-Agent | Single Agent (Chosen) |
|---------------|-------------|----------------------|
| Context isolation | Not needed (~2K tokens max) | Simpler, no coordination |
| Token overhead | ~15x baseline for coordination | ~4x baseline |
| Tool fragmentation | Teaching tools split across agents | All tools available everywhere |
| Failure modes | Supervisor bottleneck, coordination overhead | None of these |

### Why Modes Over Separate Agents

- Same underlying capabilities, different behavioral instructions
- Mode is a prompt configuration, not an architectural boundary
- Single endpoint simplifies frontend integration
- Agentic RAG available on ALL pages

### Why Background Service Over Supervisor Agent

Progress tracking requirements:

- Record page visits (timestamp)
- Mark practice completed (timestamp)
- Query completion status (boolean)

These are deterministic CRUD operations. An LLM agent would add:

- Latency (~200-500ms reasoning)
- Cost (tokens for simple decisions)
- Failure modes (hallucination, wrong tool calls)

A simple async service with database writes is faster, cheaper, and more reliable.

## Consequences

### Positive

- **All pages get teaching help**: Agentic RAG no longer "trapped"
- **Simpler architecture**: One agent, one endpoint, two modes
- **No coordination overhead**: No supervisor/worker communication
- **Cheaper**: Single agent invocation per conversation turn
- **Agent vs pipeline decision preserved**: Agent still controls TTS as tool (ADR-002 core insight)

### Negative

- **Mode parameter required**: Frontend must specify "help" or "practice"
- **Exchange counting**: Practice mode needs exchange_count for flip detection

### Mitigations

- Mode derived from page context (vocabulary page → help, practice page → practice)
- Exchange count tracked in frontend conversation state

## Files Changed

### Delete (Old Agents)

- `src/backend/app/agents/conversation_agent.py`
- `src/backend/app/agents/demo_agent.py`
- `src/backend/app/agents/lesson_teacher_agent.py`
- `src/backend/app/routers/demo.py`
- `src/backend/app/prompts/demo/`
- `src/backend/app/prompts/conversation_partner/`

### Create (New Agent)

- `src/backend/app/agents/unified_teaching_agent.py`
- `src/backend/app/prompts/agent/mode_help.md`
- `src/backend/app/prompts/agent/mode_practice.md`

### Keep (Agentic RAG)

- `src/backend/app/services/teaching_help_service.py`
- `src/backend/app/models/performance.py`
- `src/backend/app/tools/teaching_help.py`

## References

- Multi-agent patterns skill from context engineering research
- [ADR-001](ADR-001-AI-AGENT-ARCHITECTURE.md) - Original architecture (superseded)
- [ADR-002](ADR-002-CONVERSATION-PARTNER-AGENT.md) - Agent vs pipeline (superseded, core insight preserved)
