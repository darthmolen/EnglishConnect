"""Report formatting for evaluation results.

Provides:
- Summary format (one-liner per dimension)
- Verbose format (details for each test case)
- Iteration summary (baseline vs final comparison)
- JSON export format
"""

from typing import Optional
from tests.evaluation.runner import EvaluationResults, TestResult
from tests.evaluation.rubrics import Dimension


def format_summary(results: EvaluationResults) -> str:
    """Format one-line summary.

    Example:
        language_choice (practice): 3/4 (75.0%)
    """
    return results.summary


def format_report(results: EvaluationResults) -> str:
    """Format multi-line summary report.

    Example:
        Dimension: language_choice
        Mode: practice
        Pass Rate: 75.0% (3/4)
          Passed: 3
          Failed: 1
          Skipped (N/A): 0
    """
    lines = [
        f"Dimension: {results.dimension.value if results.dimension else 'all'}",
    ]

    if results.mode:
        lines.append(f"Mode: {results.mode}")

    evaluated = results.passed + results.failed
    lines.extend([
        f"Pass Rate: {results.pass_rate:.1%} ({results.passed}/{evaluated})",
        f"  Passed: {results.passed}",
        f"  Failed: {results.failed}",
        f"  Skipped (N/A): {results.skipped}",
    ])

    return "\n".join(lines)


def format_verbose_report(results: EvaluationResults) -> str:
    """Format detailed report with each test case.

    Example:
        Dimension: language_choice
        Pass Rate: 75.0% (3/4)

        --- Test Cases ---

        [PASS] lc-practice-001
          Judge: Agent correctly started in English...
          Latency: 1234ms

        [FAIL] lc-practice-002
          Judge: Agent started in Spanish instead of English...
          Agent: ¡Genial! Vamos a practicar...
          Latency: 987ms
    """
    lines = [format_report(results), "", "--- Test Cases ---", ""]

    for result in results.results:
        status = result.status
        lines.append(f"[{status}] {result.test_id}")
        lines.append(f"  Judge: {result.judge_response[:80]}...")

        # Show agent response for failures
        if result.passed is False:
            agent_text = result.agent_response[:80] if result.agent_response else "(empty)"
            lines.append(f"  Agent: {agent_text}...")

            # Show tool calls
            if result.tool_calls:
                tools = [tc.get("tool", tc.get("name", "?")) for tc in result.tool_calls]
                lines.append(f"  Tools: {', '.join(tools)}")
            else:
                lines.append("  Tools: None")

        lines.append(f"  Latency: {result.latency_ms:.0f}ms")
        lines.append("")

    return "\n".join(lines)


def format_failures_only(results: EvaluationResults) -> str:
    """Format only failed test cases for quick debugging."""
    failures = [r for r in results.results if r.passed is False]

    if not failures:
        return "No failures!"

    lines = [
        f"=== {len(failures)} Failures ===",
        "",
    ]

    for result in failures:
        lines.append(f"[FAIL] {result.test_id} ({result.dimension.value})")
        lines.append(f"  Judge: {result.judge_response}")
        lines.append(f"  Agent: {result.agent_response[:100]}..." if result.agent_response else "  Agent: (empty)")
        lines.append("")

    return "\n".join(lines)


def format_iteration_summary(
    baseline: dict[str, dict],
    final: dict[str, dict],
    iterations: int,
    commits: list[str],
) -> str:
    """Format summary after iteration loop completes.

    Args:
        baseline: Dict of dimension -> {passed, failed, total, pass_rate}
        final: Same structure as baseline
        iterations: Number of iterations completed
        commits: List of commit messages made

    Returns:
        Markdown-formatted summary
    """
    # Calculate overall rates
    def overall_rate(data: dict) -> float:
        total_passed = sum(d["passed"] for d in data.values())
        total_tests = sum(d["passed"] + d["failed"] for d in data.values())
        return total_passed / total_tests if total_tests > 0 else 0

    baseline_overall = overall_rate(baseline)
    final_overall = overall_rate(final)

    lines = [
        "## Evaluation Summary",
        "",
        f"**Baseline**: {baseline_overall:.0%} overall",
        f"**Final**: {final_overall:.0%} overall",
        f"**Iterations**: {iterations}",
        "",
        "### Dimension Results",
        "",
        "| Dimension | Baseline | Final | Change |",
        "|-----------|----------|-------|--------|",
    ]

    for dim in baseline.keys():
        b_rate = baseline[dim]["pass_rate"]
        f_rate = final.get(dim, baseline[dim])["pass_rate"]
        change = f_rate - b_rate
        sign = "+" if change >= 0 else ""
        emoji = "" if change > 0 else ("" if change < 0 else "")
        lines.append(f"| {dim} | {b_rate:.0%} | {f_rate:.0%} | {sign}{change:.0%} {emoji} |")

    lines.extend([
        "",
        "### Commits Made",
        "",
    ])

    if commits:
        for commit in commits:
            lines.append(f"- `{commit}`")
    else:
        lines.append("- (no commits)")

    return "\n".join(lines)


def format_json_export(results: EvaluationResults) -> dict:
    """Format results for JSON export.

    Returns:
        Dictionary ready for json.dumps()
    """
    return {
        "dimension": results.dimension.value if results.dimension else "all",
        "mode": results.mode,
        "summary": {
            "total": results.total_tests,
            "passed": results.passed,
            "failed": results.failed,
            "skipped": results.skipped,
            "pass_rate": results.pass_rate,
        },
        "results": [
            {
                "id": r.test_id,
                "dimension": r.dimension.value,
                "status": r.status,
                "passed": r.passed,
                "judge_response": r.judge_response,
                "agent_response": r.agent_response[:200] if r.agent_response else None,
                "tool_calls": r.tool_calls,
                "latency_ms": r.latency_ms,
            }
            for r in results.results
        ],
    }


def format_multi_dimension_summary(
    results_by_dimension: dict[str, EvaluationResults]
) -> str:
    """Format summary across multiple dimensions.

    Args:
        results_by_dimension: Dict of dimension_name -> EvaluationResults

    Returns:
        Formatted table
    """
    lines = [
        "=== Evaluation Summary ===",
        "",
        "| Dimension | Passed | Failed | Skip | Rate |",
        "|-----------|--------|--------|------|------|",
    ]

    total_passed = 0
    total_failed = 0
    total_skipped = 0

    for dim_name, results in results_by_dimension.items():
        lines.append(
            f"| {dim_name} | {results.passed} | {results.failed} | "
            f"{results.skipped} | {results.pass_rate:.0%} |"
        )
        total_passed += results.passed
        total_failed += results.failed
        total_skipped += results.skipped

    total = total_passed + total_failed
    overall_rate = total_passed / total if total > 0 else 0

    lines.extend([
        "|-----------|--------|--------|------|------|",
        f"| **Total** | {total_passed} | {total_failed} | {total_skipped} | **{overall_rate:.0%}** |",
    ])

    return "\n".join(lines)
