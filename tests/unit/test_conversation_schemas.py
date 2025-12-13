"""Unit tests for conversation Pydantic schemas."""

import pytest


def test_conversation_request_requires_message():
    """ConversationRequest should require message field."""
    from app.schemas.conversation import ConversationRequest

    request = ConversationRequest(
        message="Hello, how are you?",
        lesson_number=5
    )
    assert request.message == "Hello, how are you?"
    assert request.lesson_number == 5


def test_conversation_request_optional_history():
    """ConversationRequest should accept optional conversation history."""
    from app.schemas.conversation import ConversationRequest, ChatMessage

    request = ConversationRequest(
        message="What's your name?",
        lesson_number=5,
        history=[
            ChatMessage(role="user", content="Hi"),
            ChatMessage(role="assistant", content="Hello!")
        ]
    )
    assert len(request.history) == 2
    assert request.history[0].role == "user"


def test_conversation_request_default_history():
    """ConversationRequest history should default to empty list."""
    from app.schemas.conversation import ConversationRequest

    request = ConversationRequest(message="Hello", lesson_number=1)
    assert request.history == []


def test_conversation_response_has_text():
    """ConversationResponse should have text and lesson_number."""
    from app.schemas.conversation import ConversationResponse

    response = ConversationResponse(
        text="I am your English tutor!",
        lesson_number=5
    )
    assert response.text == "I am your English tutor!"
    assert response.lesson_number == 5


def test_chat_message_user_role():
    """ChatMessage should accept 'user' role."""
    from app.schemas.conversation import ChatMessage

    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"


def test_chat_message_assistant_role():
    """ChatMessage should accept 'assistant' role."""
    from app.schemas.conversation import ChatMessage

    msg = ChatMessage(role="assistant", content="Hi there!")
    assert msg.role == "assistant"
    assert msg.content == "Hi there!"
