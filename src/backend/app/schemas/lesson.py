"""Pydantic schemas for lesson API endpoints."""

from pydantic import BaseModel


class LessonSummary(BaseModel):
    """Summary of a lesson for list view."""

    lesson_number: int
    title: str
    objective: str | None = None


class VocabularyItemSchema(BaseModel):
    """Vocabulary item with English/Spanish pair."""

    english: str
    spanish: str
    category: str | None = None


class QAPatternSchema(BaseModel):
    """Q&A pattern template with optional native language translations.

    The 'translation' fields contain the learner's native language equivalent.
    The frontend displays these without assuming any specific language.
    """

    pattern_number: int
    question_template: str
    question_translation: str | None = None  # Native language translation
    answer_template: str
    answer_translation: str | None = None  # Native language translation
    examples: list[dict] | None = None  # Each dict has q, a, optionally q_translation, a_translation


class LessonDetail(BaseModel):
    """Full lesson details including vocabulary and patterns."""

    lesson_number: int
    title: str
    objective: str | None = None
    learning_principle_title: str | None = None
    learning_principle_content: str | None = None
    learning_principle_full: str | None = None
    ponder_questions: list[str] = []
    pattern_images: list[str] = []
    vocabulary: list[VocabularyItemSchema] = []
    patterns: list[QAPatternSchema] = []
    evaluation_criteria: list[str] = []
