"""Lesson-based teacher agent with structured phase progression."""

from typing import Optional

from app.models.content import LessonPhase
from app.models.performance import PerformanceContext
from app.prompts import load_prompt, render_prompt
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
        instruction_language: str = "es",
        performance_context: Optional[PerformanceContext] = None,
    ):
        """Initialize the teacher agent.

        Args:
            lesson: Full lesson details with vocabulary and patterns
            phase: Current lesson phase from database
            phase_state: Current state within the phase (indices, completed items)
            instruction_language: Language for explanations ('es' or 'en', default 'es')
            performance_context: Optional tracking of student struggle signals
        """
        self.lesson = lesson
        self.phase = phase
        self.phase_state = phase_state
        self.instruction_language = instruction_language
        self.performance_context = performance_context or PerformanceContext()

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
        template = load_prompt("teacher/base.md")
        return render_prompt(
            template,
            lesson_number=self.lesson.lesson_number,
            lesson_title=self.lesson.title,
            lesson_objective=self.lesson.objective or "Practice English conversation",
            phase_name=self.phase.phase_name.upper(),
        )

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
        return load_prompt("teacher/tools.md")

    def _get_current_focus_prompt(self) -> str:
        """Get context about the current item being practiced."""
        if self.phase.phase_type == "vocabulary" and self.lesson.vocabulary:
            idx = min(self.phase_state.vocab_index, len(self.lesson.vocabulary) - 1)
            vocab = self.lesson.vocabulary[idx]
            progress = f"Word {idx + 1} of {len(self.lesson.vocabulary)}"
            template = load_prompt("teacher/focus_vocabulary.md")
            return render_prompt(
                template,
                progress=progress,
                word_english=vocab.english,
                word_spanish=vocab.spanish,
                word_category=vocab.category or "general",
            )

        elif self.phase.phase_type == "patterns" and self.lesson.patterns:
            idx = min(self.phase_state.pattern_index, len(self.lesson.patterns) - 1)
            pattern = self.lesson.patterns[idx]
            progress = f"Pattern {idx + 1} of {len(self.lesson.patterns)}"
            template = load_prompt("teacher/focus_patterns.md")
            return render_prompt(
                template,
                progress=progress,
                question_template=pattern.question_template,
                answer_template=pattern.answer_template,
            )

        return ""

    def _intro_prompt(self) -> str:
        """Prompt for the introduction phase."""
        return load_prompt("teacher/phase_intro.md")

    def _vocabulary_prompt(self) -> str:
        """Prompt for the vocabulary phase."""
        # Build vocab list
        if self.lesson.vocabulary:
            vocab_lines = [
                f"- {v.english} = {v.spanish}" for v in self.lesson.vocabulary
            ]
            vocab_list = "\n".join(vocab_lines)
        else:
            vocab_list = "No vocabulary for this lesson."

        template = load_prompt("teacher/phase_vocabulary.md")
        return render_prompt(template, vocab_list=vocab_list)

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
            patterns_list = "\n".join(pattern_lines)
        else:
            patterns_list = "No patterns for this lesson."

        template = load_prompt("teacher/phase_patterns.md")
        return render_prompt(template, patterns_list=patterns_list)

    def _practice_prompt(self) -> str:
        """Prompt for the practice phase."""
        # Build vocab list for reference
        vocab_words = (
            ", ".join([v.english for v in self.lesson.vocabulary])
            if self.lesson.vocabulary
            else "None"
        )

        # Build patterns list for reference
        if self.lesson.patterns:
            pattern_lines = []
            for p in self.lesson.patterns:
                pattern_lines.append(
                    f"Pattern {p.pattern_number}:\n"
                    f"  Q: {p.question_template}\n"
                    f"  A: {p.answer_template}"
                )
            patterns_list = "\n".join(pattern_lines)
        else:
            patterns_list = "No patterns for this lesson."

        # Instruction language for explanations
        instruction_lang_text = "Spanish" if self.instruction_language == "es" else "English"

        # Get performance context for adaptive help
        perf_ctx = self.performance_context.to_prompt_context()

        template = load_prompt("teacher/phase_practice.md")
        return render_prompt(
            template,
            vocab_words=vocab_words,
            patterns_list=patterns_list,
            instruction_language=instruction_lang_text,
            current_pattern_index=self.phase_state.pattern_index,
            total_patterns=len(self.lesson.patterns) if self.lesson.patterns else 0,
            # Performance context for adaptive help
            struggle_level=perf_ctx["struggle_level"],
            consecutive_errors=perf_ctx["consecutive_errors"],
            needs_help=perf_ctx["needs_help"],
        )

    def _wrapup_prompt(self) -> str:
        """Prompt for the wrap-up phase."""
        return load_prompt("teacher/phase_wrapup.md")
