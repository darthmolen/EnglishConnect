"""Tests for Realtime API text input formatting.

TDD Task 2: Verify format_text_input creates correct message structure.
"""

import pytest


def test_realtime_text_message_format():
    """Text input should be formatted as conversation.item.create."""
    from app.services.realtime_session import format_text_input

    message = format_text_input("I'm ready to practice!")

    assert message["type"] == "conversation.item.create"
    assert message["item"]["type"] == "message"
    assert message["item"]["role"] == "user"
    assert message["item"]["content"][0]["type"] == "input_text"
    assert message["item"]["content"][0]["text"] == "I'm ready to practice!"


def test_realtime_text_message_with_spanish():
    """Text input should handle Spanish characters correctly."""
    from app.services.realtime_session import format_text_input

    message = format_text_input("Tengo una pregunta sobre el patrón 1.")

    assert message["item"]["content"][0]["text"] == "Tengo una pregunta sobre el patrón 1."


def test_realtime_text_message_empty_string():
    """Empty text should still create valid message structure."""
    from app.services.realtime_session import format_text_input

    message = format_text_input("")

    assert message["type"] == "conversation.item.create"
    assert message["item"]["content"][0]["text"] == ""
