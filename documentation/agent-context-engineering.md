# Agent Context Engineering

This document details how we engineer the LLM agent's context (system prompt), the file structure, assembly order, and testing patterns.

## Overview

The agent's context is the system prompt that shapes its behavior. We use a modular, template-based approach that:

1. **Separates concerns** - Each aspect of behavior lives in its own file
2. **Enables testing** - Context is built deterministically from inputs
3. **Supports iteration** - Change behavior by editing markdown files, not code

## File Structure

```
src/backend/app/
├── agents/
│   └── unified_teaching_agent.py    # Agent class, assembles context
├── prompts/
│   ├── __init__.py                  # Exports load_prompt, render_prompt
│   ├── loader.py                    # Template loading and rendering
│   └── agent/
│       ├── base.md                  # Personality, PII rules, language detection
│       ├── mode_help.md             # Help mode behavior (vocabulary page)
│       ├── mode_practice.md         # Practice mode behavior (practice page)
│       └── tools.md                 # Tool usage instructions
└── models/
    └── performance.py               # PerformanceContext for struggle tracking
```

## Context Assembly Order

The `UnifiedTeachingAgent.build_system_prompt()` method assembles context in this order:

```
┌─────────────────────────────────────────────────────────────────┐
│                    FINAL SYSTEM PROMPT                          │
├─────────────────────────────────────────────────────────────────┤
│  1. BASE PROMPT (base.md)                                       │
│     ├── PII protection rules (MANDATORY - never ask for)        │
│     ├── Language detection rules (Spanish → respond Spanish)    │
│     ├── Personality (friendly, patient teacher)                 │
│     └── Lesson context (number, title, objective)               │
├─────────────────────────────────────────────────────────────────┤
│  2. MODE PROMPT (mode_help.md OR mode_practice.md)              │
│     ├── Mode-specific behavior instructions                     │
│     ├── Vocabulary list (formatted from lesson data)            │
│     ├── Patterns list (practice mode only)                      │
│     ├── Performance context (struggle level, errors)            │
│     ├── Focus instruction (if focus_pattern set)                │
│     └── Flip instruction (practice mode, based on exchanges)    │
├─────────────────────────────────────────────────────────────────┤
│  3. TOOLS PROMPT (tools.md)                                     │
│     ├── speak() - TTS tool (REQUIRED for every response)        │
│     ├── get_teaching_help() - Agentic RAG                       │
│     ├── record_attempt() - Progress tracking                    │
│     └── Important rules and usage guidelines                    │
└─────────────────────────────────────────────────────────────────┘
```

## Template System

### Loading (`load_prompt`)

```python
from app.prompts import load_prompt

# Loads from src/backend/app/prompts/agent/base.md
template = load_prompt("agent/base.md")
```

- Files are loaded relative to the `prompts/` directory
- Uses `@lru_cache` for performance (prompts are read once)
- Returns raw markdown with `{placeholders}`

### Rendering (`render_prompt`)

```python
from app.prompts import render_prompt

rendered = render_prompt(
    template,
    lesson_number=5,
    lesson_title="Hobbies",
    vocab_list="- exercise = hacer ejercicio\n- play = jugar",
)
```

- Uses simple `{placeholder}` syntax (not Jinja2)
- Unmatched placeholders are left unchanged (partial rendering)
- All values converted to strings

## Dynamic Context Variables

### From Lesson Data

| Variable | Source | Example |
|----------|--------|---------|
| `{lesson_number}` | `lesson.lesson_number` | `5` |
| `{lesson_title}` | `lesson.title` | `"Hobbies and Interests"` |
| `{lesson_objective}` | `lesson.objective` | `"Learn to talk about hobbies"` |
| `{vocab_list}` | `_format_vocab_list()` | `"- exercise = hacer ejercicio\n- sing = cantar"` |
| `{patterns_list}` | `_format_patterns_list()` | `"Pattern 1:\n  Q: What do you like to do?\n  A: I like to..."` |

### From Request Parameters

| Variable | Source | Example |
|----------|--------|---------|
| `{exchange_count}` | `request.exchange_count` | `3` |
| `{instruction_language}` | `request.instruction_language` | `"Spanish"` or `"English"` |
| `{flip_instruction}` | `_get_flip_instruction()` | `"Time to flip! Prompt the student to ask YOU a question now."` |
| `{focus_instruction}` | `_get_focus_instruction()` | `"**FOCUS PATTERN**: Pattern 1..."` |

### From Performance Tracking

| Variable | Source | Example |
|----------|--------|---------|
| `{struggle_level}` | `performance_context.struggle_level` | `"low"`, `"medium"`, `"high"` |
| `{consecutive_errors}` | `performance_context.consecutive_errors` | `2` |
| `{needs_help}` | `performance_context.needs_help` | `true` or `false` |

## Mode-Specific Assembly

### Help Mode (`mode="help"`)

```python
agent = UnifiedTeachingAgent(lesson=lesson, mode="help")
prompt = agent.build_system_prompt()
```

