#!/usr/bin/env python3
"""Vocabulary audio generator for EnglishConnect.

Reads vocabulary items from database, generates pronunciation audio
using TTS HTTP API, and saves to content/audio/ec1/vocab/.

Usage:
    # Ensure TTS server is running in HTTP mode:
    # cd src/services/tts-mcp && source .venv/bin/activate && python server.py --http

    # Generate vocab audio for one lesson
    python generate_vocab.py --lesson 5

    # Generate vocab audio for all lessons
    python generate_vocab.py --all

    # Dry run (preview without generating)
    python generate_vocab.py --lesson 5 --dry-run
"""

import argparse
import asyncio
import base64
import io
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import soundfile as sf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add parent paths for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.database import Base
from app.models.content import Lesson, VocabularyItem


# Configuration
VOICE = "speaker_b"  # Emma - clear, slower diction for vocabulary
OUTPUT_BASE = Path(__file__).parent.parent.parent.parent / "content" / "audio" / "ec1" / "vocab"
TTS_HTTP_URL = "http://localhost:8002"
DATABASE_URL = "postgresql+asyncpg://englishconnect:devpassword@localhost:5432/englishconnect"
PAUSE_SECONDS = 0.7  # Pause between singular and plural forms
SAMPLE_RATE = 24000


def parse_pronunciation_text(english_word: str) -> str:
    """Convert English word to pronunciation text.

    Handles slash notation for plurals:
    - "book/books" -> "book... books"
    - "child/children" -> "child... children"
    - "go to the beach" -> "go to the beach" (unchanged)
    - "father (dad)" -> "father" (parenthetical removed)

    Args:
        english_word: English word/phrase from database

    Returns:
        Text suitable for TTS pronunciation
    """
    text = english_word.strip()

    # Remove parenthetical alternatives like "father (dad)"
    text = re.sub(r'\s*\([^)]+\)\s*', ' ', text).strip()

    # Handle slash notation for singular/plural
    if '/' in text:
        parts = [p.strip() for p in text.split('/')]
        # Join with pause indicator (TTS will pause on "...")
        return '... '.join(parts)

    return text


def concatenate_wav_bytes(audio_segments: list[bytes], pause_seconds: float = 0.7) -> bytes:
    """Concatenate WAV audio bytes with pauses between segments.

    Args:
        audio_segments: List of WAV audio bytes
        pause_seconds: Pause duration between segments

    Returns:
        Combined WAV audio bytes
    """
    if not audio_segments:
        return b""

    if len(audio_segments) == 1:
        return audio_segments[0]

    import numpy as np

    pause_samples = int(SAMPLE_RATE * pause_seconds)
    all_segments = []

    for i, wav_bytes in enumerate(audio_segments):
        buffer = io.BytesIO(wav_bytes)
        audio_data, _ = sf.read(buffer)
        all_segments.append(audio_data)

        if i < len(audio_segments) - 1:
            all_segments.append(np.zeros(pause_samples, dtype=np.float32))

    combined_audio = np.concatenate(all_segments)

    output_io = io.BytesIO()
    sf.write(output_io, combined_audio, SAMPLE_RATE, format="WAV")
    output_io.seek(0)
    return output_io.read()


async def synthesize_text(client: httpx.AsyncClient, tts_url: str, text: str) -> bytes:
    """Call TTS HTTP API to synthesize text.

    Args:
        client: HTTP client
        tts_url: TTS server URL
        text: Text to synthesize

    Returns:
        WAV audio bytes
    """
    response = await client.post(
        f"{tts_url}/synthesize",
        json={"text": text, "voice": VOICE},
        timeout=60.0,
    )
    response.raise_for_status()

    data = response.json()
    audio_b64 = data["audio_base64"]
    return base64.b64decode(audio_b64)


def calculate_duration(audio_bytes: bytes) -> float:
    """Calculate audio duration in seconds."""
    buffer = io.BytesIO(audio_bytes)
    audio_data, sample_rate = sf.read(buffer)
    return len(audio_data) / sample_rate


