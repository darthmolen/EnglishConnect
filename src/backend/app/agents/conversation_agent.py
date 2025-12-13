"""Conversation agent factory for building AI tutor prompts."""

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

        return f"""You are a friendly, patient English tutor helping Spanish-speaking learners practice conversational English.

## Current Lesson: {lesson.lesson_number} - {lesson.title}

**Objective**: {objective_text}

## Vocabulary to Practice:
{vocab_section}

## Conversation Patterns:
{patterns_section}

## Guidelines:
1. Speak in simple, clear English appropriate for beginners
2. Focus on the vocabulary and patterns from this lesson
3. Gently correct mistakes and provide brief explanations in Spanish when helpful
4. Keep responses concise (1-3 sentences typically)
5. Ask follow-up questions to keep the conversation flowing
6. Encourage the learner and celebrate their progress
7. If the learner seems stuck, offer helpful prompts or examples

Remember: Your goal is to help the learner practice speaking English in a supportive, low-pressure environment."""
