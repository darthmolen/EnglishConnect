#!/usr/bin/env python3
"""Content ingestion script to parse lesson markdown files into the database.

Usage:
    python src/tools/content_ingestion.py --course ec1 --lessons-dir content/refined/ec1/books/englishconnect_1_para_los_alumnos/lessons
"""

import argparse
import asyncio
import re
from pathlib import Path

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import Base
from app.models.content import Course, Lesson, VocabularyItem, QAPattern, EvaluationCriterion, ExampleSentence


class LessonParser:
    """Parse lesson markdown files and extract structured content."""

    def __init__(self, markdown_content: str, lesson_number: int):
        self.content = markdown_content
        self.lesson_number = lesson_number

    def parse(self) -> dict:
        """Parse the markdown and return structured lesson data."""
        return {
            "lesson_number": self.lesson_number,
            "title": self._extract_title(),
            "objective": self._extract_objective(),
            "learning_principle_title": self._extract_principle_title(),
            "learning_principle": self._extract_principle_content(),
            "vocabulary": self._extract_vocabulary(),
            "qa_patterns": self._extract_patterns(),
            "evaluation_criteria": self._extract_criteria(),
        }

    def _extract_title(self) -> str:
        """Extract lesson title from markdown."""
        # Look for # **Title** pattern after LESSON X
        match = re.search(r"# \*\*(.+?)\*\*", self.content)
        if match:
            return match.group(1).strip()
        return f"Lesson {self.lesson_number}"

    def _extract_objective(self) -> str | None:
        """Extract lesson objective (OBJETIVO line)."""
        match = re.search(r"\*\*OBJETIVO:\s*(.+?)\*\*", self.content)
        if match:
            return match.group(1).strip()
        return None

    def _extract_principle_title(self) -> str | None:
        """Extract learning principle title."""
        match = re.search(
            r"Study the Principle of Learning:\s*(.+?)(?:\*\*|\n)", self.content
        )
        if match:
            return match.group(1).strip()
        return None

    def _extract_principle_content(self) -> str | None:
        """Extract learning principle content (italicized text after title)."""
        match = re.search(
            r"Study the Principle of Learning:.+?\n\n\*(.+?)\*\n", self.content, re.DOTALL
        )
        if match:
            return match.group(1).strip()
        return None

    def _extract_vocabulary(self) -> list[dict]:
        """Extract vocabulary tables from markdown."""
        vocabulary = []

        # Find vocabulary tables (| english | spanish | format)
        table_pattern = r"\|([^|]+)\|([^|]+)\|"

        # Find the Memorize Vocabulary section - capture until Practice Pattern 1
        vocab_section = re.search(
            r"## \*\*Memorize Vocabulary\*\*(.+?)(?=## \*\*Practice Pattern|\Z)",
            self.content,
            re.DOTALL,
        )

        if vocab_section:
            section_text = vocab_section.group(1)

            # Extract table rows
            for match in re.finditer(table_pattern, section_text):
                english = match.group(1).strip()
                spanish = match.group(2).strip()
                word_pos = match.start()

                # Skip header rows and empty rows
                if english and spanish and english != "---" and not english.startswith("-"):
                    # Skip category headers like "Verbs", "Nouns", "Adjectives"
                    if spanish and not spanish.isspace():
                        vocabulary.append({
                            "english_word": english,
                            "spanish_translation": spanish,
                            "category": self._guess_category_at_pos(word_pos, section_text),
                        })

        return vocabulary

    # Category patterns to look for (ordered by specificity)
    CATEGORY_PATTERNS = [
        ("Verbs", "verb"),
        ("Nouns 1", "noun"),
        ("Nouns 2", "noun"),
        ("Nouns", "noun"),
        ("Adjectives", "adjective"),
        ("Adverbs", "adverb"),
        ("Prepositions", "preposition"),
        ("Pronouns", "pronoun"),
        ("Phrases", "phrase"),
        ("Question Words", "question_word"),
        ("Time", "time"),
        ("Days", "day"),
        ("Numbers", "number"),
        ("Price", "price"),
        ("Symbols", "symbol"),
        ("Colors", "color"),
        ("Places", "place"),
        ("Food", "food"),
        ("Clothing", "clothing"),
        ("Body Parts", "body_part"),
        ("Family", "family"),
        ("Occupations", "occupation"),
    ]

    def _guess_category_at_pos(self, word_pos: int, context: str) -> str | None:
        """Guess the category based on the word's position in context.

        Looks for ### **Category** headers that appear before the word position.
        """
        # Find the closest category header that appears BEFORE this word
        best_match = None
        best_pos = -1

        for cat_name, cat_value in self.CATEGORY_PATTERNS:
            # Look for ### **Category** pattern
            pattern = rf"###\s*\*\*{cat_name}"
            for match in re.finditer(pattern, context, re.IGNORECASE):
                cat_pos = match.start()
                # Category must appear before word and be closer than any previous match
                if cat_pos < word_pos and cat_pos > best_pos:
                    best_pos = cat_pos
                    best_match = cat_value

        return best_match

    def _guess_category(self, word: str, context: str) -> str | None:
        """Guess the category of a vocabulary word based on context.

        Looks for ### **Category** headers that appear before the word.
        Deprecated: use _guess_category_at_pos when position is known.
        """
        word_pos = context.find(word)
        if word_pos == -1:
            return None

        return self._guess_category_at_pos(word_pos, context)

    def _extract_patterns(self) -> list[dict]:
        """Extract Q&A patterns from markdown."""
        patterns = []

        # Look for Practice Pattern sections
        pattern_sections = re.finditer(
            r"## \*\*Practice Pattern (\d+)\*\*(.+?)(?=## |\Z)",
            self.content,
            re.DOTALL,
        )

        for match in pattern_sections:
            pattern_num = int(match.group(1))
            section_text = match.group(2)

            # Extract Q: and A: lines
            q_match = re.search(r"Q:\s*(.+?)(?:\n|$)", section_text)
            a_match = re.search(r"A:\s*(.+?)(?:\n|$)", section_text)

            if q_match and a_match:
                patterns.append({
                    "pattern_number": pattern_num,
                    "question_template": q_match.group(1).strip(),
                    "answer_template": a_match.group(1).strip(),
                    "examples": None,  # Will be populated below
                })

        # Look for separate Examples sections (may be outside Pattern sections)
        examples_section = re.search(
            r"## \*\*Examples\*\*(.+?)(?=## |\Z)",
            self.content,
            re.DOTALL,
        )

        if examples_section:
            section_text = examples_section.group(1)
            # Extract Q/A pairs from Examples section
            example_pairs = re.findall(
                r"Q:\s*(.+?)\n+A:\s*(.+?)(?:\n|$)",
                section_text,
            )
            examples = [{"q": q.strip(), "a": a.strip()} for q, a in example_pairs]

            # Associate examples with the first pattern (most common case)
            if examples and patterns:
                patterns[0]["examples"] = examples

        return patterns

    def _extract_criteria(self) -> list[str]:
        """Extract evaluation criteria ('I can:' statements)."""
        criteria = []

        # Find the Evaluate Your Progress section
        eval_section = re.search(
            r"Evaluate Your Progress(.+?)(?=Evaluate Your Efforts|\Z)",
            self.content,
            re.DOTALL,
        )

        if eval_section:
            section_text = eval_section.group(1)
            # Find bullet points starting with "Say", "Ask", etc.
            for match in re.finditer(r"[•\*]\s*(.+?)(?:\n|$)", section_text):
                criterion = match.group(1).strip()
                if criterion and not criterion.startswith("!"):  # Skip image refs
                    criteria.append(criterion)

        return criteria


