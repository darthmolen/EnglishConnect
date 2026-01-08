#!/usr/bin/env python3
"""Generate pre-recorded intro audio for each lesson.

These intros are played when a user enters the Practice or Vocabulary sections.
They explain how each section works and what to expect.

Usage:
    python src/tools/generate_intros.py                    # Generate split intros (default)
    python src/tools/generate_intros.py --page practice    # Practice only
    python src/tools/generate_intros.py --page vocabulary  # Vocabulary only
    python src/tools/generate_intros.py --language es      # Spanish only
    python src/tools/generate_intros.py --legacy           # Generate old combined format

Split mode (default) generates:
    - unique/lesson-XX-{lang}.wav: Short lesson-specific intro
    - instructions-{lang}.wav: Shared instructions (one per page type)

This reduces storage from ~228MB to ~32MB (86% reduction).

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
OUTPUT_BASE = Path("content/audio/ec1/intros")

# Voice for intros (warm, friendly)
INTRO_VOICE = "speaker_b"

# =============================================================================
# SPLIT MODE TEMPLATES (default - reduces storage by 86%)
# =============================================================================

# Unique intro per lesson (short, ~5 seconds)
UNIQUE_TEMPLATES = {
    "vocabulary": {
        "en": "Welcome to Lesson {lesson_number}'s vocabulary where we go over {lesson_title}.",
        "es": "Bienvenido al vocabulario de la Lección {lesson_number} donde repasamos {lesson_title}.",
    },
    "practice": {
        "en": "Welcome to Lesson {lesson_number}'s practice session where we work on {lesson_title}.",
        "es": "Bienvenido a la sesión de práctica de la Lección {lesson_number} donde trabajamos con {lesson_title}.",
    },
}

# Shared instructions per page type (same for all lessons, ~30 seconds)
INSTRUCTIONS_TEMPLATES = {
    "vocabulary": {
        "en": """Please go through all the vocabulary and memorize them. There are play buttons next to each word that can be used for listening.
After you play the word, it's recommended to say that word out loud and mimic what you hear.
You can do this as many times as you need before moving on to the practice session.
If at any time you have questions about the vocabulary or how they are used, you can ask in Spanish or English for help by using the microphone button at the bottom of the page.""",
        "es": """Por favor revisa todo el vocabulario y memorízalo. Hay botones de reproducción junto a cada palabra que puedes usar para escuchar.
Después de reproducir la palabra, se recomienda que la digas en voz alta e imites lo que escuchas.
Puedes hacer esto tantas veces como necesites antes de pasar a la sesión de práctica.
Si en algún momento tienes preguntas sobre el vocabulario o cómo se usa, puedes preguntar en español o inglés usando el botón del micrófono en la parte inferior de la página.""",
    },
    "practice": {
        "en": """Feel free to look at the different patterns. There are play buttons by each example that you can listen to.
If you have any questions about the patterns or vocabulary, please ask using the microphone button below.
When you're ready, either use the microphone button and say "I'm ready" or hit the green Play button and we'll start conversing using the patterns on this page.""",
        "es": """Siéntete libre de mirar los diferentes patrones. Hay botones de reproducción junto a cada ejemplo que puedes escuchar.
Si tienes alguna pregunta sobre los patrones o el vocabulario, por favor pregunta usando el botón del micrófono abajo.
Cuando estés listo, usa el botón del micrófono y di "Estoy listo" o presiona el botón verde de Play y comenzaremos a conversar usando los patrones en esta página.""",
    },
}

# =============================================================================
# LEGACY MODE TEMPLATES (combined intro + instructions per lesson)
# =============================================================================

# Practice page intro templates (legacy)
PRACTICE_TEMPLATE_EN = """Welcome to conversation group where we practice different conversation patterns for Lesson {lesson_number}: {lesson_title}.
Feel free to look at the different patterns. There are play buttons by each example that you can listen to.
If you have any questions about the patterns or vocabulary, please ask using the microphone button below.
When you're ready, either use the microphone button and say "I'm ready" or hit the green Play button and we'll start conversing using the patterns on this page."""

PRACTICE_TEMPLATE_ES = """Bienvenido al grupo de conversación donde practicamos diferentes patrones de conversación para la Lección {lesson_number}: {lesson_title}.
Siéntete libre de mirar los diferentes patrones. Hay botones de reproducción junto a cada ejemplo que puedes escuchar.
Si tienes alguna pregunta sobre los patrones o el vocabulario, por favor pregunta usando el botón del micrófono abajo.
Cuando estés listo, usa el botón del micrófono y di "Estoy listo" o presiona el botón verde de Play y comenzaremos a conversar usando los patrones en esta página."""

