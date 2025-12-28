"""Demo agent for playing pre-recorded audio examples."""

from app.prompts import load_prompt, render_prompt
from app.schemas.lesson import LessonDetail


class DemoAgent:
    """Agent that plays pre-recorded demo audio and answers questions.

    Flow:
    1. Play demo audio files sequentially
    2. After each demo, ask if student wants to repeat
    3. At the end, ask if there are questions
    4. Answer basic questions about the patterns/vocabulary
    """

    def __init__(
        self,
        lesson: LessonDetail,
        demo_metadata: list[dict],
    ):
        """Initialize the demo agent.

        Args:
            lesson: Full lesson details with vocabulary and patterns
            demo_metadata: List of demo audio metadata from the audio API
        """
        self.lesson = lesson
        self.demo_metadata = demo_metadata

    def build_system_prompt(self) -> str:
        """Build system prompt for the demo agent.

        Returns:
            Complete system prompt string
        """
        # Build demo list
        demo_lines = []
        for i, demo in enumerate(self.demo_metadata):
            pattern_num = demo.get("pattern_number", i + 1)
            example_idx = demo.get("example_index", 1)
            duration = demo.get("duration_seconds", 0)
            demo_lines.append(
                f"- Demo {i}: Pattern {pattern_num}, Example {example_idx} ({duration:.1f}s)"
            )
        demo_list = "\n".join(demo_lines) if demo_lines else "No demos available."

        # Build vocabulary section
        if self.lesson.vocabulary:
            vocab_lines = [
                f"- {v.english} = {v.spanish}" for v in self.lesson.vocabulary
            ]
            vocab_section = "\n".join(vocab_lines)
        else:
            vocab_section = "No specific vocabulary for this lesson."

        # Build patterns section
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
            patterns_section = "No specific Q&A patterns for this lesson."

        template = load_prompt("demo/base.md")
        return render_prompt(
            template,
            lesson_number=self.lesson.lesson_number,
            lesson_title=self.lesson.title,
            lesson_objective=self.lesson.objective or "Practice English conversation",
            demo_count=len(self.demo_metadata),
            demo_list=demo_list,
            vocab_section=vocab_section,
            patterns_section=patterns_section,
        )
