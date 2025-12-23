# tests/unit/test_auth_middleware.py
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException

from app.middleware.auth import verify_token, get_current_user


@pytest.mark.asyncio
async def test_verify_token_valid():
    """Valid token returns decoded claims."""
    mock_claims = {
        "oid": "user-object-id",
        "preferred_username": "user@example.com",
        "name": "Test User",
    }

    with patch("app.middleware.auth.decode_token") as mock_decode:
        mock_decode.return_value = mock_claims
        claims = await verify_token("valid-token")
        assert claims["oid"] == "user-object-id"


@pytest.mark.asyncio
async def test_verify_token_invalid_raises():
    """Invalid token raises HTTPException 401."""
    with patch("app.middleware.auth.decode_token") as mock_decode:
        mock_decode.side_effect = Exception("Invalid token")

        with pytest.raises(HTTPException) as exc_info:
            await verify_token("invalid-token")

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_creates_user():
    """get_current_user creates user if not exists."""
    mock_claims = {
        "oid": "new-user-id",
        "preferred_username": "new@example.com",
        "name": "New User",
    }
    mock_user = MagicMock()
    mock_user.id = "uuid-123"

    # Mock credentials object
    mock_credentials = MagicMock()
    mock_credentials.credentials = "valid-token"

    with patch("app.middleware.auth.verify_token", return_value=mock_claims):
        with patch("app.middleware.auth.UserService") as MockService:
            mock_service = MockService.return_value
            mock_service.get_or_create_user = AsyncMock(return_value=mock_user)

            mock_db = AsyncMock()
            user = await get_current_user(credentials=mock_credentials, db=mock_db)

            assert user == mock_user
            mock_service.get_or_create_user.assert_called_once_with(
                oauth_provider="microsoft",
                oauth_id="new-user-id",
                email="new@example.com",
                display_name="New User",
            )
