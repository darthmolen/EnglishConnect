#!/usr/bin/env python
"""Interactive CLI for agent testing and prompt engineering.

Usage:
    python -m tests.harness.cli --agent teacher --lesson 5

Commands during conversation:
    /phase      - Show current phase and state
    /tools      - Show last tool calls
    /history    - Show full conversation transcript
    /save       - Save transcript to file
    /reset      - Reset to initial state
    /prompt     - Show current system prompt
    /quit       - Exit the CLI
"""

import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from harness.agent_harness import AgentTestHarness


def print_header(harness: AgentTestHarness) -> None:
    """Print CLI header."""
    print("=" * 60)
    print(f" Agent Test Harness - {harness.agent_type.title()}")
    print(f" Lesson {harness.lesson.lesson_number}: {harness.lesson.title}")
    print("=" * 60)
    print()
    print("Commands: /phase /tools /history /save /reset /prompt /quit")
    print()


def print_response(response) -> None:
    """Print agent response with formatting."""
    print()
    print(f"\033[94m[Teacher]\033[0m {response.text}")

    # Show if speak was called
    if response.spoken_text:
        lang = response.spoken_language or "en"
        print(f"\033[90m  (spoke in {lang})\033[0m")


def print_status(harness: AgentTestHarness) -> None:
    """Print current status line."""
    phase = harness.phase.phase_type
    vocab_count = len(harness.lesson.vocabulary)
    pattern_count = len(harness.lesson.patterns)

    state_info = ""
    if phase == "vocabulary":
        idx = harness.phase_state.vocab_index + 1
        state_info = f" | Vocab: {idx}/{vocab_count}"
    elif phase == "patterns":
        idx = harness.phase_state.pattern_index + 1
        state_info = f" | Pattern: {idx}/{pattern_count}"

    print()
    print(f"\033[90m─── Phase: {phase}{state_info} ───\033[0m")


def handle_command(cmd: str, harness: AgentTestHarness) -> bool:
    """Handle slash commands. Returns True to continue, False to quit."""
    if cmd == "/quit" or cmd == "/exit":
        return False

    elif cmd == "/phase":
        print(f"\nCurrent phase: {harness.phase.phase_type}")
        print(f"Phase state: vocab_index={harness.phase_state.vocab_index}, "
              f"pattern_index={harness.phase_state.pattern_index}")
        print(f"Items completed: {harness.phase_state.items_completed}")
        print(f"Phase history: {' -> '.join(harness.phase_history)}")

    elif cmd == "/tools":
        print("\nLast 5 tool calls:")
        for tc in harness.all_tool_calls[-5:]:
            print(f"  - {tc['name']}: {tc.get('arguments', {})}")

    elif cmd == "/history":
        print("\n" + harness.get_transcript())

    elif cmd == "/save":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcript_L{harness.lesson.lesson_number}_{timestamp}.txt"
        Path(filename).write_text(harness.get_transcript())
        print(f"\nSaved to {filename}")

    elif cmd == "/reset":
        harness.reset()
        print("\nHarness reset to initial state.")

    elif cmd == "/prompt":
        print("\n" + "=" * 40)
        print("CURRENT SYSTEM PROMPT")
        print("=" * 40)
        prompt = harness._build_system_prompt()
        print(prompt)
        print("=" * 40)

    elif cmd.startswith("/"):
        print(f"\nUnknown command: {cmd}")
        print("Available: /phase /tools /history /save /reset /prompt /quit")

    else:
        # Not a command
        return True

    return True


async def run_cli(harness: AgentTestHarness) -> None:
    """Run the interactive CLI loop."""
    print_header(harness)

    # Get initial greeting
    print("\033[93mStarting conversation...\033[0m")
    try:
        response = await harness.send("")
        print_response(response)
        print_status(harness)
    except Exception as e:
        print(f"\033[91mError getting initial response: {e}\033[0m")
        return

    while True:
        try:
            user_input = input("\n\033[92m[You]\033[0m > ").strip()

            if not user_input:
                continue

            # Check for commands
            if user_input.startswith("/"):
                should_continue = handle_command(user_input, harness)
                if not should_continue:
                    print("\nGoodbye!")
                    break
                continue

            # Send message to agent
            print("\033[93mThinking...\033[0m", end="\r")
            response = await harness.send(user_input)
            print(" " * 20, end="\r")  # Clear "Thinking..."

            print_response(response)
            print_status(harness)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except EOFError:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n\033[91mError: {e}\033[0m")


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive CLI for agent testing and prompt engineering"
    )
    parser.add_argument(
        "--agent",
        choices=["teacher", "partner"],
        default="teacher",
        help="Agent type to test (default: teacher)"
    )
    parser.add_argument(
        "--lesson",
        type=int,
        default=5,
        help="Lesson number to use (default: 5)"
    )
    parser.add_argument(
        "--db",
        action="store_true",
        help="Load lesson from database instead of mock data"
    )

    args = parser.parse_args()

    # Create harness
    if args.db:
        print(f"Loading lesson {args.lesson} from database...")
        harness = await AgentTestHarness.create(
            lesson_number=args.lesson,
            agent_type=args.agent,
        )
    else:
        print(f"Using mock lesson {args.lesson}...")
        harness = AgentTestHarness.create_with_mock_lesson(
            lesson_number=args.lesson,
            agent_type=args.agent,
        )

    await run_cli(harness)


if __name__ == "__main__":
    asyncio.run(main())
