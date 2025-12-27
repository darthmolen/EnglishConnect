"""Progress API router for tracking user learning progress."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.progress import UserProgress, PracticeSession, ConversationExchange
from app.models.content import Lesson
from app.services.lesson_progress_service import LessonProgressService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/progress", tags=["progress"])


# Pydantic schemas
class LessonProgress(BaseModel):
    """Progress for a single lesson."""

    lesson_id: int
    lesson_number: int
    title: str
    status: str  # not_started, in_progress, completed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class OverallProgress(BaseModel):
    """Overall user progress summary."""

    total_lessons: int
    completed_lessons: int
    in_progress_lessons: int
    completion_percentage: float
    total_practice_sessions: int
    total_exchanges: int
    total_practice_minutes: int


class ConversationStats(BaseModel):
    """Statistics about conversation practice."""

    total_sessions: int
    total_exchanges: int
    total_minutes: int
    avg_session_length_minutes: float
    avg_exchanges_per_session: float
    sessions_by_lesson: dict[int, int]


class MarkCompleteResponse(BaseModel):
    """Response for marking a lesson complete."""

    lesson_id: int
    status: str
    completed_at: datetime


@router.get("", response_model=OverallProgress)
async def get_overall_progress(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get overall learning progress summary for authenticated user."""
    service = LessonProgressService(db)
    stats = await service.get_overall_stats(user_id=current_user.id, course_id="ec1")

    total_lessons = stats["total_lessons"]
    completed_lessons = stats["completed"]
    completion_pct = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

    return OverallProgress(
        total_lessons=total_lessons,
        completed_lessons=completed_lessons,
        in_progress_lessons=stats["in_progress"],
        completion_percentage=round(completion_pct, 1),
        total_practice_sessions=stats["total_practice_sessions"],
        total_exchanges=stats["total_exchanges"],
        total_practice_minutes=stats["total_practice_minutes"],
    )


@router.get("/lessons", response_model=list[LessonProgress])
async def get_lesson_progress(
    current_user: CurrentUser,
    course_id: str = Query("ec1", description="Course ID"),
    db: AsyncSession = Depends(get_db),
):
    """Get progress for all lessons in a course for authenticated user.

    Returns lesson list with completion status.
    """
    service = LessonProgressService(db)
    lessons = await service.get_lesson_progress_list(
        user_id=current_user.id, course_id=course_id
    )

    return [
        LessonProgress(
            lesson_id=lesson["lesson_id"],
            lesson_number=lesson["lesson_number"],
            title=lesson["title"],
            status=lesson["status"],
            started_at=lesson["started_at"],
            completed_at=lesson["completed_at"],
        )
        for lesson in lessons
    ]


@router.post("/lessons/{lesson_id}/complete", response_model=MarkCompleteResponse)
async def mark_lesson_complete(
    lesson_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Mark a lesson as completed for authenticated user.

    Creates or updates the progress record for this lesson.
    """
    # Verify lesson exists
    lesson_result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = lesson_result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Get or create progress record
    progress_result = await db.execute(
        select(UserProgress).where(
            UserProgress.lesson_id == lesson_id,
            UserProgress.user_id == current_user.id,
        )
    )
    progress = progress_result.scalar_one_or_none()

    now = datetime.utcnow()

    if progress:
        progress.status = "completed"
        progress.completed_at = now
    else:
        progress = UserProgress(
            user_id=current_user.id,
            lesson_id=lesson_id,
            status="completed",
            started_at=now,
            completed_at=now,
        )
        db.add(progress)

    await db.commit()

    return MarkCompleteResponse(
        lesson_id=lesson_id,
        status="completed",
        completed_at=now,
    )


@router.post("/lessons/{lesson_id}/start", response_model=LessonProgress)
async def start_lesson(
    lesson_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Mark a lesson as in progress for authenticated user.

    Called when user starts practicing a lesson.
    """
    # Verify lesson exists
    lesson_result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = lesson_result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Get or create progress record
    progress_result = await db.execute(
        select(UserProgress).where(
            UserProgress.lesson_id == lesson_id,
            UserProgress.user_id == current_user.id,
        )
    )
    progress = progress_result.scalar_one_or_none()

    now = datetime.utcnow()

    if progress:
        if progress.status == "not_started":
            progress.status = "in_progress"
            progress.started_at = now
    else:
        progress = UserProgress(
            user_id=current_user.id,
            lesson_id=lesson_id,
            status="in_progress",
            started_at=now,
        )
        db.add(progress)

    await db.commit()

    return LessonProgress(
        lesson_id=lesson_id,
        lesson_number=lesson.lesson_number,
        title=lesson.title,
        status=progress.status,
        started_at=progress.started_at,
        completed_at=progress.completed_at,
    )


@router.get("/stats", response_model=ConversationStats)
async def get_conversation_stats(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get conversation practice statistics for authenticated user.

    Returns aggregated stats about practice sessions.
    """
    # Total sessions
    sessions_result = await db.execute(select(func.count(PracticeSession.id)))
    total_sessions = sessions_result.scalar() or 0

    # Total exchanges
    exchanges_result = await db.execute(select(func.count(ConversationExchange.id)))
    total_exchanges = exchanges_result.scalar() or 0

    # Total minutes
    minutes_result = await db.execute(
        select(func.coalesce(func.sum(PracticeSession.duration_seconds), 0))
    )
    total_seconds = minutes_result.scalar() or 0
    total_minutes = total_seconds // 60

    # Average session length
    avg_length = (total_minutes / total_sessions) if total_sessions > 0 else 0

    # Average exchanges per session
    avg_exchanges = (total_exchanges / total_sessions) if total_sessions > 0 else 0

    # Sessions by lesson
    by_lesson_result = await db.execute(
        select(PracticeSession.lesson_id, func.count(PracticeSession.id))
        .group_by(PracticeSession.lesson_id)
    )
    sessions_by_lesson = {row[0]: row[1] for row in by_lesson_result.all() if row[0]}

    return ConversationStats(
        total_sessions=total_sessions,
        total_exchanges=total_exchanges,
        total_minutes=total_minutes,
        avg_session_length_minutes=round(avg_length, 1),
        avg_exchanges_per_session=round(avg_exchanges, 1),
        sessions_by_lesson=sessions_by_lesson,
    )