**Includes:**
- `base.md` - personality, language rules
- `mode_help.md` - wait for questions, use get_teaching_help
- `tools.md` - speak(), get_teaching_help()

**Key behaviors:**
- Do NOT initiate conversation
- Only respond when student asks
- Use get_teaching_help for word explanations

### Practice Mode (`mode="practice"`)

```python
agent = UnifiedTeachingAgent(
    lesson=lesson,
    mode="practice",
    exchange_count=3,
    focus_pattern=1,  # Optional
)
prompt = agent.build_system_prompt()
```

**Includes:**
- `base.md` - personality, language rules
- `mode_practice.md` - lead conversation, flip roles, patterns
- `tools.md` - speak(), get_teaching_help(), record_attempt()

**Key behaviors:**
- Lead first (ask questions)
- Flip after 3-5 exchanges (student asks)
- If focus_pattern set, start with that pattern

## Testing Patterns

We test context engineering through **prompt content assertions**. This verifies that the assembled prompt contains the expected content for given inputs.

### Test Structure

```
tests/unit/test_unified_teaching_agent.py
├── TestUnifiedTeachingAgentInit     # Constructor tests
├── TestHelpModePrompt               # Help mode content tests
├── TestPracticeModePrompt           # Practice mode content tests
├── TestPerformanceContextIntegration # Struggle level tests
├── TestToolInstructions             # Tool presence tests
├── TestEdgeCases                    # Empty vocab, high exchange counts
└── TestFocusPattern                 # Focus pattern functionality
```

### Testing Philosophy

1. **Test inputs, not outputs** - We test that the right content appears in the prompt, not what the LLM does with it

2. **Use fixtures** - Create sample lessons with known content

3. **Assert substring presence** - Check that key phrases appear in the assembled prompt

### Example Tests

```python
@pytest.fixture
def sample_lesson():
    """Create a sample lesson for testing."""
    return LessonDetail(
        lesson_number=5,
        title="Hobbies and Interests",
        objective="Learn to talk about hobbies",
        vocabulary=[
            VocabularyItemSchema(english="exercise", spanish="hacer ejercicio"),
        ],
        patterns=[
            QAPatternSchema(
                pattern_number=1,
                question_template="What do you like to do?",
                answer_template="I like to [activity].",
            ),
        ],
    )


class TestHelpModePrompt:
    """Test help mode prompt generation."""

    def test_help_mode_prompt_includes_vocabulary(self, sample_lesson):
        """Help mode prompt should include vocabulary list."""
        agent = UnifiedTeachingAgent(lesson=sample_lesson, mode="help")
        prompt = agent.build_system_prompt()

        assert "exercise" in prompt
        assert "hacer ejercicio" in prompt

    def test_help_mode_prompt_wait_behavior(self, sample_lesson):
        """Help mode should instruct agent to wait for questions."""
        agent = UnifiedTeachingAgent(lesson=sample_lesson, mode="help")
        prompt = agent.build_system_prompt()

        assert "wait" in prompt.lower() or "only respond" in prompt.lower()


class TestPracticeModePrompt:
    """Test practice mode prompt generation."""

    def test_practice_mode_prompt_includes_patterns(self, sample_lesson):
        """Practice mode prompt should include patterns."""
        agent = UnifiedTeachingAgent(lesson=sample_lesson, mode="practice")
        prompt = agent.build_system_prompt()

        assert "What do you like to do?" in prompt
        assert "I like to" in prompt

    def test_practice_mode_prompt_flip_suggestion(self, sample_lesson):
        """Practice mode should suggest flip after 3-5 exchanges."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
            exchange_count=4,
        )
        prompt = agent.build_system_prompt()

        flip_indicators = ["you ask", "now you", "your turn", "flip"]
        assert any(ind in prompt.lower() for ind in flip_indicators)


class TestFocusPattern:
    """Test focus_pattern functionality."""

    def test_focus_pattern_in_prompt(self, sample_lesson):
        """Focus pattern should appear in system prompt."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
            focus_pattern=1,
        )
        prompt = agent.build_system_prompt()

        assert "focus" in prompt.lower() or "pattern 1" in prompt.lower()
        assert "What do you like to do?" in prompt

    def test_invalid_focus_pattern_graceful(self, sample_lesson):
        """Agent should handle non-existent pattern gracefully."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
            focus_pattern=99,  # Doesn't exist
        )
        prompt = agent.build_system_prompt()
        assert len(prompt) > 0  # Doesn't crash
```

### Running Tests

```bash
# Run all agent context tests
python -m pytest tests/unit/test_unified_teaching_agent.py -v

# Run specific test class
python -m pytest tests/unit/test_unified_teaching_agent.py::TestFocusPattern -v
```

## Editing Prompts

### Workflow

1. **Edit the markdown file** - e.g., `src/backend/app/prompts/agent/mode_practice.md`
2. **Add/update placeholders** - Use `{placeholder_name}` syntax
3. **Update agent code** - Pass new variables to `render_prompt()` if needed
4. **Add tests** - Verify the expected content appears in assembled prompts
5. **Run tests** - `python -m pytest tests/unit/test_unified_teaching_agent.py`

