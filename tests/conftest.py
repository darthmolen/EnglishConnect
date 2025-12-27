"""Pytest configuration and fixtures for EnglishConnect tests."""

import asyncio
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src" / "backend"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "services" / "content-mcp"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "tools"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))  # For harness imports


# Test database URL (use test database to avoid polluting dev data)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://englishconnect:devpassword@localhost:5432/englishconnect_test"
)
TEST_DATABASE_URL_SYNC = TEST_DATABASE_URL.replace("+asyncpg", "")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def sync_engine():
    """Create synchronous database engine for setup/teardown."""
    url = TEST_DATABASE_URL_SYNC.replace("englishconnect_test", "englishconnect")
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
async def async_engine():
    """Create async database engine."""
    # First ensure the test database exists
    main_url = TEST_DATABASE_URL.replace("englishconnect_test", "englishconnect")
    main_engine = create_async_engine(main_url, isolation_level="AUTOCOMMIT")

    async with main_engine.connect() as conn:
        # Check if test database exists, create if not
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname='englishconnect_test'")
        )
        if not result.scalar():
            await conn.execute(text("CREATE DATABASE englishconnect_test"))

    await main_engine.dispose()

    # Now connect to test database
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def db_tables(async_engine):
    """Create all database tables."""
    from app.database import Base
    from app.models import (
        Course, Lesson, VocabularyItem, QAPattern, EvaluationCriterion, ExampleSentence,
        User, UserSettings, UserProgress, VocabularyMastery, PracticeSession
    )

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Cleanup after all tests
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(async_engine, db_tables):
    """Create a new database session for each test."""
    async_session = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sample_lesson_markdown():
    """Sample lesson markdown content for testing parser.

    Structure matches real lesson files in content/refined/ec1/books/.../lessons/
    """
    return '''<span id="page-41-0"></span>**LESSON 5**

# **Hobbies and Interests**

**OBJETIVO: APRENDERÉ A HABLAR SOBRE EL POR QUÉ A ALGUIEN LE GUSTA HACER O NO HACER ALGO.**

## Personal Study

## **Study the Principle of Learning: Learn by Study and by Faith**

*In EnglishConnect, we rely on God to learn by study and by faith.*

## **Memorize Vocabulary**

| because       | porque          |
|---------------|-----------------|
| Verbs         |                 |
| exercise      | hacer ejercicio |
| learn English | aprender inglés |

| boring      | aburrido    |
|-------------|-------------|
| cheap       | barato      |
| fun         | divertido   |

## **Practice Pattern 1**

Q: What do you like to do?

A: I like to (*verb*).

Q: Why do you like to (*verb*)?

A: I like to (*verb*) because it's (*adjective*).

## **Examples**

Q: Why do you like to sing?

A: I like to sing because it's fun.

#### Evaluate Your Progress

I can:

• Say why I like something.

• Say why I don't like something.

#### Evaluate Your Efforts
'''


@pytest.fixture
async def sample_course(db_session):
    """Create a sample course for testing."""
    from app.models.content import Course

    course = Course(
        id="test_ec1",
        name="Test EnglishConnect 1",
        description="Test course",
        total_lessons=25
    )
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)
    return course


@pytest.fixture
async def sample_lesson(db_session, sample_course):
    """Create a sample lesson with vocabulary, patterns, and example sentences."""
    from app.models.content import Lesson, VocabularyItem, QAPattern, EvaluationCriterion, ExampleSentence

    lesson = Lesson(
        course_id=sample_course.id,
        lesson_number=5,
        title="Hobbies and Interests",
        objective="Learn to talk about why someone likes or doesn't like something",
        learning_principle="Learn by Study and by Faith",
        learning_principle_title="Learn by Study and by Faith"
    )
    db_session.add(lesson)
    await db_session.flush()

    # Add vocabulary
    vocab_items = [
        VocabularyItem(lesson_id=lesson.id, english_word="because", spanish_translation="porque"),
        VocabularyItem(lesson_id=lesson.id, english_word="exercise", spanish_translation="hacer ejercicio", category="verb"),
        VocabularyItem(lesson_id=lesson.id, english_word="boring", spanish_translation="aburrido", category="adjective"),
        VocabularyItem(lesson_id=lesson.id, english_word="fun", spanish_translation="divertido", category="adjective"),
    ]
    for item in vocab_items:
        db_session.add(item)

    # Add patterns
    pattern = QAPattern(
        lesson_id=lesson.id,
        pattern_number=1,
        question_template="What do you like to do?",
        answer_template="I like to (*verb*).",
        examples=[{"q": "Why do you like to sing?", "a": "I like to sing because it's fun."}]
    )
    db_session.add(pattern)
    await db_session.flush()

    # Add example sentences (extracted from patterns for searchability)
    example_sentences = [
        ExampleSentence(
            lesson_id=lesson.id,
            pattern_id=pattern.id,
            sentence_type="question",
            english_text="Why do you like to sing?"
        ),
        ExampleSentence(
            lesson_id=lesson.id,
            pattern_id=pattern.id,
            sentence_type="answer",
            english_text="I like to sing because it's fun."
        ),
        ExampleSentence(
            lesson_id=lesson.id,
            pattern_id=pattern.id,
            sentence_type="question",
            english_text="Why doesn't she like to cook?"
        ),
        ExampleSentence(
            lesson_id=lesson.id,
            pattern_id=pattern.id,
            sentence_type="answer",
            english_text="She doesn't like to cook because it's difficult."
        ),
    ]
    for example in example_sentences:
        db_session.add(example)

    # Add evaluation criteria
    criteria = [
        EvaluationCriterion(lesson_id=lesson.id, criterion="Say why I like something.", sort_order=0),
        EvaluationCriterion(lesson_id=lesson.id, criterion="Say why I don't like something.", sort_order=1),
    ]
    for c in criteria:
        db_session.add(c)

    await db_session.commit()
    await db_session.refresh(lesson)
    return lesson
