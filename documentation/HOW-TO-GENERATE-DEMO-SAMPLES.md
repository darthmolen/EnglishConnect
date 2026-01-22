# How to Generate Demo Audio Samples

This document explains how to generate the pre-recorded audio demos for lesson pattern examples.

## Overview

Demo audio files are pre-generated dialogues that demonstrate Q&A pattern examples. Each demo consists of:
- A **teacher** voice asking a question (speaker_d / Grace)
- A **student** voice answering (speaker_c / Davis)

Files are stored in `content/audio/ec1/demos/lesson-{number}/` with:
- `pattern-{N}-ex{M}-{hash}.wav` - The audio file
- `pattern-{N}-ex{M}-{hash}.json` - Metadata (dialogue text, duration, etc.)

## Prerequisites

1. **Database running** with lesson content loaded:
   ```bash
   docker compose up -d postgres
   ```

2. **TTS server running** in HTTP mode:
   ```bash
   cd src/services/tts-mcp
   source .venv/bin/activate
   python server.py --http
   ```

   Verify it's running:
   ```bash
   curl http://localhost:8002/health
   ```

3. **Backend venv** with dependencies:
   ```bash
   cd src/backend
   source .venv/bin/activate
   ```

## Usage

The demo generator script is at `src/tools/demo-generator/generate_demos.py`.

### Generate demos for a specific lesson

```bash
cd src/tools/demo-generator
source ../../backend/.venv/bin/activate
python generate_demos.py --lesson 15
```

### Generate a single demo (for testing)

```bash
python generate_demos.py --lesson 15 --single
```

### Generate demos for all lessons

```bash
python generate_demos.py --all
```

### Parallel generation (faster)

```bash
python generate_demos.py --lesson 15 --parallel 3
```

### Custom database or TTS URL

```bash
python generate_demos.py --lesson 15 \
  --database-url "postgresql+asyncpg://user:pass@host:5432/db" \
  --tts-url "http://localhost:8002"
```

## Regenerating Specific Lessons

If audio files are corrupted or out of sync with the database:

1. **Delete existing files** for that lesson:
   ```bash
   rm content/audio/ec1/demos/lesson-15/*
   ```

2. **Regenerate**:
   ```bash
   python generate_demos.py --lesson 15
   ```

## Regenerating Individual Examples

To regenerate a single example (without deleting the entire lesson):

```bash
cd src/tools/demo-generator
source ../../backend/.venv/bin/activate

# Regenerate lesson 15, pattern 1, example 3
python regenerate_example.py --lesson 15 --pattern 1 --example 3
```

### Using Different Voices

If an example sounds wrong (garbled, wrong tone), try a different voice:

```bash
# List available voices
python regenerate_example.py --list-voices

# Use speaker_b (Emma) for a more upbeat student voice
python regenerate_example.py --lesson 15 --pattern 1 --example 3 --student-voice speaker_b

# Change teacher voice too
python regenerate_example.py --lesson 15 --pattern 1 --example 3 --teacher-voice speaker_b --student-voice speaker_a
```

The script automatically deletes old files for that specific example before generating new ones.

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     PostgreSQL Database                      │
│                                                              │
│  lessons ──> qa_patterns ──> example_sentences               │
│                              (questions & answers)           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               generate_demos.py                              │
│                                                              │
│  1. Fetch examples for lesson                                │
│  2. Pair questions with answers                              │
│  3. Call TTS API for each line                               │
│  4. Concatenate with pauses                                  │
│  5. Save WAV + JSON metadata                                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              TTS Server (VibeVoice)                          │
│              http://localhost:8002                           │
│                                                              │
│  POST /synthesize                                            │
│  {"text": "...", "voice": "speaker_d"}                       │
│  Returns: {"audio_base64": "..."}                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           content/audio/ec1/demos/lesson-{N}/                │
│                                                              │
│  pattern-1-ex1-abc123.wav   pattern-1-ex1-abc123.json        │
│  pattern-1-ex2-def456.wav   pattern-1-ex2-def456.json        │
│  pattern-2-ex1-ghi789.wav   pattern-2-ex1-ghi789.json        │
└─────────────────────────────────────────────────────────────┘
```

## JSON Metadata Format

Each audio file has a sidecar JSON with this structure:

```json
{
  "lesson_number": 15,
  "pattern_number": 1,
  "example_index": 2,
  "dialogue": [
    {
      "speaker": "teacher",
      "voice": "speaker_d",
      "text": "What does he do for work?"
    },
    {
      "speaker": "student",
      "voice": "speaker_c",
      "text": "He sells computers."
    }
  ],
  "created_at": "2026-01-22T20:39:17.641206+00:00",
  "duration_seconds": 4.9,
  "audio_format": "wav",
  "sample_rate": 24000
}
```

## Troubleshooting

### "Cannot connect to TTS server"

Make sure the TTS server is running in HTTP mode:
```bash
cd src/services/tts-mcp
source .venv/bin/activate
python server.py --http
```

### "Lesson X not found"

The lesson doesn't exist in the database. Check:
```bash
docker compose exec postgres psql -U englishconnect -d englishconnect \
  -c "SELECT lesson_number, title FROM lessons WHERE course_id = 'ec1' ORDER BY lesson_number;"
```

### "No dialogues found"

The lesson has no Q&A patterns or example sentences. Check:
```bash
docker compose exec postgres psql -U englishconnect -d englishconnect -c "
SELECT l.lesson_number, p.pattern_number, e.sentence_type, e.english_text
FROM lessons l
JOIN qa_patterns p ON l.id = p.lesson_id
JOIN example_sentences e ON p.id = e.pattern_id
WHERE l.lesson_number = 15
ORDER BY p.pattern_number, e.sentence_type;"
```

### Audio doesn't match what's shown in the app

The audio files were generated before the database was updated. Delete and regenerate:
```bash
rm content/audio/ec1/demos/lesson-15/*
python generate_demos.py --lesson 15
```

## Voice Configuration

The script uses these voices (defined in `generate_demos.py`):

| Role | Voice ID | Name |
|------|----------|------|
| Teacher | speaker_d | Grace |
| Student | speaker_c | Davis |

To change voices, edit the constants at the top of `generate_demos.py`:
```python
TEACHER_VOICE = "speaker_d"  # Grace
STUDENT_VOICE = "speaker_c"  # Davis
```

Available voices: `speaker_a` through `speaker_f`
