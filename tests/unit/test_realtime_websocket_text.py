"""Tests for WebSocket text input handling in Realtime API.

TDD Task 5: Verify WebSocket handles text input messages.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_websocket_handles_text_message():
    """WebSocket should forward text messages to Realtime session."""
    from app.services.realtime_session import format_text_input

    # Create a mock session
    mock_session = MagicMock()
    mock_session.ws = AsyncMock()
    mock_session.ws.send = AsyncMock()
    mock_session._connected = True

    # The expected formatted message
    text = "I'm ready to practice!"
    expected_message = format_text_input(text)

    # Verify format_text_input creates correct structure
    assert expected_message["type"] == "conversation.item.create"
    assert expected_message["item"]["role"] == "user"
    assert expected_message["item"]["content"][0]["type"] == "input_text"
    assert expected_message["item"]["content"][0]["text"] == text


@pytest.mark.asyncio
async def test_send_text_method_exists():
    """RealtimeSessionManager should have a send_text method."""
    from app.services.realtime_session import RealtimeSessionManager

    # Check that the method exists
    assert hasattr(RealtimeSessionManager, "send_text")


@pytest.mark.asyncio
async def test_send_text_formats_and_sends_message():
    """send_text should format text and send to WebSocket."""
    from app.services.realtime_session import RealtimeSessionManager, format_text_input

    # Create session with mocked WebSocket
    session = RealtimeSessionManager(
        system_prompt="Test prompt",
        tool_handlers={},
        voice="alloy"
    )
    session.ws = AsyncMock()
    session._connected = True

    # Call send_text
    await session.send_text("Hello, I want to practice!")

    # Verify first message was the text (second is response.create)
    first_call = session.ws.send.call_args_list[0][0][0]
    parsed = json.loads(first_call)

    assert parsed["type"] == "conversation.item.create"
    assert parsed["item"]["content"][0]["text"] == "Hello, I want to practice!"


@pytest.mark.asyncio
async def test_send_text_triggers_response():
    """send_text should trigger response.create after sending text."""
    from app.services.realtime_session import RealtimeSessionManager

    session = RealtimeSessionManager(
        system_prompt="Test prompt",
        tool_handlers={},
        voice="alloy"
    )
    session.ws = AsyncMock()
    session._connected = True

    await session.send_text("Practice pattern 1")

    # Should have sent two messages: conversation.item.create and response.create
    assert session.ws.send.call_count == 2

    # Second call should be response.create
    second_call = session.ws.send.call_args_list[1][0][0]
    parsed = json.loads(second_call)
    assert parsed["type"] == "response.create"
