# Agent Conversation Workflow

This document describes the data flow for voice-enabled agent conversations in EnglishConnect. The agent controls TTS as a tool, deciding what to speak, in which language, and when.

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React SPA)                              │
│                                                                             │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────────────┐    │
│  │  Microphone │───▶│  STT Service     │───▶│  Text Message           │    │
│  │  (Browser)  │    │  (faster-whisper)│    │  + mode + exchange_count│    │
│  └─────────────┘    └──────────────────┘    └───────────┬─────────────┘    │
│                                                         │                   │
│                                                         ▼                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      API Request                                     │   │
│  │  POST /api/practice/conversation                                     │   │
│  │  { message, lesson_number, mode, exchange_count, history,            │   │
│  │    instruction_language, focus_pattern? }                            │   │
│  └─────────────────────────────────┬───────────────────────────────────┘   │
│                                    │                                        │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                                 │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  conversation.py router                                              │   │
│  │                                                                      │   │
│  │  1. Load lesson content from database                                │   │
│  │  2. Create UnifiedTeachingAgent with mode + optional focus_pattern   │   │
│  │  3. Build system prompt with mode-specific behavior                  │   │
│  │  4. Call LLM agent with tool definitions                             │   │
│  └─────────────────────────────────┬───────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  azure_openai.py - get_agent_response()                              │   │
│  │                                                                      │   │
│  │  Tool Calling Loop (max 5 iterations):                               │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │  LLM (GPT-4o-mini) receives:                                 │    │   │
│  │  │  - System prompt (mode context, lesson content)              │    │   │
│  │  │  - User message (transcribed speech)                         │    │   │
│  │  │  - Conversation history                                      │    │   │
│  │  │  - Available tools: speak(), get_teaching_help(),            │    │   │
│  │  │                     record_attempt()                         │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                         │                                            │   │
│  │                         ▼                                            │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │  LLM decides to call tools:                                  │    │   │
│  │  │                                                              │    │   │
│  │  │  speak(text="Hello! Let's practice.", language="en")        │    │   │
│  │  │       │                                                      │    │   │
│  │  │       └──▶ TTS-MCP generates audio_base64                    │    │   │
│  │  │       └──▶ Returns: { spoken: true, text, language, audio }  │    │   │
│  │  │                                                              │    │   │
│  │  │  get_teaching_help(query="family vocabulary")               │    │   │
│  │  │       │                                                      │    │   │
│  │  │       └──▶ Returns vocabulary and patterns from lesson      │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                         │                                            │   │
│  │                         ▼                                            │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │  LLM returns final response (no more tool calls)            │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────┬───────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  conversation.py - Response Assembly                                 │   │
│  │                                                                      │   │
│  │  1. Extract audio from speak() tool result (prefers English)        │   │
│  │  2. Use spoken text as response text                                │   │
│  │  3. Auto-synthesize if agent didn't call speak()                    │   │
│  │  4. Return ConversationResponse with text + audio                   │   │
│  └─────────────────────────────────┬───────────────────────────────────┘   │
│                                    │                                        │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API Response                                      │
│                                                                             │
│  {                                                                          │
│    "text": "Hello! Let's practice.",                                        │
│    "audio_base64": "...",                                                   │
│    "audio_format": "wav",                                                   │
│    "language": "en",                                                        │
│    "lesson_number": 5                                                       │
│  }                                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND - Response Handling                      │
│                                                                             │
│  useConversation.ts:                                                        │
│                                                                             │
│  1. Add message to conversation:                                            │
│     addMessage({ role: 'assistant', content: response.text })               │
│                                                                             │
│  2. Play audio:                                                             │
│     await playAudio(response.audio_base64)                                  │
│                                                                             │
│  3. Increment exchange count (for practice mode flip detection)             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### 1. Unified Teaching Agent with Two Modes

Single agent handles both pages with different behaviors:

| Mode       | Page       | Behavior                                          |
|------------|------------|---------------------------------------------------|
| `help`     | Vocabulary | Answer questions only, use `get_teaching_help`    |
| `practice` | Practice   | Lead conversation, flip roles after 3-5 exchanges |

### 2. Pattern-Focused Practice (Optional)

In practice mode, an optional `focus_pattern` parameter allows targeted practice of a specific Q&A pattern. When set:

- The agent's system prompt includes a `FOCUS PATTERN` section highlighting the specific pattern
- The agent starts the conversation using that pattern
- After practicing it a few times, the agent can naturally expand to related patterns

**User Flow:**

1. User clicks "Practice" button on a specific pattern in the UI
2. Frontend calls `startPatternPractice(patternNumber)` which:
   - Sets `focusPattern` in the store
   - Clears messages and resets exchange count
   - Ensures agent mode is "practice"
3. Next API call includes `focus_pattern` parameter
4. Agent receives focused instructions in its system prompt

### 3. Agent Controls TTS (Not a Pipeline)

This is NOT a traditional pipeline where text automatically flows through TTS. The LLM agent has a `speak()` tool and decides:

- **What** to say (the text)
- **Which language** to use (en/es)
- **Whether** to speak at all (can just return text)

### 4. Exchange Count for Role Flipping

In practice mode, the frontend tracks `exchange_count`. After 3-5 exchanges, the agent prompts the student to ask questions instead of just responding.

### 5. Agentic RAG via get_teaching_help

The agent can retrieve vocabulary, patterns, and exercises from the current lesson context using the `get_teaching_help` tool. This enables context-aware responses.

## Tool Definitions

### speak()

```json
{
  "name": "speak",
  "description": "Speak text aloud to the student using text-to-speech.",
  "parameters": {
    "text": "The text to speak aloud",
    "language": "en or es",
    "voice": "speaker_a through speaker_f"
  }
}
```

### get_teaching_help()

```json
{
  "name": "get_teaching_help",
  "description": "Retrieve vocabulary, patterns, or exercises from the lesson.",
  "parameters": {
    "query": "What to search for (e.g., 'family vocabulary', 'greeting patterns')"
  }
}
```

### record_attempt()

```json
{
  "name": "record_attempt",
  "description": "Record a student's attempt at vocabulary or patterns.",
  "parameters": {
    "item_type": "vocab or pattern",
    "correct": true/false
  }
}
```

## Services Involved

| Service     | Port  | Role                                            |
|-------------|-------|-------------------------------------------------|
| Frontend    | 5173  | React SPA, captures audio, displays chat        |
| Backend     | 8000  | FastAPI, orchestrates agent, assembles response |
| STT         | 8001  | faster-whisper, transcribes speech to text      |
| TTS-MCP     | stdio | VibeVoice, generates speech from text           |
| Content-MCP | stdio | Serves lesson content (vocabulary, patterns)    |

## Related Files

- `src/backend/app/routers/conversation.py` - Unified conversation endpoint
- `src/backend/app/agents/unified_teaching_agent.py` - Agent with mode-based prompts
- `src/backend/app/services/azure_openai.py` - LLM with tool calling
- `src/backend/app/services/tool_handlers.py` - Tool implementations
- `src/frontend/src/hooks/useConversation.ts` - Response handling
- `src/frontend/src/stores/conversationStore.ts` - State management
