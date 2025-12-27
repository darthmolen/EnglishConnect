"""Test scenarios for the teacher agent.

These scenarios define multi-step conversation flows to test
the structured lesson teacher agent's behavior.
"""

from harness.scenarios import Scenario, ScenarioStep


# Green path: Happy path through all phases with cooperative student
GREEN_PATH = Scenario(
    name="green_path",
    lesson_number=5,
    description="Happy path through all phases with cooperative student",
    steps=[
        ScenarioStep(
            student_input="Hello, I'm ready to learn!",
            expected_phase="intro",
        ),
        ScenarioStep(
            student_input="Yes, let's begin!",
            expect_tool="advance_phase",
        ),
        ScenarioStep(
            student_input="exercise",
            expected_phase="vocabulary",
            expect_tool="record_attempt",
        ),
        ScenarioStep(
            student_input="sing",
            expect_tool="record_attempt",
        ),
        ScenarioStep(
            student_input="play",
            expect_tool="record_attempt",
        ),
        ScenarioStep(
            student_input="read",
            expect_tool="record_attempt",
        ),
        ScenarioStep(
            student_input="cook",
            expect_tool="advance_phase",
        ),
    ],
)


# Skip ahead: Student demonstrates mastery, agent should recognize
SKIP_AHEAD = Scenario(
    name="skip_ahead",
    lesson_number=5,
    description="Student demonstrates mastery, agent may recognize and adapt",
    steps=[
        ScenarioStep(
            student_input="Hi! I already know exercise, sing, play, read, cook. Can we skip to practice?",
            expected_phase="intro",
        ),
        ScenarioStep(
            student_input="I can say all the words: exercise means hacer ejercicio, sing is cantar, play is jugar. Can we move on?",
        ),
    ],
)


# Bilingual Spanish: Student requests Spanish explanation
BILINGUAL_SPANISH = Scenario(
    name="bilingual_spanish",
    lesson_number=5,
    description="Student requests Spanish explanation",
    steps=[
        ScenarioStep(
            student_input="Hola! No entiendo. ¿Puedes explicar en español?",
            expect_contains=["español"],  # Agent should acknowledge Spanish request
        ),
        ScenarioStep(
            student_input="¿Qué significa 'exercise'?",
            expect_contains=["ejercicio"],  # Should explain in Spanish
        ),
    ],
)


# Confusion: Student expresses confusion and needs help
STUDENT_CONFUSION = Scenario(
    name="student_confusion",
    lesson_number=5,
    description="Student expresses confusion and needs teacher help",
    steps=[
        ScenarioStep(
            student_input="Hello, I'm ready!",
            expected_phase="intro",
        ),
        ScenarioStep(
            student_input="Yes, let's start",
            expect_tool="advance_phase",
        ),
        ScenarioStep(
            student_input="I don't understand. What does this word mean?",
            expected_phase="vocabulary",
        ),
        ScenarioStep(
            student_input="Can you repeat that more slowly?",
        ),
    ],
)


# Minimal responses: Student gives minimal input
MINIMAL_RESPONSES = Scenario(
    name="minimal_responses",
    lesson_number=5,
    description="Student gives minimal single-word responses",
    steps=[
        ScenarioStep(
            student_input="Hi",
            expected_phase="intro",
        ),
        ScenarioStep(
            student_input="Yes",
            expect_tool="advance_phase",
        ),
        ScenarioStep(
            student_input="exercise",
            expected_phase="vocabulary",
        ),
        ScenarioStep(
            student_input="OK",
        ),
    ],
)


# Enthusiastic student: Highly engaged student
ENTHUSIASTIC_STUDENT = Scenario(
    name="enthusiastic_student",
    lesson_number=5,
    description="Highly engaged and enthusiastic student",
    steps=[
        ScenarioStep(
            student_input="Hi teacher! I'm so excited to learn English today! This is going to be great!",
            expected_phase="intro",
        ),
        ScenarioStep(
            student_input="Yes please! I can't wait to learn new words! Let's go!",
            expect_tool="advance_phase",
        ),
        ScenarioStep(
            student_input="Exercise! I love to exercise! Hacer ejercicio is so fun!",
            expected_phase="vocabulary",
            expect_tool="record_attempt",
        ),
    ],
)


# All scenarios for easy iteration
ALL_TEACHER_SCENARIOS = [
    GREEN_PATH,
    SKIP_AHEAD,
    BILINGUAL_SPANISH,
    STUDENT_CONFUSION,
    MINIMAL_RESPONSES,
    ENTHUSIASTIC_STUDENT,
]
