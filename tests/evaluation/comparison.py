"""A/B comparison for prompt variations with position bias mitigation.

This module implements pairwise comparison with position swap to detect
and mitigate the 40% position bias found in LLM judges.

Algorithm:
1. Run test case with Prompt A -> Response A
2. Run test case with Prompt B -> Response B
3. Judge compares (A first, B second) -> Winner AB
4. Judge compares (B first, A second) -> Winner BA (normalized)
5. If AB == BA (consistent): count as valid win
6. If AB != BA (inconsistent): discard (position bias detected)

Usage:
    comparator = ABComparison()
    result = await comparator.compare(
        prompt_a_path="src/backend/app/prompts/agent/mode_practice.md",
        prompt_b_path="prompts/mode_practice_v2.md",
        test_cases=runner.load_test_cases(dimension=Dimension.LANGUAGE_CHOICE),
    )
    print(f"Winner: {result.winner}")
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from tests.evaluation.judge import JudgeLLM

logger = logging.getLogger(__name__)


class Winner(Enum):
    """Comparison outcome."""
    A = "A"
    B = "B"
    TIE = "tie"


@dataclass
class PairwiseResult:
    """Result of comparing two responses on a single test case."""

    test_id: str
    winner_ab: Winner  # Winner when A shown first
    winner_ba: Winner  # Winner when B shown first (normalized to A/B frame)
    consistent: bool   # Same winner in both orderings
    final_winner: Optional[Winner]  # Only set if consistent
    reason_ab: str = ""
    reason_ba: str = ""

    @property
    def is_valid_win(self) -> bool:
        """True if both orderings agree on a winner (not tie)."""
        return self.consistent and self.final_winner in (Winner.A, Winner.B)


@dataclass
class ComparisonResults:
    """Aggregated A/B comparison results."""

    total_comparisons: int
    consistent_a_wins: int
    consistent_b_wins: int
    ties: int
    inconsistent: int  # Different winner when order swapped (position bias)
    results: list[PairwiseResult]

    @property
    def winner(self) -> Winner:
        """Overall winner based on consistent wins only."""
        if self.consistent_a_wins > self.consistent_b_wins:
            return Winner.A
        elif self.consistent_b_wins > self.consistent_a_wins:
            return Winner.B
        return Winner.TIE

    @property
    def confidence(self) -> float:
        """Confidence in the result (ratio of consistent vs inconsistent)."""
        total = self.consistent_a_wins + self.consistent_b_wins + self.ties + self.inconsistent
        if total == 0:
            return 0.0
        consistent = self.consistent_a_wins + self.consistent_b_wins + self.ties
        return consistent / total

    @property
    def summary(self) -> str:
        """One-line summary."""
        return (
            f"Winner: {self.winner.value} | "
            f"A wins: {self.consistent_a_wins}, B wins: {self.consistent_b_wins}, "
            f"Ties: {self.ties}, Inconsistent: {self.inconsistent} | "
            f"Confidence: {self.confidence:.0%}"
        )


class ABComparison:
    """Compare two prompt variants using pairwise evaluation with position swap."""

    COMPARISON_PROMPT = """You are comparing two responses from an English teaching agent.

## Test Scenario
Student input: {user_input}
Context: {context}
Expected behavior: {expected_behavior}

## Response A
{response_a}

## Response B
{response_b}

## Instructions
Compare which response better matches the expected behavior.
Do NOT prefer responses because they are longer.
Do NOT prefer responses based on position (first vs second).
Focus ONLY on quality according to the expected behavior.
Ties are acceptable when responses are genuinely equivalent.

