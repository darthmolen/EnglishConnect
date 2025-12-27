"""Teacher-specific test fixtures."""

import pytest


# All teacher tests are marked as agent_integration
pytestmark = [
    pytest.mark.agent_integration,
]
