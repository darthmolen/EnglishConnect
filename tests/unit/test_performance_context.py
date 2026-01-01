"""Unit tests for PerformanceContext model."""

import pytest

from app.models.performance import PerformanceContext


class TestPerformanceContext:
    """Test PerformanceContext tracking and struggle detection."""

    def test_initial_state(self):
        """Should start with zero errors and low struggle level."""
        ctx = PerformanceContext()
        assert ctx.consecutive_errors == 0
        assert ctx.help_requests == 0
        assert ctx.struggle_level == "low"

    def test_tracks_consecutive_errors(self):
        """Should track consecutive incorrect attempts."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        assert ctx.consecutive_errors == 1

        ctx.record_attempt(correct=False)
        assert ctx.consecutive_errors == 2

        ctx.record_attempt(correct=False)
        assert ctx.consecutive_errors == 3

    def test_resets_on_correct_answer(self):
        """Should reset consecutive errors when student answers correctly."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)
        assert ctx.consecutive_errors == 2

        ctx.record_attempt(correct=True)
        assert ctx.consecutive_errors == 0

    def test_struggle_level_low(self):
        """Should be 'low' with 0-1 consecutive errors."""
        ctx = PerformanceContext()
        assert ctx.struggle_level == "low"

        ctx.record_attempt(correct=False)
        assert ctx.struggle_level == "low"

    def test_struggle_level_medium(self):
        """Should be 'medium' with 2 consecutive errors."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)
        assert ctx.consecutive_errors == 2
        assert ctx.struggle_level == "medium"

    def test_struggle_level_high(self):
        """Should be 'high' with 3+ consecutive errors."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)
        assert ctx.consecutive_errors == 3
        assert ctx.struggle_level == "high"

        # Should stay high with more errors
        ctx.record_attempt(correct=False)
        assert ctx.consecutive_errors == 4
        assert ctx.struggle_level == "high"

    def test_tracks_help_requests(self):
        """Should track explicit help requests."""
        ctx = PerformanceContext()
        ctx.record_help_request()
        assert ctx.help_requests == 1

        ctx.record_help_request()
        assert ctx.help_requests == 2

    def test_needs_help_low_struggle(self):
        """Should not need help at low struggle level."""
        ctx = PerformanceContext()
        assert ctx.needs_help is False

    def test_needs_help_medium_struggle(self):
        """Should need help at medium struggle level."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)
        assert ctx.needs_help is True

    def test_needs_help_high_struggle(self):
        """Should need help at high struggle level."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)
        assert ctx.needs_help is True

    def test_to_prompt_context(self):
        """Should produce context dict for prompt injection."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)
        ctx.record_help_request()

        prompt_ctx = ctx.to_prompt_context()
        assert prompt_ctx["consecutive_errors"] == 2
        assert prompt_ctx["struggle_level"] == "medium"
        assert prompt_ctx["help_requests"] == 1
        assert prompt_ctx["needs_help"] is True

    def test_reset(self):
        """Should reset all tracking state."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)
        ctx.record_help_request()

        ctx.reset()
        assert ctx.consecutive_errors == 0
        assert ctx.help_requests == 0
        assert ctx.struggle_level == "low"
