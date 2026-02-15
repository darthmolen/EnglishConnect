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
from app.models.content import Course, Lesson, VocabularyItem, QAPattern, EvaluationCriterion, ExampleSentence, LessonPhase


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
            "learning_principle_full": self._extract_principle_full(),
            "ponder_questions": self._extract_ponder_questions(),
            "pattern_images": self._extract_pattern_images(),
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

    def _extract_principle_full(self) -> str | None:
        """Extract full learning principle text including all paragraphs.

        Captures text from principle section headers (like "## **Eres un hijo de Dios**")
        until the next major section (Ponder or Memorize).

        Lesson 1 has a separate section header for the principle.
        Lessons 2+ have content directly after the italic summary.
        """
        # First try: Lesson 1 style - separate section header like "## **Eres un hijo de Dios**"
        match = re.search(
            r"#{2,4} \*\*(?:Eres|You Are|El|La|Los|Las|Ser|Tener|Hacer|Escuchar|Hablar|Actuar|Orar|Confiar).+?\*\*\n\n(.+?)(?=#{2,4} \*\*Ponder|#{2,4} \*\*Memorize)",
            self.content,
            re.DOTALL,
        )

        # Fallback: Lessons 2+ style - content after italic summary, before Ponder
        if not match:
            match = re.search(
                r"Study the Principle of Learning:.+?\n\n\*.+?\*\n\n(.+?)(?=#{2,4} \*\*Ponder|#{2,4}\s+\*\*Ponder)",
                self.content,
                re.DOTALL,
            )

        if match:
            # Clean up the text - remove image references and extra whitespace
            text = match.group(1)
            text = re.sub(r"!\[.*?\]\(.*?\)", "", text)  # Remove image refs
            text = re.sub(r"\n{3,}", "\n\n", text)  # Normalize whitespace
            return text.strip()
        return None

    def _extract_ponder_questions(self) -> list[str]:
        """Extract ponder/reflection questions from Ponder section (any header level)."""
        questions = []

        # Find the Ponder section (## to #### header levels)
        ponder_section = re.search(
            r"#{2,4}\s*\*{0,2}Ponder\*{0,2}(.+?)(?=#{2,4}\s|\Z)",
            self.content,
            re.DOTALL,
        )

        if ponder_section:
            section_text = ponder_section.group(1)
            # Find bullet points (- or •)
            for match in re.finditer(r"[-•]\s*(.+?)(?:\n|$)", section_text):
                question = match.group(1).strip()
                if question and not question.startswith("!"):  # Skip image refs
                    questions.append(question)

        return questions

    def _extract_pattern_images(self) -> list[str]:
        """Extract Figure image paths from markdown (not Picture images).

        Figures are typically pattern diagrams, while Pictures are generic photos.
        """
        images = []

        # Find all image references with Figure in the filename (../ prefix optional)
        for match in re.finditer(r"!\[.*?\]\((?:\.\./)?(_page_\d+_Figure_\d+\.jpeg)\)", self.content):
            image_path = match.group(1)
            images.append(image_path)

        return images

    @staticmethod
    def _expand_br_cells(text: str) -> str:
        """Preprocess markdown tables to expand <br>-concatenated cells.

        Marker sometimes squashes multi-row tables into single rows with <br> separators:
        | word1<br>trans1<br>word2<br>trans2 | word3 | trans3 |
        This expands them into proper table rows.
        Also cleans individual <br> in cells (e.g. "send an email<br>message" → "send an email message").
        """
        lines = text.split('\n')
        expanded = []
        for line in lines:
            # Check if this is a table row with a <br>-heavy cell (>4 <br> tags = likely concatenated pairs)
            if line.startswith('|') and '<br>' in line and line.count('<br>') > 4:
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if cells:
                    # Find the cell with many <br> tags
                    br_cell_idx = max(range(len(cells)), key=lambda i: cells[i].count('<br>'))
                    br_cell = cells[br_cell_idx]
                    parts = [p.strip() for p in br_cell.split('<br>') if p.strip()]

                    # Extract en/es pairs from the <br> cell
                    for i in range(0, len(parts) - 1, 2):
                        expanded.append(f"| {parts[i]} | {parts[i + 1]} |")

                    # Also add the remaining normal cells as a separate row
                    other_cells = [c for j, c in enumerate(cells) if j != br_cell_idx]
                    if len(other_cells) >= 2:
                        expanded.append(f"| {other_cells[0]} | {other_cells[1]} |")
                    continue

            # Clean minor <br> in individual cells (e.g., line breaks within a phrase)
            if '<br>' in line and line.startswith('|'):
                line = line.replace('<br>', ' ')
            expanded.append(line)
        return '\n'.join(expanded)

    def _extract_vocabulary(self) -> list[dict]:
        """Extract vocabulary tables from markdown."""
        vocabulary = []

        # Find vocabulary tables (| english | spanish | format)
        table_pattern = r"\|([^|]+)\|([^|]+)\|"

        # Find the Memorize Vocabulary section - capture until Practice Pattern 1
        vocab_section = re.search(
            r"#{1,4}\s*\*{0,2}Memorize Vocabulary\*{0,2}(.+?)(?=#{1,4}\s*\*{0,2}Practice Pattern|\Z)",
            self.content,
            re.DOTALL,
        )

        if vocab_section:
            # Preprocess to expand <br>-concatenated cells (Marker artifact)
            section_text = self._expand_br_cells(vocab_section.group(1))

            # Extract table rows
            for match in re.finditer(table_pattern, section_text):
                english = match.group(1).strip().rstrip('*')  # Remove trailing asterisks
                spanish = match.group(2).strip().rstrip('*')  # Remove trailing asterisks
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
            # Look for ### or #### **Category** pattern
            pattern = rf"#{2,4}\s*\*\*{cat_name}"
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
        """Extract Q&A patterns from markdown.

        Finds each Practice Pattern section and extracts:
        - The Q/A template
        - Examples from the Examples subsection within that pattern's area
        """
        patterns = []

        # Find all pattern header positions (any header level ##-####)
        pattern_headers = list(re.finditer(
            r"#{1,4}\s*\*{0,2}Practice Pattern (\d+)\*{0,2}",
            self.content,
        ))

        for i, match in enumerate(pattern_headers):
            pattern_num = int(match.group(1))
            section_start = match.end()

            # Section ends at next pattern header
            if i + 1 < len(pattern_headers):
                section_end = pattern_headers[i + 1].start()
            else:
                # For last pattern, end at next major section (not Examples/Questions/Answers)
                # Look for headers like "Use the Patterns", "Additional Activities", etc.
                remaining = self.content[section_start:]
                next_major = re.search(
                    r"\n#{1,2} (?!\*{0,2}Examples|\*{0,2}Questions|\*{0,2}Answers)",
                    remaining,
                )
                section_end = section_start + next_major.start() if next_major else len(self.content)

            section_text = self.content[section_start:section_end]

            # Extract pattern template - try Q:/A: first, then A:/B: (dialogue format)
            q_match = re.search(r"Q:\s*(.+?)(?:\n|$)", section_text)
            q_es_match = re.search(r"Q_es:\s*(.+?)(?:\n|$)", section_text)
            a_match = re.search(r"A:\s*(.+?)(?:\n|$)", section_text)
            a_es_match = re.search(r"A_es:\s*(.+?)(?:\n|$)", section_text)

            # Check for A:/B: dialogue format if Q:/A: not found
            is_dialogue = False
            if not q_match:
                q_match = re.search(r"A:\s*(.+?)(?:\n|$)", section_text)
                a_match = re.search(r"B:\s*(.+?)(?:\n|$)", section_text)
                is_dialogue = True

            if q_match and a_match:
                pattern_data = {
                    "pattern_number": pattern_num,
                    "question_template": q_match.group(1).strip(),
                    "question_template_es": q_es_match.group(1).strip() if q_es_match else None,
                    "answer_template": a_match.group(1).strip(),
                    "answer_template_es": a_es_match.group(1).strip() if a_es_match else None,
                    "examples": None,
                }

                # Look for Examples section within this pattern's area
                # Match any header level (##, ###, ####) with or without bold **
                examples_match = re.search(
                    r"#{2,4}\s*\*{0,2}Examples\*{0,2}\s*\n(.+?)(?=#{2,4}\s|\Z)",
                    section_text,
                    re.DOTALL | re.IGNORECASE,
                )

                if examples_match:
                    examples_text = examples_match.group(1)
                    # Extract pairs from Examples section
                    # Handle Q:/A: format with optional Q_es:/A_es: translations
                    if is_dialogue:
                        # A:/B: dialogue format (no Spanish translation support)
                        example_pairs = re.findall(
                            r"(?:^|\n)\s*-?\s*A:\s*(.+?)\n+\s*-?\s*B:\s*(.+?)(?:\n|$)",
                            examples_text,
                        )
                        if example_pairs:
                            pattern_data["examples"] = [
                                {"q": q.strip(), "a": a.strip()}
                                for q, a in example_pairs
                            ]
                    else:
                        # Q:/A: question-answer format with optional Q_es:/A_es:
                        # Match Q: followed optionally by Q_es:, then A: followed optionally by A_es:
                        example_pattern = re.compile(
                            r"(?:^|\n)\s*-?\s*Q:\s*(.+?)\n"  # Q: line
                            r"(?:\s*Q_es:\s*(.+?)\n)?"        # Optional Q_es: line
                            r"\s*-?\s*A:\s*(.+?)"             # A: line
                            r"(?:\n\s*A_es:\s*(.+?))?"        # Optional A_es: line
                            r"(?:\n|$)",
                            re.MULTILINE
                        )
                        example_matches = example_pattern.findall(examples_text)
                        if example_matches:
                            pattern_data["examples"] = [
                                {
                                    "q": q.strip(),
                                    "q_es": q_es.strip() if q_es else None,
                                    "a": a.strip(),
                                    "a_es": a_es.strip() if a_es else None,
                                }
                                for q, q_es, a, a_es in example_matches
                            ]

                patterns.append(pattern_data)

        return patterns

    def _find_best_pattern_for_examples(
        self, examples: list[dict], patterns: list[dict]
    ) -> int:
        """Find which pattern the examples best match based on keywords.

        Extracts key question words from pattern templates and examples,
        then scores each pattern by how many examples match its keywords.
        """
        if len(patterns) == 1:
            return 0

        # Extract first significant word from each pattern's question template
        pattern_keywords = []
        for p in patterns:
            q_template = p.get("question_template", "").lower()
            # Get the first question word (What, Why, Do, Does, etc.)
            words = q_template.split()
            keyword = words[0] if words else ""
            pattern_keywords.append(keyword)

        # Score each pattern by counting matching examples
        scores = [0] * len(patterns)
        for example in examples:
            example_q = example.get("q", "").lower()
            first_word = example_q.split()[0] if example_q.split() else ""

            for i, keyword in enumerate(pattern_keywords):
                if keyword and first_word == keyword:
                    scores[i] += 1

        # Return pattern with highest score, defaulting to first if tied
        max_score = max(scores) if scores else 0
        if max_score > 0:
            return scores.index(max_score)
        return 0

    def _extract_criteria(self) -> list[dict]:
        """Extract evaluation criteria ('I can:' statements) with Spanish translations.

        Returns list of dicts with 'criterion' (English) and 'criterion_es' (Spanish).
        """
        criteria = []

        # Find the Evaluate Your Progress section
        eval_section = re.search(
            r"Evaluate Your Progress(.+?)(?=Evaluate Your Efforts|\Z)",
            self.content,
            re.DOTALL,
        )

        if eval_section:
            section_text = eval_section.group(1)
            # Find bullet points, collecting English and optional Spanish translation
            # Format: • English criterion
            #         • _es: Spanish translation (optional)
            lines = section_text.split('\n')
            current_criterion = None

            for line in lines:
                line = line.strip()
                # Check for Spanish translation line
                if line.startswith('• _es:') or line.startswith('* _es:'):
                    if current_criterion:
                        current_criterion['criterion_es'] = line[6:].strip()
                # Check for English criterion line
                elif line.startswith('•') or line.startswith('*'):
                    text = line[1:].strip()
                    # Skip image refs, short entries, and asterisk-only entries
                    if text and not text.startswith('!') and not text.startswith('_es:') and len(text) > 2:
                        # Save previous criterion if exists
                        if current_criterion:
                            criteria.append(current_criterion)
                        current_criterion = {'criterion': text, 'criterion_es': None}

            # Don't forget the last criterion
            if current_criterion:
                criteria.append(current_criterion)

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
            lesson.learning_principle_full = lesson_data["learning_principle_full"]
            lesson.ponder_questions = lesson_data["ponder_questions"]
            lesson.pattern_images = lesson_data["pattern_images"]
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
                learning_principle_full=lesson_data["learning_principle_full"],
                ponder_questions=lesson_data["ponder_questions"],
                pattern_images=lesson_data["pattern_images"],
                content_path=str(lesson_file.relative_to(lessons_dir.parent.parent.parent.parent)),
            )
            session.add(lesson)
            await session.flush()  # Get the lesson ID

            # Create default phases for new lesson
            default_phases = [
                ("intro", "Introduction", 0),
                ("vocabulary", "Vocabulary", 1),
                ("patterns", "Q&A Patterns", 2),
                ("practice", "Practice", 3),
                ("wrapup", "Wrap-up", 4),
            ]
            for phase_type, phase_name, sort_order in default_phases:
                phase = LessonPhase(
                    lesson_id=lesson.id,
                    phase_type=phase_type,
                    phase_name=phase_name,
                    sort_order=sort_order,
                )
                session.add(phase)
            print(f"  - Created {len(default_phases)} phases")

        # Ensure phases exist for existing lessons too
        existing_phases = await session.execute(
            select(LessonPhase).where(LessonPhase.lesson_id == lesson.id)
        )
        if not existing_phases.scalars().first():
            # No phases exist, create them
            default_phases = [
                ("intro", "Introduction", 0),
                ("vocabulary", "Vocabulary", 1),
                ("patterns", "Q&A Patterns", 2),
                ("practice", "Practice", 3),
                ("wrapup", "Wrap-up", 4),
            ]
            for phase_type, phase_name, sort_order in default_phases:
                phase = LessonPhase(
                    lesson_id=lesson.id,
                    phase_type=phase_type,
                    phase_name=phase_name,
                    sort_order=sort_order,
                )
                session.add(phase)
            print(f"  - Created missing phases for existing lesson")

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
                question_template_es=pattern.get("question_template_es"),
                answer_template=pattern["answer_template"],
                answer_template_es=pattern.get("answer_template_es"),
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
        for i, crit_data in enumerate(lesson_data["evaluation_criteria"]):
            eval_criterion = EvaluationCriterion(
                lesson_id=lesson.id,
                criterion=crit_data["criterion"],
                criterion_es=crit_data.get("criterion_es"),
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