### Adding a New Variable

1. Add placeholder to template: `{new_variable}`

2. Compute value in agent:

   ```python
   def _get_new_variable(self) -> str:
       return "computed value"
   ```

3. Pass to render:

   ```python
   return render_prompt(
       template,
       new_variable=self._get_new_variable(),
   )
   ```

4. Test:

   ```python
   def test_new_variable_in_prompt(self, sample_lesson):
       agent = UnifiedTeachingAgent(lesson=sample_lesson, mode="practice")
       prompt = agent.build_system_prompt()
       assert "computed value" in prompt
   ```

## LLM-as-Judge Evaluation System

Beyond unit testing prompt content, we use an **LLM-as-judge evaluation system** to validate agent behavior end-to-end. This catches regressions that static prompt tests cannot detect.

### Architecture

```text
tests/
├── evaluation/           # LLM-as-judge system
│   ├── cli.py            # CLI entry point
│   ├── judge.py          # vLLM client for Qwen 2.5-7B
│   ├── rubrics.py        # 6 rubric dimensions with prompts
│   ├── runner.py         # Test execution + judging
│   └── report.py         # Result formatting
└── golden/               # Test cases from documented issues
    ├── schema.json       # Test case JSON schema
    ├── practice_mode/    # Practice mode test cases
    └── help_mode/        # Help mode test cases
```

### Rubric Dimensions

We evaluate agent behavior across 6 dimensions derived from real user issues:

| Dimension              | Description                                              | Pass Criteria                                |
| ---------------------- | -------------------------------------------------------- | -------------------------------------------- |
| `language_choice`      | Practice starts English, help responds in student's lang | First speak() call uses correct language     |
| `tool_usage`           | Always calls speak(), never fallback                     | speak() tool called, no auto-synthesis       |
| `output_cleanliness`   | No markdown/URLs in spoken text                          | Text contains no `[links]` or `http://`      |
| `confusion_recovery`   | Asks clarification when input ambiguous                  | Offers alternatives for homophones           |
| `persona_consistency`  | Redirects personal questions to student                  | Doesn't invent personal details              |
| `curriculum_alignment` | Vocabulary within lesson level                           | Uses only vocab from current/prior lessons   |

### Test Case Structure

Test cases are stored in `tests/golden/` as JSON:

```json
{
  "id": "lc-practice-001",
  "dimension": "language_choice",
  "mode": "practice",
  "source": "documented_issue",
  "issue_ref": "Issue 1",
  "user_input": "I'm ready to practice!",
  "context": {
    "lesson_number": 7,
    "exchange_count": 0
  },
  "expected_behavior": "Practice mode should start in English",
  "expected_pass": true
}
```

### Running Evaluations

```bash
# Run all dimensions
python -m tests.evaluation.cli --dimension all

# Run specific dimension
python -m tests.evaluation.cli --dimension language_choice --verbose

# Save results to file
python -m tests.evaluation.cli --dimension all --output results.json
```

### Evaluation Results (2026-01-05 Baseline)

| Dimension            | Pass Rate  |
| -------------------- | ---------- |
| language_choice      | 70%        |
| tool_usage           | 83%        |
| output_cleanliness   | 100%       |
| confusion_recovery   | 75%        |
| persona_consistency  | 100%       |
| curriculum_alignment | 50%        |
| **Overall**          | **79.3%**  |

Target pass rate: 80%

### Iterative Prompt Improvement Workflow

1. **Identify failing dimension** - Run evaluation, find lowest pass rate
2. **Analyze failures** - Run with `--verbose` to see judge reasoning
3. **Edit prompt** - Modify relevant `.md` file in `prompts/agent/`
4. **Re-evaluate** - Run evaluation again
5. **Commit if improved** - Only commit if pass rate increases

### Bias Mitigation

The evaluation system uses several techniques to reduce judge bias:

- **Position swap for A/B** - When comparing prompts, swap order and check consistency
- **Chain-of-thought** - Require judge to explain before scoring
- **Evidence-based** - Judge must cite specific text from agent response

### Key Learnings

1. **Phonetic awareness for STT errors** - Agent needs explicit guidance about homophones (marry/Mary/merry)
2. **Language rules are mode-specific** - Practice mode starts English, help mode responds in student's language
3. **Tool usage requires positive examples** - Show correct flow, not just "don't do X"
4. **Persona consistency needs explicit redirect** - "I'm an AI, but tell me about YOUR family"

## Related Files

- [unified_teaching_agent.py](../src/backend/app/agents/unified_teaching_agent.py) - Agent implementation
- [loader.py](../src/backend/app/prompts/loader.py) - Template loading utilities
- [test_unified_teaching_agent.py](../tests/unit/test_unified_teaching_agent.py) - Agent tests
- [general-agent-conversation-workflow.md](general-agent-conversation-workflow.md) - End-to-end workflow
- [rubrics.py](../tests/evaluation/rubrics.py) - LLM-as-judge rubric definitions
- [functional-issues.md](../planning/completed/functional-issues.md) - Original issue documentation
