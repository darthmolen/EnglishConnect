# Content Ingestion Pipeline

Hub document for the full content pipeline: **PDF → Markdown → Chunk → Translate → Normalize → Audit → Ingest → Audio**.

## Pipeline Overview

```
content/raw/{course}/            # Source PDFs
        │
        ▼  [Marker MCP]
content/refined/{course}/books/{book}/  # Full markdown + images
        │
        ▼  [chunk_by_lesson.py]
content/refined/{course}/books/{book}/lessons/  # Per-lesson markdown
        │
        ▼  [translate_patterns.py]  (needs vLLM)
        ▼  [normalize_lessons.py]
        ▼  [audit_lessons.py]
        │
        ▼  [content_ingestion.py]  (needs PostgreSQL)
      PostgreSQL (lessons, vocabulary, patterns, examples, criteria)
        │
        ├──▶ [generate_vocab.py]    (needs Piper)     → content/audio/{course}/vocab/
        ├──▶ [generate_demos.py]    (needs VibeVoice)  → content/audio/{course}/demos/
        └──▶ [generate_intros.py]   (needs both)       → content/audio/{course}/intros/
```

## Courses

| Course ID | Source PDF | Lessons | Status |
|-----------|-----------|---------|--------|
| `ec1` | `content/raw/ec1/englishconnect_1_para_los_alumnos.pdf` | 25 | Ingested |
| `ec2` | `content/raw/ec2/englishconnect_2_for_learners.pdf` | 20 | Ingested |

## Prerequisites

| Service | How to start | When needed |
|---------|-------------|-------------|
| PostgreSQL | `./start.sh infra` or `docker compose up -d` | Ingestion + audio gen |
| Marker venv | `source src/tools/marker_mcp/venv/bin/activate` | PDF conversion |
| Backend venv | `source src/backend/.venv/bin/activate` | All tools |
| vLLM (Qwen) | `./start.sh llm` | `translate_patterns.py` only |
| VibeVoice TTS | VS Code: "TTS VibeVoice (HTTP)" debug config | Demo + intro audio |
| Piper TTS | Library import (no server needed) | Vocab + intro audio |

## Step-by-Step Quick Reference

All commands assume you're in the project root. Replace `{course}` with `ec1`, `ec2`, etc.

### 1. Convert PDF → Markdown

```bash
source src/tools/marker_mcp/venv/bin/activate
python -c "
from src.tools.marker_mcp.server import convert_pdf
print(convert_pdf(
    'content/raw/{course}/YOUR_PDF.pdf',
    'content/refined/{course}/books/BOOK_NAME'
))
"
```

### 2. Chunk into lessons

```bash
python src/tools/chunk_by_lesson.py \
  content/refined/{course}/books/BOOK_NAME/OUTPUT.md \
  content/refined/{course}/books/BOOK_NAME/lessons
```

### 3. Translate patterns (needs vLLM running)

```bash
python src/tools/translate_patterns.py \
  --lessons-dir content/refined/{course}/books/BOOK_NAME/lessons
```

### 4. Normalize headers

```bash
python src/tools/normalize_lessons.py \
  --lessons-dir content/refined/{course}/books/BOOK_NAME/lessons
```

### 5. Audit

```bash
python src/tools/audit_lessons.py \
  --lessons-dir content/refined/{course}/books/BOOK_NAME/lessons
```

### 6. Ingest into database

```bash
src/backend/.venv/bin/python src/tools/content_ingestion.py \
  --course {course} \
  --course-name "EnglishConnect N" \
  --lessons-dir content/refined/{course}/books/BOOK_NAME/lessons
```

### 7. Generate audio

```bash
# Vocabulary audio (Piper — CPU only, no server needed)
python src/tools/vocab-generator/generate_vocab.py --course {course} --all

# Demo dialogues (VibeVoice — needs TTS server on port 8002)
python src/tools/demo-generator/generate_demos.py --course {course} --all

# Intro audio (both VibeVoice + Piper)
python src/tools/generate_intros.py --course {course}
```

