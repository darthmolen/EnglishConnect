#!/usr/bin/env python3
"""Generate pre-recorded intro audio for each lesson.

These intros are played when a user enters the Practice section.
They explain how the practice session works and what to expect.

Usage:
    python src/tools/generate_intros.py

Requires:
    - TTS service running on port 8002 (for English/VibeVoice)
    - Piper models installed (for Spanish/Dave)
    - Database with lessons populated
"""

import asyncio
import base64
import os
import sys
from pathlib import Path

import httpx
from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker

# Add src paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "piper"))

from app.models.content import Lesson
from service import PiperService

# Configuration
TTS_URL = os.getenv("TTS_URL", "http://localhost:8002")
PIPER_SERVICE: PiperService | None = None  # Lazy init
# Load DATABASE_URL from .env, convert asyncpg to psycopg2 for sync access
_db_url = os.getenv("DATABASE_URL", "postgresql://englishconnect:devpassword@localhost:5432/englishconnect")
# Normalize the URL for psycopg2
DATABASE_URL = _db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace("postgresql://", "postgresql+psycopg2://")
OUTPUT_DIR = Path("content/audio/ec1/intros")

# Voice for intros (warm, friendly)
INTRO_VOICE = "speaker_b"

# Intro templates - personalized for each lesson
INTRO_TEMPLATE_EN = """Welcome to conversation group where we practice different conversation patterns for Lesson {lesson_number}: {lesson_title}.
Feel free to look at the different patterns. There are play buttons by each example that you can listen to.
If you have any questions about the patterns or vocabulary, please ask using the microphone button below.
When you're ready, either use the microphone button and say "I'm ready" or hit the green Play button and we'll start conversing using the patterns on this page."""

INTRO_TEMPLATE_ES = """Bienvenido al grupo de conversación donde practicamos diferentes patrones de conversación para la Lección {lesson_number}: {lesson_title}.
Siéntete libre de mirar los diferentes patrones. Hay botones de reproducción junto a cada ejemplo que puedes escuchar.
Si tienes alguna pregunta sobre los patrones o el vocabulario, por favor pregunta usando el botón del micrófono abajo.
Cuando estés listo, usa el botón del micrófono y di "Estoy listo" o presiona el botón verde de Play y comenzaremos a conversar usando los patrones en esta página."""

# For backward compatibility
INTRO_TEMPLATE = INTRO_TEMPLATE_EN


def get_piper_service() -> PiperService:
    """Get or create Piper service (lazy initialization)."""
    global PIPER_SERVICE
    if PIPER_SERVICE is None:
        PIPER_SERVICE = PiperService()
    return PIPER_SERVICE


async def generate_intro(lesson_number: int, lesson_title: str, language: str = "en") -> bool:
    """Generate intro audio for a lesson in the specified language.

    Uses:
    - VibeVoice (Emma) for English
    - Piper (Dave) for Spanish
    """
    template = INTRO_TEMPLATE_ES if language == "es" else INTRO_TEMPLATE_EN
    text = template.format(
        lesson_number=lesson_number,
        lesson_title=lesson_title,
    )
    output_file = OUTPUT_DIR / f"lesson-{lesson_number:02d}-{language}.wav"

    print(f"Generating {language.upper()} intro for Lesson {lesson_number}: {lesson_title}...")

    try:
        if language == "es":
            # Use Piper (Dave) for Spanish - native pronunciation
            piper = get_piper_service()
            audio_data = piper.synthesize(text, language="es", resample=True)
            output_file.write_bytes(audio_data)
            print(f"  ✓ Saved (Piper/Dave): {output_file} ({len(audio_data) / 1024:.1f} KB)")
            return True
        else:
            # Use VibeVoice (Emma) for English
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{TTS_URL}/synthesize",
                    json={"text": text, "voice": INTRO_VOICE},
                    timeout=120.0,  # Longer timeout for longer text
                )
                response.raise_for_status()

                result = response.json()
                audio_data = base64.b64decode(result["audio_base64"])

                output_file.write_bytes(audio_data)
                print(f"  ✓ Saved (VibeVoice/Emma): {output_file} ({len(audio_data) / 1024:.1f} KB)")
                return True

    except httpx.HTTPError as e:
        print(f"  ✗ HTTP Error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def get_lessons() -> list[tuple[int, str]]:
    """Get all lessons from the database."""
    # Use sync engine for simplicity in a script
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        result = session.execute(
            select(Lesson.lesson_number, Lesson.title)
            .where(Lesson.course_id == "ec1")
            .order_by(Lesson.lesson_number)
        )
        return [(row.lesson_number, row.title) for row in result.fetchall()]


async def main(language: str = "both"):
    """Generate intros for all lessons.

    Args:
        language: "en" for English only, "es" for Spanish only, "both" for both languages
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    languages = ["en", "es"] if language == "both" else [language]
    print(f"Generating lesson intros in {OUTPUT_DIR}/")
    print(f"Languages: {', '.join(lang.upper() for lang in languages)}")
    print(f"Using TTS service at: {TTS_URL}")
    print("=" * 60)

    # Get lessons from database
    try:
        lessons = get_lessons()
        print(f"Found {len(lessons)} lessons in database")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Make sure PostgreSQL is running and the database is populated.")
        return

    if not lessons:
        print("No lessons found. Run content ingestion first.")
        return

    print("=" * 60)

    # Generate intros sequentially (to avoid TTS overload)
    total_count = len(lessons) * len(languages)
    success_count = 0
    for lang in languages:
        print(f"\n--- Generating {lang.upper()} intros ---")
        for lesson_number, lesson_title in lessons:
            if await generate_intro(lesson_number, lesson_title, lang):
                success_count += 1

    print("=" * 60)
    print(f"Generated {success_count}/{total_count} intros")

    if success_count > 0:
        print(f"\nIntro files saved in: {OUTPUT_DIR}/")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate intro audio for lessons")
    parser.add_argument(
        "--language", "-l",
        choices=["en", "es", "both"],
        default="both",
        help="Language for intros: en (English), es (Spanish), or both (default)"
    )
    args = parser.parse_args()
    asyncio.run(main(args.language))
