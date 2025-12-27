"""Shared fixtures for agent integration tests.

These tests require Azure OpenAI credentials and make real API calls.
They are skipped if credentials are not available.
"""

import os
import sys
from pathlib import Path

import pytest

# Ensure paths are set up for imports (needed for VS Code test discovery)
_project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_project_root / "src" / "backend"))
sys.path.insert(0, str(_project_root / "tests"))

from harness.agent_harness import AgentTestHarness
from app.schemas.lesson import VocabularyItemSchema, QAPatternSchema


# Skip all agent integration tests if no Azure credentials
pytestmark = pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_API_KEY"),
    reason="Azure OpenAI credentials required for agent integration tests"
)


@pytest.fixture
def mock_lesson_vocabulary() -> list[VocabularyItemSchema]:
    """Standard vocabulary for test lessons."""
    return [
        VocabularyItemSchema(english="exercise", spanish="hacer ejercicio", category="hobbies"),
        VocabularyItemSchema(english="sing", spanish="cantar", category="hobbies"),
        VocabularyItemSchema(english="play", spanish="jugar", category="hobbies"),
        VocabularyItemSchema(english="read", spanish="leer", category="hobbies"),
        VocabularyItemSchema(english="cook", spanish="cocinar", category="hobbies"),
    ]


@pytest.fixture
def mock_lesson_patterns() -> list[QAPatternSchema]:
    """Standard Q&A patterns for test lessons."""
    return [
        QAPatternSchema(
            pattern_number=1,
            question_template="What do you like to do?",
            answer_template="I like to [activity].",
        ),
        QAPatternSchema(
            pattern_number=2,
            question_template="Do you like to [activity]?",
            answer_template="Yes, I like to [activity]. / No, I don't like to [activity].",
        ),
    ]


@pytest.fixture
def teacher_harness(
    mock_lesson_vocabulary: list[VocabularyItemSchema],
    mock_lesson_patterns: list[QAPatternSchema],
):
    """Create teacher agent harness with mock lesson data.

    Returns a factory function that creates harnesses.
    Use: harness = teacher_harness(lesson_number=5)
    """
    def _create(
        lesson_number: int = 5,
        title: str = "Hobbies and Interests",
        objective: str = "Learn to talk about hobbies and free-time activities",
    ) -> AgentTestHarness:
        return AgentTestHarness.create_with_mock_lesson(
            lesson_number=lesson_number,
            title=title,
            objective=objective,
            vocabulary=mock_lesson_vocabulary,
            patterns=mock_lesson_patterns,
            agent_type="teacher",
        )

    return _create


@pytest.fixture
def partner_harness(
    mock_lesson_vocabulary: list[VocabularyItemSchema],
    mock_lesson_patterns: list[QAPatternSchema],
):
    """Create conversation partner harness with mock lesson data.

    Returns a factory function that creates harnesses.
    Use: harness = partner_harness(lesson_number=5)
    """
    def _create(
        lesson_number: int = 5,
        title: str = "Hobbies and Interests",
        objective: str = "Learn to talk about hobbies and free-time activities",
    ) -> AgentTestHarness:
        return AgentTestHarness.create_with_mock_lesson(
            lesson_number=lesson_number,
            title=title,
            objective=objective,
            vocabulary=mock_lesson_vocabulary,
            patterns=mock_lesson_patterns,
            agent_type="partner",
        )

    return _create


@pytest.fixture
async def teacher_harness_db():
    """Create teacher agent harness with lesson from database.

    Returns a factory function that creates harnesses asynchronously.
    Use: harness = await teacher_harness_db(lesson_number=5)

    Requires database to be running with lesson data.
    """
    async def _create(
        lesson_number: int = 5,
        course_id: str = "ec1",
    ) -> AgentTestHarness:
        return await AgentTestHarness.create(
            lesson_number=lesson_number,
            course_id=course_id,
            agent_type="teacher",
        )

    return _create
