"""E2E test configuration for Playwright.

These tests require:
- Frontend to be running (npm run dev)
- Backend services to be running (./start.sh)

Usage:
    pytest tests/e2e/ --headed  # Watch browser
    pytest tests/e2e/           # Headless mode
"""

import socket

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

# Default URLs
FRONTEND_URL = "http://localhost:5173"  # Vite default
BACKEND_URL = "http://localhost:8000"


def check_service_available(host: str, port: int) -> bool:
    """Check if a service is available."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        return result == 0
    except Exception:
        return False
    finally:
        sock.close()


def check_frontend_available() -> bool:
    """Check if frontend dev server is running."""
    return check_service_available("127.0.0.1", 5173)


def check_backend_available() -> bool:
    """Check if backend is running."""
    return check_service_available("127.0.0.1", 8000)


# Skip all E2E tests if services aren't running
def pytest_collection_modifyitems(config, items):
    """Skip E2E tests if required services aren't running."""
    frontend_up = check_frontend_available()
    backend_up = check_backend_available()

    for item in items:
        if "e2e" in str(item.fspath):
            if not frontend_up:
                item.add_marker(pytest.mark.skip(
                    reason="Frontend not available at localhost:5173. Run 'npm run dev' first."
                ))
            elif not backend_up:
                item.add_marker(pytest.mark.skip(
                    reason="Backend not available at localhost:8000. Run './start.sh' first."
                ))


@pytest.fixture(scope="session")
def frontend_url():
    """Provide frontend URL."""
    return FRONTEND_URL


@pytest.fixture(scope="session")
def backend_url():
    """Provide backend URL."""
    return BACKEND_URL


@pytest_asyncio.fixture(scope="function")
async def browser():
    """Provide a Playwright browser instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest_asyncio.fixture(scope="function")
async def page(browser):
    """Provide a fresh browser page for each test."""
    context = await browser.new_context()
    page = await context.new_page()
    yield page
    await context.close()
