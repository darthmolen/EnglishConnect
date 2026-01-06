# Phase 8: Unified Agent Enrichment

**Status**: Planning
**Architecture**: [agent-architecture.md](../../documentation/agent-architecture.md)
**ADR**: [ADR-005 Revalidation](../../documentation/ADR/ADR-005-UNIFIED-TEACHING-AGENT.md#revalidation-2026-01-05)
**Started**: 2026-01-05

## Goal

Enrich the UnifiedTeachingAgent with pedagogical patterns identified from context-engineering research while preserving the single-agent architecture from ADR-005.

## Deliverables

1. Silent error tracking in practice mode
2. Structured output metadata schema
3. Native language interference awareness
4. Enhanced curriculum format (deferred - separate phase if needed)

## Tasks

### Task 1: Silent Error Tracking in Practice Mode

**Files**:
- `src/backend/app/prompts/agent/mode_practice.md`

**Changes**:

Add new section to practice mode prompt:

```markdown
## Error Handling (Silent Tracking)

When the student makes an error during practice:

1. **DO NOT explicitly correct** - Overcorrection kills fluency
2. **Model the correct form naturally** in your response
3. **Track the error mentally** - Include in your structured output

### Implicit Correction Examples

Student says: "I go to church with family"
❌ WRONG: "Actually, you should say 'with MY family'"
✅ CORRECT: speak("That's great that you go to church with your family! Do you go every Sunday?")
   → Your response naturally models "your family" (correct possessive)

Student says: "Yesterday I go to store"
❌ WRONG: "The past tense of 'go' is 'went'"
✅ CORRECT: speak("Oh nice! I went to the store yesterday too. What did you buy?")
   → Your response naturally models "went" and "yesterday"

### When to Break the Rule

Only explicitly correct if:
- Same error type occurs 3+ times in session
- Student explicitly asks "Was that correct?"
- Error causes communication breakdown
```

**Verification**:
- [ ] Run existing integration tests (should still pass)
- [ ] Add test: agent models correct form when error detected
- [ ] Add test: agent doesn't explicitly correct minor errors

---

### Task 2: Structured Output Metadata

**Files**:
- `src/backend/app/prompts/agent/mode_practice.md`
- `src/backend/app/prompts/agent/mode_help.md`
- `src/backend/app/routers/conversation.py` (parse output)
- `src/backend/app/schemas/conversation.py` (response schema)

**Changes**:

Add structured output section to both mode prompts:

```markdown
## Structured Output (Required)

After your response, include a YAML block with session metadata:

\`\`\`yaml
# session_metadata
vocab_used: ["family", "church"]        # Lesson vocab in your response
errors_observed:                         # Practice mode only
  - type: "article_omission"
    utterance: "with family"
    modeled: "your family"
implicit_modeling: true                  # Did you model correct form?
engagement: "high"                       # high/medium/low based on student
correction_explicit: false               # Did you explicitly correct?
\`\`\`

This metadata helps track progress without parsing your natural language.
```

**Schema Updates**:

```python
# src/backend/app/schemas/conversation.py
class ErrorObservation(BaseModel):
    type: str  # article_omission, verb_tense, adjective_placement
    utterance: str
    modeled: Optional[str] = None

class SessionMetadata(BaseModel):
    vocab_used: list[str] = []
    errors_observed: list[ErrorObservation] = []
    implicit_modeling: bool = False
    engagement: Literal["high", "medium", "low"] = "high"
    correction_explicit: bool = False
```

**Verification**:
- [ ] Add parsing logic to extract YAML from agent response
- [ ] Add schema validation for metadata
- [ ] Test: metadata extracted correctly from practice response
- [ ] Test: metadata extracted correctly from help response

---

### Task 3: Native Language Interference Awareness

**Files**:
- `src/backend/app/prompts/agent/base.md` (add native language context)
- `src/backend/app/agents/unified_teaching_agent.py` (pass interference patterns)
- `src/backend/app/prompts/agent/mode_practice.md` (use patterns)

**Changes**:

Add to base prompt:

```markdown
## Student's Native Language: {native_language}

### Common Interference Patterns

{native_language_patterns}

Use this knowledge to:
- Anticipate likely errors before they happen
- Model correct forms proactively in your examples
- Understand WHY the student makes certain errors
```

**Default Spanish patterns**:

```python
SPANISH_INTERFERENCE_PATTERNS = """
Spanish speakers commonly:
- **Omit articles/possessives**: "I go with family" (should be "my family")
- **Place adjectives after nouns**: "house big" (should be "big house")
- **Confuse ser/estar mapping**: Different from English "to be"
- **Use false cognates**: "actually" ≠ "actualmente" (currently)
- **Omit subject pronouns**: "Is tall" (should be "He is tall")
"""
```

**Implementation in agent**:

```python
def _get_base_prompt(self) -> str:
    template = load_prompt("agent/base.md")

    # Default to Spanish patterns (expandable later)
    native_patterns = SPANISH_INTERFERENCE_PATTERNS

    return render_prompt(
        template,
        native_language="Spanish",
        native_language_patterns=native_patterns,
        # ... existing params
    )
```

**Verification**:
- [ ] Base prompt includes native language section
- [ ] Agent response shows awareness of Spanish patterns
- [ ] Test: agent proactively models possessives when teaching family vocab

---

### Task 4: Enhanced Curriculum Format (Deferred)

**Decision**: Defer to separate phase. Current content works. Enriching curriculum YAML (connection_prompt, native_language_note) requires:
- Content ingestion updates
- Database schema changes (if storing in DB)
- Manual content review

This is lower ROI than the prompt-level changes above. Track in backlog.

---

## Test Plan

### Unit Tests

```python
# tests/unit/agents/test_unified_teaching_agent.py

def test_practice_prompt_includes_error_handling_section():
    """Verify practice prompt has silent error tracking guidance."""
    agent = UnifiedTeachingAgent(lesson, mode="practice")
    prompt = agent.build_system_prompt()
    assert "Error Handling (Silent Tracking)" in prompt
    assert "DO NOT explicitly correct" in prompt

def test_base_prompt_includes_native_language():
    """Verify base prompt includes native language patterns."""
    agent = UnifiedTeachingAgent(lesson, mode="practice")
    prompt = agent.build_system_prompt()
    assert "Native Language: Spanish" in prompt
    assert "Omit articles/possessives" in prompt
```

### Integration Tests

```python
# tests/integration/agents/test_enriched_behavior.py

async def test_agent_models_correct_form_on_error():
    """Agent should model correct form without explicit correction."""
    # Student says "I go with family"
    # Agent response should contain "your family" or "my family"
    pass

async def test_structured_metadata_in_response():
    """Agent response should include parseable session metadata."""
    # Parse YAML block from response
    # Validate against SessionMetadata schema
    pass
```

## Acceptance Criteria

- [ ] Practice mode prompt includes silent error tracking section
- [ ] Both modes include structured output schema
- [ ] Base prompt includes native language interference patterns
- [ ] Agent responses include parseable metadata YAML
- [ ] All existing tests still pass
- [ ] New integration tests validate enriched behavior

## Rollback Plan

All changes are prompt-only (Tasks 1-3). Rollback by reverting prompt files:
- `git checkout HEAD~1 -- src/backend/app/prompts/agent/`

Schema changes (Task 2) require removing new fields from response handling.

## Dependencies

None. All changes build on existing infrastructure.

## Notes

- Keep prompts within reasonable length (< 3K tokens per mode)
- Monitor for regression in core behaviors (TTS calls, tool usage)
- Structured output parsing should be lenient (graceful degradation if YAML missing)
