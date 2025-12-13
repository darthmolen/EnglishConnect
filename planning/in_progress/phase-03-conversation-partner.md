# Phase 3: React SPA Conversation Partner

**Status**: 🔜 Ready to Start
**Goal**: Web-based voice conversation with lesson selection

## Overview

Build a React SPA that enables voice-based English practice conversations. Users select a lesson, then engage in spoken dialogue with the AI tutor. The AI uses lesson content (vocabulary, patterns) to guide contextual practice.

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
│                          │  - currentLesson                              │
│                          │  - conversation                               │
│                          │  - isRecording                                │
│                          └───────┬───────┘                              │
└──────────────────────────────────┼──────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
           ┌───────────┐   ┌───────────┐   ┌───────────┐
           │  Backend  │   │    STT    │   │    TTS    │
           │   :8000   │   │   :8001   │   │   (MCP)   │
           │           │   │           │   │           │
           │ Azure AI  │   │  Whisper  │   │ VibeVoice │
           │ Content   │   │    VAD    │   │           │
           └───────────┘   └───────────┘   └───────────┘
```

## User Flow

1. **Landing** → User sees lesson list (EC1 lessons 1-25)
2. **Select Lesson** → Lesson details shown (title, objective, vocabulary preview)
3. **Start Conversation** → Click mic button to begin
4. **Voice Loop**:
   - User speaks → VAD detects end → STT transcribes
   - Transcript appears in UI
   - AI responds (streaming text + TTS audio)
   - Loop continues until user stops

## Tasks

### 3.1 Frontend Setup

- [ ] Initialize Vite + React + TypeScript project in `src/frontend/`
- [ ] Install and configure shadcn/ui
- [ ] Set up Tailwind CSS
- [ ] Configure Zustand store
- [ ] Create basic layout (sidebar + main area)

### 3.2 Lesson Selector

- [ ] Create LessonList component (fetch from Content MCP via backend)
- [ ] Create LessonCard component (title, objective preview)
- [ ] Create LessonDetail component (vocabulary, patterns)
- [ ] Wire up lesson selection to Zustand store

### 3.3 Voice Interface

- [ ] Create VoiceButton component (mic on/off states)
- [ ] Implement WebSocket connection to STT service
- [ ] Handle audio recording via MediaRecorder API
- [ ] Display real-time transcription
- [ ] Handle VAD-based utterance detection

### 3.4 Conversation Display

- [ ] Create ConversationView component
- [ ] Create MessageBubble component (user vs AI styling)
- [ ] Implement auto-scroll to latest message
- [ ] Show typing/thinking indicator during AI response

### 3.5 AI Integration

- [ ] Create backend endpoint for conversation (`POST /api/conversation`)
- [ ] Integrate Azure AI Foundry (GPT-4o-mini)
- [ ] Include lesson context in prompts (vocabulary, patterns)
- [ ] Stream AI responses to frontend
- [ ] Trigger TTS playback for AI responses

### 3.6 TTS Playback

- [ ] Create audio playback service
- [ ] Handle TTS via backend (calls TTS MCP)
- [ ] Stream audio chunks to browser
- [ ] Implement playback queue for long responses

### 3.7 Testing

- [ ] E2E tests with Playwright (in `tests/e2e/`)
- [ ] Test lesson selection flow
- [ ] Test voice recording (mock audio)
- [ ] Test conversation display

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

- [ ] User can browse and select EC1 lessons
- [ ] Voice recording works via browser mic
- [ ] Transcription appears in real-time
- [ ] AI responds with lesson-appropriate content
- [ ] TTS plays AI responses audibly
- [ ] Conversation flows naturally (< 2s latency target)
- [ ] UI is clean and responsive
- [ ] E2E tests pass in CI

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
