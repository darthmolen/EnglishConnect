"""Service for retrieving teaching help content when students struggle.

Provides vocabulary, patterns, workbook exercises, and lesson explanations
from multiple sources to help the agent adapt to student confusion.
"""

import re
from pathlib import Path
from typing import Optional

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import VocabularyItem, QAPattern, Lesson


# Category mappings for natural language queries
CATEGORY_MAP = {
    # Spanish
    "sustantivos": "noun",
    "sustantivo": "noun",
    "verbos": "verb",
    "verbo": "verb",
    "adjetivos": "adjective",
    "adjetivo": "adjective",
    # English
    "nouns": "noun",
    "noun": "noun",
    "verbs": "verb",
    "verb": "verb",
    "adjectives": "adjective",
    "adjective": "adjective",
}

# Keywords that indicate user wants patterns, not vocabulary
PATTERN_KEYWORDS = {
    "frases", "frase", "patrones", "patron", "patrón",
    "patterns", "pattern", "phrases", "phrase",
    "sentences", "sentence", "oraciones", "oracion", "oración",
}


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

    def _parse_query(self, query: str) -> dict:
        """Parse natural language query into structured search parameters.

        Extracts lesson numbers and category keywords from queries like:
        - "sustantivos lección 6" → lesson_filters=[6], category="noun"
        - "nouns from lesson 6" → lesson_filters=[6], category="noun"
        - "frases de leccion 6 y 7" → lesson_filters=[6, 7], wants_patterns=True
        - "what does brother mean" → lesson_filters=[], category=None, keywords=["brother"]

        Args:
            query: Natural language query string

        Returns:
            Dict with keys: lesson_filters, category, keywords, wants_patterns
        """
        result = {
            "lesson_filters": [],  # Now a list to support "lesson 6 y 7"
            "category": None,
            "keywords": [],
            "wants_patterns": False,  # True when user asks for frases/patterns
        }

        query_lower = query.lower()

        # Extract all lesson numbers: "lección 6 y 7", "lessons 6 and 7"
        # Matches: lecci[oó]n 6, lesson 6, etc.
        lesson_matches = re.findall(r'lecci[oó]n\s+(\d+)|lesson\s+(\d+)|(?<=\s)(\d+)(?=\s*(?:y|and|\s|$))', query_lower)
        for match in lesson_matches:
            # Each match is a tuple, one group will have the number
            num = next((g for g in match if g), None)
            if num:
                lesson_num = int(num)
                if lesson_num not in result["lesson_filters"]:
                    result["lesson_filters"].append(lesson_num)

        # Check if user wants patterns (frases, patrones, etc.)
        for pattern_kw in PATTERN_KEYWORDS:
            if pattern_kw in query_lower:
                result["wants_patterns"] = True
                break

        # Extract category from keywords (only if NOT asking for patterns)
        if not result["wants_patterns"]:
            for keyword, category in CATEGORY_MAP.items():
                if keyword in query_lower:
                    result["category"] = category
                    break

        # Extract remaining keywords (words not matching lesson/category/pattern patterns)
        cleaned = re.sub(r'lecci[oó]n\s+\d+|lesson\s+\d+', '', query_lower)
        for cat_word in CATEGORY_MAP.keys():
            cleaned = cleaned.replace(cat_word, '')
        for pat_kw in PATTERN_KEYWORDS:
            cleaned = cleaned.replace(pat_kw, '')
        # Remove common filler words
        cleaned = re.sub(r'\b(de|la|el|los|las|from|the|of|and|y|dame|give|me|show|muestra|muéstrame)\b', '', cleaned)
        # Extract remaining words
        words = [w.strip() for w in cleaned.split() if w.strip()]
        result["keywords"] = words

        # Backward compatibility: set lesson_filter to first lesson if any
        result["lesson_filter"] = result["lesson_filters"][0] if result["lesson_filters"] else None

        return result

    async def search_cumulative_vocab(
        self,
        query: str,
        up_to_lesson: int,
        limit: int = 5,
        lesson_filter: Optional[int] = None,
        category: Optional[str] = None,
    ) -> list[VocabularyItem]:
        """Search vocabulary from lessons, with optional lesson/category filters.

        Args:
            query: Search term (matches English word or Spanish translation)
            up_to_lesson: Maximum lesson number to include
            limit: Maximum results to return
            lesson_filter: If set, only search this specific lesson
            category: If set, only return vocab with this category (noun, verb, etc.)

        Returns:
            List of matching VocabularyItem objects
        """
        if not self.session:
            return []

        # Determine which lessons to search
        if lesson_filter is not None:
            # Search only the specified lesson
            lesson_result = await self.session.execute(
                select(Lesson.id).where(
                    Lesson.course_id == "ec1",
                    Lesson.lesson_number == lesson_filter
                )
            )
        else:
            # Search all lessons up to the specified number
            lesson_result = await self.session.execute(
                select(Lesson.id).where(
                    Lesson.course_id == "ec1",
                    Lesson.lesson_number <= up_to_lesson
                )
            )
        lesson_ids = [row[0] for row in lesson_result.fetchall()]

        if not lesson_ids:
            return []

        # Build where conditions
        conditions = [VocabularyItem.lesson_id.in_(lesson_ids)]

        # Add category filter if specified
        if category:
            conditions.append(VocabularyItem.category == category)

        # Add keyword search only if there are actual keywords to search
        # (not if the query is just category/lesson references)
        parsed = self._parse_query(query)
        if parsed["keywords"]:
            # Search by remaining keywords
            keyword_conditions = []
            for keyword in parsed["keywords"]:
                keyword_pattern = f"%{keyword}%"
                keyword_conditions.append(
                    or_(
                        VocabularyItem.english_word.ilike(keyword_pattern),
                        VocabularyItem.spanish_translation.ilike(keyword_pattern),
                    )
                )
            if keyword_conditions:
                conditions.append(or_(*keyword_conditions))

        # If we have category or lesson filter but no keywords, return all matching
        # Otherwise we'd return nothing for "sustantivos lección 6"
        result = await self.session.execute(
            select(VocabularyItem)
            .where(and_(*conditions))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_patterns(
        self,
        query: str,
        up_to_lesson: int,
        limit: int = 10,
        lesson_filters: Optional[list[int]] = None,
        list_all: bool = False,
    ) -> list[QAPattern]:
        """Search Q&A patterns from lessons.

        Args:
            query: Search term (matches question/answer templates)
            up_to_lesson: Maximum lesson number to include (used if lesson_filters empty)
            limit: Maximum results to return
            lesson_filters: If set, only search these specific lessons
            list_all: If True, return all patterns without keyword filtering

        Returns:
            List of matching QAPattern objects
        """
        if not self.session:
            return []

        # Determine which lessons to search
        if lesson_filters:
            # Search specific lessons
            lesson_result = await self.session.execute(
                select(Lesson.id, Lesson.lesson_number).where(
                    Lesson.course_id == "ec1",
                    Lesson.lesson_number.in_(lesson_filters)
                )
            )
        else:
            # Search all lessons up to the specified number
            lesson_result = await self.session.execute(
                select(Lesson.id, Lesson.lesson_number).where(
                    Lesson.course_id == "ec1",
                    Lesson.lesson_number <= up_to_lesson
                )
            )
        lesson_ids = [row[0] for row in lesson_result.fetchall()]

        if not lesson_ids:
            return []

        # Build query
        if list_all:
            # Return all patterns for the lessons (no keyword filtering)
            result = await self.session.execute(
                select(QAPattern)
                .where(QAPattern.lesson_id.in_(lesson_ids))
                .limit(limit)
            )
        else:
            # Search patterns by keyword
            query_lower = f"%{query.lower()}%"
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

        Parses natural language queries to extract:
        - Lesson numbers: "lección 6 y 7" → filter to lessons 6 and 7
        - Categories: "sustantivos" → filter to category="noun"
        - Pattern requests: "frases" → return patterns, not vocabulary

        Args:
            query: What the student is confused about
            lesson_number: Current lesson number (searches up to this lesson)

        Returns:
            Dict with keys: vocabulary, patterns, exercises, explanation, source
        """
        # Parse query to extract structured search parameters
        parsed = self._parse_query(query)

        vocab_list = []
        pattern_list = []

        if parsed["wants_patterns"]:
            # User asked for patterns/frases - search both Q&A patterns AND phrase vocabulary
            patterns = await self.search_patterns(
                query=query,
                up_to_lesson=lesson_number,
                lesson_filters=parsed["lesson_filters"] if parsed["lesson_filters"] else None,
                list_all=True,  # Get all patterns for the lesson(s)
                limit=20,  # Higher limit for listing
            )
            pattern_list = [
                {
                    "question": p.question_template,
                    "answer": p.answer_template,
                    "examples": p.examples[:2] if p.examples else [],
                }
                for p in patterns
            ]

            # Also get vocabulary items with "phrase" category (multi-word expressions)
            # These are stored in vocabulary but are phrases like "Tell me about..."
            vocabulary = await self.search_cumulative_vocab(
                query=query,
                up_to_lesson=lesson_number,
                lesson_filter=parsed["lesson_filter"],
                category="phrase",  # Filter to phrase category
            )
            vocab_list = [
                {
                    "english": v.english_word,
                    "spanish": v.spanish_translation,
                    "category": v.category,
                }
                for v in vocabulary
            ]
        else:
            # Search DB for vocabulary with parsed filters
            vocabulary = await self.search_cumulative_vocab(
                query=query,
                up_to_lesson=lesson_number,
                lesson_filter=parsed["lesson_filter"],
                category=parsed["category"],
            )
            vocab_list = [
                {
                    "english": v.english_word,
                    "spanish": v.spanish_translation,
                    "category": v.category,
                }
                for v in vocabulary
            ]

            # Also search patterns by keyword (not listing all)
            patterns = await self.search_patterns(query, lesson_number)
            pattern_list = [
                {
                    "question": p.question_template,
                    "answer": p.answer_template,
                    "examples": p.examples[:2] if p.examples else [],
                }
                for p in patterns
            ]

        # Get workbook exercises and lesson explanation (file-based)
        exercises = self.get_workbook_exercises(lesson_number, query)
        explanation = self.get_lesson_explanation(lesson_number, query)

        # Build source string
        if parsed["lesson_filters"]:
            source = f"lessons-{'-'.join(str(l) for l in parsed['lesson_filters'])}"
        else:
            source = f"lesson-{lesson_number}"

        return {
            "vocabulary": vocab_list,
            "patterns": pattern_list,
            "exercises": exercises,
            "explanation": explanation,
            "source": source,
        }
