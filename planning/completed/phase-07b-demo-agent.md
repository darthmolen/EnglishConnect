# Phase 7B: Demo Agent (Interactive)

## Overview

Create an interactive demo agent that plays pre-generated audio dialogues and helps users understand the conversation patterns.

## Goals

1. Build a helpful demo agent that guides users through audio examples
2. Add a Demo block to the practice view UI
3. Enable audio playback with repeat functionality

## Completed

### DemoPlayer Component

**File:** `src/frontend/src/components/content/DemoPlayer.tsx`

- Play/pause button with bilingual label
- Fetches demo metadata from `/api/audio/demos/{course_id}?lesson_number=N`
- Plays demo audio files sequentially
- Shows progress indicator (e.g., "2/5")
- Shows total duration and example count
- Integrated into PracticeView between vocabulary and patterns

### Demo Agent Backend

**File:** `src/backend/app/agents/demo_agent.py`

DemoAgent class that:
- Takes lesson details and demo metadata
- Builds system prompt with available demos, vocabulary, and patterns context

**File:** `src/backend/app/routers/demo.py`

REST API endpoints:
- `POST /api/demo/conversation` - Interactive demo conversation
- `GET /api/demo/metadata/{course_id}/{lesson_number}` - Demo metadata

Tools available to the agent:
- `play_demo(demo_index)` - Play pre-recorded demo audio
- `speak(text, language)` - TTS for agent responses

**File:** `src/backend/app/prompts/demo/base.md`

System prompt that instructs the agent to:
1. Play demos sequentially
2. Ask "Would you like me to repeat?" (bilingual)
3. At the end, ask "Any questions about the examples?" (bilingual)
4. Answer basic questions about patterns/vocabulary

### Files Modified

- `src/frontend/src/components/content/PracticeView.tsx` - Added DemoPlayer
- `src/frontend/src/components/ContentWindow.tsx` - Passes lessonNumber to PracticeView
- `src/backend/app/main.py` - Added demo router

## Remaining Work: Agent Routing & Multi-Actor Conversation

### Actor Map

| Actor | Endpoint | Tools | UI Status |
|-------|----------|-------|-----------|
| Conversation Partner | `/api/conversation` | `speak()` | Only one wired |
| Teacher Agent | `/api/lesson/conversation` | `speak()`, `advance_phase()`, `record_attempt()` | Built, not wired |
| Demo Agent | `/api/demo/conversation` | `speak()`, `play_demo()` | Built, not wired |

### Critical Gap

Frontend is hardcoded to `/api/conversation`. Teacher and Demo agents are unreachable from UI.

### Routing Strategy (Section-Based)

```text
Section selected → Agent used
─────────────────────────────
Principle       → (no conversation)
Goals           → (no conversation)
Vocabulary      → Teacher Agent (phase: vocabulary)
Patterns        → Teacher Agent (phase: patterns)
Practice        → Conversation Partner
  └─► Demo Play clicked → Demo Agent
      └─► Demo finished → Conversation Partner
```

**Menu reorder**: Vocabulary and Patterns before Practice

**Demo exit rule**: Demo Agent always passes to Conversation Partner

### User Requirements

- Shared history: All actors share one conversation thread
- Visual distinction: Each actor has different name/color
- Separators: Mode changes show a divider in conversation

### Implementation Tasks

1. **Reorder Menu Sections** - `LessonSections.tsx`
   - Change: Principle → Goals → Practice → Vocabulary → Patterns
   - To: Principle → Goals → Vocabulary → Patterns → Practice

2. **Add Agent Mode to Store** - `conversationStore.ts`
   - Add `agentMode: 'conversation' | 'lesson' | 'demo'`
   - Add `setAgentMode()` action

3. **Update API with Routing** - `api.ts`
   - Route to correct endpoint based on agentMode

4. **Section-Based Agent Selection** - `useConversation.ts`
   - Vocabulary/Patterns → lesson agent
   - Practice → conversation agent
   - Demo Play button → demo agent

5. **Add Demo Control Buttons** - `DemoPlayer.tsx`
   - Repeat / Next / Questions / Finished buttons
   - "Finished" exits to Conversation Partner

6. **Visual Distinction in Conversation** - `ConversationView.tsx`
   - Actor names with messages
   - Different colors (Teacher: blue, Demo: purple, Conversation: green)
   - Separators when mode changes

## Dependencies

- Phase 7 demo audio files (19 files generated)
- Content MCP `list_demo_audio`, `get_demo_audio` tools
- Backend `/api/audio/demos` and `/api/audio/stream` endpoints
- TTS MCP for agent voice responses

## Future: A2A Integration

When A2A is implemented, the demo agent can hand off complex questions to the teacher agent for more detailed explanations.