async def fetch_lesson_vocabulary(session: AsyncSession, lesson_number: int) -> tuple[Lesson | None, list[VocabularyItem]]:
    """Fetch vocabulary items for a lesson.

    Returns:
        Tuple of (lesson, vocabulary_items)
    """
    # Get lesson
    stmt = select(Lesson).where(
        Lesson.course_id == "ec1",
        Lesson.lesson_number == lesson_number
    )
    result = await session.execute(stmt)
    lesson = result.scalar_one_or_none()

    if not lesson:
        return None, []

    # Get vocabulary items
    stmt = select(VocabularyItem).where(
        VocabularyItem.lesson_id == lesson.id
    ).order_by(VocabularyItem.category, VocabularyItem.id)
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


async def generate_vocab_audio(
    client: httpx.AsyncClient,
    tts_url: str,
    lesson_number: int,
    vocab: VocabularyItem,
    index: int,
    dry_run: bool = False,
) -> Path | None:
    """Generate audio for a single vocabulary item.

    Args:
        client: HTTP client
        tts_url: TTS server URL
        lesson_number: Lesson number
        vocab: Vocabulary item from database
        index: Index within category (for filename)
        dry_run: If True, don't actually generate

    Returns:
        Path to generated audio file, or None on error/dry-run
    """
    pronunciation_text = parse_pronunciation_text(vocab.english_word)

    print(f"  [{vocab.category or 'uncategorized'}] {vocab.english_word}")
    print(f"    → Pronunciation: \"{pronunciation_text}\"")

    if dry_run:
        return None

    try:
        # Generate audio
        audio_bytes = await synthesize_text(client, tts_url, pronunciation_text)
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
        metadata = {
            "lesson_number": lesson_number,
            "english_word": vocab.english_word,
            "spanish_translation": vocab.spanish_translation,
            "category": vocab.category,
            "pronunciation_text": pronunciation_text,
            "voice": VOICE,
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
    client: httpx.AsyncClient,
    tts_url: str,
    lesson_number: int,
    dry_run: bool = False,
) -> list[Path]:
    """Generate vocabulary audio for a lesson.

    Args:
        session: Database session
        client: HTTP client
        tts_url: TTS server URL
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

        path = await generate_vocab_audio(
            client, tts_url, lesson_number, vocab, index, dry_run
        )
        if path:
            generated.append(path)

    return generated


async def main():
    parser = argparse.ArgumentParser(description="Generate vocabulary audio files")
    parser.add_argument("--lesson", type=int, help="Lesson number to generate for")
    parser.add_argument("--all", action="store_true", help="Generate for all lessons")
    parser.add_argument("--dry-run", action="store_true", help="Preview without generating")
    parser.add_argument(
        "--database-url",
        default=DATABASE_URL,
        help="Database URL",
    )
    parser.add_argument(
        "--tts-url",
        default=TTS_HTTP_URL,
        help="TTS HTTP server URL",
    )
    args = parser.parse_args()

    if not args.lesson and not args.all:
        parser.error("Either --lesson or --all is required")

    # Create engine and session
    engine = create_async_engine(args.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Create HTTP client for TTS
    async with httpx.AsyncClient() as client:
        # Test TTS connection (skip for dry run)
        if not args.dry_run:
            try:
                response = await client.get(f"{args.tts_url}/health", timeout=5.0)
                response.raise_for_status()
                print(f"TTS server connected: {args.tts_url}")
            except Exception as e:
                print(f"Error: Cannot connect to TTS server at {args.tts_url}")
                print(f"Start it with: cd src/services/tts-mcp && python server.py --http")
                print(f"Error details: {e}")
                return

        print(f"Voice: {VOICE} (Emma)")
        print(f"Output: {OUTPUT_BASE}/")
        print()

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
                    print(f"\n{'='*60}")
                    print(f"Lesson {lesson_num}")
                    print(f"{'='*60}")
                    generated = await generate_vocab_for_lesson(
                        session, client, args.tts_url, lesson_num, args.dry_run
                    )
                    total_generated.extend(generated)

                print(f"\n\nTotal generated: {len(total_generated)} audio files")
            else:
                generated = await generate_vocab_for_lesson(
                    session, client, args.tts_url, args.lesson, args.dry_run
                )
                if not args.dry_run:
                    print(f"\nGenerated: {len(generated)} audio files")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
