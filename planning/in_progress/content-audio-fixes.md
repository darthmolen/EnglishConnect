# Content Audio Fixes

## Status: In Progress

## Prerequisites

1. Start TTS server: `/start-tts` or manually:
   ```bash
   cd src/services/tts-mcp && source .venv/bin/activate && python server.py --http
   ```

2. Activate backend venv:
   ```bash
   cd src/tools/demo-generator
   source ../../backend/.venv/bin/activate
   ```

---

## Issue 1: L15>P1>E3 - Garbled Answer

**Problem**: The answer audio for Lesson 15, Pattern 1, Example 3 is garbled.

**Fix**:
```bash
python regenerate_example.py --lesson 15 --pattern 1 --example 3 --student-voice speaker_b
```

Then flush cache:
```bash
redis-cli FLUSHALL
```

---

## Issue 2: Missing Audio Files (6 lessons)

Scan found examples in the database without corresponding audio files:

| Lesson | Pattern | Expected | Actual | Missing |
|--------|---------|----------|--------|---------|
| 3 | 1 | 2 | 1 | 1 |
| 4 | 1 | 2 | 1 | 1 |
| 9 | 2 | 2 | 1 | 1 |
| 11 | 1 | 3 | 2 | 1 |
| 13 | 1 | 2 | 1 | 1 |
| 17 | 2 | 3 | 2 | 1 |

**Fix**: Regenerate each affected lesson:
```bash
rm content/audio/ec1/demos/lesson-03/*
python generate_demos.py --lesson 3

rm content/audio/ec1/demos/lesson-04/*
python generate_demos.py --lesson 4

rm content/audio/ec1/demos/lesson-09/*
python generate_demos.py --lesson 9

rm content/audio/ec1/demos/lesson-11/*
python generate_demos.py --lesson 11

rm content/audio/ec1/demos/lesson-13/*
python generate_demos.py --lesson 13

rm content/audio/ec1/demos/lesson-17/*
python generate_demos.py --lesson 17
```

---

## Verification

After fixes, in the app:
1. Navigate to each lesson's Patterns section
2. Play all examples
3. Confirm audio matches displayed text and sounds correct

---

## Tools

- `generate_demos.py` - Regenerate all demos for a lesson
- `regenerate_example.py` - Regenerate single example with voice selection
- `/start-tts` - Start TTS server
- `/stop-tts` - Stop TTS server
