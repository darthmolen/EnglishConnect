"""Audio router for streaming demo audio files."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/audio", tags=["audio"])

# Path to audio content
# In container: /app/content/audio
# In development: relative to source tree
_dev_audio_path = Path(__file__).parent.parent.parent.parent.parent / "content" / "audio"
AUDIO_BASE = _dev_audio_path if _dev_audio_path.exists() else Path("/app/content/audio")


class DemoMetadata(BaseModel):
    """Demo audio metadata."""

    lesson_number: int
    pattern_number: int
    example_index: int
    dialogue: list[dict]
    created_at: str
    duration_seconds: float
    audio_format: str
    sample_rate: int
    audio_path: str
    stream_url: str


class VocabAudioMetadata(BaseModel):
    """Vocabulary audio metadata."""

    lesson_number: int
    english_word: str
    spanish_translation: str
    category: str | None
    pronunciation_text: str
    voice: str
    created_at: str
    duration_seconds: float
    audio_format: str
    sample_rate: int
    stream_url: str


@router.get("/demos/{course_id}")
async def list_demos(
    course_id: str,
    lesson_number: int | None = Query(None, description="Filter by lesson number"),
) -> list[dict]:
    """List available demo audio files.

    Args:
        course_id: Course identifier (e.g., 'ec1')
        lesson_number: Optional filter by lesson number

    Returns:
        List of demo metadata with stream URLs
    """
    import glob

    demos_dir = AUDIO_BASE / course_id / "demos"
    if not demos_dir.exists():
        return []

    if lesson_number:
        pattern = str(demos_dir / f"lesson-{lesson_number:02d}" / "*.json")
    else:
        pattern = str(demos_dir / "lesson-*" / "*.json")

    demos = []
    for meta_path in glob.glob(pattern):
        try:
            with open(meta_path) as f:
                meta = json.load(f)

            # Add streaming URL
            audio_path = Path(meta_path).with_suffix(".wav")
            relative_path = audio_path.relative_to(AUDIO_BASE)
            meta["stream_url"] = f"/api/audio/stream/{relative_path}"
            meta["audio_path"] = str(audio_path)
            demos.append(meta)
        except Exception:
            continue

    # Sort by lesson_number, pattern_number, example_index
    demos.sort(key=lambda d: (
        d.get("lesson_number", 0),
        d.get("pattern_number", 0),
        d.get("example_index", 0),
    ))

    return demos


@router.get("/vocab/{course_id}")
async def list_vocab_audio(
    course_id: str,
    lesson_number: int = Query(..., description="Lesson number"),
) -> list[dict]:
    """List available vocabulary audio files for a lesson.

    Args:
        course_id: Course identifier (e.g., 'ec1')
        lesson_number: Lesson number (required)

    Returns:
        List of vocabulary audio metadata with stream URLs
    """
    import glob

    vocab_dir = AUDIO_BASE / course_id / "vocab" / f"lesson-{lesson_number:02d}"
    if not vocab_dir.exists():
        return []

    pattern = str(vocab_dir / "*.json")

    vocab_items = []
    for meta_path in glob.glob(pattern):
        try:
            with open(meta_path) as f:
                meta = json.load(f)

            # Add streaming URL
            audio_path = Path(meta_path).with_suffix(".wav")
            relative_path = audio_path.relative_to(AUDIO_BASE)
            meta["stream_url"] = f"/api/audio/stream/{relative_path}"
            vocab_items.append(meta)
        except Exception:
            continue

    # Sort by category, then by filename (which has index)
    vocab_items.sort(key=lambda v: (
        v.get("category") or "zzz",  # Put uncategorized last
        v.get("english_word", ""),
    ))

    return vocab_items


@router.get("/intros/{course_id}")
async def get_intro(
    course_id: str,
    lesson_number: int = Query(..., description="Lesson number"),
    language: str = Query("es", description="Language for intro: 'en' or 'es'"),
    page_type: str = Query("practice", description="Page type: 'practice' or 'vocabulary'"),
) -> dict:
    """Get intro audio URL for a lesson page in the specified language.

    Args:
        course_id: Course identifier (e.g., 'ec1')
        lesson_number: Lesson number (required)
        language: Language for intro ('en' or 'es', default 'es')
        page_type: Page type ('practice' or 'vocabulary', default 'practice')

    Returns:
        Dict with stream_url if intro exists, or empty dict
    """
    # Validate inputs
    lang = language if language in ("en", "es") else "es"
    page = page_type if page_type in ("practice", "vocabulary") else "practice"

    intro_path = AUDIO_BASE / course_id / "intros" / page / f"lesson-{lesson_number:02d}-{lang}.wav"
    if not intro_path.exists():
        return {}

    relative_path = intro_path.relative_to(AUDIO_BASE)
    return {
        "lesson_number": lesson_number,
        "language": lang,
        "page_type": page,
        "stream_url": f"/api/audio/stream/{relative_path}",
    }


@router.get("/stream/{file_path:path}")
async def stream_audio(file_path: str) -> FileResponse:
    """Stream an audio file.

    Args:
        file_path: Path relative to audio base directory

    Returns:
        Audio file stream with appropriate headers
    """
    # Security: Validate path
    if ".." in file_path:
        raise HTTPException(status_code=400, detail="Invalid path")

    audio_path = AUDIO_BASE / file_path
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    # Validate file is within audio directory
    try:
        audio_path.resolve().relative_to(AUDIO_BASE.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")

    return FileResponse(
        audio_path,
        media_type="audio/wav",
        headers={"Accept-Ranges": "bytes"},
    )
