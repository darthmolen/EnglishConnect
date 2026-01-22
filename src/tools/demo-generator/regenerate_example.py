#!/usr/bin/env python3
"""Regenerate a single demo example for EnglishConnect.

Usage:
    # Ensure TTS server is running in HTTP mode:
    # cd src/services/tts-mcp && source .venv/bin/activate && python server.py --http

    # Regenerate lesson 15, pattern 1, example 3
    python regenerate_example.py --lesson 15 --pattern 1 --example 3

    # Use a different voice (speaker_b = Emma, more upbeat)
    python regenerate_example.py --lesson 15 --pattern 1 --example 3 --teacher-voice speaker_b

    # List available voices
    python regenerate_example.py --list-voices
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

# Add parent paths for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.models.content import Lesson, QAPattern, ExampleSentence


# Configuration
OUTPUT_BASE = Path(__file__).parent.parent.parent.parent / "content" / "audio" / "ec1" / "demos"
TTS_HTTP_URL = "http://localhost:8002"
DATABASE_URL = "postgresql+asyncpg://englishconnect:devpassword@localhost:5432/englishconnect"
PAUSE_SECONDS = 0.5
SAMPLE_RATE = 24000

# Default voices
DEFAULT_TEACHER_VOICE = "speaker_d"  # Grace
DEFAULT_STUDENT_VOICE = "speaker_c"  # Davis


def concatenate_wav_bytes(audio_segments: list[bytes], pause_seconds: float = 0.5) -> bytes:
    """Concatenate WAV audio bytes with pauses between segments."""
    if not audio_segments:
        return b""

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


async def synthesize_text(client: httpx.AsyncClient, tts_url: str, text: str, voice: str) -> bytes:
    """Call TTS HTTP API to synthesize text."""
    response = await client.post(
        f"{tts_url}/synthesize",
        json={"text": text, "voice": voice},
        timeout=60.0,
    )
    response.raise_for_status()

    data = response.json()
    audio_b64 = data["audio_base64"]
    return base64.b64decode(audio_b64)


async def list_voices(tts_url: str):
    """List available voices from TTS server."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{tts_url}/voices", timeout=5.0)
        response.raise_for_status()
        voices = response.json()

        print("\nAvailable voices:")
        print("-" * 60)
        for v in voices:
            print(f"  {v['id']:12} - {v['name']:8} - {v['description']}")
        print()


async def get_example_from_db(
    session: AsyncSession,
    lesson_number: int,
    pattern_number: int,
    example_index: int
) -> dict | None:
    """Fetch a specific example from the database."""
    # Get lesson
    stmt = (
        select(Lesson)
        .where(Lesson.course_id == "ec1", Lesson.lesson_number == lesson_number)
    )
    result = await session.execute(stmt)
    lesson = result.scalar_one_or_none()

    if not lesson:
        print(f"Error: Lesson {lesson_number} not found")
        return None

    # Get pattern
    stmt = (
        select(QAPattern)
        .where(QAPattern.lesson_id == lesson.id, QAPattern.pattern_number == pattern_number)
    )
    result = await session.execute(stmt)
    pattern = result.scalar_one_or_none()

    if not pattern:
        print(f"Error: Pattern {pattern_number} not found in lesson {lesson_number}")
        return None

    # Get example sentences
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

    if example_index < 1 or example_index > min(len(questions), len(answers)):
        print(f"Error: Example {example_index} not found (available: 1-{min(len(questions), len(answers))})")
        print(f"  Questions: {questions}")
        print(f"  Answers: {answers}")
        return None

    return {
        "question": questions[example_index - 1],
        "answer": answers[example_index - 1],
    }


