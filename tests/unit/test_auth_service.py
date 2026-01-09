# tests/unit/test_auth_service.py
"""Unit tests for AuthService - TDD: tests written BEFORE implementation."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_hash_password_returns_bcrypt_hash(self):
        """Hash should return a bcrypt hash starting with $2b$."""
        from app.services.auth_service import AuthService

        auth_service = AuthService()
        password = "securepassword123"

        hashed = auth_service.hash_password(password)

        assert hashed.startswith("$2b$")
        assert len(hashed) == 60  # bcrypt hashes are 60 chars

    def test_verify_password_correct(self):
        """Verify should return True for correct password."""
        from app.services.auth_service import AuthService

        auth_service = AuthService()
        password = "securepassword123"
        hashed = auth_service.hash_password(password)

        result = auth_service.verify_password(password, hashed)

        assert result is True

    def test_verify_password_incorrect(self):
        """Verify should return False for incorrect password."""
        from app.services.auth_service import AuthService

        auth_service = AuthService()
        password = "securepassword123"
        wrong_password = "wrongpassword"
        hashed = auth_service.hash_password(password)

        result = auth_service.verify_password(wrong_password, hashed)

        assert result is False


class TestAccessToken:
    """Tests for JWT access token functionality."""

    def test_create_access_token_contains_user_id_and_roles(self):
        """Access token payload should contain user_id and roles."""
        from app.services.auth_service import AuthService

        auth_service = AuthService()
        user_id = uuid4()
        roles = ["student", "teacher"]

        token = auth_service.create_access_token(user_id, roles)
        payload = auth_service.decode_access_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["roles"] == roles
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_access_token_valid(self):
        """Should decode a valid token successfully."""
        from app.services.auth_service import AuthService

        auth_service = AuthService()
        user_id = uuid4()
        roles = ["student"]

        token = auth_service.create_access_token(user_id, roles)
        payload = auth_service.decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)

    def test_decode_access_token_expired_raises(self):
        """Should raise error for expired token."""
        from app.services.auth_service import AuthService
        from jose import jwt, JWTError
        from app.config import get_settings

        auth_service = AuthService()
        settings = get_settings()
        user_id = uuid4()

        # Create an expired token manually
        expired_payload = {
            "sub": str(user_id),
            "roles": ["student"],
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
            "iat": datetime.utcnow() - timedelta(hours=2),
            "type": "access",
        }
        expired_token = jwt.encode(
            expired_payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(JWTError):
            auth_service.decode_access_token(expired_token)

    def test_decode_access_token_invalid_signature_raises(self):
        """Should raise error for token with invalid signature."""
        from app.services.auth_service import AuthService
        from jose import jwt, JWTError

        auth_service = AuthService()
        user_id = uuid4()

        # Create token with wrong secret
        bad_payload = {
            "sub": str(user_id),
            "roles": ["student"],
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "type": "access",
        }
        bad_token = jwt.encode(bad_payload, "wrong-secret", algorithm="HS256")

        with pytest.raises(JWTError):
            auth_service.decode_access_token(bad_token)


class TestRefreshToken:
    """Tests for refresh token functionality."""

    @pytest.mark.asyncio
    async def test_create_refresh_token_stores_hash(self):
        """Creating refresh token should store hashed version in DB."""
        from app.services.auth_service import AuthService

        mock_db = AsyncMock()
        auth_service = AuthService(mock_db)
        user_id = uuid4()

        token = await auth_service.create_refresh_token(user_id)

        # Token should be returned (not the hash)
        assert token is not None
        assert len(token) > 20  # URL-safe base64

        # DB should have been called to store
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_refresh_token_valid(self):
        """Should return token record for valid refresh token."""
        from app.services.auth_service import AuthService
        from app.models.auth import RefreshToken

        mock_db = AsyncMock()
        auth_service = AuthService(mock_db)
        user_id = uuid4()

        # First create a token
        token = await auth_service.create_refresh_token(user_id)

        # Get the hash that was stored
        stored_token = mock_db.add.call_args[0][0]
        assert isinstance(stored_token, RefreshToken)

        # Now mock the DB to return this token on query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [stored_token]
        mock_db.execute.return_value = mock_result

        # Verify should find the token
        result = await auth_service.verify_refresh_token(token)

        assert result is not None
        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_verify_refresh_token_revoked_fails(self):
        """Should return None for revoked refresh token."""
        from app.services.auth_service import AuthService
        from app.models.auth import RefreshToken

        mock_db = AsyncMock()
        auth_service = AuthService(mock_db)

        # Create a revoked token in DB
        revoked_token = RefreshToken(
            id=uuid4(),
            user_id=uuid4(),
            token_hash="some-hash",
            expires_at=datetime.utcnow() + timedelta(days=30),
            revoked_at=datetime.utcnow(),  # Revoked!
        )

        # Mock DB to return empty (revoked tokens filtered out)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await auth_service.verify_refresh_token("any-token")

        assert result is None

    @pytest.mark.asyncio
    async def test_revoke_refresh_token(self):
        """Should set revoked_at timestamp on token."""
        from app.services.auth_service import AuthService
        from app.models.auth import RefreshToken

        mock_db = AsyncMock()
        auth_service = AuthService(mock_db)
        token_id = uuid4()

        # Mock finding the token
        existing_token = RefreshToken(
            id=token_id,
            user_id=uuid4(),
            token_hash="some-hash",
            expires_at=datetime.utcnow() + timedelta(days=30),
            revoked_at=None,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_token
        mock_db.execute.return_value = mock_result

        await auth_service.revoke_refresh_token(token_id)

        assert existing_token.revoked_at is not None
        mock_db.commit.assert_called()


class TestPasswordResetToken:
    """Tests for password reset token functionality."""

    @pytest.mark.asyncio
    async def test_create_password_reset_token(self):
        """Should create a password reset token and store hash."""
        from app.services.auth_service import AuthService
        from app.models.auth import PasswordResetToken

        mock_db = AsyncMock()
        auth_service = AuthService(mock_db)
        user_id = uuid4()

        token = await auth_service.create_password_reset_token(user_id)

        assert token is not None
        assert len(token) > 20

        # Verify it was stored
        mock_db.add.assert_called_once()
        stored = mock_db.add.call_args[0][0]
        assert isinstance(stored, PasswordResetToken)
        assert stored.user_id == user_id
        assert stored.expires_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_verify_password_reset_token_valid(self):
        """Should return token record for valid reset token."""
        from app.services.auth_service import AuthService
        from app.models.auth import PasswordResetToken

        mock_db = AsyncMock()
        auth_service = AuthService(mock_db)
        user_id = uuid4()

        # Create token
        token = await auth_service.create_password_reset_token(user_id)
        stored_token = mock_db.add.call_args[0][0]

        # Mock DB to return this token
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [stored_token]
        mock_db.execute.return_value = mock_result

        result = await auth_service.verify_password_reset_token(token)

        assert result is not None
        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_verify_password_reset_token_used_fails(self):
        """Should return None for already-used reset token."""
        from app.services.auth_service import AuthService

        mock_db = AsyncMock()
        auth_service = AuthService(mock_db)

        # Mock DB to return empty (used tokens filtered out)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await auth_service.verify_password_reset_token("any-token")

        assert result is None

    @pytest.mark.asyncio
    async def test_mark_password_reset_token_used(self):
        """Should set used_at timestamp on token."""
        from app.services.auth_service import AuthService
        from app.models.auth import PasswordResetToken

        mock_db = AsyncMock()
        auth_service = AuthService(mock_db)
        token_id = uuid4()

        existing_token = PasswordResetToken(
            id=token_id,
            user_id=uuid4(),
            token_hash="some-hash",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            used_at=None,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_token
        mock_db.execute.return_value = mock_result

        await auth_service.mark_password_reset_token_used(token_id)

        assert existing_token.used_at is not None
        mock_db.commit.assert_called()
