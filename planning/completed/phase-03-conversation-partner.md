# Phase 3: React SPA Conversation Partner

**Status**: ✅ Complete
**Goal**: Web-based voice conversation with intelligent agent

## Overview

Build a React SPA with an **intelligent conversation partner agent** that enables voice-based English practice. The agent is NOT a pipeline - it controls TTS/STT as tools and makes intelligent decisions about when to speak, what language to use, and how to pace responses.

See [ADR-002: Conversation Partner Agent vs Pipeline](../../documentation/ADR/ADR-002-CONVERSATION-PARTNER-AGENT.md) for architectural decision.

## MVP Scope (Option B: Voice + Lesson Selector)

- Lesson selector showing EC1 lessons 1-25
- Voice conversation interface
- Real-time transcription display (user speech → text)
- AI response with TTS playback
- Current lesson context visible during conversation

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | React 18 + TypeScript |
| Build | Vite |
| UI Components | shadcn/ui |
| State | Zustand |
| Styling | Tailwind CSS |
| LLM | Azure AI Foundry (GPT-4o-mini) |
| Voice | WebSocket to STT/TTS services |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         React SPA (localhost:5173)                       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐  │
│  │ Lesson Selector │    │  Voice Controls │    │  Conversation View  │  │
│  │  (sidebar)      │    │  (mic button)   │    │  (transcript)       │  │
│  └────────┬────────┘    └────────┬────────┘    └──────────┬──────────┘  │
│           │                      │                        │             │
│           └──────────────────────┼────────────────────────┘             │
│                                  │                                       │
│                          ┌───────▼───────┐                              │
│                          │  Zustand Store │                              │
└──────────────────────────────────┼──────────────────────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
     ┌─────────────┐    ┌──────────────────────┐    ┌─────────────┐
     │    STT      │    │  Conversation Agent  │    │    TTS      │
     │   :8001     │    │      (Backend)       │    │   (MCP)     │
     │             │    │                      │    │             │
     │  Whisper    │───▶│  - GPT-4o-mini       │───▶│  VibeVoice  │
     │  (transcribe│    │  - Lesson context    │    │  (speak)    │
     │   audio)    │    │  - MCP tool: speak() │    │             │
     └─────────────┘    │  - MCP tool: lesson()│    └─────────────┘
                        └──────────────────────┘
                                   │
                    Agent decides: language, pacing, response
