"""Integration test configuration and fixtures.

These tests require:
- PostgreSQL to be running (./start.sh infra)
- Content to be ingested (./start.sh ingest)
"""

import asyncio
import pytest


def check_postgres_available():
    """Check if PostgreSQL is available."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 5432))
        return result == 0
    except Exception:
        return False
    finally:
        sock.close()


# Skip all integration tests if database is not available
def pytest_collection_modifyitems(config, items):
    """Skip integration tests if PostgreSQL is not running."""
    if not check_postgres_available():
        skip_marker = pytest.mark.skip(
            reason="PostgreSQL not available. Run './start.sh infra' first."
        )
        for item in items:
            if "integration" in str(item.fspath):
                item.add_marker(skip_marker)
