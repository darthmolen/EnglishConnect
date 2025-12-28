#!/usr/bin/env python3
"""Content MCP Server - Exposes lesson content to Claude agents.

This server provides tools for agents to query:
- Lesson information (title, objectives, learning principles)
- Vocabulary items with translations
- Q&A patterns for practice
- Evaluation criteria

Usage:
    python server.py
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Load environment variables
load_dotenv()

# Database setup (async with asyncpg)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://englishconnect:devpassword@localhost:5432/englishconnect"
)

# Ensure URL uses asyncpg driver
if "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Import models (inline to avoid complex imports)
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


class Course(Base):
    __tablename__ = "courses"
    id = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    total_lessons = Column(Integer, nullable=False)


class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True)
    course_id = Column(String(20), ForeignKey("courses.id"))
    lesson_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    objective = Column(Text)
    learning_principle = Column(Text)
    learning_principle_title = Column(String(200))
    content_path = Column(String(500))


class VocabularyItem(Base):
    __tablename__ = "vocabulary_items"
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    english_word = Column(String(200), nullable=False)
    spanish_translation = Column(String(200), nullable=False)
    pronunciation_hint = Column(String(200))
    category = Column(String(50))


class QAPattern(Base):
    __tablename__ = "qa_patterns"
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    pattern_number = Column(Integer, nullable=False)
    question_template = Column(String(500), nullable=False)
    answer_template = Column(String(500), nullable=False)
    examples = Column(JSONB)


class EvaluationCriterion(Base):
    __tablename__ = "evaluation_criteria"
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    criterion = Column(Text, nullable=False)
    sort_order = Column(Integer, default=0)


class ExampleSentence(Base):
    __tablename__ = "example_sentences"
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    pattern_id = Column(Integer, ForeignKey("qa_patterns.id"))
    sentence_type = Column(String(20))  # 'question' or 'answer'
    english_text = Column(Text, nullable=False)
    spanish_translation = Column(Text)


# Create MCP server
mcp = FastMCP("content")


@mcp.tool()
async def get_lesson(course_id: str, lesson_number: int) -> str:
    """Get complete lesson data including title, objective, and learning principle.

    Args:
        course_id: Course identifier (e.g., 'ec1')
        lesson_number: Lesson number (1-25)

    Returns:
        JSON string with lesson data
    """
    async with async_session() as session:
        result = await session.execute(
            select(Lesson).where(
                Lesson.course_id == course_id,
                Lesson.lesson_number == lesson_number,
            )
        )
        lesson = result.scalar_one_or_none()

        if not lesson:
            return json.dumps({
                "error": f"Lesson {lesson_number} not found in course {course_id}"
            })

        # Get vocabulary
        vocab_result = await session.execute(
            select(VocabularyItem).where(VocabularyItem.lesson_id == lesson.id)
        )
        vocab_items = vocab_result.scalars().all()

        # Get patterns
        patterns_result = await session.execute(
            select(QAPattern).where(QAPattern.lesson_id == lesson.id)
        )
        patterns = patterns_result.scalars().all()

        # Get evaluation criteria
        criteria_result = await session.execute(
            select(EvaluationCriterion)
            .where(EvaluationCriterion.lesson_id == lesson.id)
            .order_by(EvaluationCriterion.sort_order)
        )
        criteria = criteria_result.scalars().all()

        return json.dumps({
            "lesson_number": lesson.lesson_number,
            "title": lesson.title,
            "objective": lesson.objective,
            "learning_principle": {
                "title": lesson.learning_principle_title,
                "content": lesson.learning_principle,
            },
            "vocabulary": [
                {
                    "english": v.english_word,
                    "spanish": v.spanish_translation,
                    "category": v.category,
                }
                for v in vocab_items
            ],
            "patterns": [
                {
                    "number": p.pattern_number,
                    "question_template": p.question_template,
                    "answer_template": p.answer_template,
                    "examples": p.examples,
                }
                for p in patterns
            ],
            "evaluation_criteria": [c.criterion for c in criteria],
        })


@mcp.tool()
async def get_vocabulary(course_id: str, lesson_number: int) -> str:
    """Get vocabulary list for a specific lesson.

    Args:
        course_id: Course identifier (e.g., 'ec1')
        lesson_number: Lesson number (1-25)

    Returns:
        JSON array of vocabulary items with English/Spanish pairs
    """
    async with async_session() as session:
        result = await session.execute(
            select(Lesson).where(
                Lesson.course_id == course_id,
                Lesson.lesson_number == lesson_number,
            )
        )
        lesson = result.scalar_one_or_none()

        if not lesson:
            return json.dumps({"error": f"Lesson {lesson_number} not found"})

        vocab_result = await session.execute(
            select(VocabularyItem).where(VocabularyItem.lesson_id == lesson.id)
        )
        vocab_items = vocab_result.scalars().all()

        return json.dumps([
            {
                "english": v.english_word,
                "spanish": v.spanish_translation,
                "category": v.category,
            }
            for v in vocab_items
        ])


@mcp.tool()
async def get_patterns(course_id: str, lesson_number: int) -> str:
    """Get Q&A patterns for a specific lesson.

    Args:
        course_id: Course identifier (e.g., 'ec1')
        lesson_number: Lesson number (1-25)

    Returns:
        JSON array of Q&A patterns with templates and examples
    """
    async with async_session() as session:
        result = await session.execute(
            select(Lesson).where(
                Lesson.course_id == course_id,
                Lesson.lesson_number == lesson_number,
            )
        )
        lesson = result.scalar_one_or_none()

        if not lesson:
            return json.dumps({"error": f"Lesson {lesson_number} not found"})

        patterns_result = await session.execute(
            select(QAPattern).where(QAPattern.lesson_id == lesson.id)
        )
        patterns = patterns_result.scalars().all()

        return json.dumps([
            {
                "number": p.pattern_number,
                "question_template": p.question_template,
                "answer_template": p.answer_template,
                "examples": p.examples,
            }
            for p in patterns
        ])


@mcp.tool()
async def get_cumulative_vocabulary(course_id: str, up_to_lesson: int) -> str:
    """Get all vocabulary from lesson 1 up to the specified lesson.

    Useful for conversation practice that can use words from previous lessons.

    Args:
        course_id: Course identifier (e.g., 'ec1')
        up_to_lesson: Include vocabulary up to this lesson number

    Returns:
        JSON array of vocabulary items from all lessons up to the specified one
    """
    async with async_session() as session:
        lessons_result = await session.execute(
            select(Lesson).where(
                Lesson.course_id == course_id,
                Lesson.lesson_number <= up_to_lesson,
            )
        )
        lessons = lessons_result.scalars().all()

        lesson_ids = [l.id for l in lessons]

        vocab_result = await session.execute(
            select(VocabularyItem).where(VocabularyItem.lesson_id.in_(lesson_ids))
        )
        vocab_items = vocab_result.scalars().all()

        return json.dumps([
            {
                "english": v.english_word,
                "spanish": v.spanish_translation,
                "category": v.category,
                "lesson_id": v.lesson_id,
            }
            for v in vocab_items
        ])


@mcp.tool()
async def list_lessons(course_id: str) -> str:
    """List all lessons in a course.

    Args:
        course_id: Course identifier (e.g., 'ec1')

    Returns:
        JSON array of lesson summaries
    """
    async with async_session() as session:
        result = await session.execute(
            select(Lesson)
            .where(Lesson.course_id == course_id)
            .order_by(Lesson.lesson_number)
        )
        lessons = result.scalars().all()

        return json.dumps([
            {
                "lesson_number": l.lesson_number,
                "title": l.title,
                "objective": l.objective,
            }
            for l in lessons
        ])


@mcp.tool()
async def search_vocabulary(query: str, course_id: str = "ec1") -> str:
    """Search for vocabulary words matching a query.

    Args:
        query: Search term (matches English or Spanish)
        course_id: Course identifier (default: 'ec1')

    Returns:
        JSON array of matching vocabulary items
    """
    async with async_session() as session:
        # Get lesson IDs for the course
        lessons_result = await session.execute(
            select(Lesson).where(Lesson.course_id == course_id)
        )
        lessons = lessons_result.scalars().all()
        lesson_ids = [l.id for l in lessons]

        # Search vocabulary
        vocab_result = await session.execute(
            select(VocabularyItem).where(
                VocabularyItem.lesson_id.in_(lesson_ids),
                (
                    VocabularyItem.english_word.ilike(f"%{query}%") |
                    VocabularyItem.spanish_translation.ilike(f"%{query}%")
                )
            )
        )
        vocab_items = vocab_result.scalars().all()

        return json.dumps([
            {
                "english": v.english_word,
                "spanish": v.spanish_translation,
                "category": v.category,
                "lesson_id": v.lesson_id,
            }
            for v in vocab_items
        ])


@mcp.tool()
async def search_examples(query: str, course_id: str = "ec1", sentence_type: str = None) -> str:
    """Search for example sentences matching a query.

    Searches concrete example sentences from Q&A patterns, useful for
    finding real usage examples or generating demo dialogues.

    Args:
        query: Search term (matches English text)
        course_id: Course identifier (default: 'ec1')
        sentence_type: Filter by 'question' or 'answer' (optional)

    Returns:
        JSON array of matching example sentences with lesson context
    """
    async with async_session() as session:
        # Get lesson IDs for the course
        lessons_result = await session.execute(
            select(Lesson).where(Lesson.course_id == course_id)
        )
        lessons = lessons_result.scalars().all()
        lesson_ids = [l.id for l in lessons]
        lesson_map = {l.id: l.lesson_number for l in lessons}

        # Build query
        filters = [
            ExampleSentence.lesson_id.in_(lesson_ids),
            ExampleSentence.english_text.ilike(f"%{query}%")
        ]
        if sentence_type:
            filters.append(ExampleSentence.sentence_type == sentence_type)

        examples_result = await session.execute(
            select(ExampleSentence).where(*filters)
        )
        examples = examples_result.scalars().all()

        return json.dumps([
            {
                "english_text": e.english_text,
                "sentence_type": e.sentence_type,
                "lesson_number": lesson_map.get(e.lesson_id),
                "pattern_id": e.pattern_id,
            }
            for e in examples
        ])


@mcp.tool()
async def get_example_sentences(course_id: str, lesson_number: int) -> str:
    """Get all example sentences for a specific lesson.

    Returns concrete example Q&A pairs that demonstrate the lesson patterns.

    Args:
        course_id: Course identifier (e.g., 'ec1')
        lesson_number: Lesson number (1-25)

    Returns:
        JSON array of example sentences grouped by type
    """
    async with async_session() as session:
        result = await session.execute(
            select(Lesson).where(
                Lesson.course_id == course_id,
                Lesson.lesson_number == lesson_number,
            )
        )
        lesson = result.scalar_one_or_none()

        if not lesson:
            return json.dumps({"error": f"Lesson {lesson_number} not found"})

        examples_result = await session.execute(
            select(ExampleSentence).where(ExampleSentence.lesson_id == lesson.id)
        )
        examples = examples_result.scalars().all()

        return json.dumps({
            "questions": [e.english_text for e in examples if e.sentence_type == "question"],
            "answers": [e.english_text for e in examples if e.sentence_type == "answer"],
            "all": [
                {
                    "text": e.english_text,
                    "type": e.sentence_type,
                    "pattern_id": e.pattern_id,
                }
                for e in examples
            ]
        })


# Audio content directory (relative to project root)
AUDIO_BASE = Path(__file__).parent.parent.parent.parent / "content" / "audio"


@mcp.tool()
async def list_demo_audio(course_id: str, lesson_number: int = None) -> str:
    """List available demo audio files for a course.

    Searches the content/audio directory for generated demo dialogues.

    Args:
        course_id: Course identifier (e.g., 'ec1')
        lesson_number: Optional lesson number to filter by

    Returns:
        JSON array of demo audio metadata
    """
    import glob
    import base64

    demos_dir = AUDIO_BASE / course_id / "demos"
    if not demos_dir.exists():
        return json.dumps([])

    if lesson_number:
        pattern = str(demos_dir / f"lesson-{lesson_number:02d}" / "*.json")
    else:
        pattern = str(demos_dir / "lesson-*" / "*.json")

    demos = []
    for meta_path in glob.glob(pattern):
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            # Add audio path and stream URL
            audio_path = Path(meta_path).with_suffix(".wav")
            meta["audio_path"] = str(audio_path)
            meta["has_audio"] = audio_path.exists()
            demos.append(meta)
        except Exception:
            continue

    # Sort by lesson_number, pattern_number, example_index
    demos.sort(key=lambda d: (
        d.get("lesson_number", 0),
        d.get("pattern_number", 0),
        d.get("example_index", 0),
    ))

    return json.dumps(demos)


@mcp.tool()
async def get_demo_audio(audio_path: str) -> str:
    """Get a specific demo audio file as base64.

    Args:
        audio_path: Full path to the audio file (from list_demo_audio)

    Returns:
        JSON with base64-encoded audio and metadata
    """
    import base64

    audio_path = Path(audio_path)
    if not audio_path.exists():
        return json.dumps({"error": f"Audio file not found: {audio_path}"})

    # Security: Validate path is within expected directory
    try:
        audio_path.resolve().relative_to(AUDIO_BASE.resolve())
    except ValueError:
        return json.dumps({"error": "Invalid audio path"})

    # Read audio file
    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")

    # Load metadata if available
    meta_path = audio_path.with_suffix(".json")
    meta = {}
    if meta_path.exists():
        try:
            with open(meta_path) as f:
                meta = json.load(f)
        except Exception:
            pass

    return json.dumps({
        "audio_base64": audio_b64,
        "format": "wav",
        "sample_rate": meta.get("sample_rate", 24000),
        **meta,
    })


if __name__ == "__main__":
    mcp.run()
