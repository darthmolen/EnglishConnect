"""Sanity tests for conversation partner agent.

Basic functionality tests for the free-form conversation partner.

These tests make REAL Azure OpenAI calls and cost money.
Run with: pytest -m "agent_integration and agent_sanity" -v
"""

import pytest


@pytest.mark.agent_sanity
class TestConversationPartnerSanity:
    """Sanity tests for conversation partner agent."""

    @pytest.mark.asyncio
    async def test_initial_greeting(self, partner_harness):
        """Partner should respond to initial greeting."""
        harness = partner_harness()

        response = await harness.send("Hello!")

        assert response.text, "Partner should respond"
        assert len(response.text) > 5, "Response should be substantive"

    @pytest.mark.asyncio
    async def test_speak_tool_called(self, partner_harness):
        """Partner should call speak() for responses."""
        harness = partner_harness()

        response = await harness.send("Hi there!")

        tool_names = [tc["name"] for tc in response.tool_calls]
        assert "speak" in tool_names, "Partner should call speak()"

    @pytest.mark.asyncio
    async def test_handles_conversation_topic(self, partner_harness):
        """Partner should engage with conversation topics."""
        harness = partner_harness()

        await harness.send("Hello!")
        response = await harness.send("I like to exercise every day.")

        assert response.text, "Should respond to topic"

    @pytest.mark.asyncio
    async def test_handles_questions(self, partner_harness):
        """Partner should respond to questions."""
        harness = partner_harness()

        await harness.send("Hello!")
        response = await harness.send("What do you like to do?")

        assert response.text, "Should answer questions"
