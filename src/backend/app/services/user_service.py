# src/backend/app/services/user_service.py
"""User service for OAuth user management."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserService:
    """Service for user CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_user(
        self,
        oauth_provider: str,
        oauth_id: str,
        email: str,
        display_name: str | None = None,
    ) -> User:
        """Get existing user or create new one from OAuth data."""
        # Try to find existing user by OAuth ID
        stmt = select(User).where(
            User.oauth_provider == oauth_provider,
            User.oauth_id == oauth_id,
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            return user

        # Create new user
        user = User(
            email=email,
            display_name=display_name or email.split("@")[0],
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
