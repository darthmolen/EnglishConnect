# ADR-002: Conversation Partner Agent vs Pipeline

**Status**: Accepted
**Date**: 2025-12-13
**Decision Makers**: Project Team

## Context

EnglishConnect needs to integrate voice capabilities (STT and TTS) with the LLM-powered conversation feature. Two architectural approaches were considered:

### Option 1: Pipeline Architecture

```
User speaks → STT → text → LLM → text → TTS → plays
```

A deterministic flow where:
- User speech is always transcribed
- Transcribed text is always sent to LLM
- LLM response is always spoken via TTS
- Backend orchestrates the flow; LLM has no control over voice

### Option 2: Agent Architecture

```
User speaks → STT → text → Agent (with tools) → Agent calls speak() → plays
```

The LLM is an intelligent agent with access to tools:
- `speak(text, voice)` - Speak text aloud to the student
- `get_lesson_context()` - Access current lesson vocabulary and patterns
- Future tools: `show_image()`, `highlight_word()`, etc.

## Decision

**We chose the Agent Architecture (Option 2).**

The conversation partner is an intelligent agent that decides when and how to use voice capabilities.

## Rationale

### Why Pipeline Fails Our Goals

The pipeline approach would:
1. **Always transcribe → always respond → always speak** - No flexibility
2. **No language switching** - Can't flip to Spanish mid-conversation for clarification
3. **No pacing control** - Can't slow down to spell words or emphasize
4. **No vocabulary awareness** - Can't detect when student needs simpler words
5. **Build something we'd tear down** - Technical debt from day one

### Why Agent Serves Our Goals

The agent approach enables:

1. **Language Flipping**: Agent decides when to switch to Spanish
   - "Let me explain that in Spanish: esto significa..."
   - Returns to English when student understands

2. **Pacing for Comprehension**: Agent controls speech
   - "Let me spell that: H-E-L-L-O"
   - Can repeat phrases slower if needed

3. **Vocabulary Awareness**: Agent knows the lesson
   - Accesses current lesson vocabulary via tool
   - Rephrases using words student has learned
   - Avoids vocabulary beyond current level

4. **Natural Conversation**: Agent chooses responses
   - Can ask clarifying questions instead of answering
   - Can pause and wait instead of filling silence
   - Feels like a real conversation partner

5. **Extensibility**: Add tools without architecture changes
   - `show_image()` - Display visual aids
   - `highlight_word()` - Emphasize vocabulary in UI
   - `play_audio_example()` - Native speaker samples

## Consequences

### Positive

- Aligns directly with project vision (intelligent conversation partner)
- More natural, human-like interactions
- Extensible via MCP tools without architectural changes
- Agent can improve with better prompts (no code changes)
- Supports the core problem: providing a practice partner that adapts

### Negative

- Slightly more complex than pipeline
- Agent must be well-prompted to use tools appropriately
- May add latency for tool-use reasoning (~100-200ms)
- Need to handle cases where agent doesn't call speak()

### Mitigations

- Well-designed system prompt with clear tool usage guidance
- Default behavior prompts agent to always speak responses
- Monitoring for cases where voice isn't used when expected

## Alternatives Rejected

1. **Pipeline First, Agent Later**: Would create technical debt. The pipeline code would need to be removed when adding agent capabilities. "Simple is the way of the dark side" - easy to build, but wrong direction.

2. **Hybrid (Pipeline + Optional Agent Override)**: Added complexity without clear benefit. Either the agent controls voice or it doesn't.

3. **No Voice Control by Agent**: Misses the entire value proposition of a conversation partner that can adapt its communication style.

## Implementation Notes

The conversation partner agent will:
1. Receive transcribed user speech as input
2. Have access to TTS via MCP `speak()` tool
3. Have access to lesson context via `get_lesson_context()` tool
4. Be prompted to respond naturally and use voice appropriately
5. Control language choice (EN/ES) based on student needs

## References

- [ADR-001: AI Agent Architecture](ADR-001-AI-AGENT-ARCHITECTURE.md)
- [README: Vision Statement](../../README.md#vision-intelligent-conversation-partner)
- [CLAUDE.md: Guiding Principle](../../CLAUDE.md#guiding-principle)
