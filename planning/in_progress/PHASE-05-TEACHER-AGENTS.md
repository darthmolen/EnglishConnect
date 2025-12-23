# Phase 5A: LessonBasedTeacherAgent - Structured Lesson Flow

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a structured teacher agent that guides students through lessons in linear phases: Intro → Vocabulary → Patterns → Practice → Wrap-up.

**Architecture:** New `LessonBasedTeacherAgent` replaces the current conversation agent. Tracks lesson phase in session state. System prompt changes per phase to guide behavior.

**Key Files:**
- `src/backend/app/agents/lesson_teacher_agent.py` (new)
- `src/backend/app/agents/conversation_agent.py` (refactor or deprecate)
- `src/backend/app/routers/conversation.py` (update to use new agent)
- `src/backend/app/schemas/conversation.py` (add phase tracking)

---

## Lesson Phases

| Phase | Agent Behavior |
|-------|---------------|
| **1. Intro** | Greet, state lesson topic and objective |
| **2. Vocabulary** | Present each word, have student repeat, confirm |
| **3. Patterns** | Explain each Q&A pattern with examples |
| **4. Practice** | Ask pattern questions, student answers using vocabulary |
| **5. Wrap-up** | Summary, encouragement, offer to continue or end |

---

## Task 1: Create LessonBasedTeacherAgent

**File:** `src/backend/app/agents/lesson_teacher_agent.py`

```python
class LessonPhase(str, Enum):
    INTRO = "intro"
    VOCABULARY = "vocabulary"
    PATTERNS = "patterns"
    PRACTICE = "practice"
    WRAPUP = "wrapup"

class LessonBasedTeacherAgent:
    def __init__(self, lesson: LessonDetail):
        self.lesson = lesson
        self.phase = LessonPhase.INTRO
        self.vocab_index = 0
        self.pattern_index = 0

    def build_system_prompt(self) -> str:
        """Build phase-specific system prompt."""
        # Returns different prompts based on self.phase

    def advance_phase(self) -> bool:
        """Move to next phase. Returns False if at end."""

    def get_current_focus(self) -> dict:
        """Get current vocab word or pattern being practiced."""
```

---

## Task 2: Add Session State for Phase Tracking

**File:** `src/backend/app/schemas/conversation.py`

Add `lesson_phase` to request/response:
```python
class ConversationRequest(BaseModel):
    message: str
    lesson_number: int
    history: list[ChatMessage] = []
    lesson_phase: str | None = None  # Track current phase

class ConversationResponse(BaseModel):
    text: str
    lesson_number: int
    lesson_phase: str  # Return current phase
    phase_progress: dict | None = None  # e.g., {"vocab": "3/10", "pattern": "1/4"}
    # ... audio fields
```

---

## Task 3: Update Conversation Router

**File:** `src/backend/app/routers/conversation.py`

- Instantiate `LessonBasedTeacherAgent` with lesson
- Track phase across conversation turns
- Return phase info in response

---

## Task 4: Phase-Specific System Prompts

Each phase gets a focused prompt:

**Intro:** "Welcome the student, introduce today's lesson..."
**Vocabulary:** "You are reviewing vocabulary. Present: {word}. Ask them to repeat..."
**Patterns:** "Explain pattern {n}: Q: {question} A: {answer}..."
**Practice:** "Ask questions using the patterns. Correct gently..."
**Wrap-up:** "Summarize what they practiced, celebrate progress..."

---

## Task 5: Frontend Phase Display (Optional)

Show current phase in UI: "Vocabulary (3/10)" or progress bar.

---

## Future Phases (Deferred)

**Phase 5B: Agentic Tutor** - Monitoring agent that interjects with help when student struggles.

**Phase 5C: Conversational Weaving** - More organic introduction of vocabulary during practice.

**Phase 5D: Student-Driven with Checkpoints** - Free practice with prompts for uncovered content.
