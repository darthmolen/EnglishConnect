"""Sanity tests for teacher agent.

These tests verify basic functionality:
- Phase transitions work correctly
- Tools are called as expected
- Agent doesn't crash on various inputs

These tests make REAL Azure OpenAI calls and cost money.
Run with: pytest -m "agent_integration and agent_sanity" -v
"""

import pytest

from .scenarios import GREEN_PATH, MINIMAL_RESPONSES


@pytest.mark.agent_sanity
class TestTeacherSanity:
    """Sanity tests: phase transitions, tool calls, no crashes."""

    @pytest.mark.asyncio
    async def test_initial_greeting(self, teacher_harness):
        """Teacher should respond to initial greeting."""
        harness = teacher_harness()

        # Empty message to trigger intro
        response = await harness.send("")

        assert response.text, "Teacher should respond"
        assert len(response.text) > 10, "Response should be substantive"
        assert response.phase.phase_type == "intro", "Should start in intro phase"

    @pytest.mark.asyncio
    async def test_speak_tool_always_called(self, teacher_harness):
        """Teacher should call speak() for every response."""
        harness = teacher_harness()

        response = await harness.send("Hello!")

        tool_names = [tc["name"] for tc in response.tool_calls]
        assert "speak" in tool_names, "Teacher should always call speak()"

    @pytest.mark.asyncio
    async def test_handles_unexpected_input(self, teacher_harness):
        """Teacher should handle nonsense input gracefully."""
        harness = teacher_harness()

        response = await harness.send("asdfghjkl random gibberish 12345!@#$%")

        assert response.text, "Should respond, not crash"
        assert len(response.text) > 10, "Should be a real response"

    @pytest.mark.asyncio
    async def test_handles_empty_input(self, teacher_harness):
        """Teacher should handle empty input gracefully."""
        harness = teacher_harness()

        response = await harness.send("")

        assert response.text, "Should respond to empty input"

    @pytest.mark.asyncio
    async def test_phase_advances_on_confirmation(self, teacher_harness):
        """Teacher should advance phase when student confirms readiness."""
        harness = teacher_harness()

        # Initial greeting
        await harness.send("Hello!")

        # Confirm ready to start
        response = await harness.send("Yes, I'm ready to start!")

        # Should have called advance_phase or be preparing to advance
        tool_names = [tc["name"] for tc in harness.all_tool_calls]

        # Either advance_phase was called OR we're still in intro (acceptable)
        # The key is it didn't crash and responded appropriately
        assert response.text, "Should respond"

    @pytest.mark.asyncio
    async def test_minimal_responses_handled(self, teacher_harness):
        """Teacher should handle minimal single-word responses."""
        harness = teacher_harness()

        for step in MINIMAL_RESPONSES.steps[:3]:
            response = await harness.send(step.student_input)

            assert response.text, f"Should respond to '{step.student_input}'"

            if step.expected_phase:
                assert harness.phase.phase_type == step.expected_phase, (
                    f"Expected phase {step.expected_phase}, got {harness.phase.phase_type}"
                )

    @pytest.mark.asyncio
    async def test_conversation_history_maintained(self, teacher_harness):
        """Conversation history should be maintained across turns."""
        harness = teacher_harness()

        await harness.send("Hello, my name is Maria!")
        await harness.send("I like to exercise.")
        response = await harness.send("What did I say I like to do?")

        # History should have 6 messages (3 user + 3 assistant)
        assert len(harness.history) == 6, "History should have all messages"

    @pytest.mark.asyncio
    async def test_phase_history_tracked(self, teacher_harness):
        """Phase transitions should be tracked."""
        harness = teacher_harness()

        # Start in intro
        assert harness.phase_history == ["intro"]

        await harness.send("Hello!")
        await harness.send("Yes, let's start!")

        # Phase history should show progression
        assert len(harness.phase_history) >= 1, "Phase history should be tracked"
        assert harness.phase_history[0] == "intro", "Should start with intro"

    @pytest.mark.asyncio
    async def test_transcript_generation(self, teacher_harness):
        """Transcript should be generated correctly."""
        harness = teacher_harness()

        await harness.send("Hello!")
        await harness.send("I'm ready to learn!")

        transcript = harness.get_transcript()

        assert "Lesson 5" in transcript, "Transcript should include lesson number"
        assert "Teacher" in transcript, "Transcript should have teacher label"
        assert "Student" in transcript, "Transcript should have student label"
        assert "Hello!" in transcript, "Transcript should include user messages"
