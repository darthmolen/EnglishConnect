# Phase 7: Demo Generator

## Overview

Built a demo dialogue generator that creates pre-rendered 2-voice audio files from lesson Q&A patterns for marketing and documentation purposes.

## Completed

### Demo Generator Script

**File:** `src/tools/demo-generator/generate_demos.py`

CLI tool that:

- Fetches Q&A patterns from database (SQLAlchemy)
- Transforms patterns into teacher-student dialogue exchanges
- Calls TTS MCP to generate 2-voice audio
- Saves audio + metadata JSON sidecar files

**Usage:**

```bash
# Generate one demo from lesson 5
python src/tools/demo-generator/generate_demos.py --lesson 5 --single

# Generate all demos for a lesson
python src/tools/demo-generator/generate_demos.py --lesson 5

# Generate demos for all lessons
python src/tools/demo-generator/generate_demos.py --all
```

**Configuration:**

- Teacher voice: Grace (speaker_d)
- Student voice: Davis (speaker_c)
- Output: `content/audio/ec1/demos/`
- Format: 24kHz WAV

### Content MCP Audio Discovery Tools

**File:** `src/services/content-mcp/server.py`

Added two new MCP tools:

- `list_demo_audio(course_id, lesson_number)` - Lists available demo audio with metadata
- `get_demo_audio(audio_path)` - Returns audio as base64

### Backend Audio Streaming Endpoint

**File:** `src/backend/app/routers/audio.py`

REST API for audio access:

- `GET /api/audio/demos/{course_id}?lesson_number=N` - List demos with stream URLs
- `GET /api/audio/stream/{path}` - Stream audio file

### Generated Content

- 19 demo audio files generated (5.3MB total)
- Covers lessons: 5, 8, 9, 14, 16, 17, 22, 23

## Known Issues

**Missing Example Sentences:**
Lessons 1-4, 6-7, 10-13, 15, 18-21, 24-25 have no example sentences in the database. Their Q&A patterns were not extracted with concrete examples during content ingestion. This should be addressed by improving the content ingestion regex patterns or manually adding examples.

**Parallel Generation:**
The `--parallel` flag causes TTS server 500 errors due to GPU mutex contention. Sequential generation (`--parallel 1`, the default) works reliably.

## File Structure

```text
content/audio/ec1/demos/
  lesson-05/
    pattern-1-ex1-*.wav + .json
    pattern-1-ex2-*.wav + .json
    pattern-1-ex3-*.wav + .json
  lesson-08/
    ...
```

## Dependencies Added

- `soundfile` - Added to backend venv for WAV concatenation
