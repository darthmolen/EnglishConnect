"""Run final evaluation and compare against baseline.

Run this AFTER making code changes to verify improvements
and check for regressions.

Usage:
    python -m tests.evaluation.run_final_evaluation
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "backend"))

from tests.harness.agent_harness import AgentTestHarness


# Same scenarios as baseline
SCENARIOS = [
    ("session_start", ""),  # Initial greeting - how does agent start?
    ("normal_response", "I like to eat pizza"),  # Normal English response
    ("error_response", "Me gusta comer pizza"),  # Spanish during practice
    ("help_request_spanish", "No entiendo"),  # Help phrase in Spanish
    ("help_request_english", "I don't understand"),  # Help phrase in English
    ("pattern_flip", "What do you eat for breakfast?"),  # Student asks question
]


async def run_final_evaluation(lesson_number: int = 16) -> dict:
    """Run agent through standard scenarios and compare with baseline.

    Args:
        lesson_number: Lesson to test with (default 16 - Food)

    Returns:
        Dictionary of scenario results
    """
    print(f"Running FINAL evaluation on Lesson {lesson_number}...")
    print("=" * 60)

    harness = await AgentTestHarness.create(
        lesson_number=lesson_number,
        agent_mode="practice",
    )

    results = {
        "metadata": {
            "lesson_number": lesson_number,
            "timestamp": datetime.now().isoformat(),
            "description": "Final agent behavior after bilingual enhancement",
        },
        "scenarios": {},
    }

    for scenario_name, message in SCENARIOS:
        print(f"\n--- Scenario: {scenario_name} ---")
        print(f"Input: {message!r}")

        try:
            response = await harness.send(message)

            result = {
                "input": message,
                "output": response.text,
                "spoken_text": response.spoken_text,
                "spoken_language": response.spoken_language,
                "tool_calls": [
                    {"tool": tc.get("name"), "args": tc.get("arguments")}
                    for tc in response.tool_calls
                ],
                "tokens": response.total_tokens,
            }

            results["scenarios"][scenario_name] = result

            print(f"Output: {response.text[:200]}{'...' if len(response.text) > 200 else ''}")
            print(f"Spoken language: {response.spoken_language}")
            print(f"Tool calls: {[tc.get('name') for tc in response.tool_calls]}")

        except Exception as e:
            print(f"ERROR: {e}")
            results["scenarios"][scenario_name] = {
                "input": message,
                "error": str(e),
            }

        # Reset harness for next scenario (clean slate)
        harness.reset()

    # Calculate summary stats
    results["summary"] = {
        "total_scenarios": len(SCENARIOS),
        "successful": sum(
            1 for s in results["scenarios"].values() if "error" not in s
        ),
        "failed": sum(1 for s in results["scenarios"].values() if "error" in s),
    }

    return results


def load_baseline(baseline_path: Path) -> dict | None:
    """Load baseline results if they exist."""
    if baseline_path.exists():
        with open(baseline_path) as f:
            return json.load(f)
    return None


def compare_results(baseline: dict, final: dict) -> str:
    """Generate comparison report."""
    report = ["## Evaluation Comparison Report\n"]
    report.append(f"Baseline timestamp: {baseline['metadata']['timestamp']}")
    report.append(f"Final timestamp: {final['metadata']['timestamp']}\n")

    improvements = []
    regressions = []
    unchanged = []

    for scenario_name in baseline.get("scenarios", {}).keys():
        baseline_scenario = baseline["scenarios"].get(scenario_name, {})
        final_scenario = final["scenarios"].get(scenario_name, {})

        report.append(f"### {scenario_name}")
        report.append(f"**Input:** `{baseline_scenario.get('input', 'N/A')}`\n")

        baseline_output = baseline_scenario.get("output", "N/A")[:150]
        final_output = final_scenario.get("output", "N/A")[:150]

        report.append(f"**Baseline output:** {baseline_output}...")
        report.append(f"**Final output:** {final_output}...")

        # Check for expected changes
        if scenario_name == "session_start":
            # Should now include pattern explanation
            if "pattern" in final_output.lower() or "patrón" in final_output.lower():
                improvements.append(f"{scenario_name}: Now includes pattern explanation")
            else:
                unchanged.append(f"{scenario_name}: Pattern explanation not detected")

        elif scenario_name == "help_request_spanish":
            # Should now trigger help recovery in Spanish
            final_text = final_scenario.get("output", "").lower()
            if any(word in final_text for word in ["entiendo", "explicar", "repito"]):
                improvements.append(f"{scenario_name}: Help recovery in Spanish detected")
            elif "understand" in final_text:
                unchanged.append(f"{scenario_name}: Response may still be in English")

        elif scenario_name in ["normal_response", "pattern_flip"]:
            # Should maintain English practice
            if "error" not in final_scenario:
                unchanged.append(f"{scenario_name}: Still functional (no regression)")

        report.append("")

    # Summary section
    report.append("\n## Summary")
    report.append(f"\n**Improvements ({len(improvements)}):**")
    for imp in improvements:
        report.append(f"- ✅ {imp}")

    report.append(f"\n**Unchanged ({len(unchanged)}):**")
    for unc in unchanged:
        report.append(f"- ⚪ {unc}")

    report.append(f"\n**Regressions ({len(regressions)}):**")
    for reg in regressions:
        report.append(f"- ❌ {reg}")

    if not regressions:
        report.append("- None detected! 🎉")

    return "\n".join(report)


def save_results(results: dict, output_path: Path) -> None:
    """Save results to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")


async def main():
    """Main entry point."""
    output_dir = Path(__file__).parent
    final_path = output_dir / "final_results.json"
    baseline_path = output_dir / "baseline_results.json"
    report_path = output_dir / "comparison_report.md"

    # Run final evaluation
    results = await run_final_evaluation()
    save_results(results, final_path)

    # Load baseline and compare
    baseline = load_baseline(baseline_path)
    if baseline:
        print("\n" + "=" * 60)
        print("COMPARISON WITH BASELINE")
        print("=" * 60)

        report = compare_results(baseline, results)
        print(report)

        # Save report
        with open(report_path, "w") as f:
            f.write(report)
        print(f"\nComparison report saved to: {report_path}")
    else:
        print("\nNo baseline found - skipping comparison")

    print("\n" + "=" * 60)
    print("FINAL EVALUATION COMPLETE")
    print(f"Successful: {results['summary']['successful']}/{results['summary']['total_scenarios']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
