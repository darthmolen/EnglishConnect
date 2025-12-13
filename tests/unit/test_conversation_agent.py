"""Unit tests for ConversationAgentFactory."""

import pytest


class TestConversationAgentFactory:
    """Test ConversationAgentFactory methods."""

    def test_build_system_prompt_includes_lesson_title(self):
        """System prompt should include lesson title."""
        from app.agents.conversation_agent import ConversationAgentFactory
        from app.schemas.lesson import LessonDetail

        lesson = LessonDetail(
            lesson_number=5,
            title="Hobbies and Interests",
            objective="Learn to talk about hobbies",
            vocabulary=[],
            patterns=[],
            evaluation_criteria=[],
        )

        prompt = ConversationAgentFactory.build_system_prompt(lesson)

        assert "Hobbies and Interests" in prompt
        assert "5" in prompt

    def test_build_system_prompt_includes_vocabulary(self):
        """System prompt should include vocabulary items."""
        from app.agents.conversation_agent import ConversationAgentFactory
        from app.schemas.lesson import LessonDetail, VocabularyItemSchema

        lesson = LessonDetail(
            lesson_number=5,
            title="Hobbies",
            vocabulary=[
                VocabularyItemSchema(english="exercise", spanish="hacer ejercicio"),
                VocabularyItemSchema(english="sing", spanish="cantar"),
            ],
            patterns=[],
            evaluation_criteria=[],
        )

        prompt = ConversationAgentFactory.build_system_prompt(lesson)

        assert "exercise" in prompt
        assert "hacer ejercicio" in prompt
        assert "sing" in prompt

    def test_build_system_prompt_includes_patterns(self):
        """System prompt should include Q&A patterns."""
        from app.agents.conversation_agent import ConversationAgentFactory
        from app.schemas.lesson import LessonDetail, QAPatternSchema

        lesson = LessonDetail(
            lesson_number=5,
            title="Hobbies",
            vocabulary=[],
            patterns=[
                QAPatternSchema(
                    pattern_number=1,
                    question_template="What do you like to do?",
                    answer_template="I like to [activity].",
                )
            ],
            evaluation_criteria=[],
        )

        prompt = ConversationAgentFactory.build_system_prompt(lesson)

        assert "What do you like to do?" in prompt
        assert "I like to [activity]" in prompt

    def test_build_system_prompt_includes_objective(self):
        """System prompt should include learning objective."""
        from app.agents.conversation_agent import ConversationAgentFactory
        from app.schemas.lesson import LessonDetail

        lesson = LessonDetail(
            lesson_number=5,
            title="Hobbies",
            objective="Learn to express preferences and hobbies",
            vocabulary=[],
            patterns=[],
            evaluation_criteria=[],
        )

        prompt = ConversationAgentFactory.build_system_prompt(lesson)

        assert "Learn to express preferences and hobbies" in prompt

    def test_build_system_prompt_handles_empty_lesson(self):
        """System prompt should handle lesson with no vocabulary/patterns."""
        from app.agents.conversation_agent import ConversationAgentFactory
        from app.schemas.lesson import LessonDetail

        lesson = LessonDetail(
            lesson_number=1,
            title="Introduction",
            vocabulary=[],
            patterns=[],
            evaluation_criteria=[],
        )

        # Should not raise an error
        prompt = ConversationAgentFactory.build_system_prompt(lesson)

        assert "Introduction" in prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 0
