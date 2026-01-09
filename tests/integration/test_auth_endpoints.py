# tests/integration/test_auth_endpoints.py
"""Integration tests for authentication endpoints - TDD: tests written BEFORE implementation."""

import pytest
import uuid


def unique_email(prefix: str = "test") -> str:
    """Generate unique email for test isolation."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.example.com"


def approve_user_sync(email: str) -> None:
    """Approve a user using synchronous database access."""
    import psycopg2

    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="englishconnect",
        user="englishconnect",
        password="devpassword",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_approved = TRUE, approval_status = 'approved' WHERE email = %s",
                (email,),
            )
        conn.commit()
    finally:
        conn.close()


def create_password_reset_token_sync(email: str) -> str:
    """Create password reset token using synchronous database access."""
    import psycopg2
    import secrets
    from datetime import datetime, timedelta
    from passlib.context import CryptContext

    # Use the same hashing as auth_service
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    token = secrets.token_urlsafe(32)
    token_hash = pwd_context.hash(token)
    expires_at = datetime.utcnow() + timedelta(hours=1)

    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="englishconnect",
        user="englishconnect",
        password="devpassword",
    )
    try:
        with conn.cursor() as cur:
            # Get user ID
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"User not found: {email}")
            user_id = row[0]

            # Create token
            cur.execute(
                """
                INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
                VALUES (%s, %s, %s)
                """,
                (user_id, token_hash, expires_at),
            )
        conn.commit()
        return token
    finally:
        conn.close()


class TestAuthConfig:
    """Tests for /api/auth/config endpoint."""

    def test_get_config_returns_auth_mode(self, auth_client):
        """Should return auth mode and Azure AD settings if enabled."""
        response = auth_client.get("/api/auth/config")

        assert response.status_code == 200
        data = response.json()
        assert "auth_mode" in data
        assert data["auth_mode"] in ["local", "azure_ad", "both"]


class TestSignup:
    """Tests for /api/auth/signup endpoint."""

    def test_signup_creates_pending_user(self, auth_client):
        """Signup should create a user with pending approval status."""
        email = unique_email("newuser")
        response = auth_client.post(
            "/api/auth/signup",
            json={
                "email": email,
                "password": "securepass123",
                "confirm_password": "securepass123",
                "first_name": "Test",
                "last_name": "User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == email
        assert data["is_approved"] is False
        assert data["approval_status"] == "pending"

    def test_signup_duplicate_email_returns_409(self, auth_client):
        """Signup with existing email should return 409 Conflict."""
        email = unique_email("duplicate")

        # First signup
        response1 = auth_client.post(
            "/api/auth/signup",
            json={
                "email": email,
                "password": "securepass123",
                "confirm_password": "securepass123",
            },
        )
        assert response1.status_code == 201

        # Second signup with same email
        response = auth_client.post(
            "/api/auth/signup",
            json={
                "email": email,
                "password": "anotherpass123",
                "confirm_password": "anotherpass123",
            },
        )

        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()

    def test_signup_password_mismatch_returns_422(self, auth_client):
        """Signup with mismatched passwords should return 422 validation error."""
        email = unique_email("mismatch")
        response = auth_client.post(
            "/api/auth/signup",
            json={
                "email": email,
                "password": "securepass123",
                "confirm_password": "differentpass123",
            },
        )

        # Pydantic validation errors return 422 Unprocessable Entity
        assert response.status_code == 422

    def test_signup_short_password_returns_422(self, auth_client):
        """Signup with password < 8 chars should return 422 validation error."""
        email = unique_email("short")
        response = auth_client.post(
            "/api/auth/signup",
            json={
                "email": email,
                "password": "short",
                "confirm_password": "short",
            },
        )

        # Pydantic validation errors return 422 Unprocessable Entity
        assert response.status_code == 422


class TestLogin:
    """Tests for /api/auth/login endpoint."""

    def test_login_approved_user_returns_tokens(self, auth_client):
        """Login with approved user should return access and refresh tokens."""
        email = unique_email("approved")

        # Create user via API
        signup_response = auth_client.post(
            "/api/auth/signup",
            json={
                "email": email,
                "password": "securepass123",
                "confirm_password": "securepass123",
            },
        )
        assert signup_response.status_code == 201

        # Approve user using sync database access
        approve_user_sync(email)

        # Now login
        response = auth_client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "securepass123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_pending_user_returns_403(self, auth_client):
        """Login with pending user should return 403 Forbidden."""
        email = unique_email("pending")

        # Create a pending user
        signup_response = auth_client.post(
            "/api/auth/signup",
            json={
                "email": email,
                "password": "securepass123",
                "confirm_password": "securepass123",
            },
        )
        assert signup_response.status_code == 201

        # Try to login (user is still pending)
        response = auth_client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "securepass123",
            },
        )

        assert response.status_code == 403
        assert "pending" in response.json()["detail"].lower()

    def test_login_wrong_password_returns_401(self, auth_client):
        """Login with wrong password should return 401."""
        email = unique_email("wrongpass")

        # Create a user
        signup_response = auth_client.post(
            "/api/auth/signup",
            json={
                "email": email,
                "password": "correctpassword",
                "confirm_password": "correctpassword",
            },
        )
        assert signup_response.status_code == 201

        # Try with wrong password
        response = auth_client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401

    def test_login_nonexistent_user_returns_401(self, auth_client):
        """Login with non-existent email should return 401."""
        email = unique_email("nonexistent")
        response = auth_client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "anypassword",
            },
        )

        assert response.status_code == 401


class TestRefreshToken:
    """Tests for /api/auth/refresh endpoint."""

    def test_refresh_valid_token_returns_new_tokens(self, auth_client):
        """Refresh with valid token should return new access and refresh tokens."""
        email = unique_email("refresh")

        # Create and approve user
        signup_response = auth_client.post(
            "/api/auth/signup",
            json={
                "email": email,
                "password": "securepass123",
                "confirm_password": "securepass123",
            },
        )
        assert signup_response.status_code == 201

        approve_user_sync(email)

        # Login to get tokens
        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "securepass123",
            },
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token
        response = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_invalid_token_returns_401(self, auth_client):
        """Refresh with invalid token should return 401."""
        response = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-token-here"},
        )

        assert response.status_code == 401


class TestPasswordReset:
    """Tests for password reset endpoints."""

    def test_password_reset_request_always_returns_200(self, auth_client):
        """Password reset request should always return 200 (anti-enumeration)."""
        email = unique_email("nonexistent")
        # Request for non-existent email
        response = auth_client.post(
            "/api/auth/password-reset/request",
            json={"email": email},
        )

        assert response.status_code == 200
        assert "email" in response.json()["message"].lower()

    def test_password_reset_confirm_valid_token(self, auth_client):
        """Password reset confirm with valid token should reset password."""
        email = unique_email("resetme")

        # Create user
        signup_response = auth_client.post(
            "/api/auth/signup",
            json={
                "email": email,
                "password": "oldpassword123",
                "confirm_password": "oldpassword123",
            },
        )
        assert signup_response.status_code == 201

        # Create reset token using sync database access
        token = create_password_reset_token_sync(email)

        # Confirm reset
        response = auth_client.post(
            "/api/auth/password-reset/confirm",
            json={
                "token": token,
                "new_password": "newpassword123",
                "confirm_password": "newpassword123",
            },
        )

        assert response.status_code == 200

    def test_password_reset_confirm_expired_token_returns_400(self, auth_client):
        """Password reset confirm with expired/invalid token should return 400."""
        response = auth_client.post(
            "/api/auth/password-reset/confirm",
            json={
                "token": "invalid-or-expired-token",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123",
            },
        )

        assert response.status_code == 400
