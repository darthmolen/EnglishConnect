"""CLI for running agent evaluations.

Usage:
    # Run all dimensions
    python -m tests.evaluation.cli --dimension all

    # Run specific dimension
    python -m tests.evaluation.cli --dimension language_choice

    # Run with verbose output
    python -m tests.evaluation.cli --dimension tool_usage --verbose

    # Filter by mode
    python -m tests.evaluation.cli --dimension all --mode practice

    # Output to JSON
    python -m tests.evaluation.cli --dimension all --output results.json

    # Check if judge LLM is available
    python -m tests.evaluation.cli --check

    # List available test cases
    python -m tests.evaluation.cli --list
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "backend"))

from tests.evaluation.rubrics import Dimension
from tests.evaluation.runner import EvaluationRunner
from tests.evaluation.report import (
    format_report,
    format_verbose_report,
    format_failures_only,
    format_json_export,
    format_multi_dimension_summary,
)


def setup_logging(verbose: bool = False):
    """Configure logging for CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def check_judge_available() -> bool:
    """Check if judge LLM is available."""
    try:
        from tests.evaluation.judge import JudgeLLM
        judge = JudgeLLM()
        if judge.is_available():
            print(f" Judge LLM available at {judge.base_url}")
            print(f"  Model: {judge.model}")
            return True
        else:
            print(f" Judge LLM not available at {judge.base_url}")
            return False
    except Exception as e:
        print(f" Judge LLM error: {e}")
        return False


def list_test_cases(runner: EvaluationRunner):
    """List all available test cases."""
    cases = runner.load_test_cases()

    print(f"\n=== {len(cases)} Test Cases ===\n")

    # Group by dimension
    by_dimension: dict[str, list] = {}
    for case in cases:
        dim = case.get("dimension", "unknown")
        if dim not in by_dimension:
            by_dimension[dim] = []
        by_dimension[dim].append(case)

    for dim, dim_cases in sorted(by_dimension.items()):
        print(f"\n{dim} ({len(dim_cases)} cases):")
        for case in dim_cases:
            mode = case.get("mode", "?")
            source = case.get("source", "?")
            print(f"  [{mode}] {case['id']} ({source})")


async def run_evaluation(args):
    """Run evaluation based on CLI arguments."""
    runner = EvaluationRunner()

    # Handle --list
    if args.list:
        list_test_cases(runner)
        return 0

    # Handle --check
    if args.check:
        return 0 if check_judge_available() else 1

    # Verify judge is available before running
    if not check_judge_available():
        print("\nCannot run evaluation without judge LLM.")
        print("Start vLLM: cd src/services/vllm && ./start.sh")
        return 1

    # Determine dimensions to evaluate
    if args.dimension == "all":
        dimensions = list(Dimension)
    else:
        dimensions = [Dimension(args.dimension)]

    # Run evaluations
    all_results = {}

    for dim in dimensions:
        print(f"\n=== Evaluating: {dim.value} ===\n")

        results = await runner.run_evaluation(
            dimension=dim,
            mode=args.mode,
            use_mock_lesson=not args.real_db,
        )

        all_results[dim.value] = results

        # Print results
        if args.verbose:
            print(format_verbose_report(results))
        elif args.failures:
            print(format_failures_only(results))
        else:
            print(format_report(results))

    # Print overall summary if multiple dimensions
    if len(dimensions) > 1:
        print("\n" + format_multi_dimension_summary(all_results))

    # Calculate overall pass rate
    total_passed = sum(r.passed for r in all_results.values())
    total_failed = sum(r.failed for r in all_results.values())
    total = total_passed + total_failed
    overall_rate = total_passed / total if total > 0 else 0

    print(f"\n Overall: {total_passed}/{total} ({overall_rate:.1%})")

    # Save to JSON if requested
    if args.output:
        output_data = {
            "overall_pass_rate": overall_rate,
            "dimensions": {
                dim: format_json_export(results)
                for dim, results in all_results.items()
            },
        }
        Path(args.output).write_text(json.dumps(output_data, indent=2))
        print(f"\nResults saved to {args.output}")

    # Return exit code based on pass rate
    if args.threshold:
        if overall_rate < args.threshold:
            print(f"\n FAILED: Pass rate {overall_rate:.1%} < threshold {args.threshold:.1%}")
            return 1
        else:
            print(f"\n PASSED: Pass rate {overall_rate:.1%} >= threshold {args.threshold:.1%}")
            return 0

    return 0 if overall_rate >= 0.8 else 1


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run LLM-as-Judge evaluations on teaching agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tests.evaluation.cli --dimension all
  python -m tests.evaluation.cli --dimension language_choice --verbose
  python -m tests.evaluation.cli --dimension tool_usage --mode practice
  python -m tests.evaluation.cli --check
  python -m tests.evaluation.cli --list
        """,
    )

    parser.add_argument(
        "--dimension", "-d",
        type=str,
        choices=["all"] + [d.value for d in Dimension],
        default="all",
        help="Dimension to evaluate (default: all)",
    )

    parser.add_argument(
        "--mode", "-m",
        type=str,
        choices=["help", "practice"],
        help="Filter to specific agent mode",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed results for each test case",
    )

    parser.add_argument(
        "--failures", "-f",
        action="store_true",
        help="Show only failed test cases",
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output results to JSON file",
    )

    parser.add_argument(
        "--threshold", "-t",
        type=float,
        help="Pass rate threshold (0-1). Exit 1 if below.",
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if judge LLM is available",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available test cases",
    )

    parser.add_argument(
        "--real-db",
        action="store_true",
        help="Use real database for lessons (default: mock data)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    setup_logging(args.debug)

    try:
        exit_code = asyncio.run(run_evaluation(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
