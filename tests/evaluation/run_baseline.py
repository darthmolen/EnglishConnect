"""Capture baseline agent behavior before bilingual enhancement.

Run this BEFORE making any code changes to establish a baseline
for detecting regressions.

Usage:
    python -m tests.evaluation.run_baseline
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "backend"))

from tests.harness.agent_harness import AgentTestHarness


# Test scenarios that capture key agent behaviors
SCENARIOS = [
    ("session_start", ""),  # Initial greeting - how does agent start?
    ("normal_response", "I like to eat pizza"),  # Normal English response
    ("error_response", "Me gusta comer pizza"),  # Spanish during practice
    ("help_request_spanish", "No entiendo"),  # Help phrase in Spanish
    ("help_request_english", "I don't understand"),  # Help phrase in English
    ("pattern_flip", "What do you eat for breakfast?"),  # Student asks question
]


async def run_baseline_evaluation(lesson_number: int = 16) -> dict:
    """Run agent through standard scenarios and save responses.

    Args:
        lesson_number: Lesson to test with (default 16 - Food)

    Returns:
        Dictionary of scenario results
    """
    print(f"Running baseline evaluation on Lesson {lesson_number}...")
    print("=" * 60)

    harness = await AgentTestHarness.create(
        lesson_number=lesson_number,
        agent_mode="practice",
    )

    results = {
        "metadata": {
            "lesson_number": lesson_number,
            "timestamp": datetime.now().isoformat(),
            "description": "Baseline agent behavior before bilingual enhancement",
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


def save_results(results: dict, output_path: Path) -> None:
    """Save results to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")


async def main():
    """Main entry point."""
    output_dir = Path(__file__).parent
    output_path = output_dir / "baseline_results.json"

    # Check if baseline already exists
    if output_path.exists():
        print(f"WARNING: Baseline already exists at {output_path}")
        response = input("Overwrite? [y/N]: ")
        if response.lower() != "y":
            print("Aborted.")
            return

    results = await run_baseline_evaluation()
    save_results(results, output_path)

    print("\n" + "=" * 60)
    print("BASELINE EVALUATION COMPLETE")
    print(f"Successful: {results['summary']['successful']}/{results['summary']['total_scenarios']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
