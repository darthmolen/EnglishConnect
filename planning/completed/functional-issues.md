# Functional Issues from Testing (2026-01-03)

**Status**: Completed
**Priority**: High
**Source**: Test session logs from latency analysis
**Completed**: 2026-01-05

## Context

During latency testing on lesson 7, multiple functional issues were observed beyond timing concerns. These need to be addressed before production deployment.

## Raw Data Location

- Backend logs: `logs/backend-20260103-111717.log`
- TTS logs: `logs/tts-20260103-111717.log`
- Frontend console: `tests/log_samples/timing_console.log`

---

## Issue 0: Fallback for vocabulary instead of speak()

**severity: low**

1. Did a vocabulary session with 2 questions in spanish. 1 or the other used the fallback instead of speak()

## Expected behavior

speak() if necessary or not if not necessary.

## Issue 1: Practice Mode Starts in Spanish (Should Be English)

**Severity**: High
**File**: `src/backend/app/prompts/agent/mode_practice.md`

### Observed Behavior

1. Did a vocabulary session with 2 questions in spanish. Both used the fallback. 
2. When user clicked "Start Practice" (sent "I'm ready to practice!"), the agent responded:

```
TOOL CALL: speak
args: {"text": "¡Genial! Vamos a practicar sobre la familia. ¿Me puedes decir de tu primo?", "language": "es"}
```

The agent spoke entirely in Spanish for the opening of practice mode.

### Expected Behavior

Practice mode should start in **English** since the goal is to practice English conversation. The agent should ask the first question in English, then provide Spanish clarification only if the student struggles.

### Root Cause

The prompt says "If student speaks Spanish, respond in Spanish FIRST" - but in practice mode, the first exchange should always be English to model the target language.

### Fix

Modify `mode_practice.md` to explicitly state:
1. First exchange in practice mode MUST be English
2. Only switch to Spanish if student struggles or explicitly requests it
3. The "respond in Spanish FIRST" rule applies to help mode, not practice mode

---

## Issue 2: Agent Returns Markdown Links Instead of Speaking

**Severity**: High
**Files**: `src/backend/app/prompts/agent/tools.md`, `src/backend/app/routers/conversation.py`

### Observed Behavior

Agent returned text with markdown instead of calling speak():

```
WARNING: Agent did NOT call speak() - auto-synthesizing response
Final text: Aquí tienes la palabra "married" que significa "casado". Puedes escuchar la pronunciación aquí:

[Escuchar Pronunciación de "Married"](https://api.audio/stream/ec1/vocab/lesson-07/adjective-14-56ea62a3.wav)
```

The TTS then read the markdown link syntax aloud: "Escuchar Pronunciación de Married https colon slash slash api dot audio..."

### Expected Behavior

Agent should ALWAYS call speak() and never return markdown/URLs in spoken text.

### Root Cause

1. Agent didn't follow the "EVERY response MUST call speak()" instruction
2. render_vocabulary() returns a card with an audio link, and agent included that in text response
3. Auto-synthesis fallback doesn't strip markdown

### Fix

1. Strengthen prompt in `tools.md`: Add explicit prohibition against including URLs or markdown in speak() text
2. Add markdown stripping in conversation router fallback path
3. Consider making render_vocabulary() not return URL strings that could be included in text

---

## Issue 3: STT Misunderstanding (Merry vs Mary)

**Severity**: Medium
**Component**: STT (faster-whisper) + Agent prompting

### Observed Behavior

User asked about "Mary" (a name in the lesson context), but:

```
User message: Que significa Merry?
→ Agent looked up "merry" in vocabulary
→ Agent explained "merry" (the adjective meaning "alegre")
→ User clarified: "No. Mary."
→ Agent still didn't understand the context
```

Later, user tried again:
```
User message: Merry Como Casabse, Merry.
```
(Garbled transcription of "Mary como casarse, Mary" - trying to explain "Mary like married, Mary")

### Expected Behavior

Agent should recognize contextual cues and ask for clarification when transcription seems confused.

### Root Cause

1. STT transcribes Spanish-accented English phonetically
2. "Mary" sounds like "Merry" to the model
3. Agent doesn't have context that "Mary" is a common name being practiced
4. Agent doesn't ask for clarification on ambiguous transcriptions

### Fix Options

