# Agent Conversation Workflow

This document describes the data flow for voice-enabled agent conversations in EnglishConnect. Unlike traditional chatbots where text flows directly to the user, our agent controls TTS as a tool, deciding what to speak, in which language, and when.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React SPA)                              │
│                                                                             │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────────────┐    │
│  │  Microphone │───▶│  STT Service     │───▶│  Text Message           │    │
│  │  (Browser)  │    │  (faster-whisper)│    │  + activeSection        │    │
│  └─────────────┘    └──────────────────┘    └───────────┬─────────────┘    │
│                                                         │                   │
│                                                         ▼                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      API Request                                     │   │
│  │  POST /api/lesson/conversation                                       │   │
│  │  { message, lesson_number, history, section }                        │   │
│  └─────────────────────────────────┬───────────────────────────────────┘   │
│                                    │                                        │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                                 │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  lesson.py router                                                    │   │
│  │                                                                      │   │
│  │  1. Load lesson content from Content-MCP                             │   │
│  │  2. Get/create user progress                                         │   │
│  │  3. Override phase if section parameter provided                     │   │
│  │  4. Build system prompt with phase-specific context                  │   │
│  │  5. Call LLM agent with tool definitions                             │   │
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
│  │  │  - System prompt (phase context, lesson content)             │    │   │
│  │  │  - User message (transcribed speech)                         │    │   │
│  │  │  - Conversation history                                      │    │   │
│  │  │  - Available tools: speak(), advance_phase(), record_attempt()│   │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                         │                                            │   │
│  │                         ▼                                            │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │  LLM decides to call tools:                                  │    │   │
│  │  │                                                              │    │   │
│  │  │  speak(text="Hola, el patrón es...", language="es")         │    │   │
│  │  │       │                                                      │    │   │
│  │  │       └──▶ TTS-MCP generates audio_base64                    │    │   │
│  │  │       └──▶ Returns: { spoken: true, text, language, audio }  │    │   │
│  │  │                                                              │    │   │
│  │  │  speak(text="Hello, the pattern is...", language="en")      │    │   │
│  │  │       │                                                      │    │   │
│  │  │       └──▶ TTS-MCP generates audio_base64                    │    │   │
│  │  │       └──▶ Returns: { spoken: true, text, language, audio }  │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                         │                                            │   │
│  │                         ▼                                            │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │  LLM returns final response (no more tool calls):            │    │   │
│  │  │                                                              │    │   │
│  │  │  agent_result = {                                            │    │   │
│  │  │    "text": "Final LLM message (may differ from spoken)",     │    │   │
│  │  │    "tool_calls": [...],                                      │    │   │
│  │  │    "tool_results": [                                         │    │   │
│  │  │      { tool: "speak", result: { text, language, audio } },   │    │   │
│  │  │      { tool: "speak", result: { text, language, audio } }    │    │   │
│  │  │    ]                                                         │    │   │
│  │  │  }                                                           │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────┬───────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  lesson.py - Response Assembly                                       │   │
│  │                                                                      │   │
│  │  1. Collect all audio_chunks from speak() tool results              │   │
│  │  2. Build response_text from all audio_chunks (joined with space)   │   │
│  │  3. Return LessonConversationResponse with both                     │   │
│  └─────────────────────────────────┬───────────────────────────────────┘   │
│                                    │                                        │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API Response                                      │
│                                                                             │
│  {                                                                          │
│    "text": "Hola, el patrón es... Hello, the pattern is...",               │
│    "audio_chunks": [                                                        │
│      { "text": "Hola, el patrón es...", "language": "es", "audio_base64" }, │
│      { "text": "Hello, the pattern is...", "language": "en", "audio_base64"}│
│    ],                                                                       │
│    "phase": { ... },                                                        │
│    "phase_state": { ... }                                                   │
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
│     addMessage({ role: 'assistant', content: response.text })              │
│     Shows: "Hola, el patrón es... Hello, the pattern is..."                │
│                                                                             │
│  2. Play audio chunks sequentially:                                         │
│     for (chunk of response.audio_chunks) {                                  │
│       await playAudio(chunk.audio_base64)  // Waits for each to finish     │
│     }                                                                       │
│     Plays: Spanish audio, then English audio                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### 1. Agent Controls TTS (Not a Pipeline)

This is NOT a traditional pipeline where text automatically flows through TTS. The LLM agent has a `speak()` tool and decides:
- **What** to say (the text)
- **Which language** to use (en/es)
- **When** to speak (can speak multiple times)
- **Whether** to speak at all (can just return text)

### 2. Two Different "Text" Values

There are two distinct text values in the response:

| Value | Source | Purpose |
|-------|--------|---------|
| `agent_result["text"]` | LLM's final message after tool calls | What the LLM "says" as text (may not be spoken) |
| `tool_results[].result.text` | Text passed to each speak() call | What was actually spoken as audio |

**Important**: The `response.text` sent to frontend is the **joined spoken texts**, not the LLM's final text message. This ensures the conversation transcript accurately reflects what was heard.

### 3. Audio Chunk Accumulation

When the agent calls speak() multiple times:

```python
# Old (buggy): Only kept last audio
for tool_result in tool_results:
    spoken_text = tool_result["text"]  # Overwritten each time!

# New (fixed): Accumulate all chunks
audio_chunks = []
for tool_result in tool_results:
    audio_chunks.append(AudioChunkSchema(...))

response_text = " ".join(chunk.text for chunk in audio_chunks)
```

### 4. Sequential Audio Playback

Frontend plays audio chunks sequentially, waiting for each to finish:

```typescript
for (const chunk of response.audio_chunks) {
  await playAudio(chunk.audio_base64)  // Promise resolves when audio ENDS
}
```

This ensures proper pacing for bilingual responses (Spanish first, then English).

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

### advance_phase()

```json
{
  "name": "advance_phase",
  "description": "Move to the next phase or item in the lesson.",
  "parameters": {
    "reason": "Brief reason for advancing"
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

| Service | Port | Role |
|---------|------|------|
| Frontend | 5173 | React SPA, captures audio, displays conversation |
| Backend | 8000 | FastAPI, orchestrates agent, assembles responses |
| STT | 8001 | faster-whisper, transcribes speech to text |
| TTS-MCP | stdio | VibeVoice, generates speech from text |
| Content-MCP | stdio | Serves lesson content (vocabulary, patterns) |

## Related Files

- `src/backend/app/routers/lesson.py` - Main conversation endpoint
- `src/backend/app/services/azure_openai.py` - Agent with tool calling
- `src/backend/app/services/tool_handlers.py` - TTS integration
- `src/frontend/src/hooks/useConversation.ts` - Response handling
- `src/frontend/src/hooks/useAudioPlayer.ts` - Audio playback
