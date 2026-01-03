"""Evaluation runner - executes golden dataset against agent and judges results.

The runner:
1. Loads test cases from golden dataset
2. Runs each case through the agent harness
3. Judges results using local Qwen 2.5-7B
4. Aggregates pass/fail metrics

Usage:
    from tests.evaluation.runner import EvaluationRunner

    runner = EvaluationRunner()
    results = await runner.run_evaluation(dimension=Dimension.LANGUAGE_CHOICE)
    print(results.summary)
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Literal

from tests.evaluation.rubrics import Dimension, RUBRICS, get_rubrics_for_mode
from tests.evaluation.judge import JudgeLLM

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a single test case evaluation."""

    test_id: str
    dimension: Dimension
    passed: Optional[bool]  # None = N/A (skipped)
    judge_response: str
    agent_response: str
    tool_calls: list[dict]
    latency_ms: float
    expected_pass: bool = True

    @property
    def status(self) -> str:
        """Get status string."""
        if self.passed is None:
            return "N/A"
        return "PASS" if self.passed else "FAIL"


@dataclass
class EvaluationResults:
    """Aggregated results from an evaluation run."""

    dimension: Optional[Dimension]
    mode: Optional[str]
    total_tests: int
    passed: int
    failed: int
    skipped: int  # N/A responses
    results: list[TestResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Pass rate excluding skipped tests."""
        evaluated = self.passed + self.failed
        if evaluated == 0:
            return 0.0
        return self.passed / evaluated

    @property
    def summary(self) -> str:
        """One-line summary."""
        dim_name = self.dimension.value if self.dimension else "all"
        mode_str = f" ({self.mode})" if self.mode else ""
        return f"{dim_name}{mode_str}: {self.passed}/{self.passed + self.failed} ({self.pass_rate:.1%})"


class EvaluationRunner:
    """Run golden dataset evaluations against the agent."""

    def __init__(
        self,
        golden_dir: Optional[Path] = None,
        judge: Optional[JudgeLLM] = None,
    ):
        """Initialize runner.

        Args:
            golden_dir: Path to golden dataset directory
            judge: JudgeLLM instance (created if not provided)
        """
        self.golden_dir = golden_dir or Path(__file__).parent.parent / "golden"
        self._judge = judge

    @property
    def judge(self) -> JudgeLLM:
        """Lazy-load judge to allow running without vLLM available."""
        if self._judge is None:
            self._judge = JudgeLLM()
        return self._judge

    def load_test_cases(
        self,
        dimension: Optional[Dimension] = None,
        mode: Optional[Literal["help", "practice"]] = None,
    ) -> list[dict]:
        """Load test cases from golden dataset.

        Args:
            dimension: Filter to specific dimension
            mode: Filter to specific mode

        Returns:
            List of test case dictionaries
        """
        cases = []

        # Scan mode directories
        for mode_dir in self.golden_dir.iterdir():
            if not mode_dir.is_dir():
                continue

            # Filter by mode
            dir_mode = mode_dir.name.replace("_mode", "")
            if mode and dir_mode != mode:
                continue

            # Load all JSON files in directory
            for json_file in mode_dir.glob("*.json"):
                try:
                    with open(json_file) as f:
                        file_cases = json.load(f)

                    # Add mode to each case
                    for case in file_cases:
                        case["mode"] = dir_mode

                    # Filter by dimension
                    if dimension:
                        file_cases = [
                            c for c in file_cases
                            if c.get("dimension") == dimension.value
                        ]

                    cases.extend(file_cases)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in {json_file}: {e}")
                except Exception as e:
                    logger.error(f"Error loading {json_file}: {e}")

        logger.info(f"Loaded {len(cases)} test cases")
        return cases

    async def run_single_test(
        self,
        test_case: dict,
        use_mock_lesson: bool = True,
    ) -> TestResult:
        """Run a single test case through agent and judge.

        Args:
            test_case: Test case dictionary from golden dataset
            use_mock_lesson: Use mock lesson data (no database needed)

        Returns:
            TestResult with pass/fail and details
        """
        # Import harness here to avoid circular imports
        from tests.harness.agent_harness import AgentTestHarness

        start_time = time.time()

        try:
            # Create harness with test context
            lesson_number = test_case["context"]["lesson_number"]
            mode = test_case["mode"]

            # Build vocabulary from context if provided
            vocabulary = None
            if "vocabulary" in test_case["context"]:
                from app.schemas.lesson import VocabularyItemSchema
                vocabulary = [
                    VocabularyItemSchema(
                        english=v["english"],
                        spanish=v["spanish"],
                        category="test",
                    )
                    for v in test_case["context"]["vocabulary"]
                ]

            if use_mock_lesson:
                harness = AgentTestHarness.create_with_mock_lesson(
                    lesson_number=lesson_number,
                    agent_mode=mode,
                    vocabulary=vocabulary,
                )
            else:
                harness = await AgentTestHarness.create(
                    lesson_number=lesson_number,
                    agent_mode=mode,
                )

            # Set exchange count if provided
            if "exchange_count" in test_case["context"]:
                harness.exchange_count = test_case["context"]["exchange_count"]

            # Add history if provided
            if "history" in test_case["context"]:
                harness.history = test_case["context"]["history"].copy()

            # Run agent
            response = await harness.send(test_case["user_input"])
            latency_ms = (time.time() - start_time) * 1000

            # Get rubric and build judge prompt
            dimension = Dimension(test_case["dimension"])
            rubric = RUBRICS[dimension]

            # Build context for judge
            context = {
                "mode": mode,
                "lesson_number": lesson_number,
                "vocabulary": self._format_vocab(
                    test_case["context"].get("vocabulary", [])
                ),
            }

            # Format tool calls for judge
            tool_calls = response.tool_calls or []

            judge_prompt = rubric.build_prompt(
                user_input=test_case["user_input"],
                context=context,
                agent_response=response.text or "",
                tool_calls=tool_calls,
            )

            # Get judge verdict
            judge_response = self.judge.judge(judge_prompt)
            passed = self._parse_verdict(judge_response)

            return TestResult(
                test_id=test_case["id"],
                dimension=dimension,
                passed=passed,
                judge_response=judge_response,
                agent_response=response.text or "",
                tool_calls=tool_calls,
                latency_ms=latency_ms,
                expected_pass=test_case.get("expected_pass", True),
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Test {test_case['id']} failed with error: {e}")

            return TestResult(
                test_id=test_case["id"],
                dimension=Dimension(test_case["dimension"]),
                passed=False,
                judge_response=f"ERROR: {str(e)}",
                agent_response="",
                tool_calls=[],
                latency_ms=latency_ms,
                expected_pass=test_case.get("expected_pass", True),
            )

    async def run_evaluation(
        self,
        dimension: Optional[Dimension] = None,
        mode: Optional[Literal["help", "practice"]] = None,
        use_mock_lesson: bool = True,
    ) -> EvaluationResults:
        """Run full evaluation on golden dataset.

        Args:
            dimension: Filter to specific dimension (None = all)
            mode: Filter to specific mode (None = all)
            use_mock_lesson: Use mock lesson data

        Returns:
            EvaluationResults with aggregated metrics
        """
        test_cases = self.load_test_cases(dimension, mode)

        if not test_cases:
            logger.warning("No test cases found")
            return EvaluationResults(
                dimension=dimension,
                mode=mode,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
            )

        results = []
        for i, case in enumerate(test_cases, 1):
            logger.info(f"Running test {i}/{len(test_cases)}: {case['id']}")
            result = await self.run_single_test(case, use_mock_lesson)
            results.append(result)

            # Log result immediately
            logger.info(f"  {result.status}: {result.judge_response[:60]}...")

        # Aggregate
        passed = sum(1 for r in results if r.passed is True)
        failed = sum(1 for r in results if r.passed is False)
        skipped = sum(1 for r in results if r.passed is None)

        return EvaluationResults(
            dimension=dimension,
            mode=mode,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            results=results,
        )

    def _parse_verdict(self, judge_response: str) -> Optional[bool]:
        """Parse PASS/FAIL/N/A from judge response.

        Args:
            judge_response: Raw judge output

        Returns:
            True=pass, False=fail, None=N/A
        """
        response_upper = judge_response.strip().upper()
        if response_upper.startswith("PASS"):
            return True
        elif response_upper.startswith("FAIL"):
            return False
        elif response_upper.startswith("N/A"):
            return None
        else:
            # Unclear verdict - log and treat as fail
            logger.warning(f"Unclear judge verdict: {judge_response[:50]}...")
            return False

    def _format_vocab(self, vocabulary: list) -> str:
        """Format vocabulary list for judge context."""
        if not vocabulary:
            return "None provided"
        items = [f"{v['english']} ({v['spanish']})" for v in vocabulary[:10]]
        return ", ".join(items)


async def run_quick_evaluation(
    dimension: Optional[Dimension] = None,
    mode: Optional[Literal["help", "practice"]] = None,
) -> EvaluationResults:
    """Convenience function for quick evaluation runs.

    Args:
        dimension: Filter to dimension
        mode: Filter to mode

    Returns:
        EvaluationResults
    """
    runner = EvaluationRunner()
    return await runner.run_evaluation(dimension=dimension, mode=mode)
