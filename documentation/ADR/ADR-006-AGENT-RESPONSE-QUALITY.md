# ADR-006: Agent Response Quality Evaluation

**Status**: Accepted
**Date**: 2026-01-05
**Decision Makers**: Project Team

## Context

The UnifiedTeachingAgent (ADR-005) produces natural language responses that are difficult to validate with traditional unit tests. We observed several behavioral issues that only manifested in real conversations:

1. **Language choice errors**: Practice mode sometimes started in Spanish instead of English
2. **Tool usage failures**: Agent occasionally returned text without calling speak() tool
3. **Output contamination**: Markdown syntax and URLs leaked into TTS-spoken text
4. **Ambiguity mishandling**: Agent guessed meanings instead of asking for clarification
5. **Persona inconsistency**: Agent invented personal details when asked personal questions
6. **Curriculum drift**: Agent used vocabulary beyond the student's current lesson level

These issues shared a common characteristic: they required semantic understanding to detect, not just string matching or schema validation.

### Alternatives Considered

**1. Manual Testing**
- Pros: High accuracy, catches nuanced issues
- Cons: Doesn't scale, inconsistent coverage, no regression detection

**2. Rule-Based Assertions**
- Pros: Fast, deterministic
- Cons: Brittle, can't catch semantic issues (e.g., "Did the agent's tone match the student's language?")

**3. Human Evaluation Panel**
- Pros: Gold standard accuracy
- Cons: Expensive, slow, not suitable for CI/CD

**4. LLM-as-Judge (Chosen)**
- Pros: Scales to CI/CD, catches semantic issues, correlates with human judgment
- Cons: Requires calibration, has known biases, costs tokens

## Decision

**Use LLM-as-judge evaluation with dimension-specific rubrics to validate agent behavior.**

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

### Judge Model Selection

**Local Qwen 2.5-7B via vLLM** for bulk evaluation:
- Runs on existing GPU infrastructure
- No per-token cost for iteration
- Fast enough for CI/CD (~2s per judgment)

**Claude spot-checks** for calibration:
- Validate rubric quality against stronger model
- Catch judge bias or prompt issues

### Rubric Dimensions

Each dimension maps to a documented behavioral issue:

| Dimension | Issue | Pass Criteria |
|-----------|-------|---------------|
| `language_choice` | Issue 1 | Practice starts English, help responds in student's language |
| `tool_usage` | Issue 0 | Always calls speak(), never auto-synthesis fallback |
| `output_cleanliness` | Issue 2 | No markdown/URLs in spoken text |
| `confusion_recovery` | Issue 3 | Asks clarification for ambiguous input |
| `persona_consistency` | Issue 5 | Redirects personal questions to student |
| `curriculum_alignment` | New | Vocabulary within lesson level |

### Evaluation Protocol

1. **Direct scoring** for objective criteria (tool_usage, output_cleanliness)
2. **Chain-of-thought** required before all judgments
3. **Evidence-based** - judge must cite specific text from response
4. **Position swap** for A/B prompt comparisons (bias mitigation)

### Golden Dataset

Test cases derived from:
- Documented issues in `planning/completed/functional-issues.md`
- Synthetic cases for edge coverage
- Target: 30-50 cases covering all dimensions

## Rationale

### Why LLM-as-Judge Over Alternatives

From evaluation research (MT-Bench, G-Eval):

| Approach | Semantic Detection | Scales to CI/CD | Cost |
|----------|-------------------|-----------------|------|
| Manual testing | Yes | No | High (human time) |
| Rule-based | No | Yes | Low |
| Human panel | Yes | No | Very high |
| LLM-as-judge | Yes | Yes | Medium (tokens) |

LLM-as-judge is the only approach that catches semantic issues AND scales to automated pipelines.

### Why Dimension-Specific Rubrics

Generic "rate this response 1-5" prompts produce unreliable scores. Research shows:
- Rubrics reduce variance by 40-60%
- Domain-specific criteria improve correlation with human judgment
- Explicit level descriptions enable consistent scoring

Our rubrics include:
- Clear pass/fail criteria
- Examples of passing and failing behavior
- Required evidence format

### Why Local Model Over API

| Factor | Local (Qwen 2.5-7B) | API (Claude/GPT-4) |
|--------|---------------------|-------------------|
| Cost per judgment | ~$0 (GPU only) | ~$0.01-0.05 |
| Iteration speed | Unlimited | Rate limited |
| Privacy | Data stays local | Sent to provider |
| Quality | Good for rubric-based | Better for open-ended |

For rubric-based evaluation with clear criteria, local models perform comparably to larger APIs while enabling unlimited iteration.

### Why 80% Target Pass Rate

- 100% is unrealistic for semantic evaluation (LLM variability)
- 80% catches regressions while allowing for edge cases
- Below 80% indicates prompt issues requiring attention

## Consequences

### Positive

- **Regression detection**: CI/CD can catch behavioral issues before merge
- **Iterative improvement**: Run eval → edit prompt → re-eval loop
- **Documented quality**: Pass rates provide objective quality metrics
- **Scalable**: No human bottleneck for testing

### Negative

- **Judge bias**: Position bias, length bias, self-enhancement bias
- **Calibration overhead**: Must validate judge accuracy periodically
- **GPU requirement**: Local vLLM needs CUDA-capable hardware
- **Not deterministic**: Same input may get different judgments

### Mitigations

- Position swap for A/B comparisons
- Chain-of-thought before scoring
- Evidence citation requirement
- Claude spot-checks for calibration
- Multiple runs for flaky cases

## Results

Baseline evaluation (2026-01-05):

| Dimension | Pass Rate |
|-----------|-----------|
| language_choice | 70% |
| tool_usage | 83% |
| output_cleanliness | 100% |
| confusion_recovery | 75% |
| persona_consistency | 100% |
| curriculum_alignment | 50% |
| **Overall** | **79.3%** |

Prompt improvements from 65.5% → 79.3% through:
1. Adding explicit language rules for practice mode
2. Adding phonetic awareness for STT homophones
3. Adding persona redirect instructions

## Files Created

- `tests/evaluation/` - Evaluation system
- `tests/golden/` - Test case dataset
- `tests/evaluation/rubrics.py` - Rubric definitions

## References

- [Judging LLM-as-a-Judge (Zheng et al., 2023)](https://arxiv.org/abs/2306.05685)
- [G-Eval: NLG Evaluation using GPT-4 (Liu et al., 2023)](https://arxiv.org/abs/2303.16634)
- [functional-issues.md](../../planning/completed/functional-issues.md) - Source issues
- [agent-context-engineering.md](../agent-context-engineering.md) - Implementation details
- [ADR-005](ADR-005-UNIFIED-TEACHING-AGENT.md) - Agent architecture this evaluates
