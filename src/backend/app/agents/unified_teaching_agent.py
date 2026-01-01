"""Unified teaching agent with help and practice modes.

Consolidates teaching functionality into a single agent with two modes:
- Help mode: Answer questions only (vocabulary page)
- Practice mode: Lead conversation, flip roles (practice page)

See ADR-005 for architecture decision rationale.
"""

from typing import Literal, Optional

from app.models.performance import PerformanceContext
from app.prompts import load_prompt, render_prompt
from app.schemas.lesson import LessonDetail


class UnifiedTeachingAgent:
    """Unified agent that adapts behavior based on mode.

    Modes:
    - "help": Vocabulary page - answer questions only, use get_teaching_help
    - "practice": Practice page - lead conversation, flip roles after 3-5 exchanges

    Both modes have access to the same tools (speak, get_teaching_help, record_attempt)
    but use them differently based on behavioral instructions.
    """

    def __init__(
        self,
        lesson: LessonDetail,
        mode: Literal["help", "practice"],
        exchange_count: int = 0,
        instruction_language: str = "es",
        performance_context: Optional[PerformanceContext] = None,
        focus_pattern: Optional[int] = None,
    ):
        """Initialize the unified teaching agent.

        Args:
            lesson: Full lesson details with vocabulary and patterns
            mode: "help" for vocabulary page, "practice" for practice page
            exchange_count: Number of conversation exchanges (for flip detection)
            instruction_language: Language for explanations ('es' or 'en', default 'es')
            performance_context: Optional tracking of student struggle signals
            focus_pattern: Optional pattern number to focus practice on
        """
        self.lesson = lesson
        self.mode = mode
        self.exchange_count = exchange_count
        self.instruction_language = instruction_language
        self.performance_context = performance_context or PerformanceContext()
        self.focus_pattern = focus_pattern

    def build_system_prompt(self) -> str:
        """Build mode-specific system prompt for the LLM.

        Returns:
            Complete system prompt string
        """
        base_prompt = self._get_base_prompt()
        mode_prompt = self._get_mode_prompt()
        tools_prompt = self._get_tools_prompt()

        return f"""{base_prompt}

{mode_prompt}

{tools_prompt}"""

    def _get_base_prompt(self) -> str:
        """Get the base personality and context prompt."""
        template = load_prompt("agent/base.md")
        return render_prompt(
            template,
            lesson_number=self.lesson.lesson_number,
            lesson_title=self.lesson.title,
            lesson_objective=self.lesson.objective or "Practice English conversation",
        )

    def _get_mode_prompt(self) -> str:
        """Get mode-specific behavioral instructions."""
        if self.mode == "help":
            return self._build_help_prompt()
        else:
            return self._build_practice_prompt()

    def _get_tools_prompt(self) -> str:
        """Get the tools usage instructions."""
        return load_prompt("agent/tools.md")

    def _build_help_prompt(self) -> str:
        """Build help mode prompt (vocabulary page)."""
        # Build vocab list
        vocab_list = self._format_vocab_list()

        # Get performance context
        perf_ctx = self.performance_context.to_prompt_context()

        # Instruction language text
        instruction_lang_text = "Spanish" if self.instruction_language == "es" else "English"

        template = load_prompt("agent/mode_help.md")
        return render_prompt(
            template,
            vocab_list=vocab_list,
            struggle_level=perf_ctx["struggle_level"],
            consecutive_errors=perf_ctx["consecutive_errors"],
            needs_help=perf_ctx["needs_help"],
            instruction_language=instruction_lang_text,
        )

    def _build_practice_prompt(self) -> str:
        """Build practice mode prompt (practice page)."""
        # Build vocab and patterns lists
        vocab_list = self._format_vocab_list()
        patterns_list = self._format_patterns_list()

        # Get performance context
        perf_ctx = self.performance_context.to_prompt_context()

        # Instruction language text
        instruction_lang_text = "Spanish" if self.instruction_language == "es" else "English"

        # Flip instruction based on exchange count
        flip_instruction = self._get_flip_instruction()

        # Focus pattern instruction
        focus_instruction = self._get_focus_instruction()

        template = load_prompt("agent/mode_practice.md")
        return render_prompt(
            template,
            vocab_list=vocab_list,
            patterns_list=patterns_list,
            exchange_count=self.exchange_count,
            struggle_level=perf_ctx["struggle_level"],
            consecutive_errors=perf_ctx["consecutive_errors"],
            needs_help=perf_ctx["needs_help"],
            instruction_language=instruction_lang_text,
            flip_instruction=flip_instruction,
            focus_instruction=focus_instruction,
        )

    def _get_focus_instruction(self) -> str:
        """Get focus pattern instruction if a specific pattern is targeted."""
        if not self.focus_pattern:
            return ""

        # Find the focused pattern
        focused = None
        for p in self.lesson.patterns:
            if p.pattern_number == self.focus_pattern:
                focused = p
                break

        if not focused:
            return ""

        return f"""
**FOCUS PATTERN**: The student wants to practice Pattern {self.focus_pattern} specifically.
- Q: {focused.question_template}
- A: {focused.answer_template}

Start the conversation using THIS pattern. After practicing it a few times, you can naturally expand to related patterns."""

    def _format_vocab_list(self) -> str:
        """Format vocabulary list for prompt."""
        if not self.lesson.vocabulary:
            return "No vocabulary for this lesson."

        lines = [f"- {v.english} = {v.spanish}" for v in self.lesson.vocabulary]
        return "\n".join(lines)

    def _format_patterns_list(self) -> str:
        """Format patterns list for prompt."""
        if not self.lesson.patterns:
            return "No patterns for this lesson."

        lines = []
        for p in self.lesson.patterns:
            lines.append(
                f"Pattern {p.pattern_number}:\n"
                f"  Q: {p.question_template}\n"
                f"  A: {p.answer_template}"
            )
        return "\n".join(lines)

    def _get_flip_instruction(self) -> str:
        """Get flip instruction based on exchange count."""
        if self.exchange_count < 3:
            return "You are still leading. Ask questions using the patterns."
        elif self.exchange_count < 5:
            return "Time to flip! Prompt the student to ask YOU a question now."
        else:
            return "Natural conversation - mix asking and answering. The student may ask you questions."
