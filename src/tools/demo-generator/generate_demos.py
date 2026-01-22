#!/usr/bin/env python3
"""Demo dialogue generator for EnglishConnect.

Reads lesson Q&A patterns from database, generates 2-voice dialogues
using TTS MCP HTTP API, and saves to content/audio/ec1/demos/.

Usage:
    # Ensure TTS server is running in HTTP mode:
    # cd src/services/tts-mcp && source .venv/bin/activate && python server.py --http

    # Generate one demo from lesson 5
    python generate_demos.py --lesson 5 --single

    # Generate all demos for lesson 5
    python generate_demos.py --lesson 5

    # Generate demos for all lessons
    python generate_demos.py --all
"""

import argparse
import asyncio
import base64
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np
import soundfile as sf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

# Add parent paths for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.database import Base
from app.models.content import Lesson, QAPattern, ExampleSentence


# Configuration
TEACHER_VOICE = "speaker_d"  # Grace
STUDENT_VOICE = "speaker_c"  # Davis
OUTPUT_BASE = Path(__file__).parent.parent.parent.parent / "content" / "audio" / "ec1" / "demos"
TTS_HTTP_URL = "http://localhost:8002"
DATABASE_URL = "postgresql+asyncpg://englishconnect:devpassword@localhost:5432/englishconnect"
PAUSE_SECONDS = 0.5
SAMPLE_RATE = 24000


def concatenate_wav_bytes(audio_segments: list[bytes], pause_seconds: float = 0.5) -> bytes:
    """Concatenate WAV audio bytes with pauses between segments.

    Uses soundfile to handle float32 WAV format from TTS server.

    Args:
        audio_segments: List of WAV audio bytes
        pause_seconds: Pause duration between segments

    Returns:
        Combined WAV audio bytes
    """
    if not audio_segments:
        return b""

    pause_samples = int(SAMPLE_RATE * pause_seconds)
    all_segments = []

    for i, wav_bytes in enumerate(audio_segments):
        # Read audio data using soundfile (handles float format)
        buffer = io.BytesIO(wav_bytes)
        audio_data, _ = sf.read(buffer)
        all_segments.append(audio_data)

        # Add silence between segments (not after last)
        if i < len(audio_segments) - 1:
            all_segments.append(np.zeros(pause_samples, dtype=np.float32))

    # Combine all segments
    combined_audio = np.concatenate(all_segments)

    # Write to WAV bytes
    output_io = io.BytesIO()
    sf.write(output_io, combined_audio, SAMPLE_RATE, format="WAV")
    output_io.seek(0)
    return output_io.read()


async def synthesize_text(client: httpx.AsyncClient, tts_url: str, text: str, voice: str) -> bytes:
    """Call TTS HTTP API to synthesize text.

    Args:
        client: HTTP client
        tts_url: TTS server URL
        text: Text to synthesize
        voice: Voice ID (speaker_a through speaker_f)

    Returns:
        WAV audio bytes
    """
    response = await client.post(
        f"{tts_url}/synthesize",
        json={"text": text, "voice": voice},
        timeout=60.0,
    )
    response.raise_for_status()

    data = response.json()
    audio_b64 = data["audio_base64"]
    return base64.b64decode(audio_b64)


async def generate_dialogue_audio(
    client: httpx.AsyncClient,
    tts_url: str,
    dialogue: list[dict],
) -> tuple[bytes, float]:
    """Generate audio for a dialogue.

    Args:
        client: HTTP client
        tts_url: TTS server URL
        dialogue: List of {"speaker": voice_id, "text": text}

    Returns:
        Tuple of (WAV audio bytes, duration in seconds)
    """
    audio_segments = []

    for turn in dialogue:
        voice = turn["speaker"]
        text = turn["text"]
        print(f"    Synthesizing: [{voice}] {text[:50]}...")

        audio_bytes = await synthesize_text(client, tts_url, text, voice)
        audio_segments.append(audio_bytes)

    # Concatenate with pauses
    combined = concatenate_wav_bytes(audio_segments, PAUSE_SECONDS)

    # Calculate duration
    duration = len(combined) / (SAMPLE_RATE * 2)  # 16-bit mono

    return combined, duration


