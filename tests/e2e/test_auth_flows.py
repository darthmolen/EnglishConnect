# tests/e2e/test_auth_flows.py
"""E2E tests for authentication flows.

These tests verify the complete user journey:
1. Sign up -> Pending approval -> Admin approves -> Login
2. Password reset flow
3. Admin user management

Requires:
- Frontend running (npm run dev)
- Backend running (./start.sh)
- Database with roles seeded
"""

import pytest
import uuid
from playwright.async_api import expect

# Mark all tests in this file as E2E
pytestmark = pytest.mark.e2e


def unique_email(prefix: str = "e2e") -> str:
    """Generate unique email for test isolation."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.example.com"


class TestSignUpFlow:
    """Test user signup and approval flow."""

    @pytest.mark.asyncio
    async def test_signup_shows_pending_message(self, page, frontend_url):
        """Test that signup shows pending approval message."""
        email = unique_email("signup")

        # Navigate to login page
        await page.goto(f"{frontend_url}#/login")

        # Wait for page to load
        await expect(page.locator("h1")).to_contain_text("Sign In")

        # Click "Create account" link
        await page.click("text=Create account")

        # Wait for signup form
        await expect(page.locator("h1")).to_contain_text("Create Account")

        # Fill signup form
        await page.fill('input[type="email"]', email)
        await page.fill('input[id="signupPassword"]', "securepass123")
        await page.fill('input[id="confirmPassword"]', "securepass123")

        # Submit
        await page.click('button[type="submit"]')

        # Should show pending approval message
        await expect(page.locator("h1")).to_contain_text("Pending Approval")
        await expect(page.locator("text=administrator will review")).to_be_visible()

    @pytest.mark.asyncio
    async def test_signup_password_mismatch_shows_error(self, page, frontend_url):
        """Test that mismatched passwords show error."""
        await page.goto(f"{frontend_url}#/login")

        # Navigate to signup
        await page.click("text=Create account")
        await expect(page.locator("h1")).to_contain_text("Create Account")

        # Fill form with mismatched passwords
        await page.fill('input[type="email"]', unique_email())
        await page.fill('input[id="signupPassword"]', "password123")
        await page.fill('input[id="confirmPassword"]', "different456")

        # Submit
        await page.click('button[type="submit"]')

        # Should show error
        await expect(page.locator("text=Passwords do not match")).to_be_visible()

    @pytest.mark.asyncio
    async def test_login_pending_user_shows_error(self, page, frontend_url, backend_url):
        """Test that pending users cannot login."""
        email = unique_email("pending")
        password = "securepass123"

        # First, create a user via API (pending by default)
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{backend_url}/api/auth/signup",
                json={
                    "email": email,
                    "password": password,
                    "confirm_password": password,
                },
            )
            assert response.status_code == 201

        # Now try to login
        await page.goto(f"{frontend_url}#/login")
        await expect(page.locator("h1")).to_contain_text("Sign In")

        await page.fill('input[type="email"]', email)
        await page.fill('input[type="password"]', password)
        await page.click('button[type="submit"]')

        # Should show pending approval error
        await expect(page.locator("text=pending approval")).to_be_visible()


class TestLoginFlow:
    """Test login flows."""

    @pytest.mark.asyncio
    async def test_login_success_redirects(self, page, frontend_url, backend_url):
        """Test that successful login redirects to main app."""
        # Create and approve user via API
        email = unique_email("approved")
        password = "securepass123"

        import httpx
        import psycopg2

        # Create user
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{backend_url}/api/auth/signup",
                json={
                    "email": email,
                    "password": password,
                    "confirm_password": password,
                },
            )
            assert response.status_code == 201
            user_id = response.json()["id"]

        # Approve user directly in database (admin action)
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
                    "UPDATE users SET is_approved = TRUE, approval_status = 'approved' WHERE id = %s",
                    (user_id,),
                )
            conn.commit()
        finally:
            conn.close()

        # Now login
        await page.goto(f"{frontend_url}#/login")
        await page.fill('input[type="email"]', email)
        await page.fill('input[type="password"]', password)
        await page.click('button[type="submit"]')

        # Should redirect to main app (hash should be #/ or empty)
        await page.wait_for_url(lambda url: "#/login" not in url)

        # Should see main app content
        await expect(page.locator("text=EnglishConnect")).to_be_visible()

    @pytest.mark.asyncio
    async def test_login_invalid_credentials_shows_error(self, page, frontend_url):
        """Test that invalid credentials show error."""
        await page.goto(f"{frontend_url}#/login")

        await page.fill('input[type="email"]', "nonexistent@test.com")
        await page.fill('input[type="password"]', "wrongpassword")
        await page.click('button[type="submit"]')

        # Should show error
        await expect(page.locator("text=Invalid")).to_be_visible()


class TestPasswordReset:
    """Test password reset flow."""

    @pytest.mark.asyncio
    async def test_password_reset_shows_confirmation(self, page, frontend_url):
        """Test that password reset request shows confirmation."""
        await page.goto(f"{frontend_url}#/login")

        # Click forgot password
        await page.click("text=Forgot password")

        # Should show reset form
        await expect(page.locator("h1")).to_contain_text("Reset Password")

        # Enter email
        await page.fill('input[type="email"]', "test@example.com")
        await page.click('button[type="submit"]')

        # Should show confirmation (anti-enumeration: always succeeds)
        await expect(page.locator("text=Check Your Email")).to_be_visible()


class TestAdminUserManagement:
    """Test admin user management."""

    @pytest.mark.asyncio
    async def test_admin_can_view_users(self, page, frontend_url, backend_url):
        """Test that admin can view user list."""
        # Create admin user
        admin_email = unique_email("admin")
        admin_password = "adminpass123"

        import httpx
        import psycopg2

        # Create user
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{backend_url}/api/auth/signup",
                json={
                    "email": admin_email,
                    "password": admin_password,
                    "confirm_password": admin_password,
                },
            )
            user_id = response.json()["id"]

        # Make user an approved admin
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="englishconnect",
            user="englishconnect",
            password="devpassword",
        )
        try:
            with conn.cursor() as cur:
                # Approve user
                cur.execute(
                    "UPDATE users SET is_approved = TRUE, approval_status = 'approved' WHERE id = %s",
                    (user_id,),
                )
                # Get admin role id
                cur.execute("SELECT id FROM roles WHERE name = 'admin'")
                admin_role_id = cur.fetchone()[0]
                # Assign admin role
                cur.execute(
                    "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (user_id, admin_role_id),
                )
            conn.commit()
        finally:
            conn.close()

        # Login as admin
        await page.goto(f"{frontend_url}#/login")
        await page.fill('input[type="email"]', admin_email)
        await page.fill('input[type="password"]', admin_password)
        await page.click('button[type="submit"]')

        # Wait for login to complete
        await page.wait_for_url(lambda url: "#/login" not in url)

        # Navigate to admin page
        await page.goto(f"{frontend_url}#/admin")

        # Should see user management
        await expect(page.locator("text=User Management")).to_be_visible()

        # Should see user table
        await expect(page.locator("table")).to_be_visible()

    @pytest.mark.asyncio
    async def test_non_admin_cannot_access_admin_page(self, page, frontend_url, backend_url):
        """Test that non-admin users are redirected from admin page."""
        # Create regular user
        email = unique_email("regular")
        password = "userpass123"

        import httpx
        import psycopg2

        # Create and approve user
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{backend_url}/api/auth/signup",
                json={
                    "email": email,
                    "password": password,
                    "confirm_password": password,
                },
            )
            user_id = response.json()["id"]

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
                    "UPDATE users SET is_approved = TRUE, approval_status = 'approved' WHERE id = %s",
                    (user_id,),
                )
            conn.commit()
        finally:
            conn.close()

        # Login
        await page.goto(f"{frontend_url}#/login")
        await page.fill('input[type="email"]', email)
        await page.fill('input[type="password"]', password)
        await page.click('button[type="submit"]')

        await page.wait_for_url(lambda url: "#/login" not in url)

        # Try to access admin page
        await page.goto(f"{frontend_url}#/admin")

        # Should be redirected away from admin page
        await page.wait_for_url(lambda url: "#/admin" not in url)


class TestLogout:
    """Test logout flow."""

    @pytest.mark.asyncio
    async def test_logout_clears_session(self, page, frontend_url, backend_url):
        """Test that logout clears the session."""
        # Create approved user
        email = unique_email("logout")
        password = "userpass123"

        import httpx
        import psycopg2

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{backend_url}/api/auth/signup",
                json={
                    "email": email,
                    "password": password,
                    "confirm_password": password,
                },
            )
            user_id = response.json()["id"]

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
                    "UPDATE users SET is_approved = TRUE, approval_status = 'approved' WHERE id = %s",
                    (user_id,),
                )
            conn.commit()
        finally:
            conn.close()

        # Login
        await page.goto(f"{frontend_url}#/login")
        await page.fill('input[type="email"]', email)
        await page.fill('input[type="password"]', password)
        await page.click('button[type="submit"]')

        await page.wait_for_url(lambda url: "#/login" not in url)

        # Should see user profile (sign out button)
        await expect(page.locator("text=Sign out")).to_be_visible()

        # Click sign out
        await page.click("text=Sign out")

        # Should show login button again
        await expect(page.locator("text=Sign In")).to_be_visible()
