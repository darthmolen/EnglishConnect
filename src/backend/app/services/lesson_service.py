"""Service for lesson data access and transformation."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, VocabularyItem, QAPattern, EvaluationCriterion
from app.schemas.lesson import (
    LessonSummary,
    LessonDetail,
    VocabularyItemSchema,
    QAPatternSchema,
)


class LessonService:
    """Service for accessing lesson data from the database."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session

    async def list_lessons(self, course_id: str) -> list[LessonSummary]:
        """List all lessons for a course.

        Args:
            course_id: Course identifier (e.g., 'ec1')

        Returns:
            List of LessonSummary objects ordered by lesson number
        """
        result = await self.session.execute(
            select(Lesson)
            .where(Lesson.course_id == course_id)
            .order_by(Lesson.lesson_number)
        )
        return [
            LessonSummary(
                lesson_number=lesson.lesson_number,
                title=lesson.title,
                objective=lesson.objective,
            )
            for lesson in result.scalars().all()
        ]

    async def get_lesson_detail(
        self, course_id: str, lesson_number: int
    ) -> LessonDetail | None:
        """Get detailed lesson data including vocabulary and patterns.

        Args:
            course_id: Course identifier (e.g., 'ec1')
            lesson_number: Lesson number within the course

        Returns:
            LessonDetail with all related data, or None if not found
        """
        # Get the lesson
        result = await self.session.execute(
            select(Lesson).where(
                Lesson.course_id == course_id,
                Lesson.lesson_number == lesson_number,
            )
        )
        lesson = result.scalar_one_or_none()

        if not lesson:
            return None

        # Get related data
        vocab_result = await self.session.execute(
            select(VocabularyItem).where(VocabularyItem.lesson_id == lesson.id)
        )
        patterns_result = await self.session.execute(
            select(QAPattern)
            .where(QAPattern.lesson_id == lesson.id)
            .order_by(QAPattern.pattern_number)
        )
        criteria_result = await self.session.execute(
            select(EvaluationCriterion)
            .where(EvaluationCriterion.lesson_id == lesson.id)
            .order_by(EvaluationCriterion.sort_order)
        )

        return LessonDetail(
            lesson_number=lesson.lesson_number,
            title=lesson.title,
            objective=lesson.objective,
            learning_principle_title=lesson.learning_principle_title,
            learning_principle_content=lesson.learning_principle,
            learning_principle_full=lesson.learning_principle_full,
            ponder_questions=lesson.ponder_questions or [],
            pattern_images=lesson.pattern_images or [],
            vocabulary=[
                VocabularyItemSchema(
                    english=v.english_word,
                    spanish=v.spanish_translation,
                    category=v.category,
                )
                for v in vocab_result.scalars()
            ],
            patterns=[
                QAPatternSchema(
                    pattern_number=p.pattern_number,
                    question_template=p.question_template,
                    answer_template=p.answer_template,
                    examples=p.examples,
                )
                for p in patterns_result.scalars()
            ],
            evaluation_criteria=[c.criterion for c in criteria_result.scalars()],
        )
