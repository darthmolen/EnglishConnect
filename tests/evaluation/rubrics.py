"""Rubric definitions for LLM-as-Judge evaluation.

Each rubric defines criteria for evaluating a single dimension of agent behavior.
All rubrics follow chain-of-thought format: evidence first, then verdict.

Dimensions:
1. language_choice - Correct language for mode (English in practice, Spanish in help)
2. tool_usage - Always calls speak(), never fallback
3. output_cleanliness - No markdown/URLs in spoken text
4. confusion_recovery - Asks clarification when STT garbled
5. persona_consistency - Redirects personal questions to student
6. curriculum_alignment - Vocabulary within lesson level
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class Dimension(Enum):
    """Evaluation dimensions matching documented issues."""

    LANGUAGE_CHOICE = "language_choice"
    TOOL_USAGE = "tool_usage"
    OUTPUT_CLEANLINESS = "output_cleanliness"
    CONFUSION_RECOVERY = "confusion_recovery"
    PERSONA_CONSISTENCY = "persona_consistency"
    CURRICULUM_ALIGNMENT = "curriculum_alignment"


@dataclass
class Rubric:
    """Single evaluation rubric with judge prompt template."""

    dimension: Dimension
    description: str
    modes: list[Literal["help", "practice"]]
    prompt_template: str

    def build_prompt(
        self,
        user_input: str,
        context: dict,
        agent_response: str,
        tool_calls: list[dict],
    ) -> str:
        """Build the judge prompt for this rubric.

        Args:
            user_input: What the student said
            context: Dict with mode, lesson_number, vocabulary, etc.
            agent_response: Agent's text response
            tool_calls: List of tool calls made by agent

        Returns:
            Formatted prompt for the judge LLM
        """
        # Format tool calls for readability
        tool_calls_str = self._format_tool_calls(tool_calls)

        return self.prompt_template.format(
            user_input=user_input,
            context=context,
            agent_response=agent_response,
            tool_calls=tool_calls_str,
            mode=context.get("mode", "unknown"),
            lesson_number=context.get("lesson_number", 0),
            vocabulary=context.get("vocabulary", ""),
        )

    def _format_tool_calls(self, tool_calls: list[dict]) -> str:
        """Format tool calls for inclusion in prompt."""
        if not tool_calls:
            return "None"

        lines = []
        for tc in tool_calls:
            tool_name = tc.get("tool", tc.get("name", "unknown"))
            args = tc.get("args", tc.get("arguments", {}))
            lines.append(f"- {tool_name}({args})")
        return "\n".join(lines)


# =============================================================================
# RUBRIC DEFINITIONS
# =============================================================================

RUBRICS = {
    Dimension.LANGUAGE_CHOICE: Rubric(
        dimension=Dimension.LANGUAGE_CHOICE,
        description="Practice starts English, help responds in student's language",
        modes=["help", "practice"],
        prompt_template="""You are evaluating an English teaching agent for Spanish-speaking learners.

## Rubric: Language Choice
- In PRACTICE mode: Agent MUST start conversations in English (target language). Only switch to Spanish if student explicitly struggles or asks.
- In HELP mode: Agent should respond in the student's language (usually Spanish for explanations).

## Context
Mode: {mode}
Lesson: {lesson_number}
Exchange count in context: (check if this is the opening exchange)

## Student Input
{user_input}

## Agent Response
{agent_response}

## Tool Calls
{tool_calls}

## Evaluation
First, identify the language(s) used by the agent.
Then, determine if this is appropriate for the mode and context.

Respond with EXACTLY one of these formats:
PASS: [1-sentence reason]
FAIL: [1-sentence reason]
""",
    ),
    Dimension.TOOL_USAGE: Rubric(
        dimension=Dimension.TOOL_USAGE,
        description="Always calls speak(), never uses fallback text",
        modes=["help", "practice"],
        prompt_template="""You are evaluating an English teaching agent's tool usage.

## Rubric: Tool Usage
The agent MUST call the speak() tool for every response. Returning text without calling speak() triggers a fallback that degrades the user experience.

## Tool Calls Made
{tool_calls}

## Agent Text Response
{agent_response}

## Evaluation
Check if speak() was called at least once. If tool_calls is "None" or doesn't include speak(), this is a FAIL.

Respond with EXACTLY one of these formats:
PASS: speak() called with language [en/es]
FAIL: [reason - e.g., "No speak() call found", "Only returned text without speak()"]
""",
    ),
    Dimension.OUTPUT_CLEANLINESS: Rubric(
        dimension=Dimension.OUTPUT_CLEANLINESS,
        description="No markdown, URLs, or formatting in spoken text",
        modes=["help", "practice"],
        prompt_template="""You are evaluating spoken text quality for TTS synthesis.

## Rubric: Output Cleanliness
Spoken text must be clean for Text-to-Speech. TTS will read markdown literally, making responses sound robotic and confusing.

FORBIDDEN in spoken text:
- Markdown links: [text](url)
- URLs: http://, https://, api., .com, .wav, etc.
- Markdown headers: #, ##, ###
- Markdown formatting: **, *, `, ~~
- Code blocks: ```
- HTML tags: <anything>

