# src/backend/app/routers/auth.py
"""Authentication router for Azure AD OAuth."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.middleware.auth import CurrentUser
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserResponse(BaseModel):
    """User response schema."""
    id: str
    email: str
    display_name: str | None
    oauth_provider: str

    class Config:
        from_attributes = True


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> User:
    """Get current authenticated user info."""
    return current_user
