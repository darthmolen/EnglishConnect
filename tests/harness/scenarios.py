"""Scenario data structures for agent integration testing.

Scenarios define multi-step test cases with expected behaviors.
"""

from dataclasses import dataclass, field


@dataclass
class ScenarioStep:
    """Single step in a test scenario.

    Attributes:
        student_input: What the student says
        expected_phase: Assert phase type after this step (optional)
        expect_tool: Assert this tool was called (optional)
        expect_contains: Semantic check - response should contain these strings (optional)
        expect_not_contains: Semantic check - response should NOT contain these (optional)
    """

    student_input: str
    expected_phase: str | None = None
    expect_tool: str | None = None
    expect_contains: list[str] = field(default_factory=list)
    expect_not_contains: list[str] = field(default_factory=list)


@dataclass
class Scenario:
    """Complete test scenario with multiple steps.

    Attributes:
        name: Unique scenario identifier
        lesson_number: Lesson to use for this scenario
        description: Human-readable description of what this tests
        steps: List of scenario steps to execute
    """

    name: str
    lesson_number: int
    description: str
    steps: list[ScenarioStep]

    def __str__(self) -> str:
        return f"Scenario({self.name}: {self.description})"