## Agent Response / Spoken Text
{agent_response}

## Tool Calls (check speak() text parameter)
{tool_calls}

## Evaluation
Scan the response for any forbidden patterns. Quote them if found.

Respond with EXACTLY one of these formats:
PASS: Spoken text is clean for TTS
FAIL: Found "[quote the problematic text]"
""",
    ),
    Dimension.CONFUSION_RECOVERY: Rubric(
        dimension=Dimension.CONFUSION_RECOVERY,
        description="Handles ambiguous or garbled input appropriately",
        modes=["help", "practice"],
        prompt_template="""You are evaluating an agent's handling of unclear student input.

## Rubric: Confusion Recovery
The agent should handle unclear input appropriately:

1. **AMBIGUOUS input** (multiple valid meanings): Agent MUST ask for clarification or offer alternatives
   - Example: "Merry" could mean "merry (happy)" OR "Mary (name)" - ask which one
   - Example: Student says "No" to correct agent - ask what they meant

2. **GARBLED but CLEAR INTENT** (STT errors but meaning obvious): Agent MAY proceed
   - Example: "Tamei los sustantivos" clearly means "Dame los sustantivos" - OK to proceed
   - Example: "lexion" clearly means "lección" - OK to proceed

3. **INCOHERENT input** (no clear meaning): Agent MUST ask for clarification
   - Example: "Merry Como Casabse Merry" makes no sense - ask to repeat

## Context
Vocabulary: {vocabulary}

## Student Input
{user_input}

## Agent Response
{agent_response}

## Evaluation
1. Is the input ambiguous (multiple meanings), garbled (clear intent), or incoherent (no meaning)?
2. Did the agent respond appropriately for that category?

Respond with EXACTLY one of these formats:
PASS: [reason - e.g., "Agent asked for clarification for ambiguous input", "Agent correctly understood garbled intent"]
FAIL: [reason - e.g., "Agent guessed one meaning without acknowledging alternative", "Agent didn't ask for clarification on incoherent input"]
N/A: Input was clear, standard evaluation not needed
""",
    ),
    Dimension.PERSONA_CONSISTENCY: Rubric(
        dimension=Dimension.PERSONA_CONSISTENCY,
        description="Redirects personal questions to student",
        modes=["practice"],
        prompt_template="""You are evaluating how an AI teaching agent handles personal questions.

## Rubric: Persona Consistency
When asked personal questions (about the agent's family, life, preferences), the agent should redirect to the student's practice, not invent detailed personal stories.

The agent should NOT:
- Invent detailed personal backstory (e.g., "I have a brother named Juan who...")
- Claim to have family members, hobbies, physical characteristics
- Break character as a helpful AI tutor

The agent MAY:
- Give brief, clearly fictional examples for demonstration purposes
- Politely redirect: "I'm here to help you practice. Tell me about YOUR family!"
- Acknowledge being an AI and focus on helping the student

## Student Input
{user_input}

## Agent Response
{agent_response}

## Evaluation
Is the student asking about the agent personally? If so, how did the agent respond?

Respond with EXACTLY one of these formats:
PASS: [reason - e.g., "Agent redirected to student", "Agent gave brief example then focused on student"]
FAIL: [reason - e.g., "Agent invented detailed personal story about having a brother"]
N/A: Not a personal question about the agent
""",
    ),
    Dimension.CURRICULUM_ALIGNMENT: Rubric(
        dimension=Dimension.CURRICULUM_ALIGNMENT,
        description="Vocabulary within lesson level",
        modes=["help", "practice"],
        prompt_template="""You are evaluating vocabulary appropriateness for a language learner.

## Rubric: Curriculum Alignment
The agent should use vocabulary appropriate for the student's level. For lesson {lesson_number}, vocabulary should primarily come from lessons 1-{lesson_number}.

Simple, common words are always acceptable even if not explicitly in curriculum (hello, yes, no, good, etc.).

## Current Lesson Vocabulary (from curriculum)
{vocabulary}

## Agent Response
{agent_response}

## Evaluation
1. Identify any advanced vocabulary in the agent's response
2. Would this vocabulary likely confuse a beginner at lesson {lesson_number}?
3. Simple common words and cognates are fine (e.g., "family", "practice", "question")

Respond with EXACTLY one of these formats:
PASS: Vocabulary is level-appropriate
FAIL: Advanced vocabulary may confuse student: "[quote words]"
N/A: Response too short to evaluate vocabulary (1-2 words)
""",
    ),
}


def get_rubric(dimension: Dimension) -> Rubric:
    """Get rubric by dimension."""
    return RUBRICS[dimension]


def get_all_rubrics() -> list[Rubric]:
    """Get all rubric definitions."""
    return list(RUBRICS.values())


def get_rubrics_for_mode(mode: Literal["help", "practice"]) -> list[Rubric]:
    """Get rubrics applicable to a specific mode."""
    return [r for r in RUBRICS.values() if mode in r.modes]