async def fetch_lesson_dialogues(session: AsyncSession, lesson_number: int) -> list[dict]:
    """Fetch Q&A examples for a lesson, grouped by pattern.

    Returns list of dialogues, each with:
    - pattern_number
    - dialogue: [{"speaker": ..., "text": ...}, ...]
    """
    # Get lesson
    stmt = (
        select(Lesson)
        .where(Lesson.course_id == "ec1", Lesson.lesson_number == lesson_number)
        .options(selectinload(Lesson.qa_patterns))
    )
    result = await session.execute(stmt)
    lesson = result.scalar_one_or_none()

    if not lesson:
        print(f"Lesson {lesson_number} not found")
        return []

    print(f"Found lesson {lesson_number}: {lesson.title}")

    dialogues = []

    for pattern in lesson.qa_patterns:
        # Get example sentences for this pattern
        stmt = (
            select(ExampleSentence)
            .where(ExampleSentence.pattern_id == pattern.id)
            .order_by(ExampleSentence.id)
        )
        result = await session.execute(stmt)
        examples = result.scalars().all()

        # Group questions and answers
        questions = [e.english_text for e in examples if e.sentence_type == "question"]
        answers = [e.english_text for e in examples if e.sentence_type == "answer"]

        # Create dialogue pairs
        for i, (q, a) in enumerate(zip(questions, answers)):
            dialogue = {
                "pattern_number": pattern.pattern_number,
                "example_index": i + 1,
                "dialogue": [
                    {"speaker": TEACHER_VOICE, "text": q},
                    # Add "..." to answer to prevent TTS truncation at end
                    {"speaker": STUDENT_VOICE, "text": a + "..."},
                ],
            }
            dialogues.append(dialogue)

    return dialogues


