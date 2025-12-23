"""Service for lesson phase progress tracking."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content import Lesson, LessonPhase
from app.models.progress import UserProgress
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

    async def advance_phase(self, progress: UserProgress) -> UserProgress:
        """Move to the next phase in the lesson.

        Handles both advancing within a phase (vocab/pattern index) and
        moving to the next phase type.

        Args:
            progress: Current UserProgress record

        Returns:
            Updated UserProgress

        Raises:
            ValueError: If already at the last phase
        """
        phases = await self.get_lesson_phases(progress.lesson_id)
        current_idx = next(
            (i for i, p in enumerate(phases) if p.id == progress.phase_id), None
        )

        if current_idx is None:
            raise ValueError("Current phase not found in lesson phases")

        phase_state = PhaseStateSchema.model_validate(progress.phase_state or {})
        current_phase = phases[current_idx]

        # For vocabulary phase, check if we need to advance vocab_index
        if current_phase.phase_type == "vocabulary":
            # Get vocab count from lesson (would need lesson detail)
            # For now, advance to next phase
            pass

        # For patterns phase, check if we need to advance pattern_index
        if current_phase.phase_type == "patterns":
            # Similar logic
            pass

        # Move to next phase
        if current_idx >= len(phases) - 1:
            # Already at last phase (wrapup), mark lesson complete
            progress.status = "completed"
            progress.completed_at = datetime.utcnow()
        else:
            next_phase = phases[current_idx + 1]
            progress.phase_id = next_phase.id
            # Reset phase state for new phase
            progress.phase_state = PhaseStateSchema().model_dump()

        await self.session.flush()

        # Reload with updated relationship
        return await self.get_user_progress(progress.user_id, progress.lesson_id)

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