## Tool Reference

| Tool | Path | Purpose | Inputs | Outputs |
|------|------|---------|--------|---------|
| Marker MCP | `src/tools/marker_mcp/server.py` | PDF → Markdown | PDF file | `.md` + images |
| Chunk | `src/tools/chunk_by_lesson.py` | Split full markdown into per-lesson files | Full `.md` | `lessons/lesson-NN.md` |
| Translate | `src/tools/translate_patterns.py` | Add Spanish translations to Q/A patterns | Lesson dir | Updates `.md` in place |
| Normalize | `src/tools/normalize_lessons.py` | Standardize headers and formatting | Lesson dir | Updates `.md` in place |
| Audit | `src/tools/audit_lessons.py` | Validate required sections exist | Lesson dir | Console report |
| Ingest | `src/tools/content_ingestion.py` | Parse markdown → PostgreSQL | Lesson dir + course ID | DB rows |
| Vocab audio | `src/tools/vocab-generator/generate_vocab.py` | Generate pronunciation audio | DB + Piper | `.wav` files |
| Demo audio | `src/tools/demo-generator/generate_demos.py` | Generate dialogue demos | DB + VibeVoice | `.wav` + `.json` |
| Regen example | `src/tools/demo-generator/regenerate_example.py` | Regenerate a single demo | Lesson/pattern/example | `.wav` + `.json` |
| Intro audio | `src/tools/generate_intros.py` | Generate lesson intro audio | DB + both TTS | `.wav` files |
| Voice samples | `src/tools/generate_voice_samples.py` | Generate TTS voice samples | VibeVoice | `.wav` files |

## Related Documentation

- [HOW-TO-GENERATE-DEMO-SAMPLES.md](HOW-TO-GENERATE-DEMO-SAMPLES.md) — Detailed demo audio generation guide (voices, regeneration, data flow, troubleshooting)
- [LOCAL-TTS-VOICES.md](LOCAL-TTS-VOICES.md) — VibeVoice setup, available voices, configuration

## Verification

After ingestion, verify data:

```bash
# Check lesson counts by course
docker compose exec postgres psql -U englishconnect -d englishconnect \
  -c "SELECT course_id, COUNT(*) FROM lessons GROUP BY course_id"

# Check a specific lesson's content
docker compose exec postgres psql -U englishconnect -d englishconnect -c "
SELECT l.lesson_number, l.title,
  (SELECT COUNT(*) FROM vocabulary_items v WHERE v.lesson_id = l.id) AS vocab,
  (SELECT COUNT(*) FROM qa_patterns p WHERE p.lesson_id = l.id) AS patterns
FROM lessons l WHERE l.course_id = '{course}'
ORDER BY l.lesson_number;"
```

## Adding a New Course

1. Place source PDF in `content/raw/{new_course}/`
2. Run steps 1–7 above
3. If the new course has different markdown structure (header levels, table formats), update regex in:
   - `content_ingestion.py` — `LessonParser` patterns
   - `normalize_lessons.py` — `CATEGORY_PATTERNS`
   - `audit_lessons.py` — `SECTION_PATTERNS`
4. Add the new course to `start.sh` → `ingest_content()` for auto-ingestion
5. Verify with the SQL queries above

## Known Gotchas

- **Marker `<br>` artifacts**: Marker sometimes concatenates multi-row table cells with `<br>` tags. `content_ingestion.py` has `_expand_br_cells()` to handle this.
- **Inconsistent header levels**: EC1 uses `##`, EC2 uses `#`–`####`. All regex uses `#{1,4}` to handle both.
- **EC2 lesson numbering gaps**: EC2 skips lessons 6, 10, 14, 18, 22 (unit boundaries). 20 actual lesson files.
- **Marker OOM**: Large PDFs may exhaust GPU memory. Close other GPU processes or reduce batch size.
- **Missing translations**: `translate_patterns.py` requires vLLM running. If patterns have no `Q_es:`/`A_es:` lines, the LLM service was likely unavailable.