```

**Key Insight**: The agent controls TTS via MCP tools. It decides WHEN and HOW to speak.

## User Flow

1. **Landing** → User sees lesson list (EC1 lessons 1-25)
2. **Select Lesson** → Lesson details shown (title, objective, vocabulary preview)
3. **Start Conversation** → Click mic button to begin
4. **Voice Loop** (Agent-Controlled):
   - User speaks → STT transcribes → text sent to agent
   - Agent receives text + lesson context
   - Agent decides: response content, language (EN/ES), pacing
   - Agent calls `speak()` tool → TTS generates audio → plays
   - Transcript appears in UI (both user and agent text)
   - Loop continues until user stops

**Agent Capabilities**:
- Flip to Spanish when student needs clarification
- Slow down and spell words when needed
- Stay within lesson vocabulary
- Ask clarifying questions instead of assuming

## Tasks

### 3.1 Frontend Setup

- [x] Initialize Vite + React + TypeScript project in `src/frontend/`
- [x] Install and configure shadcn/ui
- [x] Set up Tailwind CSS
- [x] Configure Zustand store
- [x] Create basic layout (sidebar + main area)

### 3.2 Lesson Selector

- [x] Create LessonList component (fetch from Content MCP via backend)
- [x] Create LessonCard component (title, objective preview)
- [x] Create LessonDetail component (vocabulary, patterns)
- [x] Wire up lesson selection to Zustand store

### 3.3 Voice Interface

- [x] Create VoiceButton component (mic on/off states)
- [x] Implement HTTP POST to STT service (simplified from WebSocket)
- [x] Handle audio recording via MediaRecorder API
- [x] Display transcription after recording
- [x] Handle VAD-based utterance detection (server-side)

### 3.4 Conversation Display

- [x] Create ConversationView component
- [x] Create MessageBubble component (user vs AI styling)
- [x] Implement auto-scroll to latest message
- [x] Show loading indicator during AI response

### 3.5 Conversation Partner Agent

- [x] Create backend endpoint for conversation (`POST /api/conversation`)
- [x] Integrate Azure AI Foundry (GPT-4o-mini)
- [x] Design agent system prompt for conversation partner
- [x] Give agent access to TTS via `speak()` tool
- [x] Lesson context passed to agent via system prompt
- [x] Auto-synthesis fallback when agent forgets speak()

### 3.6 TTS Integration (Agent-Controlled)

- [x] Add HTTP endpoint to TTS MCP server for backend access
- [x] Create backend service to call TTS when agent invokes `speak()`
- [x] Return audio to frontend for playback
- [x] Handle agent's voice/language choices

### 3.7 Testing

- [ ] E2E tests with Playwright (deferred to Phase 11)
- [x] Manual test lesson selection flow
- [x] Manual test voice recording
- [x] Manual test conversation display

## UI Design

### Layout

```
┌────────────────────────────────────────────────────────────┐
│  EnglishConnect                              [Settings ⚙]  │
├──────────────┬─────────────────────────────────────────────┤
│              │                                             │
│  LESSONS     │   Lesson 5: Hobbies and Interests          │
│              │   ─────────────────────────────             │
│  ○ Lesson 1  │                                             │
│  ○ Lesson 2  │   [Conversation transcript here]            │
│  ○ Lesson 3  │                                             │
│  ○ Lesson 4  │   User: I like to play soccer.              │
│  ● Lesson 5  │   AI: That's great! How often do you        │
│  ○ Lesson 6  │       play soccer?                          │
│  ○ Lesson 7  │   User: I play every weekend.               │
│  ...         │   AI: Nice! Do you play with friends        │
│              │       or family?                            │
│              │                                             │
│              │   ┌─────────────────────────────────────┐   │
│              │   │  🎤  [Recording...]                 │   │
│              │   └─────────────────────────────────────┘   │
│              │                                             │
├──────────────┴─────────────────────────────────────────────┤
│  Vocabulary: soccer, play, exercise, weekend, friends      │
└────────────────────────────────────────────────────────────┘
```

### Theme

- Neutral colors (shadcn defaults)
- Clean, minimal design
- Accessible contrast ratios
- Mobile-responsive (sidebar collapses)

## File Structure

```
src/frontend/
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── package.json
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/
│   │   ├── ui/                 # shadcn components
│   │   ├── LessonList.tsx
│   │   ├── LessonCard.tsx
│   │   ├── LessonDetail.tsx
│   │   ├── VoiceButton.tsx
│   │   ├── ConversationView.tsx
│   │   └── MessageBubble.tsx
│   ├── stores/
│   │   └── conversationStore.ts
│   ├── services/
│   │   ├── api.ts              # Backend API calls
│   │   ├── audioRecorder.ts    # Mic recording
│   │   └── audioPlayer.ts      # TTS playback
│   ├── hooks/
│   │   ├── useVoiceRecording.ts
│   │   └── useConversation.ts
│   └── types/
│       └── index.ts
```

## API Endpoints (Backend)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/lessons` | GET | List all lessons |
| `/api/lessons/{id}` | GET | Get lesson details |
| `/api/conversation` | POST | Send message, get AI response |
| `/api/tts` | POST | Generate TTS audio |
| `/ws/voice` | WebSocket | Real-time voice streaming |

## Dependencies

### Frontend

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "zustand": "^4.5.0",
    "@radix-ui/react-*": "latest",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0",
    "lucide-react": "^0.300.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "@types/react": "^18.2.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "@playwright/test": "^1.40.0"
  }
}
```

## Success Criteria

- [x] User can browse and select EC1 lessons
- [x] Voice recording works via browser mic
- [x] Transcription appears after recording (STT integration)
- [x] Agent responds with lesson-appropriate content
- [x] Agent calls TTS tool to speak responses (with auto-synthesis fallback)
- [x] Conversation flows (latency ~2-3s including TTS)
- [x] UI is clean and responsive
- [ ] E2E tests pass in CI (deferred to Phase 11)
- [ ] Agent can flip to Spanish for clarification (needs prompt tuning - Phase 11)

## Non-Goals (Phase 3)

- User authentication (Phase 4)
- Progress tracking (Phase 4)
- Multiple courses (future)
- Offline mode (future)
- Mobile app (future)

## Estimated Effort

| Task | Complexity |
|------|------------|
| Frontend setup | Low |
| Lesson selector | Low |
| Voice interface | Medium |
| AI integration | Medium |
| TTS playback | Medium |
| E2E testing | Low |

## References

- [shadcn/ui docs](https://ui.shadcn.com)
- [Zustand docs](https://docs.pmnd.rs/zustand)
- [Vite React guide](https://vitejs.dev/guide/)
- [Azure AI Foundry](https://azure.microsoft.com/en-us/products/ai-foundry)
