# Phase 7D: Vocabulary Audio

## Overview

Built vocabulary audio generation system: CLI tool to generate WAV files for all vocabulary items, API endpoint to serve them, and UI play buttons for ad-hoc playback.

**Business Value:** Students can play vocabulary pronunciation ad hoc, and the teacher agent can use MCP tool to play vocabulary during practice sessions.

## Completed

### Vocabulary Audio Generator Script

**File:** `src/tools/vocab-generator/generate_vocab.py`

CLI tool that:

- Fetches vocabulary from database (VocabularyItem model)
- Parses slash notation (e.g., "book/books" → "book... books")
- Removes parenthetical alternatives (e.g., "father (dad)" → "father")
- Calls TTS HTTP API sequentially (to avoid 500 errors)
- Saves WAV + JSON metadata sidecar files

**Usage:**

```bash
# Generate vocab audio for one lesson
python src/tools/vocab-generator/generate_vocab.py --lesson 5

# Generate vocab audio for all lessons
python src/tools/vocab-generator/generate_vocab.py --all

# Dry run (preview without generating)
python src/tools/vocab-generator/generate_vocab.py --lesson 5 --dry-run
```

**Configuration:**

- Voice: Emma (speaker_b) - clear, slower diction ideal for vocabulary
- Output: `content/audio/ec1/vocab/`
- Format: 24kHz WAV

### API Endpoint for Vocabulary Audio

**File:** `src/backend/app/routers/audio.py`

- `GET /api/audio/vocab/{course_id}?lesson_number=N` - List vocab audio with stream URLs
- Uses existing `/api/audio/stream/{file_path}` for streaming

### UI Play Button

**File:** `src/frontend/src/components/content/VocabularyView.tsx`

- Added play/pause button next to each vocabulary item
- Follows PatternsView pattern for audio playback
- Single audio element, toggle playback
- Button appears only when audio is available for the word

### Voice Samples

**Directory:** `content/samples/voices/`

Generated voice samples for all 6 VibeVoice voices to help choose the best voice for vocabulary:

- speaker_a_carter.wav (Carter - male, professional)
- speaker_b_emma.wav (Emma - female, warm) ← Selected for vocabulary
- speaker_c_davis.wav (Davis - male, conversational)
- speaker_d_grace.wav (Grace - female, articulate)
- speaker_e_frank.wav (Frank - male, authoritative)
- speaker_f_mike.wav (Mike - male, casual)

### Generated Content

- 487 vocabulary audio files generated (60MB total)
- Covers all 25 lessons (1-25)

## File Structure

```text
content/audio/ec1/vocab/
  lesson-01/
    adverb-01-*.wav + .json
    noun-01-*.wav + .json
    phrase-01-*.wav + .json
    pronoun-01-*.wav + .json
  lesson-02/
    ...
  lesson-25/
    ...
```

## Files Created/Modified

| File | Action |
|------|--------|
| `src/tools/vocab-generator/generate_vocab.py` | Created |
| `src/tools/generate_voice_samples.py` | Created |
| `src/backend/app/routers/audio.py` | Modified (added vocab endpoints) |
| `src/frontend/src/components/content/VocabularyView.tsx` | Modified (added play buttons) |
| `src/frontend/src/components/ContentWindow.tsx` | Modified (pass lessonNumber prop) |