Respond with EXACTLY one of these formats:
A: [brief reason why A is better]
B: [brief reason why B is better]
TIE: [brief reason why they are equivalent]
"""

    def __init__(self, judge: Optional[JudgeLLM] = None):
        """Initialize comparator.

        Args:
            judge: JudgeLLM instance (created if not provided)
        """
        self._judge = judge

    @property
    def judge(self) -> JudgeLLM:
        """Lazy-load judge."""
        if self._judge is None:
            self._judge = JudgeLLM()
        return self._judge

    async def compare(
        self,
        prompt_a_path: str,
        prompt_b_path: str,
        test_cases: list[dict],
    ) -> ComparisonResults:
        """Run pairwise comparison on all test cases.

        Args:
            prompt_a_path: Path to first prompt file
            prompt_b_path: Path to second prompt file
            test_cases: List of test case dictionaries

        Returns:
            ComparisonResults with winner and details
        """
        prompt_a = Path(prompt_a_path).read_text()
        prompt_b = Path(prompt_b_path).read_text()

        results = []

        for i, case in enumerate(test_cases, 1):
            logger.info(f"Comparing {i}/{len(test_cases)}: {case['id']}")

            result = await self._compare_single(case, prompt_a, prompt_b)
            results.append(result)

            logger.info(f"  {result.final_winner.value if result.final_winner else 'INCONSISTENT'}")

        # Aggregate
        return ComparisonResults(
            total_comparisons=len(results),
            consistent_a_wins=sum(1 for r in results if r.final_winner == Winner.A),
            consistent_b_wins=sum(1 for r in results if r.final_winner == Winner.B),
            ties=sum(1 for r in results if r.final_winner == Winner.TIE),
            inconsistent=sum(1 for r in results if not r.consistent),
            results=results,
        )

    async def _compare_single(
        self,
        case: dict,
        prompt_a: str,
        prompt_b: str,
    ) -> PairwiseResult:
        """Compare two prompts on a single test case."""
        # Get responses from each prompt variant
        response_a = await self._run_with_prompt(case, prompt_a)
        response_b = await self._run_with_prompt(case, prompt_b)

        # First pass: A first, B second
        winner_ab, reason_ab = self._judge_pair(
            case=case,
            response_a=response_a,
            response_b=response_b,
        )

        # Second pass: B first, A second
        winner_ba_raw, reason_ba = self._judge_pair(
            case=case,
            response_a=response_b,  # Swapped
            response_b=response_a,  # Swapped
        )

        # Normalize winner_ba back to A/B reference frame
        if winner_ba_raw == Winner.A:
            winner_ba = Winner.B  # "A" in swapped order means B in original
        elif winner_ba_raw == Winner.B:
            winner_ba = Winner.A  # "B" in swapped order means A in original
        else:
            winner_ba = Winner.TIE

        # Check consistency
        consistent = (winner_ab == winner_ba)
        final_winner = winner_ab if consistent else None

        return PairwiseResult(
            test_id=case["id"],
            winner_ab=winner_ab,
            winner_ba=winner_ba,
            consistent=consistent,
            final_winner=final_winner,
            reason_ab=reason_ab,
            reason_ba=reason_ba,
        )

    async def _run_with_prompt(self, case: dict, prompt: str) -> str:
        """Run agent with a specific system prompt.

        Note: In a full implementation, this would inject the custom prompt
        into the agent harness. For now, we use a simplified approach.
        """
        from tests.harness.agent_harness import AgentTestHarness

        # Create harness with mock lesson
        harness = AgentTestHarness.create_with_mock_lesson(
            lesson_number=case["context"]["lesson_number"],
            agent_mode=case["mode"],
        )

        # Set exchange count if provided
        if "exchange_count" in case["context"]:
            harness.exchange_count = case["context"]["exchange_count"]

        # Add history if provided
        if "history" in case["context"]:
            harness.history = case["context"]["history"].copy()

        # TODO: Inject custom prompt into harness
        # For now, we use the default prompt
        response = await harness.send(case["user_input"])
        return response.text or ""

    def _judge_pair(
        self,
        case: dict,
        response_a: str,
        response_b: str,
    ) -> tuple[Winner, str]:
        """Have judge compare two responses.

        Returns:
            Tuple of (winner, reason)
        """
        prompt = self.COMPARISON_PROMPT.format(
            user_input=case["user_input"],
            context=case["context"],
            expected_behavior=case.get("expected_behavior", "Respond appropriately"),
            response_a=response_a or "(empty response)",
            response_b=response_b or "(empty response)",
        )

        response = self.judge.judge(prompt)
        return self._parse_winner(response)

    def _parse_winner(self, response: str) -> tuple[Winner, str]:
        """Parse winner and reason from judge response.

        Returns:
            Tuple of (winner, reason)
        """
        response = response.strip()

        if response.upper().startswith("A:"):
            return Winner.A, response[2:].strip()
        elif response.upper().startswith("B:"):
            return Winner.B, response[2:].strip()
        elif response.upper().startswith("TIE:"):
            return Winner.TIE, response[4:].strip()
        else:
            logger.warning(f"Unclear comparison verdict: {response[:50]}...")
            return Winner.TIE, "Unclear response"


async def compare_prompts(
    prompt_a: str,
    prompt_b: str,
    test_cases: list[dict],
) -> ComparisonResults:
    """Convenience function for quick A/B comparison.

    Args:
        prompt_a: Path to first prompt
        prompt_b: Path to second prompt
        test_cases: Test cases to compare on

    Returns:
        ComparisonResults
    """
    comparator = ABComparison()
    return await comparator.compare(prompt_a, prompt_b, test_cases)
