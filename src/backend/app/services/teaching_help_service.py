"""Service for retrieving teaching help content when students struggle.

Provides vocabulary, patterns, workbook exercises, and lesson explanations
from multiple sources to help the agent adapt to student confusion.
"""

import re
from pathlib import Path
from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import VocabularyItem, QAPattern, Lesson


# Content paths
CONTENT_BASE = Path(__file__).parent.parent.parent.parent.parent.parent / "content" / "refined"
WORKBOOK_PATH = CONTENT_BASE / "ec1" / "books" / "englishconnect_workbook_1" / "lessons"
LESSON_PATH = CONTENT_BASE / "ec1" / "books" / "englishconnect_1_para_los_alumnos" / "lessons"


class TeachingHelpService:
    """Service for retrieving adaptive teaching content.

    Searches vocabulary, patterns, workbook exercises, and lesson explanations
    to provide context when students struggle.
    """

    def __init__(self, session: Optional[AsyncSession]):
        """Initialize with database session.

        Args:
            session: Async database session. Can be None for file-only operations.
        """
        self.session = session

    async def search_cumulative_vocab(
        self, query: str, up_to_lesson: int, limit: int = 5
    ) -> list[VocabularyItem]:
        """Search vocabulary from all lessons up to specified lesson number.

        Args:
            query: Search term (matches English word or Spanish translation)
            up_to_lesson: Maximum lesson number to include
            limit: Maximum results to return

        Returns:
            List of matching VocabularyItem objects
        """
        if not self.session:
            return []

        # Build query with ILIKE for case-insensitive partial matching
        query_lower = f"%{query.lower()}%"

        # Get lesson IDs for lessons up to the specified number
        lesson_result = await self.session.execute(
            select(Lesson.id).where(
                Lesson.course_id == "ec1",
                Lesson.lesson_number <= up_to_lesson
            )
        )
        lesson_ids = [row[0] for row in lesson_result.fetchall()]

        if not lesson_ids:
            return []

        # Search vocabulary in those lessons
        result = await self.session.execute(
            select(VocabularyItem)
            .where(
                VocabularyItem.lesson_id.in_(lesson_ids),
                or_(
                    VocabularyItem.english_word.ilike(query_lower),
                    VocabularyItem.spanish_translation.ilike(query_lower),
                )
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_patterns(
        self, query: str, up_to_lesson: int, limit: int = 3
    ) -> list[QAPattern]:
        """Search Q&A patterns from all lessons up to specified lesson number.

        Args:
            query: Search term (matches question/answer templates)
            up_to_lesson: Maximum lesson number to include
            limit: Maximum results to return

        Returns:
            List of matching QAPattern objects
        """
        if not self.session:
            return []

        query_lower = f"%{query.lower()}%"

        # Get lesson IDs for lessons up to the specified number
        lesson_result = await self.session.execute(
            select(Lesson.id).where(
                Lesson.course_id == "ec1",
                Lesson.lesson_number <= up_to_lesson
            )
        )
        lesson_ids = [row[0] for row in lesson_result.fetchall()]

        if not lesson_ids:
            return []

        # Search patterns in those lessons
        result = await self.session.execute(
            select(QAPattern)
            .where(
                QAPattern.lesson_id.in_(lesson_ids),
                or_(
                    QAPattern.question_template.ilike(query_lower),
                    QAPattern.answer_template.ilike(query_lower),
                )
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    def _load_workbook_content(self, lesson: int) -> Optional[str]:
        """Load workbook markdown content for a lesson.

        Args:
            lesson: Lesson number

        Returns:
            Markdown content or None if file doesn't exist
        """
        file_path = WORKBOOK_PATH / f"lesson-{lesson:02d}.md"
        if not file_path.exists():
            return None
        return file_path.read_text(encoding="utf-8")

    def _load_lesson_content(self, lesson: int) -> Optional[str]:
        """Load lesson markdown content.

        Args:
            lesson: Lesson number

        Returns:
            Markdown content or None if file doesn't exist
        """
        file_path = LESSON_PATH / f"lesson-{lesson:02d}.md"
        if not file_path.exists():
            return None
        return file_path.read_text(encoding="utf-8")

    def _parse_workbook_activities(self, content: str) -> list[dict]:
        """Extract activity sections from workbook markdown.

        Args:
            content: Raw markdown content

        Returns:
            List of dicts with 'title' and 'content' keys
        """
        activities = []

        # Split by ACTIVITY headers (e.g., "### **ACTIVITY 2: ..." or "# **ACTIVITY ...")
        pattern = r'(?:###?\s*\*{0,2}ACTIVITY\s*\d*:?\s*)(.*?)(?=###?\s*\*{0,2}ACTIVITY|\Z)'
        matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)

        for match in matches:
            activity_content = match.group(0).strip()
            # Extract title from first line
            lines = activity_content.split('\n')
            if lines:
                title_match = re.search(r'ACTIVITY\s*\d*:?\s*(.+?)(?:\*{0,2}\s*$)', lines[0], re.IGNORECASE)
                title = title_match.group(1).strip() if title_match else "Activity"
                activities.append({
                    "title": title,
                    "content": '\n'.join(lines[1:]).strip()[:500]  # Limit content size
                })

        return activities

    def get_workbook_exercises(self, lesson: int, topic: str) -> list[dict]:
        """Get workbook exercises for a lesson, filtered by topic.

        Args:
            lesson: Lesson number
            topic: Topic to filter by (searches activity titles and content)

        Returns:
            List of matching exercise dicts with 'title' and 'content'
        """
        content = self._load_workbook_content(lesson)
        if not content:
            return []

        activities = self._parse_workbook_activities(content)

        # Filter by topic (case-insensitive search in title and content)
        topic_lower = topic.lower()
        matching = [
            a for a in activities
            if topic_lower in a["title"].lower() or topic_lower in a.get("content", "").lower()
        ]

        # If no topic matches, return first few activities as general help
        if not matching and activities:
            return activities[:2]

        return matching[:3]  # Limit to 3 exercises

    def get_lesson_explanation(self, lesson: int, topic: str) -> Optional[str]:
        """Get relevant explanation section from lesson markdown.

        Args:
            lesson: Lesson number
            topic: Topic to search for

        Returns:
            Relevant section content or None if not found
        """
        content = self._load_lesson_content(lesson)
        if not content:
            return None

        topic_lower = topic.lower()

        # Look for section headers that match the topic
        sections = re.split(r'\n##\s+', content)

        for section in sections:
            if topic_lower in section.lower()[:200]:  # Check first 200 chars
                # Return first 500 chars of matching section
                return section.strip()[:500]

        # If no section match, try to find relevant paragraph
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if topic_lower in para.lower():
                return para.strip()[:500]

        return None

    async def get_teaching_help(
        self, query: str, lesson_number: int
    ) -> dict:
        """Get comprehensive teaching help from all sources.

        This is the main method called by the get_teaching_help tool.
        Combines vocabulary, patterns, exercises, and explanations.

        Args:
            query: What the student is confused about
            lesson_number: Current lesson number (searches up to this lesson)

        Returns:
            Dict with keys: vocabulary, patterns, exercises, explanation, source
        """
        # Search DB for vocabulary and patterns
        vocabulary = await self.search_cumulative_vocab(query, lesson_number)
        patterns = await self.search_patterns(query, lesson_number)

        # Get workbook exercises and lesson explanation (file-based)
        exercises = self.get_workbook_exercises(lesson_number, query)
        explanation = self.get_lesson_explanation(lesson_number, query)

        # Transform DB results to serializable dicts
        vocab_list = [
            {
                "english": v.english_word,
                "spanish": v.spanish_translation,
                "category": v.category,
            }
            for v in vocabulary
        ]

        pattern_list = [
            {
                "question": p.question_template,
                "answer": p.answer_template,
                "examples": p.examples[:2] if p.examples else [],
            }
            for p in patterns
        ]

        return {
            "vocabulary": vocab_list,
            "patterns": pattern_list,
            "exercises": exercises,
            "explanation": explanation,
            "source": f"lesson-{lesson_number}",
        }
