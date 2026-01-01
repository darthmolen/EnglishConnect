"""Performance tracking models for adaptive teaching.

Tracks student struggle signals to inform when the agent should
retrieve additional teaching content.
"""

from dataclasses import dataclass, field


@dataclass
class PerformanceContext:
    """Tracks student performance within a session for adaptive help.

    Used to detect when a student is struggling and may need additional
    teaching content retrieved via the get_teaching_help tool.

    Attributes:
        consecutive_errors: Count of wrong attempts in a row (resets on correct)
        help_requests: Count of explicit requests for help

    Properties:
        struggle_level: "low", "medium", or "high" based on consecutive_errors
        needs_help: True if struggle_level is medium or higher
    """

    consecutive_errors: int = 0
    help_requests: int = 0

    @property
    def struggle_level(self) -> str:
        """Determine struggle level based on consecutive errors.

        Returns:
            "low": 0-1 consecutive errors
            "medium": 2 consecutive errors
            "high": 3+ consecutive errors
        """
        if self.consecutive_errors >= 3:
            return "high"
        if self.consecutive_errors >= 2:
            return "medium"
        return "low"

    @property
    def needs_help(self) -> bool:
        """Check if student needs additional help.

        Returns:
            True if struggle_level is "medium" or "high"
        """
        return self.struggle_level in ("medium", "high")

    def record_attempt(self, correct: bool) -> None:
        """Record a student's attempt at a vocabulary word or pattern.

        Args:
            correct: Whether the student's attempt was correct
        """
        if correct:
            self.consecutive_errors = 0
        else:
            self.consecutive_errors += 1

    def record_help_request(self) -> None:
        """Record an explicit help request from the student."""
        self.help_requests += 1

    def reset(self) -> None:
        """Reset all tracking state."""
        self.consecutive_errors = 0
        self.help_requests = 0

    def to_prompt_context(self) -> dict:
        """Convert to dict for injection into system prompts.

        Returns:
            Dict with keys: consecutive_errors, struggle_level,
                           help_requests, needs_help
        """
        return {
            "consecutive_errors": self.consecutive_errors,
            "struggle_level": self.struggle_level,
            "help_requests": self.help_requests,
            "needs_help": self.needs_help,
        }