async def save_demo(
    lesson_number: int,
    pattern_number: int,
    example_index: int,
    dialogue: list[dict],
    audio_bytes: bytes,
    duration_seconds: float,
) -> Path:
    """Save audio file and metadata JSON sidecar."""
    output_dir = OUTPUT_BASE / f"lesson-{lesson_number:02d}"
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_filename = f"lesson{lesson_number:02d}-pattern{pattern_number}-ex{example_index}.wav"
    meta_filename = f"lesson{lesson_number:02d}-pattern{pattern_number}-ex{example_index}.json"

    audio_path = output_dir / audio_filename
    meta_path = output_dir / meta_filename

    # Save audio
    audio_path.write_bytes(audio_bytes)

    # Save metadata
    metadata = {
        "lesson_number": lesson_number,
        "pattern_number": pattern_number,
        "example_index": example_index,
        "dialogue": [
            {
                "speaker": "teacher" if turn["speaker"] == TEACHER_VOICE else "student",
                "voice": turn["speaker"],
                "text": turn["text"],
            }
            for turn in dialogue
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(duration_seconds, 2),
        "audio_format": "wav",
        "sample_rate": SAMPLE_RATE,
    }
    meta_path.write_text(json.dumps(metadata, indent=2))

    return audio_path


async def generate_single_demo(
    client: httpx.AsyncClient,
    tts_url: str,
    lesson_number: int,
    dlg: dict,
    semaphore: asyncio.Semaphore,
) -> Path | None:
    """Generate a single demo audio file with semaphore control.

    Args:
        client: HTTP client for TTS API
        tts_url: TTS server URL
        lesson_number: Lesson number
        dlg: Dialogue data
        semaphore: Semaphore for limiting concurrency

    Returns:
        Path to generated audio file, or None on error
    """
    async with semaphore:
        try:
            print(f"  [START] Pattern {dlg['pattern_number']}, example {dlg['example_index']}")
            audio_bytes, duration = await generate_dialogue_audio(client, tts_url, dlg["dialogue"])

            path = await save_demo(
                lesson_number=lesson_number,
                pattern_number=dlg["pattern_number"],
                example_index=dlg["example_index"],
                dialogue=dlg["dialogue"],
                audio_bytes=audio_bytes,
                duration_seconds=duration,
            )

            print(f"  [DONE] Pattern {dlg['pattern_number']}, example {dlg['example_index']} -> {path.name}")
            return path

        except Exception as e:
            print(f"  [ERROR] Pattern {dlg['pattern_number']}, example {dlg['example_index']}: {e}")
            return None


async def generate_demos_for_lesson(
    session: AsyncSession,
    client: httpx.AsyncClient,
    tts_url: str,
    lesson_number: int,
    single: bool = False,
    parallel: int = 1,
) -> list[Path]:
    """Generate demo audio files for a lesson.

    Args:
        session: Database session
        client: HTTP client for TTS API
        tts_url: TTS server URL
        lesson_number: Lesson number to generate for
        single: If True, only generate one demo
        parallel: Number of concurrent generations (1 = sequential)

    Returns:
        List of generated audio file paths
    """
    dialogues = await fetch_lesson_dialogues(session, lesson_number)

    if not dialogues:
        print(f"No dialogues found for lesson {lesson_number}")
        return []

    print(f"Found {len(dialogues)} dialogue(s) for lesson {lesson_number}")

    if single:
        dialogues = dialogues[:1]
        print("Single mode: generating only 1 dialogue")

    if parallel > 1:
        print(f"Parallel mode: {parallel} concurrent generations")
        semaphore = asyncio.Semaphore(parallel)

        tasks = [
            generate_single_demo(client, tts_url, lesson_number, dlg, semaphore)
            for dlg in dialogues
        ]
        results = await asyncio.gather(*tasks)
        generated = [r for r in results if r is not None]
    else:
        # Sequential mode (original behavior)
        generated = []
        semaphore = asyncio.Semaphore(1)

        for dlg in dialogues:
            path = await generate_single_demo(client, tts_url, lesson_number, dlg, semaphore)
            if path:
                generated.append(path)

    return generated


async def main():
    parser = argparse.ArgumentParser(description="Generate demo dialogue audio files")
    parser.add_argument("--lesson", type=int, help="Lesson number to generate for")
    parser.add_argument("--single", action="store_true", help="Generate only one demo")
    parser.add_argument("--all", action="store_true", help="Generate for all lessons")
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Number of concurrent TTS generations (default: 1)",
    )
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

    tts_url = args.tts_url

    if not args.lesson and not args.all:
        parser.error("Either --lesson or --all is required")

    # Create engine and session
    engine = create_async_engine(args.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Create HTTP client for TTS
    async with httpx.AsyncClient() as client:
        # Test TTS connection
        try:
            response = await client.get(f"{tts_url}/health", timeout=5.0)
            response.raise_for_status()
            print(f"TTS server connected: {tts_url}")
        except Exception as e:
            print(f"Error: Cannot connect to TTS server at {tts_url}")
            print(f"Start it with: cd src/services/tts-mcp && python server.py --http")
            print(f"Error details: {e}")
            return

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

                print(f"Generating demos for {len(lesson_numbers)} lessons...")

                total_generated = []
                for lesson_num in lesson_numbers:
                    print(f"\n{'='*60}")
                    print(f"Lesson {lesson_num}")
                    print(f"{'='*60}")
                    generated = await generate_demos_for_lesson(
                        session, client, tts_url, lesson_num,
                        single=args.single, parallel=args.parallel
                    )
                    total_generated.extend(generated)

                print(f"\n\nTotal generated: {len(total_generated)} audio files")
            else:
                generated = await generate_demos_for_lesson(
                    session, client, tts_url, args.lesson,
                    single=args.single, parallel=args.parallel
                )
                print(f"\nGenerated: {len(generated)} audio files")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
