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
from app.models.progress import UserProgress, PracticeSession, ConversationExchange
from app.models.content import Lesson

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
    user_id: Optional[str] = Query(None, description="User ID (optional, for Phase 4B)"),
    db: AsyncSession = Depends(get_db),
):
    """Get overall learning progress summary.

    Without auth (Phase 4B), returns aggregate stats for all users.
    """
    # Count total lessons
    total_lessons_result = await db.execute(select(func.count(Lesson.id)))
    total_lessons = total_lessons_result.scalar() or 0

    # Count completed lessons
    completed_result = await db.execute(
        select(func.count(UserProgress.id)).where(UserProgress.status == "completed")
    )
    completed_lessons = completed_result.scalar() or 0

    # Count in-progress lessons
    in_progress_result = await db.execute(
        select(func.count(UserProgress.id)).where(UserProgress.status == "in_progress")
    )
    in_progress_lessons = in_progress_result.scalar() or 0

    # Count practice sessions
    sessions_result = await db.execute(select(func.count(PracticeSession.id)))
    total_sessions = sessions_result.scalar() or 0

    # Count total exchanges
    exchanges_result = await db.execute(select(func.count(ConversationExchange.id)))
    total_exchanges = exchanges_result.scalar() or 0

    # Sum practice minutes
    minutes_result = await db.execute(
        select(func.coalesce(func.sum(PracticeSession.duration_seconds), 0))
    )
    total_seconds = minutes_result.scalar() or 0
    total_minutes = total_seconds // 60

    completion_pct = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

    return OverallProgress(
        total_lessons=total_lessons,
        completed_lessons=completed_lessons,
        in_progress_lessons=in_progress_lessons,
        completion_percentage=round(completion_pct, 1),
        total_practice_sessions=total_sessions,
        total_exchanges=total_exchanges,
        total_practice_minutes=total_minutes,
    )


@router.get("/lessons", response_model=list[LessonProgress])
async def get_lesson_progress(
    course_id: str = Query("ec1", description="Course ID"),
    user_id: Optional[str] = Query(None, description="User ID (optional, for Phase 4B)"),
    db: AsyncSession = Depends(get_db),
):
    """Get progress for all lessons in a course.

    Returns lesson list with completion status.
    """
    # Get all lessons for the course
    lessons_result = await db.execute(
        select(Lesson)
        .where(Lesson.course_id == course_id)
        .order_by(Lesson.lesson_number)
    )
    lessons = list(lessons_result.scalars().all())

    # Get progress for each lesson (aggregate for now, per-user in Phase 4B)
    progress_result = await db.execute(select(UserProgress))
    progress_map = {p.lesson_id: p for p in progress_result.scalars().all()}

    result = []
    for lesson in lessons:
        progress = progress_map.get(lesson.id)
        result.append(LessonProgress(
            lesson_id=lesson.id,
            lesson_number=lesson.lesson_number,
            title=lesson.title,
            status=progress.status if progress else "not_started",
            started_at=progress.started_at if progress else None,
            completed_at=progress.completed_at if progress else None,
        ))

    return result


@router.post("/lessons/{lesson_id}/complete", response_model=MarkCompleteResponse)
async def mark_lesson_complete(
    lesson_id: int,
    user_id: Optional[str] = Query(None, description="User ID (optional, for Phase 4B)"),
    db: AsyncSession = Depends(get_db),
):
    """Mark a lesson as completed.

    Creates or updates the progress record for this lesson.
    """
    # Verify lesson exists
    lesson_result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = lesson_result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Get or create progress record
    # For now without auth, we use a dummy user_id
    # In Phase 4B, this will be from the authenticated user
    dummy_user_id = None  # Will be UUID from auth

    progress_result = await db.execute(
        select(UserProgress).where(
            UserProgress.lesson_id == lesson_id,
            # UserProgress.user_id == dummy_user_id,  # Enable in Phase 4B
        )
    )
    progress = progress_result.scalar_one_or_none()

    now = datetime.utcnow()

    if progress:
        progress.status = "completed"
        progress.completed_at = now
    else:
        progress = UserProgress(
            user_id=dummy_user_id,
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
    user_id: Optional[str] = Query(None, description="User ID (optional, for Phase 4B)"),
    db: AsyncSession = Depends(get_db),
):
    """Mark a lesson as in progress.

    Called when user starts practicing a lesson.
    """
    # Verify lesson exists
    lesson_result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = lesson_result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Get or create progress record
    progress_result = await db.execute(
        select(UserProgress).where(UserProgress.lesson_id == lesson_id)
    )
    progress = progress_result.scalar_one_or_none()

    now = datetime.utcnow()

    if progress:
        if progress.status == "not_started":
            progress.status = "in_progress"
            progress.started_at = now
    else:
        progress = UserProgress(
            user_id=None,  # From auth in Phase 4B
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
    user_id: Optional[str] = Query(None, description="User ID (optional, for Phase 4B)"),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation practice statistics.

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
