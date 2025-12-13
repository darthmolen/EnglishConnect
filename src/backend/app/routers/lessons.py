"""Lessons API router for listing and retrieving lesson content."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.lesson import LessonSummary, LessonDetail
from app.services.lesson_service import LessonService

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.get("", response_model=list[LessonSummary])
async def list_lessons(
    course_id: str = "ec1",
    db: AsyncSession = Depends(get_db),
):
    """List all lessons for a course.

    Args:
        course_id: Course identifier (default: ec1)
        db: Database session dependency

    Returns:
        List of LessonSummary objects
    """
    service = LessonService(db)
    return await service.list_lessons(course_id)


@router.get("/{lesson_number}", response_model=LessonDetail)
async def get_lesson(
    lesson_number: int,
    course_id: str = "ec1",
    db: AsyncSession = Depends(get_db),
):
    """Get detailed lesson data including vocabulary and patterns.

    Args:
        lesson_number: Lesson number within the course
        course_id: Course identifier (default: ec1)
        db: Database session dependency

    Returns:
        LessonDetail with all related data

    Raises:
        HTTPException: 404 if lesson not found
    """
    service = LessonService(db)
    detail = await service.get_lesson_detail(course_id, lesson_number)

    if not detail:
        raise HTTPException(status_code=404, detail="Lesson not found")

    return detail