# Vocabulary page intro templates (legacy)
VOCABULARY_TEMPLATE_EN = """Welcome to Lesson {lesson_number}: {lesson_title} vocabulary!
Please go through all the vocabulary and memorize them. There are play buttons next to each word that can be used for listening.
After you play the word, it's recommended to say that word out loud and mimic what you hear.
You can do this as many times as you need before moving on to the practice session.
If at any time you have questions about the vocabulary or how they are used, you can ask in Spanish or English for help by using the microphone button at the bottom of the page."""

VOCABULARY_TEMPLATE_ES = """¡Bienvenido al vocabulario de la Lección {lesson_number}: {lesson_title}!
Por favor revisa todo el vocabulario y memorízalo. Hay botones de reproducción junto a cada palabra que puedes usar para escuchar.
Después de reproducir la palabra, se recomienda que la digas en voz alta e imites lo que escuchas.
Puedes hacer esto tantas veces como necesites antes de pasar a la sesión de práctica.
Si en algún momento tienes preguntas sobre el vocabulario o cómo se usa, puedes preguntar en español o inglés usando el botón del micrófono en la parte inferior de la página."""

# Template mapping (legacy)
TEMPLATES = {
    "practice": {"en": PRACTICE_TEMPLATE_EN, "es": PRACTICE_TEMPLATE_ES},
    "vocabulary": {"en": VOCABULARY_TEMPLATE_EN, "es": VOCABULARY_TEMPLATE_ES},
}

# For backward compatibility
INTRO_TEMPLATE_EN = PRACTICE_TEMPLATE_EN
INTRO_TEMPLATE_ES = PRACTICE_TEMPLATE_ES
INTRO_TEMPLATE = INTRO_TEMPLATE_EN


def get_piper_service() -> PiperService:
    """Get or create Piper service (lazy initialization)."""
    global PIPER_SERVICE
    if PIPER_SERVICE is None:
        PIPER_SERVICE = PiperService()
    return PIPER_SERVICE


async def synthesize_audio(text: str, language: str) -> bytes | None:
    """Synthesize audio from text using appropriate TTS engine.

    Args:
        text: Text to synthesize
        language: 'en' or 'es'

    Returns:
        Audio bytes (WAV format) or None on error
    """
    try:
        if language == "es":
            # Use Piper (Dave) for Spanish - native pronunciation
            piper = get_piper_service()
            return piper.synthesize(text, language="es", resample=True)
        else:
            # Use VibeVoice (Emma) for English
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{TTS_URL}/synthesize",
                    json={"text": text, "voice": INTRO_VOICE},
                    timeout=120.0,
                )
                response.raise_for_status()
                result = response.json()
                return base64.b64decode(result["audio_base64"])
    except Exception as e:
        print(f"  ✗ Synthesis error: {e}")
        return None


async def generate_unique_intro(
    lesson_number: int,
    lesson_title: str,
    language: str,
    page_type: str,
) -> bool:
    """Generate unique intro audio for a lesson (split mode).

    Args:
        lesson_number: The lesson number
        lesson_title: The lesson title
        language: 'en' or 'es'
        page_type: 'practice' or 'vocabulary'
    """
    template = UNIQUE_TEMPLATES[page_type][language]
    text = template.format(lesson_number=lesson_number, lesson_title=lesson_title)

    output_dir = OUTPUT_BASE / page_type / "unique"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"lesson-{lesson_number:02d}-{language}.wav"

    print(f"  Generating unique intro for Lesson {lesson_number}...")

    audio_data = await synthesize_audio(text, language)
    if audio_data:
        output_file.write_bytes(audio_data)
        engine = "Piper/Dave" if language == "es" else "VibeVoice/Emma"
        print(f"    ✓ Saved ({engine}): {output_file.name} ({len(audio_data) / 1024:.1f} KB)")
        return True
    return False


async def generate_instructions(language: str, page_type: str) -> bool:
    """Generate shared instructions audio (split mode).

    Args:
        language: 'en' or 'es'
        page_type: 'practice' or 'vocabulary'
    """
    text = INSTRUCTIONS_TEMPLATES[page_type][language]

    output_dir = OUTPUT_BASE / page_type
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"instructions-{language}.wav"

    print(f"  Generating shared instructions ({page_type}/{language.upper()})...")

    audio_data = await synthesize_audio(text, language)
    if audio_data:
        output_file.write_bytes(audio_data)
        engine = "Piper/Dave" if language == "es" else "VibeVoice/Emma"
        print(f"    ✓ Saved ({engine}): {output_file} ({len(audio_data) / 1024:.1f} KB)")
        return True
    return False


