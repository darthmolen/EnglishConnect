"""Conversation agent factory for building AI tutor prompts."""

from app.prompts import load_prompt, render_prompt
from app.schemas.lesson import LessonDetail


class ConversationAgentFactory:
    """Factory for creating conversation agent configurations."""

    @staticmethod
    def build_system_prompt(lesson: LessonDetail) -> str:
        """Build system prompt for the AI tutor based on lesson content.

        Args:
            lesson: LessonDetail with vocabulary, patterns, and objectives

        Returns:
            System prompt string for the LLM
        """
        # Build vocabulary section
        if lesson.vocabulary:
            vocab_lines = [
                f"- {v.english} = {v.spanish}" for v in lesson.vocabulary
            ]
            vocab_section = "\n".join(vocab_lines)
        else:
            vocab_section = "No specific vocabulary for this lesson."

        # Build patterns section
        if lesson.patterns:
            pattern_lines = []
            for p in lesson.patterns:
                pattern_lines.append(
                    f"Pattern {p.pattern_number}:\n"
                    f"  Q: {p.question_template}\n"
                    f"  A: {p.answer_template}"
                )
            patterns_section = "\n".join(pattern_lines)
        else:
            patterns_section = "No specific Q&A patterns for this lesson."

        # Build objective section
        objective_text = lesson.objective or "Practice English conversation"

        template = load_prompt("conversation_partner/base.md")
        return render_prompt(
            template,
            lesson_number=lesson.lesson_number,
            lesson_title=lesson.title,
            lesson_objective=objective_text,
            vocab_section=vocab_section,
            patterns_section=patterns_section,
        )
