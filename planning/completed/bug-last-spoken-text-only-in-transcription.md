# Bug Fix: Only Last Spoken Text Shown in Transcription

**Date**: 2025-12-29
**Status**: Complete

## Problem Statement

When the teacher agent speaks in both Spanish and English (two speak() tool calls), only ONE language's text appeared in the conversation UI. The user heard both audio files correctly, but the transcript only showed the last spoken text.

**Example**:
- User asks: "Dígame PATRÓN 1 en Inglés y Español"
- Agent speaks: Spanish pattern, then English pattern (both audio play correctly)
- UI shows: "Pattern 1 is: Question: Tell me about your (*noun*)..." (English only)
- Expected: Both Spanish AND English text in the transcript

## Root Cause

In `src/backend/app/routers/lesson.py`, the loop that processed speak() tool results overwrote a single variable on each iteration:

```python
# BUGGY CODE (line 228)
for tool_result in agent_result.get("tool_results", []):
    if tool_result.get("tool") == "speak" and tool_result.get("success"):
        result_data = tool_result.get("result", {})
        if result_data.get("spoken"):
            spoken_text = result_data.get("text")  # <-- OVERWRITES each time!

response_text = spoken_text if spoken_text else agent_result["text"]  # Only has LAST text
```

### Data Flow (Buggy)

```
LLM calls:
  speak("El patrón 1 es...", "es")  →  spoken_text = "El patrón 1 es..."
  speak("Pattern 1 is...", "en")    →  spoken_text = "Pattern 1 is..."  (overwrites!)

Result:
  response_text = "Pattern 1 is..."  (Spanish lost!)
```

## Solution

Changed from keeping only the last `spoken_text` to joining ALL audio chunk texts:

```python
# FIXED CODE
# Build response text from all audio chunks (bilingual support)
# This ensures both Spanish and English spoken texts appear in the transcript
if audio_chunks:
    response_text = " ".join(chunk.text for chunk in audio_chunks)
else:
    response_text = agent_result["text"]
```

### Data Flow (Fixed)

```
LLM calls:
  speak("El patrón 1 es...", "es")  →  audio_chunks[0].text = "El patrón 1 es..."
  speak("Pattern 1 is...", "en")    →  audio_chunks[1].text = "Pattern 1 is..."

Result:
  response_text = "El patrón 1 es... Pattern 1 is..."  (both preserved!)
```

## Important Context: Agent-Controlled TTS

This bug highlights a key architectural detail: **the LLM's final text response is different from what it speaks**.

```
agent_result = {
    "text": "Final LLM message",        ← What LLM "says" in text (not spoken)
    "tool_results": [
        { "tool": "speak", "result": { "text": "Spanish..." } },  ← Actually spoken
        { "tool": "speak", "result": { "text": "English..." } }   ← Actually spoken
    ]
}
```

The `response.text` sent to the frontend should reflect **what was spoken** (from audio_chunks), not what the LLM wrote (from agent_result["text"]).

## Files Modified

| File | Change |
|------|--------|
| `src/backend/app/routers/lesson.py` | Changed line 230 to join audio_chunks texts |

## Tests Added

| File | Tests |
|------|-------|
| `tests/integration/test_multiple_spoken_texts.py` | 5 tests covering: two speak calls, single speak, no speak, three speak calls, failed speak |

## Documentation Added

| File | Content |
|------|---------|
| `documentation/general-agent-conversation-workflow.md` | Full data flow for voice-enabled agent conversations |

## Verification

1. Run tests: `pytest tests/integration/test_multiple_spoken_texts.py -v`
2. Restart backend
3. Test Lesson 7 > Patterns
4. Ask: "Dígame el patrón 1 en español e inglés"
5. Verify transcript shows BOTH: "El patrón 1 es... Pattern 1 is..."

## Related Bugs

This is part of a series of fixes for the bilingual audio system:

- `bug-lastaudioonly-nosection.md` - Fixed audio chunk accumulation and section routing
- `bug-last-spoken-text-only-in-transcription.md` (this doc) - Fixed transcript text

## Lessons Learned

1. **Watch for overwrite-in-loop bugs**: When code evolves from handling one item to multiple items, check for variables being overwritten instead of accumulated.

2. **Agent text != spoken text**: In agent-controlled TTS, the LLM's text response and what it passes to speak() are separate things. The UI should show what was spoken, not what was written.

3. **Test with multiple tool calls**: Always test scenarios where tools are called multiple times, not just once.
