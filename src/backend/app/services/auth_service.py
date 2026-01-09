"""Authentication service for JWT and password management."""

import secrets
from datetime import datetime, timedelta
from uuid import UUID

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.auth import RefreshToken, PasswordResetToken

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession | None = None):
        """Initialize auth service with optional database session."""
        self.db = db
        self.settings = get_settings()

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, user_id: UUID, roles: list[str]) -> str:
        """Create a JWT access token."""
        expires = datetime.utcnow() + timedelta(
            minutes=self.settings.jwt_access_token_expire_minutes
        )
        payload = {
            "sub": str(user_id),
            "roles": roles,
            "exp": expires,
            "iat": datetime.utcnow(),
            "type": "access",
        }
        return jwt.encode(
            payload,
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm,
        )

    def decode_access_token(self, token: str) -> dict:
        """Decode and validate a JWT access token.

        Raises:
            JWTError: If token is invalid, expired, or has wrong signature.
        """
        payload = jwt.decode(
            token,
            self.settings.jwt_secret_key,
            algorithms=[self.settings.jwt_algorithm],
        )
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        return payload

    async def create_refresh_token(
        self,
        user_id: UUID,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> str:
        """Create and store a refresh token.

        Returns the plain token (not the hash) - this is what the client stores.
        """
        token = secrets.token_urlsafe(32)
        expires = datetime.utcnow() + timedelta(
            days=self.settings.jwt_refresh_token_expire_days
        )

        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=pwd_context.hash(token),
            expires_at=expires,
        )
        self.db.add(refresh_token)
        await self.db.commit()

        return token

    async def verify_refresh_token(self, token: str) -> RefreshToken | None:
        """Find and validate a refresh token.

        Returns the token record if valid, None if invalid/expired/revoked.
        """
        # Get all non-revoked, non-expired tokens
        stmt = select(RefreshToken).where(
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.utcnow(),
        )
        result = await self.db.execute(stmt)
        tokens = result.scalars().all()

        # Check each token's hash (bcrypt verify)
        for db_token in tokens:
            if pwd_context.verify(token, db_token.token_hash):
                return db_token

        return None

    async def revoke_refresh_token(self, token_id: UUID) -> None:
        """Revoke a refresh token by setting revoked_at."""
        stmt = select(RefreshToken).where(RefreshToken.id == token_id)
        result = await self.db.execute(stmt)
        db_token = result.scalar_one_or_none()

        if db_token:
            db_token.revoked_at = datetime.utcnow()
            await self.db.commit()

    async def revoke_all_user_refresh_tokens(self, user_id: UUID) -> None:
        """Revoke all refresh tokens for a user (e.g., on password reset)."""
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        result = await self.db.execute(stmt)
        tokens = result.scalars().all()

        for token in tokens:
            token.revoked_at = datetime.utcnow()

        await self.db.commit()

    async def create_password_reset_token(self, user_id: UUID) -> str:
        """Create and store a password reset token.

        Returns the plain token for sending in email.
        """
        token = secrets.token_urlsafe(32)
        expires = datetime.utcnow() + timedelta(
            minutes=self.settings.password_reset_expire_minutes
        )

        reset_token = PasswordResetToken(
            user_id=user_id,
            token_hash=pwd_context.hash(token),
            expires_at=expires,
        )
        self.db.add(reset_token)
        await self.db.commit()

        return token

    async def verify_password_reset_token(self, token: str) -> PasswordResetToken | None:
        """Find and validate a password reset token.

        Returns the token record if valid, None if invalid/expired/used.
        """
        # Get all unused, non-expired tokens
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.utcnow(),
        )
        result = await self.db.execute(stmt)
        tokens = result.scalars().all()

        # Check each token's hash
        for db_token in tokens:
            if pwd_context.verify(token, db_token.token_hash):
                return db_token

        return None

    async def mark_password_reset_token_used(self, token_id: UUID) -> None:
        """Mark a password reset token as used."""
        stmt = select(PasswordResetToken).where(PasswordResetToken.id == token_id)
        result = await self.db.execute(stmt)
        db_token = result.scalar_one_or_none()

        if db_token:
            db_token.used_at = datetime.utcnow()
            await self.db.commit()
