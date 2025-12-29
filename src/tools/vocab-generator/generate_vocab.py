#!/usr/bin/env python3
"""Vocabulary audio generator for EnglishConnect.

Reads vocabulary items from database, generates bilingual pronunciation audio
using Piper TTS, and saves to content/audio/ec1/vocab/.

Usage:
    # Ensure Piper venv is activated:
    # source src/services/piper/.venv/bin/activate

    # Generate vocab audio for one lesson
    python generate_vocab.py --lesson 5

    # Generate vocab audio for all lessons
    python generate_vocab.py --all

    # Dry run (preview without generating)
    python generate_vocab.py --lesson 5 --dry-run
"""

import argparse
import asyncio
import io
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import soundfile as sf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add parent paths for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "piper"))

from app.database import Base
from app.models.content import Lesson, VocabularyItem
from service import PiperService


# Configuration
OUTPUT_BASE = Path(__file__).parent.parent.parent.parent / "content" / "audio" / "ec1" / "vocab"
DATABASE_URL = "postgresql+asyncpg://englishconnect:devpassword@localhost:5432/englishconnect"
INTRA_PAUSE = 0.5  # Pause between singular/plural forms
INTER_PAUSE = 0.8  # Pause between English and Spanish
SAMPLE_RATE = 24000


def split_forms(word: str) -> list[str]:
    """Split word into separate forms for pronunciation.

    Handles slash notation for plurals and removes parentheticals:
    - "book/books" -> ["book", "books"]
    - "child/children" -> ["child", "children"]
    - "go to the beach" -> ["go to the beach"]
    - "father (dad)" -> ["father"]

    Args:
        word: Word/phrase from database

    Returns:
        List of forms to pronounce
    """
    text = word.strip()

    # Remove parenthetical alternatives like "father (dad)"
    text = re.sub(r'\s*\([^)]+\)\s*', ' ', text).strip()

    # Handle slash notation for singular/plural
    if '/' in text:
        return [p.strip() for p in text.split('/') if p.strip()]

    return [text] if text else []


def calculate_duration(audio_bytes: bytes) -> float:
    """Calculate audio duration in seconds."""
    buffer = io.BytesIO(audio_bytes)
    audio_data, sample_rate = sf.read(buffer)
    return len(audio_data) / sample_rate


async def fetch_lesson_vocabulary(
    session: AsyncSession, lesson_number: int
) -> tuple[Lesson | None, list[VocabularyItem]]:
    """Fetch vocabulary items for a lesson.

    Returns:
        Tuple of (lesson, vocabulary_items)
    """
    # Get lesson
    stmt = select(Lesson).where(
        Lesson.course_id == "ec1", Lesson.lesson_number == lesson_number
    )
    result = await session.execute(stmt)
    lesson = result.scalar_one_or_none()

    if not lesson:
        return None, []

    # Get vocabulary items
    stmt = (
        select(VocabularyItem)
        .where(VocabularyItem.lesson_id == lesson.id)
        .order_by(VocabularyItem.category, VocabularyItem.id)
    )
    result = await session.execute(stmt)
    vocab_items = list(result.scalars().all())

    return lesson, vocab_items


def generate_filename(category: str, index: int) -> str:
    """Generate unique filename for vocab audio.

    Format: {category}-{index:02d}-{uuid}.wav
    Example: nouns-01-a1b2c3d4.wav
    """
    # Sanitize category for filename
    safe_category = re.sub(r'[^a-z0-9]', '-', (category or 'uncategorized').lower())
    safe_category = re.sub(r'-+', '-', safe_category).strip('-')

    unique_id = str(uuid.uuid4())[:8]
    return f"{safe_category}-{index:02d}-{unique_id}"


