"""Service for lesson phase progress tracking."""

import uuid
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content import Lesson, LessonPhase
from app.models.progress import UserProgress, PracticeSession, ConversationExchange
from app.schemas.lesson_session import PhaseStateSchema, LessonPhaseSchema


class LessonProgressService:
    """Service for managing user progress through lesson phases."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session

    async def get_lesson_phases(self, lesson_id: int) -> list[LessonPhase]:
        """Get all phases for a lesson, ordered by sort_order.

        Args:
            lesson_id: Database ID of the lesson

        Returns:
            List of LessonPhase objects
        """
        result = await self.session.execute(
            select(LessonPhase)
            .where(LessonPhase.lesson_id == lesson_id)
            .order_by(LessonPhase.sort_order)
        )
        return list(result.scalars().all())

    async def get_phase_by_type(
        self, lesson_id: int, phase_type: str
    ) -> LessonPhase | None:
        """Get a specific phase by its type.

        Args:
            lesson_id: Database ID of the lesson
            phase_type: Phase type string ('intro', 'vocabulary', 'patterns', 'practice', 'wrapup')

        Returns:
            LessonPhase if found, None otherwise
        """
        result = await self.session.execute(
            select(LessonPhase)
            .where(
                LessonPhase.lesson_id == lesson_id,
                LessonPhase.phase_type == phase_type,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_progress(
        self, user_id: uuid.UUID, lesson_id: int
    ) -> UserProgress | None:
        """Get user's progress for a specific lesson.

        Args:
            user_id: User UUID
            lesson_id: Database ID of the lesson

        Returns:
            UserProgress with phase relationship loaded, or None
        """
        result = await self.session.execute(
            select(UserProgress)
            .options(selectinload(UserProgress.current_phase))
            .where(
                UserProgress.user_id == user_id,
                UserProgress.lesson_id == lesson_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_progress(
        self, user_id: uuid.UUID, lesson_id: int
    ) -> tuple[UserProgress, bool]:
        """Get existing progress or create new one starting at intro phase.

        Args:
            user_id: User UUID
            lesson_id: Database ID of the lesson

        Returns:
            Tuple of (UserProgress, created: bool)
        """
        progress = await self.get_user_progress(user_id, lesson_id)

        if progress:
            return progress, False

        # Get the first phase (intro) for this lesson
        phases = await self.get_lesson_phases(lesson_id)
        if not phases:
            raise ValueError(f"No phases defined for lesson {lesson_id}")

        first_phase = phases[0]

        # Create new progress record
        progress = UserProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            status="in_progress",
            started_at=datetime.utcnow(),
            phase_id=first_phase.id,
            phase_state=PhaseStateSchema().model_dump(),
        )
        self.session.add(progress)
        await self.session.flush()

        # Reload with relationship
        progress = await self.get_user_progress(user_id, lesson_id)
        return progress, True

    async def advance_phase(
        self,
        progress: UserProgress,
        total_vocab: int = 0,
        total_patterns: int = 0,
    ) -> tuple[UserProgress, dict]:
        """Move to the next phase in the lesson.

        Handles both advancing within a phase (vocab/pattern index) and
        moving to the next phase type.

        Args:
            progress: Current UserProgress record
            total_vocab: Total vocabulary items in the lesson
            total_patterns: Total patterns in the lesson

        Returns:
            Tuple of (updated UserProgress, result dict with action info)

        Raises:
            ValueError: If current phase not found
        """
        phases = await self.get_lesson_phases(progress.lesson_id)
        current_idx = next(
            (i for i, p in enumerate(phases) if p.id == progress.phase_id), None
        )

        if current_idx is None:
            raise ValueError("Current phase not found in lesson phases")

        phase_state = PhaseStateSchema.model_validate(progress.phase_state or {})
        current_phase = phases[current_idx]

        # For vocabulary phase, advance vocab_index if not at last item
        if current_phase.phase_type == "vocabulary" and phase_state.vocab_index < total_vocab - 1:
            phase_state.vocab_index += 1
            progress.phase_state = phase_state.model_dump()
            await self.session.flush()
            updated = await self.get_user_progress(progress.user_id, progress.lesson_id)
            return updated, {
                "success": True,
                "action": "next_vocab",
                "vocab_index": phase_state.vocab_index,
            }

        # For patterns phase, advance pattern_index if not at last item
        if current_phase.phase_type == "patterns" and phase_state.pattern_index < total_patterns - 1:
            phase_state.pattern_index += 1
            progress.phase_state = phase_state.model_dump()
            await self.session.flush()
            updated = await self.get_user_progress(progress.user_id, progress.lesson_id)
            return updated, {
                "success": True,
                "action": "next_pattern",
                "pattern_index": phase_state.pattern_index,
            }

        # Move to next phase or complete lesson
        if current_idx >= len(phases) - 1:
            # At last phase (wrapup), mark lesson complete
            progress.status = "completed"
            progress.completed_at = datetime.utcnow()
            await self.session.flush()
            updated = await self.get_user_progress(progress.user_id, progress.lesson_id)
            return updated, {
                "success": True,
                "action": "lesson_complete",
            }
        else:
            next_phase = phases[current_idx + 1]
            progress.phase_id = next_phase.id
            # Reset phase state for new phase
            progress.phase_state = PhaseStateSchema().model_dump()
            await self.session.flush()
            updated = await self.get_user_progress(progress.user_id, progress.lesson_id)
            return updated, {
                "success": True,
                "action": "next_phase",
                "new_phase": next_phase.phase_type,
            }

    async def advance_item_index(
        self,
        progress: UserProgress,
        item_type: str,
        total_items: int,
    ) -> tuple[UserProgress, bool]:
        """Advance the vocab_index or pattern_index within current phase.

        Args:
            progress: Current UserProgress record
            item_type: 'vocab' or 'pattern'
            total_items: Total number of items in this phase

        Returns:
            Tuple of (updated UserProgress, should_advance_phase: bool)
        """
        phase_state = PhaseStateSchema.model_validate(progress.phase_state or {})

        if item_type == "vocab":
            phase_state.vocab_index += 1
            should_advance = phase_state.vocab_index >= total_items
        elif item_type == "pattern":
            phase_state.pattern_index += 1
            should_advance = phase_state.pattern_index >= total_items
        else:
            raise ValueError(f"Unknown item_type: {item_type}")

        progress.phase_state = phase_state.model_dump()
        await self.session.flush()

        return progress, should_advance

    async def update_phase_state(
        self, progress: UserProgress, state: PhaseStateSchema
    ) -> UserProgress:
        """Update the phase_state JSONB field.

        Args:
            progress: UserProgress record to update
            state: New phase state

        Returns:
            Updated UserProgress
        """
        progress.phase_state = state.model_dump()
        await self.session.flush()
        return progress

    async def record_attempt(
        self,
        progress: UserProgress,
        item_type: str,
        item_id: str,
        correct: bool,
    ) -> UserProgress:
        """Record a student's attempt at a vocabulary word or pattern.

        Updates the items_completed list and can_skip_ahead flag.

        Args:
            progress: UserProgress record
            item_type: 'vocab' or 'pattern'
            item_id: Identifier for the item attempted
            correct: Whether the attempt was correct

        Returns:
            Updated UserProgress
        """
        phase_state = PhaseStateSchema.model_validate(progress.phase_state or {})

        if correct and item_id not in phase_state.items_completed:
            phase_state.items_completed.append(item_id)

        progress.phase_state = phase_state.model_dump()
        await self.session.flush()
        return progress

    def get_phase_schema(self, phase: LessonPhase) -> LessonPhaseSchema:
        """Convert a LessonPhase model to schema.

        Args:
            phase: LessonPhase model instance

        Returns:
            LessonPhaseSchema
        """
        return LessonPhaseSchema.model_validate(phase)

    async def get_overall_stats(
        self, user_id: uuid.UUID, course_id: str = "ec1"
    ) -> dict:
        """Get overall progress stats for a user.

        Args:
            user_id: User UUID
            course_id: Course identifier (default: ec1)

        Returns:
            Dict with keys: total_lessons, completed, in_progress, not_started,
            total_practice_sessions, total_exchanges, total_practice_minutes
        """
        # Count total lessons in course
        total_result = await self.session.execute(
            select(func.count(Lesson.id)).where(Lesson.course_id == course_id)
        )
        total_lessons = total_result.scalar() or 0

        # Count completed lessons for user
        completed_result = await self.session.execute(
            select(func.count(UserProgress.id)).where(
                UserProgress.user_id == user_id,
                UserProgress.status == "completed",
            )
        )
        completed = completed_result.scalar() or 0

        # Count in-progress lessons for user
        in_progress_result = await self.session.execute(
            select(func.count(UserProgress.id)).where(
                UserProgress.user_id == user_id,
                UserProgress.status == "in_progress",
            )
        )
        in_progress = in_progress_result.scalar() or 0

        # Count practice sessions for user
        sessions_result = await self.session.execute(
            select(func.count(PracticeSession.id)).where(
                PracticeSession.user_id == user_id
            )
        )
        total_sessions = sessions_result.scalar() or 0

        # Count exchanges in user's sessions
        exchanges_result = await self.session.execute(
            select(func.count(ConversationExchange.id))
            .join(PracticeSession, ConversationExchange.session_id == PracticeSession.id)
            .where(PracticeSession.user_id == user_id)
        )
        total_exchanges = exchanges_result.scalar() or 0

        # Sum practice minutes for user
        minutes_result = await self.session.execute(
            select(func.coalesce(func.sum(PracticeSession.duration_seconds), 0)).where(
                PracticeSession.user_id == user_id
            )
        )
        total_seconds = minutes_result.scalar() or 0

        return {
            "total_lessons": total_lessons,
            "completed": completed,
            "in_progress": in_progress,
            "not_started": total_lessons - completed - in_progress,
            "total_practice_sessions": total_sessions,
            "total_exchanges": total_exchanges,
            "total_practice_minutes": total_seconds // 60,
        }

    async def get_lesson_progress_list(
        self, user_id: uuid.UUID, course_id: str = "ec1"
    ) -> list[dict]:
        """Get per-lesson progress for a user.

        Args:
            user_id: User UUID
            course_id: Course identifier (default: ec1)

        Returns:
            List of dicts with keys: lesson_id, lesson_number, title, status,
            phase_name, started_at, completed_at
        """
        # Get all lessons for course
        lessons_result = await self.session.execute(
            select(Lesson)
            .where(Lesson.course_id == course_id)
            .order_by(Lesson.lesson_number)
        )
        lessons = list(lessons_result.scalars().all())

        # Get user's progress with current phase loaded
        progress_result = await self.session.execute(
            select(UserProgress)
            .options(selectinload(UserProgress.current_phase))
            .where(UserProgress.user_id == user_id)
        )
        progress_map = {p.lesson_id: p for p in progress_result.scalars().all()}

        result = []
        for lesson in lessons:
            progress = progress_map.get(lesson.id)
            phase_name = None
            if progress and progress.current_phase:
                phase_name = progress.current_phase.phase_name

            result.append({
                "lesson_id": lesson.id,
                "lesson_number": lesson.lesson_number,
                "title": lesson.title,
                "status": progress.status if progress else "not_started",
                "phase_name": phase_name,
                "started_at": progress.started_at if progress else None,
                "completed_at": progress.completed_at if progress else None,
            })

        return result
