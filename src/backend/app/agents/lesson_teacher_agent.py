"""Lesson-based teacher agent with structured phase progression."""

from app.models.content import LessonPhase
from app.schemas.lesson import LessonDetail
from app.schemas.lesson_session import PhaseStateSchema, PhaseProgressSchema


class LessonBasedTeacherAgent:
    """Structured lesson teacher that guides students through phases.

    Phases: intro -> vocabulary -> patterns -> practice -> wrapup

    Each phase has a specific system prompt that focuses the agent's behavior
    on the current learning objective.
    """

    def __init__(
        self,
        lesson: LessonDetail,
        phase: LessonPhase,
        phase_state: PhaseStateSchema,
    ):
        """Initialize the teacher agent.

        Args:
            lesson: Full lesson details with vocabulary and patterns
            phase: Current lesson phase from database
            phase_state: Current state within the phase (indices, completed items)
        """
        self.lesson = lesson
        self.phase = phase
        self.phase_state = phase_state

    def build_system_prompt(self) -> str:
        """Build phase-specific system prompt for the LLM.

        Returns:
            Complete system prompt string
        """
        base_prompt = self._get_base_prompt()
        phase_prompt = self._get_phase_prompt()
        tools_prompt = self._get_tools_prompt()
        focus_prompt = self._get_current_focus_prompt()

        return f"""{base_prompt}

{phase_prompt}

{focus_prompt}

{tools_prompt}"""

    def get_phase_progress(self) -> PhaseProgressSchema | None:
        """Get progress indicator for UI display.

        Returns:
            PhaseProgressSchema with current/total, or None if not applicable
        """
        if self.phase.phase_type == "vocabulary":
            return PhaseProgressSchema(
                current=self.phase_state.vocab_index + 1,
                total=len(self.lesson.vocabulary),
            )
        elif self.phase.phase_type == "patterns":
            return PhaseProgressSchema(
                current=self.phase_state.pattern_index + 1,
                total=len(self.lesson.patterns),
            )
        return None

    def _get_base_prompt(self) -> str:
        """Get the base personality and context prompt."""
        return f"""You are a friendly, patient English teacher helping Spanish-speaking learners through a structured lesson.

## Current Lesson: {self.lesson.lesson_number} - {self.lesson.title}

**Objective**: {self.lesson.objective or 'Practice English conversation'}

## Current Phase: {self.phase.phase_name.upper()}

You are guiding the student through a structured lesson. Stay focused on the current phase objectives."""

    def _get_phase_prompt(self) -> str:
        """Get phase-specific behavioral instructions."""
        prompts = {
            "intro": self._intro_prompt(),
            "vocabulary": self._vocabulary_prompt(),
            "patterns": self._patterns_prompt(),
            "practice": self._practice_prompt(),
            "wrapup": self._wrapup_prompt(),
        }
        return prompts.get(self.phase.phase_type, self._practice_prompt())

    def _get_tools_prompt(self) -> str:
        """Get the tools usage instructions."""
        return """## Your Tools:

### speak(text, language, voice)
Speaks text aloud to the student. You MUST call this tool for EVERY response.
- text: The text to speak (required)
- language: "en" for English, "es" for Spanish (required)
- voice: Use "speaker_b" (optional)

### advance_phase(reason)
Call this when the current phase objective is complete and you're ready to move on.
- reason: Brief explanation of why advancing (required)

### record_attempt(item_type, correct)
Call this after the student attempts a vocabulary word or pattern.
- item_type: "vocab" or "pattern" (required)
- correct: true if their attempt was correct (required)

## Important Rules:
1. ALWAYS use the speak tool - every response must include a speak() call
2. You are the TUTOR - respond to what the student says
3. Use simple, clear English appropriate for beginners
4. If student is confused, use speak() with language "es" for Spanish explanation
5. Be encouraging and celebrate progress"""

    def _get_current_focus_prompt(self) -> str:
        """Get context about the current item being practiced."""
        if self.phase.phase_type == "vocabulary" and self.lesson.vocabulary:
            idx = min(self.phase_state.vocab_index, len(self.lesson.vocabulary) - 1)
            vocab = self.lesson.vocabulary[idx]
            progress = f"Word {idx + 1} of {len(self.lesson.vocabulary)}"
            return f"""## Current Focus: Vocabulary ({progress})
**Word**: {vocab.english}
**Translation**: {vocab.spanish}
**Category**: {vocab.category or 'general'}"""

        elif self.phase.phase_type == "patterns" and self.lesson.patterns:
            idx = min(self.phase_state.pattern_index, len(self.lesson.patterns) - 1)
            pattern = self.lesson.patterns[idx]
            progress = f"Pattern {idx + 1} of {len(self.lesson.patterns)}"
            return f"""## Current Focus: Q&A Pattern ({progress})
**Question**: {pattern.question_template}
**Answer**: {pattern.answer_template}"""

        return ""

    def _intro_prompt(self) -> str:
        """Prompt for the introduction phase."""
        return """## Introduction Phase Instructions:

Your goals in this phase:
1. Welcome the student warmly
2. Introduce today's lesson topic and objective
3. Briefly mention what you'll be learning (vocabulary and patterns)
4. Ask if they're ready to begin

When the student confirms they're ready, call advance_phase() to move to vocabulary.

Example:
"Hello! Welcome to today's lesson. We're going to learn about [topic]. First, we'll practice some new words, then learn some conversation patterns. Are you ready to start?"
"""

    def _vocabulary_prompt(self) -> str:
        """Prompt for the vocabulary phase."""
        # Build vocab list
        if self.lesson.vocabulary:
            vocab_lines = [
                f"- {v.english} = {v.spanish}" for v in self.lesson.vocabulary
            ]
            vocab_section = "\n".join(vocab_lines)
        else:
            vocab_section = "No vocabulary for this lesson."

        return f"""## Vocabulary Phase Instructions:

You are teaching vocabulary words one at a time. Your process for EACH word:
1. Say the word clearly in English
2. Provide the Spanish translation
3. Use it in a simple example sentence
4. Ask the student to repeat the word
5. Listen and confirm/correct their pronunciation
6. Call record_attempt(item_type="vocab", correct=true/false) based on their response
7. Call advance_phase() to move to the next word (or to patterns if this is the last word)

## All Vocabulary for This Lesson:
{vocab_section}

Be patient and encouraging. If they struggle, repeat the word more slowly."""

    def _patterns_prompt(self) -> str:
        """Prompt for the patterns phase."""
        # Build patterns list
        if self.lesson.patterns:
            pattern_lines = []
            for p in self.lesson.patterns:
                pattern_lines.append(
                    f"Pattern {p.pattern_number}:\n"
                    f"  Q: {p.question_template}\n"
                    f"  A: {p.answer_template}"
                )
            patterns_section = "\n".join(pattern_lines)
        else:
            patterns_section = "No patterns for this lesson."

        return f"""## Patterns Phase Instructions:

You are teaching Q&A patterns. Your process for EACH pattern:
1. Explain the pattern structure
2. Give an example question and answer
3. Ask the student a question using the pattern
4. Listen to their answer
5. Confirm if correct or gently guide to the right answer
6. Call record_attempt(item_type="pattern", correct=true/false)
7. Call advance_phase() to move to the next pattern (or to practice if this is the last pattern)

## All Patterns for This Lesson:
{patterns_section}

Help them understand the structure, not just memorize."""

    def _practice_prompt(self) -> str:
        """Prompt for the practice phase."""
        # Build vocab and patterns for reference
        vocab_list = ", ".join([v.english for v in self.lesson.vocabulary]) if self.lesson.vocabulary else "None"

        return f"""## Practice Phase Instructions:

Now the student practices using vocabulary and patterns in natural conversation.

Your approach:
1. Ask questions that use the learned patterns
2. Encourage them to use the vocabulary words in answers
3. Keep the conversation flowing naturally
4. Gently correct errors - say the correct form and ask them to try again
5. If they struggle, switch to Spanish briefly to explain, then back to English
6. After sufficient practice (3-5 good exchanges), call advance_phase() to wrap up

## Available Vocabulary to Practice:
{vocab_list}

Keep it natural and conversational. Celebrate their successes!"""

    def _wrapup_prompt(self) -> str:
        """Prompt for the wrap-up phase."""
        return """## Wrap-up Phase Instructions:

The lesson is almost complete. Your goals:
1. Summarize what they learned today (vocabulary and patterns)
2. Celebrate their progress and effort
3. Mention one thing they did well
4. Offer a brief tip for continued practice
5. Ask if they have any questions
6. Wish them well and encourage them to practice

This is the final phase - be warm and encouraging.
After wrapping up, call advance_phase() to mark the lesson complete.

Example closing:
"Great job today! You learned [X] new words and practiced [pattern]. You did especially well with [specific example]. Keep practicing these phrases with friends or family. See you next time!"
"""