def generate_vocab_audio(
    piper: PiperService,
    lesson_number: int,
    vocab: VocabularyItem,
    index: int,
    dry_run: bool = False,
) -> Path | None:
    """Generate bilingual audio for a single vocabulary item.

    Args:
        piper: PiperService instance
        lesson_number: Lesson number
        vocab: Vocabulary item from database
        index: Index within category (for filename)
        dry_run: If True, don't actually generate

    Returns:
        Path to generated audio file, or None on error/dry-run
    """
    english_parts = split_forms(vocab.english_word)
    spanish_parts = split_forms(vocab.spanish_translation or "")

    print(f"  [{vocab.category or 'uncategorized'}] {vocab.english_word}")
    print(f"    → EN: {english_parts}")
    print(f"    → ES: {spanish_parts}")

    if dry_run:
        return None

    try:
        # Generate bilingual audio
        audio_bytes = piper.synthesize_vocabulary(
            english_parts=english_parts,
            spanish_parts=spanish_parts,
            intra_pause=INTRA_PAUSE,
            inter_pause=INTER_PAUSE,
            sample_rate=SAMPLE_RATE,
        )
        duration = calculate_duration(audio_bytes)

        # Prepare output paths
        output_dir = OUTPUT_BASE / f"lesson-{lesson_number:02d}"
        output_dir.mkdir(parents=True, exist_ok=True)

        base_filename = generate_filename(vocab.category, index)
        audio_path = output_dir / f"{base_filename}.wav"
        meta_path = output_dir / f"{base_filename}.json"

        # Save audio
        audio_path.write_bytes(audio_bytes)

        # Save metadata
        voices = piper.get_voice_info()
        metadata = {
            "lesson_number": lesson_number,
            "english_word": vocab.english_word,
            "spanish_translation": vocab.spanish_translation,
            "category": vocab.category,
            "english_parts": english_parts,
            "spanish_parts": spanish_parts,
            "format": "bilingual",
            "voices": voices,
            "intra_pause": INTRA_PAUSE,
            "inter_pause": INTER_PAUSE,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(duration, 2),
            "audio_format": "wav",
            "sample_rate": SAMPLE_RATE,
        }
        meta_path.write_text(json.dumps(metadata, indent=2))

        print(f"    ✓ Saved: {audio_path.name} ({duration:.1f}s)")
        return audio_path

    except Exception as e:
        print(f"    ✗ Error: {e}")
        return None


async def generate_vocab_for_lesson(
    session: AsyncSession,
    piper: PiperService,
    lesson_number: int,
    dry_run: bool = False,
) -> list[Path]:
    """Generate vocabulary audio for a lesson.

    Args:
        session: Database session
        piper: PiperService instance
        lesson_number: Lesson number
        dry_run: If True, preview without generating

    Returns:
        List of generated audio file paths
    """
    lesson, vocab_items = await fetch_lesson_vocabulary(session, lesson_number)

    if not lesson:
        print(f"Lesson {lesson_number} not found")
        return []

    print(f"Found lesson {lesson_number}: {lesson.title}")

    if not vocab_items:
        print(f"No vocabulary items found for lesson {lesson_number}")
        return []

    print(f"Found {len(vocab_items)} vocabulary item(s)")

    if dry_run:
        print("DRY RUN - no audio will be generated\n")

    # Track index per category for filenames
    category_indices: dict[str, int] = {}
    generated: list[Path] = []

    for vocab in vocab_items:
        category = vocab.category or 'uncategorized'
        category_indices[category] = category_indices.get(category, 0) + 1
        index = category_indices[category]

        path = generate_vocab_audio(piper, lesson_number, vocab, index, dry_run)
        if path:
            generated.append(path)

    return generated


async def main():
    parser = argparse.ArgumentParser(description="Generate bilingual vocabulary audio files")
    parser.add_argument("--lesson", type=int, help="Lesson number to generate for")
    parser.add_argument("--all", action="store_true", help="Generate for all lessons")
    parser.add_argument("--dry-run", action="store_true", help="Preview without generating")
    parser.add_argument(
        "--database-url",
        default=DATABASE_URL,
        help="Database URL",
    )
    args = parser.parse_args()

    if not args.lesson and not args.all:
        parser.error("Either --lesson or --all is required")

    # Initialize Piper service
    piper = PiperService()
    available_langs = piper.get_available_languages()

    if not args.dry_run:
        if not available_langs:
            print("Error: No Piper voice models found")
            print("Download models with:")
            print("  cd src/services/piper/models")
            print("  wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx")
            print("  wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json")
            print("  wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx")
            print("  wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx.json")
            return

        if "en" not in available_langs or "es" not in available_langs:
            print(f"Error: Need both English and Spanish voices. Have: {available_langs}")
            return

        print(f"Piper TTS ready: {piper.get_voice_info()}")
    else:
        print("DRY RUN - Piper voice check skipped")

    print(f"Output: {OUTPUT_BASE}/")
    print()

    # Create engine and session
    engine = create_async_engine(args.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        if args.all:
            # Get all lesson numbers
            stmt = (
                select(Lesson.lesson_number)
                .where(Lesson.course_id == "ec1")
                .order_by(Lesson.lesson_number)
            )
            result = await session.execute(stmt)
            lesson_numbers = [row[0] for row in result.all()]

            print(f"Generating vocab for {len(lesson_numbers)} lessons...")

            total_generated = []
            for lesson_num in lesson_numbers:
                print(f"\n{'=' * 60}")
                print(f"Lesson {lesson_num}")
                print(f"{'=' * 60}")
                generated = await generate_vocab_for_lesson(
                    session, piper, lesson_num, args.dry_run
                )
                total_generated.extend(generated)

            print(f"\n\nTotal generated: {len(total_generated)} audio files")
        else:
            generated = await generate_vocab_for_lesson(
                session, piper, args.lesson, args.dry_run
            )
            if not args.dry_run:
                print(f"\nGenerated: {len(generated)} audio files")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
