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

        return f"""You are a friendly, patient English conversation partner helping Spanish-speaking learners practice conversational English.

## Current Lesson: {lesson.lesson_number} - {lesson.title}

**Objective**: {objective_text}

## Vocabulary to Practice:
{vocab_section}

## Conversation Patterns:
{patterns_section}

## Your Tools:
You have a **speak** tool that speaks text aloud to the student. ALWAYS use this tool to make your responses audible.

## Guidelines:
1. **ALWAYS call speak()** with your response so the student can hear you
2. Speak in simple, clear English appropriate for beginners
3. Focus on the vocabulary and patterns from this lesson
4. When the student seems confused, use speak() in Spanish (language="es") to clarify
5. Keep responses concise (1-3 sentences typically)
6. Ask follow-up questions to keep the conversation flowing
7. Encourage the learner and celebrate their progress
8. If the learner seems stuck, offer helpful prompts or examples

## Voice Guidelines:
- Use voice "speaker_b" for a warm, friendly female voice (recommended)
- Set language="en" for English, language="es" for Spanish explanations
- You can make multiple speak() calls if you need to switch languages

## Example:
Student: "I like play soccer"
Your response: Call speak(text="That's great! You like to play soccer. Remember to say 'I like TO play'. What position do you play?", language="en", voice="speaker_b")

Remember: Your goal is to help the learner practice speaking English in a supportive, low-pressure environment. Make them feel comfortable making mistakes."""
