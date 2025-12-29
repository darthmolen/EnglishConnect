# Bug Fix: Last Audio Only + No Section Routing

**Date**: 2025-12-29
**Status**: Complete

## Problem Statement

Two bugs were discovered when testing the Teacher Agent on Lesson 7 > Patterns section:

1. **Wrong Pattern Content**: User clicks "Patterns" section, asks "Tell me Pattern 1", agent responds with hallucinated pattern ("¿Quién es este? Este es mi...") instead of actual lesson pattern
2. **Only Last Audio Plays**: Agent calls speak() twice (Spanish + English), but user only hears the last audio chunk

## Investigation

### Log Analysis

**Green path log** (`tests/log_samples/log_greenpath_pattern_request_wrong.txt`):
- User: "Dígame el patrón 1 en inglés y español"
- System prompt shows: `Current Phase: INTRODUCTION` (wrong - should be PATTERNS)
- Agent speaks English first, then Spanish (2 tool calls)
- Agent hallucinates: "Who is this? This is my..." (not from lesson content)

**Red path log** (`tests/log_samples/log_redpath_pattern_request_wrong.txt`):
- Similar issue - INTRODUCTION phase used instead of PATTERNS
- Agent hallucinated: "¿Cómo se llama tu hermano?" (not actual Pattern 1)

### Root Cause Analysis

#### Bug 1: Wrong Pattern (Section Not Sent)

Data flow traced:
```
Frontend: activeSection = 'patterns' (stored in conversationStore)
    ↓
API call: { message, lesson_number, history }  ← NO SECTION SENT
    ↓
Backend: Uses user's progress phase (defaults to INTRODUCTION)
    ↓
LLM: Receives INTRO prompt without patterns list → hallucinates
```

**Root cause**: Frontend `activeSection` was never included in the API request body.

#### Bug 2: Only Last Audio (Overwrite Loop)

Backend code in `lesson.py`:
```python
for tool_result in agent_result.get("tool_results", []):
    if tool_result.get("tool") == "speak":
        audio_base64 = result  # OVERWRITES each iteration!
```

**Root cause**: Loop overwrote `audio_base64` on each iteration, keeping only the last speak() result.

## Solution Design

### Decision: Frontend Audio Queue

Two options considered:
1. **Backend concatenation**: Combine WAV files server-side, return single file
2. **Frontend queue**: Return array of WAV chunks, play sequentially

**Chose frontend queue** because:
- First audio plays faster (doesn't wait for all TTS to complete)
- More natural pacing between language switches
- Simpler implementation (no audio manipulation needed)

### Backlog Item Added

TTS streaming investigation added to backlog. VibeVoice supports `VibeVoiceStreamingForConditionalGenerationInference` but current implementation doesn't use it. Could reduce latency by playing first words while rest generates.

## Implementation

### Bug 1 Fix: Add Section Parameter Through Stack

| Layer | File | Change |
|-------|------|--------|
| Frontend Types | `src/frontend/src/types/index.ts` | Added `section?: string` to request types |
| Frontend API | `src/frontend/src/services/api.ts` | Include `section` in POST body for lesson mode |
| Frontend Hook | `src/frontend/src/hooks/useConversation.ts` | Pass `activeSection` to `sendMessage()` |
| Backend Schema | `src/backend/app/schemas/lesson_session.py` | Added `section: str \| None` to request |
| Backend Router | `src/backend/app/routers/lesson.py` | Use section to override progress phase |
| Backend Service | `src/backend/app/services/lesson_progress_service.py` | Added `get_phase_by_type()` method |

Key backend logic:
```python
# If section is specified, use that phase instead of user's progress phase
if request.section:
    section_phase = await progress_service.get_phase_by_type(
        lesson_id=lesson_model.id,
        phase_type=request.section,
    )
    if section_phase:
        logger.info(f"Using section override: {request.section} (was {phase.phase_type})")
        phase = section_phase
        phase_state = PhaseStateSchema()  # Reset state for overridden phase
```

### Bug 2 Fix: Accumulate Audio Chunks

| Layer | File | Change |
|-------|------|--------|
| Backend Schema | `src/backend/app/schemas/lesson_session.py` | Added `AudioChunkSchema` and `audio_chunks` field |
| Backend Router | `src/backend/app/routers/lesson.py` | Accumulate chunks in list instead of overwriting |
| Frontend Types | `src/frontend/src/types/index.ts` | Added `AudioChunk` type, `audio_chunks` field |
| Frontend Hook | `src/frontend/src/hooks/useConversation.ts` | Sequential playback of audio chunks |
| Frontend Hook | `src/frontend/src/hooks/useAudioPlayer.ts` | Promise resolves when audio ENDS (not starts) |

Key backend logic:
```python
audio_chunks: list[AudioChunkSchema] = []

for tool_result in agent_result.get("tool_results", []):
    if tool_result.get("tool") == "speak" and tool_result.get("success"):
        result_data = tool_result.get("result", {})
        if result_data.get("spoken"):
            audio_chunks.append(AudioChunkSchema(
                audio_base64=result_data.get("audio_base64", ""),
                format=result_data.get("format", "wav"),
                language=result_data.get("language", "en"),
                text=result_data.get("text", ""),
            ))
```

Key frontend logic:
```typescript
const playAudioChunks = useCallback(
  async (response: AgentResponse) => {
    if (response.audio_chunks && response.audio_chunks.length > 0) {
      setStoreIsPlaying(true)
      try {
        for (const chunk of response.audio_chunks) {
          await playAudio(chunk.audio_base64, chunk.format || 'wav')
        }
      } finally {
        setStoreIsPlaying(false)
      }
    }
  },
  [playAudio, setStoreIsPlaying]
)
```

Critical fix in `useAudioPlayer.ts` - Promise must resolve when audio ENDS:
```typescript
return new Promise((resolve, reject) => {
  audio.onended = () => {
    setIsPlaying(false)
    resolve()  // Resolve AFTER audio finishes, not when play() starts
  }
  // ...
})
```

## Files Modified

### Backend
- `src/backend/app/schemas/lesson_session.py`
- `src/backend/app/routers/lesson.py`
- `src/backend/app/services/lesson_progress_service.py`

### Frontend
- `src/frontend/src/types/index.ts`
- `src/frontend/src/services/api.ts`
- `src/frontend/src/hooks/useConversation.ts`
- `src/frontend/src/hooks/useAudioPlayer.ts`

### Documentation
- `planning/backlog/backlog.md` - Added TTS streaming backlog item

## Backward Compatibility

Response still includes deprecated single-audio fields for backward compatibility:
- `audio_base64` - Last audio chunk (deprecated)
- `audio_format` - Last audio format (deprecated)
- `language` - Last audio language (deprecated)

New clients should use `audio_chunks` array instead.

## Testing

To verify fixes:
1. Restart backend to pick up changes
2. Open Lesson 7 > click "Patterns" section
3. Say in Spanish: "Dígame el patrón 1 en español e inglés"
4. Verify:
   - Agent gives correct Pattern 1 from lesson (not hallucinated)
   - You hear BOTH Spanish AND English audio sequentially

## Lessons Learned

1. **Always trace data flow end-to-end**: The section parameter existed in frontend state but was never sent to backend
2. **Watch for overwrite-in-loop bugs**: Common pattern when code evolves from single to multiple items
3. **Promise timing matters**: Audio playback Promise must resolve when audio ENDS, not when `play()` is called, otherwise sequential playback breaks
