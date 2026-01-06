# Backlog: Vocabulary Audio Quality (Phase 7E)

**Priority**: Medium
**Dependencies**: None
**Related**: Phase 7D vocab audio, TTS abstraction

## Problem

VibeVoice is optimized for sentences, not single-word pronunciations. Issues observed:

- Variable voice frequency as TTS tries to sound "organic"
- Some files have unexpected background music
- Some pronunciations are garbled or unclear
- Inconsistent quality across different words

## Potential Solutions

### 1. Settings fix
Find VibeVoice configuration to disable prosody variation

### 2. Prompt workaround
Add punctuation (e.g., "book." instead of "book") to signal complete utterance

### 3. Alternative TTS
Evaluate other TTS options for single-word pronunciation:
- Azure Neural TTS (cloud)
- Bark (local)
- Piper (local, lightweight)
- gpt-4o-mini-tts (cloud)

## Verification Pipeline (Future)

- Create STT script to transcribe generated vocab audio
- Compare transcription to expected pronunciation text
- Build agent to review mismatches and suggest regeneration
- Automated loop: generate → verify → flag issues → regenerate

## Example Problematic File

- `content/samples/vocab/noun-06-b37c25c1.wav`
- Input: "brother... brothers"
- Voice: speaker_b (Emma)
