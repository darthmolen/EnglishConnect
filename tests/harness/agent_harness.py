"""Core test harness for agent integration testing without voice layer.

This harness enables testing agent conversations by:
- Mocking TTS (returns fake audio, no actual synthesis)
- Using real Azure OpenAI for LLM responses
- Tracking phase transitions and tool calls
- Maintaining conversation history
"""

import logging
from dataclasses import dataclass, field
from typing import Literal

from app.agents.lesson_teacher_agent import LessonBasedTeacherAgent
from app.agents.conversation_agent import ConversationAgentFactory
from app.schemas.lesson import LessonDetail, VocabularyItemSchema, QAPatternSchema
from app.schemas.lesson_session import PhaseStateSchema
from app.services.azure_openai import get_agent_response, LESSON_AGENT_TOOLS, AGENT_TOOLS

logger = logging.getLogger(__name__)


# Standard lesson phases in order
PHASE_ORDER = ["intro", "vocabulary", "patterns", "practice", "wrapup"]


@dataclass
class MockPhase:
    """Mock LessonPhase for testing without database."""

    id: int
    phase_type: str
    phase_name: str
    sort_order: int


def create_mock_phases() -> list[MockPhase]:
    """Create standard lesson phases for testing."""
    return [
        MockPhase(id=i + 1, phase_type=pt, phase_name=pt.title(), sort_order=i)
        for i, pt in enumerate(PHASE_ORDER)
    ]


@dataclass
class AgentResponse:
    """Result from a single agent interaction."""

    text: str
    phase: MockPhase
    phase_state: PhaseStateSchema
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    spoken_text: str | None = None
    spoken_language: str | None = None