async def generate_intro_legacy(
    lesson_number: int,
    lesson_title: str,
    language: str = "en",
    page_type: str = "practice",
) -> bool:
    """Generate combined intro audio for a lesson page (legacy mode).

    Uses:
    - VibeVoice (Emma) for English
    - Piper (Dave) for Spanish

    Args:
        lesson_number: The lesson number
        lesson_title: The lesson title
        language: 'en' or 'es'
        page_type: 'practice' or 'vocabulary'
    """
    template = TEMPLATES[page_type][language]
    text = template.format(
        lesson_number=lesson_number,
        lesson_title=lesson_title,
    )
    output_dir = OUTPUT_BASE / page_type
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"lesson-{lesson_number:02d}-{language}.wav"

    print(f"Generating {page_type}/{language.upper()} intro for Lesson {lesson_number}: {lesson_title}...")

    audio_data = await synthesize_audio(text, language)
    if audio_data:
        output_file.write_bytes(audio_data)
        engine = "Piper/Dave" if language == "es" else "VibeVoice/Emma"
        print(f"  ✓ Saved ({engine}): {output_file} ({len(audio_data) / 1024:.1f} KB)")
        return True
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


async def main_split(language: str = "both", page_type: str = "both"):
    """Generate split intros for all lessons (default mode).

    This mode generates:
    - unique/lesson-XX-{lang}.wav: Short lesson-specific intro
    - instructions-{lang}.wav: Shared instructions (one per page type)

    Args:
        language: "en" for English only, "es" for Spanish only, "both" for both languages
        page_type: "practice", "vocabulary", or "both" for all page types
    """
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    languages = ["en", "es"] if language == "both" else [language]
    page_types = ["practice", "vocabulary"] if page_type == "both" else [page_type]

    print(f"Generating SPLIT lesson intros in {OUTPUT_BASE}/")
    print(f"Page types: {', '.join(page_types)}")
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

    # Generate shared instructions first (4 total: 2 page types × 2 languages)
    print("\n--- Generating shared instruction clips ---")
    instructions_count = 0
    for ptype in page_types:
        for lang in languages:
            if await generate_instructions(lang, ptype):
                instructions_count += 1

    # Generate unique intros for each lesson
    unique_count = 0
    total_unique = len(lessons) * len(languages) * len(page_types)

    for ptype in page_types:
        for lang in languages:
            print(f"\n--- Generating {ptype}/{lang.upper()} unique intros ---")
            for lesson_number, lesson_title in lessons:
                if await generate_unique_intro(lesson_number, lesson_title, lang, ptype):
                    unique_count += 1

    print("=" * 60)
    print(f"Generated {instructions_count} shared instruction clips")
    print(f"Generated {unique_count}/{total_unique} unique intro clips")

    if unique_count > 0 or instructions_count > 0:
        print(f"\nIntro files saved in: {OUTPUT_BASE}/")
        # Show size comparison
        import subprocess
        result = subprocess.run(
            ["du", "-sh", str(OUTPUT_BASE)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"Total size: {result.stdout.strip().split()[0]}")


async def main_legacy(language: str = "both", page_type: str = "both"):
    """Generate combined intros for all lessons (legacy mode).

    Args:
        language: "en" for English only, "es" for Spanish only, "both" for both languages
        page_type: "practice", "vocabulary", or "both" for all page types
    """
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    languages = ["en", "es"] if language == "both" else [language]
    page_types = ["practice", "vocabulary"] if page_type == "both" else [page_type]

    print(f"Generating LEGACY (combined) lesson intros in {OUTPUT_BASE}/")
    print(f"Page types: {', '.join(page_types)}")
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
    total_count = len(lessons) * len(languages) * len(page_types)
    success_count = 0

    for ptype in page_types:
        for lang in languages:
            print(f"\n--- Generating {ptype}/{lang.upper()} intros ---")
            for lesson_number, lesson_title in lessons:
                if await generate_intro_legacy(lesson_number, lesson_title, lang, ptype):
                    success_count += 1

    print("=" * 60)
    print(f"Generated {success_count}/{total_count} intros")

    if success_count > 0:
        print(f"\nIntro files saved in: {OUTPUT_BASE}/")


# Keep old main for backward compatibility
async def main(language: str = "both", page_type: str = "both"):
    """Generate intros for all lessons (defaults to split mode)."""
    await main_split(language, page_type)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate intro audio for lessons")
    parser.add_argument(
        "--language", "-l",
        choices=["en", "es", "both"],
        default="both",
        help="Language for intros: en (English), es (Spanish), or both (default)"
    )
    parser.add_argument(
        "--page", "-p",
        choices=["practice", "vocabulary", "both"],
        default="both",
        help="Page type for intros: practice, vocabulary, or both (default)"
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Generate combined intros (legacy mode, larger files)"
    )
    args = parser.parse_args()

    if args.legacy:
        asyncio.run(main_legacy(args.language, args.page))
    else:
        asyncio.run(main_split(args.language, args.page))
