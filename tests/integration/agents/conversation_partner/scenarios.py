"""Test scenarios for the conversation partner agent.

These scenarios define conversation flows to test the
free-form conversation partner agent's behavior.
"""

from harness.scenarios import Scenario, ScenarioStep


# Basic conversation flow
BASIC_CONVERSATION = Scenario(
    name="basic_conversation",
    lesson_number=5,
    description="Basic conversation about hobbies",
    steps=[
        ScenarioStep(
            student_input="Hello! I want to practice English.",
        ),
        ScenarioStep(
            student_input="I like to exercise.",
            expect_contains=["exercise"],
        ),
        ScenarioStep(
            student_input="What do you like to do?",
        ),
    ],
)


# Bilingual conversation
BILINGUAL_FLOW = Scenario(
    name="bilingual_flow",
    lesson_number=5,
    description="Student switches between English and Spanish",
    steps=[
        ScenarioStep(
            student_input="Hola, quiero practicar inglés",
        ),
        ScenarioStep(
            student_input="I like... como se dice cantar?",
        ),
    ],
)


# All scenarios
ALL_PARTNER_SCENARIOS = [
    BASIC_CONVERSATION,
    BILINGUAL_FLOW,
]