async def ingest_course(
    session: AsyncSession,
    course_id: str,
    course_name: str,
    lessons_dir: Path,
) -> None:
    """Ingest all lessons from a directory into the database."""

    # Create or update course
    result = await session.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()

    if not course:
        course = Course(id=course_id, name=course_name, total_lessons=0)
        session.add(course)

    # Find all lesson files
    lesson_files = sorted(lessons_dir.glob("lesson-*.md"))
    print(f"Found {len(lesson_files)} lesson files")

    for lesson_file in lesson_files:
        # Extract lesson number from filename
        match = re.search(r"lesson-(\d+)\.md", lesson_file.name)
        if not match:
            print(f"Skipping {lesson_file.name} - doesn't match pattern")
            continue

        lesson_number = int(match.group(1))
        print(f"Processing lesson {lesson_number}...")

        # Read and parse markdown
        content = lesson_file.read_text(encoding="utf-8")
        parser = LessonParser(content, lesson_number)
        lesson_data = parser.parse()

        # Check if lesson already exists
        result = await session.execute(
            select(Lesson).where(
                Lesson.course_id == course_id,
                Lesson.lesson_number == lesson_number,
            )
        )
        lesson = result.scalar_one_or_none()

        if lesson:
            # Update existing lesson
            lesson.title = lesson_data["title"]
            lesson.objective = lesson_data["objective"]
            lesson.learning_principle = lesson_data["learning_principle"]
            lesson.learning_principle_title = lesson_data["learning_principle_title"]
            lesson.content_path = str(lesson_file.relative_to(lessons_dir.parent.parent.parent.parent))
        else:
            # Create new lesson
            lesson = Lesson(
                course_id=course_id,
                lesson_number=lesson_number,
                title=lesson_data["title"],
                objective=lesson_data["objective"],
                learning_principle=lesson_data["learning_principle"],
                learning_principle_title=lesson_data["learning_principle_title"],
                content_path=str(lesson_file.relative_to(lessons_dir.parent.parent.parent.parent)),
            )
            session.add(lesson)
            await session.flush()  # Get the lesson ID

        # Clear existing child records for this lesson (makes ingestion idempotent)
        await session.execute(
            delete(ExampleSentence).where(ExampleSentence.lesson_id == lesson.id)
        )
        await session.execute(
            delete(QAPattern).where(QAPattern.lesson_id == lesson.id)
        )
        await session.execute(
            delete(VocabularyItem).where(VocabularyItem.lesson_id == lesson.id)
        )
        await session.execute(
            delete(EvaluationCriterion).where(EvaluationCriterion.lesson_id == lesson.id)
        )

        # Add vocabulary items
        for vocab in lesson_data["vocabulary"]:
            vocab_item = VocabularyItem(
                lesson_id=lesson.id,
                english_word=vocab["english_word"],
                spanish_translation=vocab["spanish_translation"],
                category=vocab.get("category"),
            )
            session.add(vocab_item)

        # Add Q&A patterns and extract example sentences
        example_count = 0
        for pattern in lesson_data["qa_patterns"]:
            qa_pattern = QAPattern(
                lesson_id=lesson.id,
                pattern_number=pattern["pattern_number"],
                question_template=pattern["question_template"],
                answer_template=pattern["answer_template"],
                examples=pattern.get("examples"),
            )
            session.add(qa_pattern)
            await session.flush()  # Get the pattern ID

            # Extract example sentences for searchability
            if pattern.get("examples"):
                for example in pattern["examples"]:
                    # Store question as example sentence
                    if example.get("q"):
                        session.add(ExampleSentence(
                            lesson_id=lesson.id,
                            pattern_id=qa_pattern.id,
                            sentence_type="question",
                            english_text=example["q"],
                        ))
                        example_count += 1
                    # Store answer as example sentence
                    if example.get("a"):
                        session.add(ExampleSentence(
                            lesson_id=lesson.id,
                            pattern_id=qa_pattern.id,
                            sentence_type="answer",
                            english_text=example["a"],
                        ))
                        example_count += 1

        # Add evaluation criteria
        for i, criterion in enumerate(lesson_data["evaluation_criteria"]):
            eval_criterion = EvaluationCriterion(
                lesson_id=lesson.id,
                criterion=criterion,
                sort_order=i,
            )
            session.add(eval_criterion)

        print(f"  - Title: {lesson_data['title']}")
        print(f"  - Vocabulary: {len(lesson_data['vocabulary'])} items")
        print(f"  - Patterns: {len(lesson_data['qa_patterns'])}")
        print(f"  - Example sentences: {example_count}")
        print(f"  - Criteria: {len(lesson_data['evaluation_criteria'])}")

    # Update course total lessons
    course.total_lessons = len(lesson_files)

    await session.commit()
    print(f"\nIngested {len(lesson_files)} lessons for course {course_id}")


async def main():
    parser = argparse.ArgumentParser(description="Ingest lesson content into database")
    parser.add_argument("--course", default="ec1", help="Course ID (default: ec1)")
    parser.add_argument("--course-name", default="EnglishConnect 1", help="Course name")
    parser.add_argument(
        "--lessons-dir",
        default="content/refined/ec1/books/englishconnect_1_para_los_alumnos/lessons",
        help="Path to lessons directory",
    )
    parser.add_argument(
        "--database-url",
        default="postgresql+asyncpg://englishconnect:devpassword@localhost:5432/englishconnect",
        help="Database URL",
    )
    args = parser.parse_args()

    # Create engine and session
    engine = create_async_engine(args.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ingest content
    lessons_path = Path(args.lessons_dir)
    if not lessons_path.exists():
        print(f"Error: Lessons directory not found: {lessons_path}")
        return

    async with async_session() as session:
        await ingest_course(session, args.course, args.course_name, lessons_path)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