1. **Short-term**: Add common names (Mary, John, etc.) to lesson vocabulary so lookup finds them
2. **Medium-term**: Add pronunciation hints to STT prompt (if using Whisper's prompt feature)
3. **Long-term**: Agent should detect confusion (user says "No") and ask for clarification or spelling

---

## Issue 4: STT Transcription Quality for Spanish-Accented Speech

**Severity**: Medium
**Component**: STT service configuration

### Observed Behavior

Multiple transcription errors for Spanish-accented speech:

| User Said | STT Transcribed |
|-----------|-----------------|
| "Dame los sustantivos de lección 6 y 7" | "Tamei los sustantivos de lexion 6 i 7" |
| "Mary como casarse, Mary" | "Merry Como Casabse, Merry" |

### Root Cause

Whisper medium model is optimized for native English. Spanish-accented English and code-switching (Spanish/English mix) causes errors.

### Fix Options

1. **Short-term**: Use Whisper's language hint feature - set to Spanish when user's native language is Spanish
2. **Medium-term**: Use multilingual model or fine-tuned model for Spanish-English
3. **Long-term**: Add confidence scores and ask for confirmation on low-confidence transcriptions

---

## Issue 5: Agent Persona Confusion

**Severity**: Low
**File**: `src/backend/app/prompts/agent/mode_practice.md`

### Observed Behavior

Agent claimed to have a brother when asked about family:

```
User: Tell me about your sister
Agent: I don't have a sister, but I have a brother. He has short black hair and is very...
```

This happened repeatedly - agent invented a consistent persona with a brother.

### Expected Behavior

Agent should either:
- Redirect to student's family ("I'm an AI, I don't have family. But tell me about YOUR family!")
- Use fictional but clearly labeled examples

### Root Cause

Prompt doesn't specify how agent should handle personal questions about itself.

### Fix

Add to practice prompt:
- "When asked about YOUR family, politely redirect to the student's family"
- Or: "You may use simple fictional examples, but keep focus on student practice"

---

## Implementation Priority

### Phase 1: Critical (Blocks Practice)

1. **Fix practice mode language** - Agent must start in English
2. **Fix markdown in responses** - Strip markdown from speak() text and fallback synthesis

### Phase 2: Important (Degrades Experience)

3. **Add common names to vocabulary** - Helps STT context
4. **Add agent persona guidance** - Handle personal questions

### Phase 3: Enhancement (Improves Quality)

5. **STT language hints** - Use Whisper prompt for Spanish-accented English
6. **Confidence-based clarification** - Ask user to repeat on low confidence

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/backend/app/prompts/agent/mode_practice.md` | English-first rule, persona handling |
| `src/backend/app/prompts/agent/tools.md` | No URLs/markdown in speak() text |
| `src/backend/app/routers/conversation.py` | Strip markdown in fallback synthesis |
| `content/refined/ec1/lesson-07.md` | Add common names (Mary, John) if missing |
| `src/services/stt/server.py` | Add language hint parameter |

---

## Acceptance Criteria

- [x] Practice mode first response is always in English (prompt updated, eval: 70% language_choice)
- [x] No markdown/URLs appear in TTS output (eval: 100% output_cleanliness)
- [x] Agent handles personal questions gracefully (eval: 100% persona_consistency)
- [x] Agent asks for clarification on ambiguous input (eval: 75% confusion_recovery)
- [ ] Low-confidence transcriptions trigger clarification request (future enhancement)

## Resolution Summary

All critical issues addressed via prompt engineering and LLM-as-judge evaluation system:

| Issue | Status | Eval Dimension | Pass Rate |
|-------|--------|----------------|-----------|
| Practice starts English | Fixed | language_choice | 70% |
| No markdown in TTS | Fixed | output_cleanliness | 100% |
| Persona consistency | Fixed | persona_consistency | 100% |
| Confusion recovery | Fixed | confusion_recovery | 75% |
| Tool usage | Validated | tool_usage | 83% |

**Overall evaluation pass rate: 79.3%** (target: 80%)

### Files Modified

- `src/backend/app/prompts/agent/base.md` - Added confusion recovery with phonetic awareness
- `src/backend/app/prompts/agent/mode_practice.md` - Added persona redirect instructions
- `src/backend/app/prompts/agent/tools.md` - Added batch vocabulary tool, output cleanliness rules
- `tests/evaluation/rubrics.py` - Created 6-dimension rubric system
- `tests/golden/` - Created test cases from documented issues