class AgentTestHarness:
    """Run agent conversations without voice layer.

    Example usage:
        harness = await AgentTestHarness.create(lesson_number=5)
        response = await harness.send("Hello!")
        print(response.text)
        print(harness.get_transcript())
    """

    def __init__(
        self,
        lesson: LessonDetail,
        agent_type: Literal["teacher", "partner"] = "teacher",
    ):
        """Initialize the harness with lesson data.

        Use the `create` class method for async initialization with database lesson.

        Args:
            lesson: LessonDetail with vocabulary and patterns
            agent_type: "teacher" for structured lesson flow, "partner" for free-form
        """
        self.lesson = lesson
        self.agent_type = agent_type

        # Phase tracking (simulated in memory)
        self.phases = create_mock_phases()
        self.phase_index = 0
        self.phase = self.phases[0]
        self.phase_state = PhaseStateSchema()

        # Conversation state
        self.history: list[dict] = []
        self.all_tool_calls: list[dict] = []
        self.all_tool_results: list[dict] = []
        self.phase_history: list[str] = [self.phase.phase_type]

    @classmethod
    async def create(
        cls,
        lesson_number: int,
        agent_type: Literal["teacher", "partner"] = "teacher",
        course_id: str = "ec1",
    ) -> "AgentTestHarness":
        """Create harness with lesson loaded from database.

        Args:
            lesson_number: Lesson number to load
            agent_type: "teacher" or "partner"
            course_id: Course ID (default "ec1")

        Returns:
            Initialized AgentTestHarness

        Raises:
            ValueError: If lesson not found
        """
        from app.database import async_session_maker
        from app.services.lesson_service import LessonService

        async with async_session_maker() as session:
            service = LessonService(session)
            lesson = await service.get_lesson_detail(course_id, lesson_number)

            if not lesson:
                raise ValueError(f"Lesson {lesson_number} not found in course {course_id}")

            return cls(lesson=lesson, agent_type=agent_type)

    @classmethod
    def create_with_mock_lesson(
        cls,
        lesson_number: int = 5,
        title: str = "Test Lesson",
        objective: str = "Test objective",
        vocabulary: list[VocabularyItemSchema] | None = None,
        patterns: list[QAPatternSchema] | None = None,
        agent_type: Literal["teacher", "partner"] = "teacher",
    ) -> "AgentTestHarness":
        """Create harness with mock lesson data (no database needed).

        Args:
            lesson_number: Lesson number for the mock
            title: Lesson title
            objective: Lesson objective
            vocabulary: List of vocabulary items
            patterns: List of Q&A patterns
            agent_type: "teacher" or "partner"

        Returns:
            Initialized AgentTestHarness with mock data
        """
        if vocabulary is None:
            vocabulary = [
                VocabularyItemSchema(english="exercise", spanish="hacer ejercicio", category="hobbies"),
                VocabularyItemSchema(english="sing", spanish="cantar", category="hobbies"),
                VocabularyItemSchema(english="play", spanish="jugar", category="hobbies"),
            ]

        if patterns is None:
            patterns = [
                QAPatternSchema(
                    pattern_number=1,
                    question_template="What do you like to do?",
                    answer_template="I like to [activity].",
                ),
            ]

        lesson = LessonDetail(
            lesson_number=lesson_number,
            title=title,
            objective=objective,
            vocabulary=vocabulary,
            patterns=patterns,
        )

        return cls(lesson=lesson, agent_type=agent_type)

    def _build_system_prompt(self) -> str:
        """Build system prompt based on agent type and current phase."""
        if self.agent_type == "teacher":
            agent = LessonBasedTeacherAgent(
                lesson=self.lesson,
                phase=self.phase,
                phase_state=self.phase_state,
            )
            return agent.build_system_prompt()
        else:
            return ConversationAgentFactory.build_system_prompt(self.lesson)

    def _get_tools(self) -> list[dict]:
        """Get tool definitions based on agent type."""
        if self.agent_type == "teacher":
            return LESSON_AGENT_TOOLS
        else:
            return AGENT_TOOLS

    async def _mock_speak_handler(
        self, text: str, language: str, voice: str = "speaker_b"
    ) -> dict:
        """Mock TTS handler that returns fake audio."""
        return {
            "spoken": True,
            "text": text,
            "language": language,
            "audio_base64": "MOCK_AUDIO_BASE64",
            "format": "wav",
            "sample_rate": 16000,
        }

    async def _advance_phase_handler(self, reason: str) -> dict:
        """Handle advance_phase tool calls, updating internal state."""
        logger.info(f"advance_phase called: {reason}")

        current_phase_type = self.phase.phase_type

        # For vocabulary/patterns, check if we're advancing within the phase
        if (
            current_phase_type == "vocabulary"
            and self.phase_state.vocab_index < len(self.lesson.vocabulary) - 1
        ):
            # Advance to next vocabulary word
            self.phase_state.vocab_index += 1
            return {
                "success": True,
                "action": "next_vocab",
                "vocab_index": self.phase_state.vocab_index,
            }

        elif (
            current_phase_type == "patterns"
            and self.phase_state.pattern_index < len(self.lesson.patterns) - 1
        ):
            # Advance to next pattern
            self.phase_state.pattern_index += 1
            return {
                "success": True,
                "action": "next_pattern",
                "pattern_index": self.phase_state.pattern_index,
            }

        else:
            # Advance to next phase
            if self.phase_index >= len(self.phases) - 1:
                # At last phase (wrapup), mark complete
                return {
                    "success": True,
                    "action": "lesson_complete",
                }
            else:
                self.phase_index += 1
                self.phase = self.phases[self.phase_index]
                self.phase_state = PhaseStateSchema()  # Reset state for new phase
                self.phase_history.append(self.phase.phase_type)
                return {
                    "success": True,
                    "action": "next_phase",
                    "new_phase": self.phase.phase_type,
                }

    async def _record_attempt_handler(self, item_type: str, correct: bool) -> dict:
        """Handle record_attempt tool calls."""
        logger.info(f"record_attempt called: type={item_type}, correct={correct}")

        if item_type == "vocab":
            item_id = f"vocab_{self.phase_state.vocab_index}"
        else:
            item_id = f"pattern_{self.phase_state.pattern_index}"

        if correct and item_id not in self.phase_state.items_completed:
            self.phase_state.items_completed.append(item_id)

        return {"recorded": True, "item_type": item_type, "correct": correct}

    async def send(self, message: str) -> AgentResponse:
        """Send a message to the agent and get a response.

        Args:
            message: Student message (can be empty string for initial greeting)

        Returns:
            AgentResponse with text, phase info, and tool call details
        """
        system_prompt = self._build_system_prompt()
        tools = self._get_tools()

        tool_handlers = {
            "speak": self._mock_speak_handler,
            "advance_phase": self._advance_phase_handler,
            "record_attempt": self._record_attempt_handler,
        }

        # Call the real Azure OpenAI agent
        result = await get_agent_response(
            system_prompt=system_prompt,
            user_message=message,
            history=self.history,
            tool_handlers=tool_handlers,
            user_id="test-harness",
            tools=tools,
        )

        # Track tool calls
        tool_calls = result.get("tool_calls", [])
        tool_results = result.get("tool_results", [])
        self.all_tool_calls.extend(tool_calls)
        self.all_tool_results.extend(tool_results)

        # Extract spoken text from tool results
        spoken_text = None
        spoken_language = None
        for tool_result in tool_results:
            if tool_result.get("tool") == "speak" and tool_result.get("success"):
                result_data = tool_result.get("result", {})
                if result_data.get("spoken"):
                    spoken_text = result_data.get("text")
                    spoken_language = result_data.get("language")

        # Use spoken text as primary response text
        response_text = spoken_text if spoken_text else result["text"]

        # Update history
        if message:  # Don't add empty messages
            self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": response_text})

        return AgentResponse(
            text=response_text,
            phase=self.phase,
            phase_state=self.phase_state,
            tool_calls=tool_calls,
            tool_results=tool_results,
            spoken_text=spoken_text,
            spoken_language=spoken_language,
        )

    def get_transcript(self) -> str:
        """Get human-readable transcript of the conversation.

        Returns:
            Formatted string with role labels and messages
        """
        lines = []
        lines.append(f"=== Lesson {self.lesson.lesson_number}: {self.lesson.title} ===")
        lines.append(f"Agent type: {self.agent_type}")
        lines.append(f"Phases visited: {' -> '.join(self.phase_history)}")
        lines.append("")

        for msg in self.history:
            role = "Student" if msg["role"] == "user" else "Teacher"
            lines.append(f"[{role}] {msg['content']}")
            lines.append("")

        return "\n".join(lines)

    def get_phase_history(self) -> list[str]:
        """Get list of phases visited in order.

        Returns:
            List of phase type strings
        """
        return self.phase_history.copy()

    def reset(self) -> None:
        """Reset the harness to initial state."""
        self.phase_index = 0
        self.phase = self.phases[0]
        self.phase_state = PhaseStateSchema()
        self.history = []
        self.all_tool_calls = []
        self.all_tool_results = []
        self.phase_history = [self.phase.phase_type]
