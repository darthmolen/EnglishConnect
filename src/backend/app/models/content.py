"""Content models for courses, lessons, vocabulary, and patterns."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Course(Base):
    """Course/curriculum model (e.g., EC1, EC2)."""

    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # 'ec1', 'ec2'
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    total_lessons: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="course")


class Lesson(Base):
    """Individual lesson model."""

    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[str] = mapped_column(String(20), ForeignKey("courses.id"))
    lesson_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str | None] = mapped_column(Text)
    learning_principle: Mapped[str | None] = mapped_column(Text)
    learning_principle_title: Mapped[str | None] = mapped_column(String(200))
    learning_principle_full: Mapped[str | None] = mapped_column(Text)  # Full principle text
    ponder_questions: Mapped[list | None] = mapped_column(JSONB)  # Reflection questions
    pattern_images: Mapped[list | None] = mapped_column(JSONB)  # Figure image paths
    content_path: Mapped[str | None] = mapped_column(String(500))  # Path to markdown file

    # Relationships
    course: Mapped["Course"] = relationship(back_populates="lessons")
    vocabulary_items: Mapped[list["VocabularyItem"]] = relationship(back_populates="lesson")
    qa_patterns: Mapped[list["QAPattern"]] = relationship(back_populates="lesson")
    evaluation_criteria: Mapped[list["EvaluationCriterion"]] = relationship(
        back_populates="lesson"
    )
    phases: Mapped[list["LessonPhase"]] = relationship(
        back_populates="lesson", order_by="LessonPhase.sort_order"
    )

    __table_args__ = ({"sqlite_autoincrement": True},)


class LessonPhase(Base):
    """Phase definition for a lesson (e.g., intro, vocabulary, patterns).

    Each lesson can define its own phases with custom configurations.
    Standard phases: intro, vocabulary, patterns, practice, wrapup
    """

    __tablename__ = "lesson_phases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"))
    phase_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'intro', 'vocabulary', 'patterns', 'practice', 'wrapup'
    phase_name: Mapped[str] = mapped_column(String(100), nullable=False)  # Display name
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[dict | None] = mapped_column(JSONB)  # Phase-specific configuration

    # Relationships
    lesson: Mapped["Lesson"] = relationship(back_populates="phases")

    __table_args__ = ({"sqlite_autoincrement": True},)


class VocabularyItem(Base):
    """Vocabulary word/phrase with translation."""

    __tablename__ = "vocabulary_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"))
    english_word: Mapped[str] = mapped_column(String(200), nullable=False)
    spanish_translation: Mapped[str] = mapped_column(String(200), nullable=False)
    pronunciation_hint: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(50))  # 'verb', 'noun', 'adjective'
    audio_url: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    lesson: Mapped["Lesson"] = relationship(back_populates="vocabulary_items")


class QAPattern(Base):
    """Question and Answer pattern template."""

    __tablename__ = "qa_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"))
    pattern_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or 2
    question_template: Mapped[str] = mapped_column(String(500), nullable=False)
    answer_template: Mapped[str] = mapped_column(String(500), nullable=False)
    placeholders: Mapped[dict | None] = mapped_column(JSONB)  # Variable slots
    examples: Mapped[list | None] = mapped_column(JSONB)  # Example Q&A pairs

    # Relationships
    lesson: Mapped["Lesson"] = relationship(back_populates="qa_patterns")


class EvaluationCriterion(Base):
    """Learning objective / 'I can' statement."""

    __tablename__ = "evaluation_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"))
    criterion: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    lesson: Mapped["Lesson"] = relationship(back_populates="evaluation_criteria")


class ExampleSentence(Base):
    """Concrete example sentences extracted from Q&A patterns.

    Stored separately for searchability and demo content generation.
    Examples: "I like to sing because it's fun", "She doesn't like to cook"
    """

    __tablename__ = "example_sentences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"))
    pattern_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("qa_patterns.id"))
    sentence_type: Mapped[str] = mapped_column(String(20))  # 'question' or 'answer'
    english_text: Mapped[str] = mapped_column(Text, nullable=False)
    spanish_translation: Mapped[str | None] = mapped_column(Text)  # If available

    # Relationships
    lesson: Mapped["Lesson"] = relationship()
    pattern: Mapped["QAPattern"] = relationship()