async def regenerate_example(
    lesson_number: int,
    pattern_number: int,
    example_index: int,
    teacher_voice: str,
    student_voice: str,
    tts_url: str,
    database_url: str,
) -> Path | None:
    """Regenerate a single example audio file."""
    # Create engine and session
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

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
            return None

        async with async_session() as session:
            # Get example from database
            example = await get_example_from_db(session, lesson_number, pattern_number, example_index)
            if not example:
                return None

            print(f"\nExample found:")
            print(f"  Q: {example['question']}")
            print(f"  A: {example['answer']}")
            print(f"\nUsing voices:")
            print(f"  Teacher: {teacher_voice}")
            print(f"  Student: {student_voice}")

            # Synthesize
            print(f"\nSynthesizing...")
            audio_segments = []

            print(f"  [{teacher_voice}] {example['question']}")
            q_audio = await synthesize_text(client, tts_url, example["question"], teacher_voice)
            audio_segments.append(q_audio)

            # Add "..." to answer to prevent TTS truncation at end
            answer_text = example["answer"] + "..."
            print(f"  [{student_voice}] {answer_text}")
            a_audio = await synthesize_text(client, tts_url, answer_text, student_voice)
            audio_segments.append(a_audio)

            # Concatenate
            combined = concatenate_wav_bytes(audio_segments, PAUSE_SECONDS)
            duration = len(combined) / (SAMPLE_RATE * 2)

            # Save
            output_dir = OUTPUT_BASE / f"lesson-{lesson_number:02d}"
            output_dir.mkdir(parents=True, exist_ok=True)

            audio_filename = f"lesson{lesson_number:02d}-pattern{pattern_number}-ex{example_index}.wav"
            meta_filename = f"lesson{lesson_number:02d}-pattern{pattern_number}-ex{example_index}.json"

            audio_path = output_dir / audio_filename
            meta_path = output_dir / meta_filename

            audio_path.write_bytes(combined)

            metadata = {
                "lesson_number": lesson_number,
                "pattern_number": pattern_number,
                "example_index": example_index,
                "dialogue": [
                    {
                        "speaker": "teacher",
                        "voice": teacher_voice,
                        "text": example["question"],
                    },
                    {
                        "speaker": "student",
                        "voice": student_voice,
                        "text": example["answer"],
                    },
                ],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": round(duration, 2),
                "audio_format": "wav",
                "sample_rate": SAMPLE_RATE,
            }
            meta_path.write_text(json.dumps(metadata, indent=2))

            print(f"\nGenerated:")
            print(f"  {audio_path}")
            print(f"  {meta_path}")
            print(f"  Duration: {duration:.2f}s")

            return audio_path

    await engine.dispose()


async def main():
    parser = argparse.ArgumentParser(description="Regenerate a single demo example")
    parser.add_argument("--lesson", type=int, help="Lesson number")
    parser.add_argument("--pattern", type=int, help="Pattern number (1 or 2)")
    parser.add_argument("--example", type=int, help="Example index (1, 2, or 3)")
    parser.add_argument(
        "--teacher-voice",
        default=DEFAULT_TEACHER_VOICE,
        help=f"Voice for teacher/question (default: {DEFAULT_TEACHER_VOICE})",
    )
    parser.add_argument(
        "--student-voice",
        default=DEFAULT_STUDENT_VOICE,
        help=f"Voice for student/answer (default: {DEFAULT_STUDENT_VOICE})",
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
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available voices and exit",
    )
    args = parser.parse_args()

    if args.list_voices:
        await list_voices(args.tts_url)
        return

    if not args.lesson or not args.pattern or not args.example:
        parser.error("--lesson, --pattern, and --example are required")

    print(f"\n{'='*60}")
    print(f"Regenerating: Lesson {args.lesson} > Pattern {args.pattern} > Example {args.example}")
    print(f"{'='*60}")

    await regenerate_example(
        lesson_number=args.lesson,
        pattern_number=args.pattern,
        example_index=args.example,
        teacher_voice=args.teacher_voice,
        student_voice=args.student_voice,
        tts_url=args.tts_url,
        database_url=args.database_url,
    )


if __name__ == "__main__":
    asyncio.run(main())
