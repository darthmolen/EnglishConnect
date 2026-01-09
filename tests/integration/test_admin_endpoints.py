# tests/integration/test_admin_endpoints.py
"""Integration tests for admin endpoints - TDD: tests written BEFORE implementation."""

import pytest
import uuid


def unique_email(prefix: str = "test") -> str:
    """Generate unique email for test isolation."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.example.com"


def create_approved_user_sync(email: str, password: str = "securepass123") -> str:
    """Create an approved user and return their ID."""
    import psycopg2
    from passlib.context import CryptContext
    from datetime import datetime

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    password_hash = pwd_context.hash(password)
    user_id = str(uuid.uuid4())

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
                """
                INSERT INTO users (id, email, password_hash, native_language, timezone, is_approved, approval_status, auth_provider, created_at, updated_at)
                VALUES (%s, %s, %s, 'es', 'America/Los_Angeles', TRUE, 'approved', 'local', %s, %s)
                RETURNING id
                """,
                (user_id, email, password_hash, datetime.utcnow(), datetime.utcnow()),
            )
            user_id = str(cur.fetchone()[0])
        conn.commit()
        return user_id
    finally:
        conn.close()


def assign_role_sync(user_id: str, role_name: str) -> None:
    """Assign a role to a user."""
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
            cur.execute("SELECT id FROM roles WHERE name = %s", (role_name,))
            role_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (user_id, role_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_access_token(auth_client, email: str, password: str) -> str:
    """Login and return access token."""
    response = auth_client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()["access_token"]


class TestAdminListUsers:
    """Tests for GET /api/auth/admin/users endpoint."""

    def test_list_users_requires_admin_role(self, auth_client):
        """Non-admin users should get 403 when listing users."""
        # Create a regular user (no admin role)
        email = unique_email("regular")
        password = "securepass123"
        user_id = create_approved_user_sync(email, password)
        assign_role_sync(user_id, "student")

        token = get_access_token(auth_client, email, password)

        response = auth_client.get(
            "/api/auth/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_list_users_as_admin_returns_users(self, auth_client):
        """Admin users should be able to list all users."""
        # Create an admin user
        email = unique_email("admin")
        password = "adminpass123"
        user_id = create_approved_user_sync(email, password)
        assign_role_sync(user_id, "admin")

        token = get_access_token(auth_client, email, password)

        response = auth_client.get(
            "/api/auth/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check user object structure
        assert "id" in data[0]
        assert "email" in data[0]
        assert "is_approved" in data[0]
        assert "approval_status" in data[0]

    def test_list_users_filter_by_pending(self, auth_client):
        """Admin can filter users by pending approval status."""
        # Create admin
        admin_email = unique_email("admin")
        admin_password = "adminpass123"
        admin_id = create_approved_user_sync(admin_email, admin_password)
        assign_role_sync(admin_id, "admin")

        # Create a pending user via signup
        pending_email = unique_email("pending")
        auth_client.post(
            "/api/auth/signup",
            json={
                "email": pending_email,
                "password": "pendingpass123",
                "confirm_password": "pendingpass123",
            },
        )

        token = get_access_token(auth_client, admin_email, admin_password)

        response = auth_client.get(
            "/api/auth/admin/users?status=pending",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        # All returned users should be pending
        for user in data:
            assert user["approval_status"] == "pending"


class TestAdminApproveUser:
    """Tests for POST /api/auth/admin/users/approve endpoint."""

    def test_approve_user_changes_status(self, auth_client):
        """Approving a user should change their status to approved."""
        # Create admin
        admin_email = unique_email("admin")
        admin_password = "adminpass123"
        admin_id = create_approved_user_sync(admin_email, admin_password)
        assign_role_sync(admin_id, "admin")

        # Create a pending user
        pending_email = unique_email("pending")
        signup_response = auth_client.post(
            "/api/auth/signup",
            json={
                "email": pending_email,
                "password": "pendingpass123",
                "confirm_password": "pendingpass123",
            },
        )
        pending_user_id = signup_response.json()["id"]

        token = get_access_token(auth_client, admin_email, admin_password)

        # Approve the user
        response = auth_client.post(
            "/api/auth/admin/users/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": pending_user_id, "approved": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_approved"] is True
        assert data["approval_status"] == "approved"

    def test_reject_user_changes_status(self, auth_client):
        """Rejecting a user should change their status to rejected."""
        # Create admin
        admin_email = unique_email("admin")
        admin_password = "adminpass123"
        admin_id = create_approved_user_sync(admin_email, admin_password)
        assign_role_sync(admin_id, "admin")

        # Create a pending user
        pending_email = unique_email("pending")
        signup_response = auth_client.post(
            "/api/auth/signup",
            json={
                "email": pending_email,
                "password": "pendingpass123",
                "confirm_password": "pendingpass123",
            },
        )
        pending_user_id = signup_response.json()["id"]

        token = get_access_token(auth_client, admin_email, admin_password)

        # Reject the user
        response = auth_client.post(
            "/api/auth/admin/users/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": pending_user_id, "approved": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_approved"] is False
        assert data["approval_status"] == "rejected"

    def test_approve_user_requires_admin(self, auth_client):
        """Non-admin users cannot approve users."""
        # Create a regular user
        email = unique_email("regular")
        password = "securepass123"
        user_id = create_approved_user_sync(email, password)
        assign_role_sync(user_id, "student")

        token = get_access_token(auth_client, email, password)

        response = auth_client.post(
            "/api/auth/admin/users/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": "some-user-id", "approved": True},
        )

        assert response.status_code == 403


class TestAdminAssignRole:
    """Tests for POST /api/auth/admin/users/role endpoint."""

    def test_assign_role_adds_role(self, auth_client):
        """Admin can assign a role to a user."""
        # Create admin
        admin_email = unique_email("admin")
        admin_password = "adminpass123"
        admin_id = create_approved_user_sync(admin_email, admin_password)
        assign_role_sync(admin_id, "admin")

        # Create target user
        target_email = unique_email("target")
        target_password = "targetpass123"
        target_id = create_approved_user_sync(target_email, target_password)
        assign_role_sync(target_id, "student")

        token = get_access_token(auth_client, admin_email, admin_password)

        # Assign teacher role
        response = auth_client.post(
            "/api/auth/admin/users/role",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": target_id, "role": "teacher"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "teacher" in data["roles"]

    def test_assign_role_requires_admin(self, auth_client):
        """Non-admin users cannot assign roles."""
        # Create a regular user
        email = unique_email("regular")
        password = "securepass123"
        user_id = create_approved_user_sync(email, password)
        assign_role_sync(user_id, "student")

        token = get_access_token(auth_client, email, password)

        response = auth_client.post(
            "/api/auth/admin/users/role",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": "some-user-id", "role": "teacher"},
        )

        assert response.status_code == 403

    def test_assign_invalid_role_returns_400(self, auth_client):
        """Assigning an invalid role should return 400."""
        # Create admin
        admin_email = unique_email("admin")
        admin_password = "adminpass123"
        admin_id = create_approved_user_sync(admin_email, admin_password)
        assign_role_sync(admin_id, "admin")

        token = get_access_token(auth_client, admin_email, admin_password)

        response = auth_client.post(
            "/api/auth/admin/users/role",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": "some-user-id", "role": "invalid_role"},
        )

        # Pydantic validation should catch this
        assert response.status_code == 422


class TestAdminNoAuth:
    """Tests for admin endpoints without authentication."""

    def test_list_users_without_auth_returns_401(self, auth_client):
        """Accessing admin endpoints without auth should return 401."""
        response = auth_client.get("/api/auth/admin/users")
        assert response.status_code == 401

    def test_approve_user_without_auth_returns_401(self, auth_client):
        """Approving users without auth should return 401."""
        response = auth_client.post(
            "/api/auth/admin/users/approve",
            json={"user_id": "some-id", "approved": True},
        )
        assert response.status_code == 401

    def test_assign_role_without_auth_returns_401(self, auth_client):
        """Assigning roles without auth should return 401."""
        response = auth_client.post(
            "/api/auth/admin/users/role",
            json={"user_id": "some-id", "role": "teacher"},
        )
        assert response.status_code == 401
