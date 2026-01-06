# Backlog: STT Confidence-Based Clarification

**Priority**: Medium
**Dependencies**: STT service API update
**Related**: confusion_recovery evaluation dimension, functional-issues.md

## Context

STT (faster-whisper) transcribes Spanish-accented English with errors, especially for homophones (Mary/merry/marry) and code-switching. Currently the agent relies on prompt-based ambiguity detection, but could benefit from STT confidence signals.

## Problem

Agent has no visibility into transcription confidence. Low-confidence transcriptions are treated the same as high-confidence ones, leading to misunderstandings.

## Proposed Solution

### 1. Expose confidence scores from STT

- faster-whisper provides word-level confidence
- Add `confidence` field to STT response
- Add `low_confidence_words` array for words below threshold (e.g., 0.7)

### 2. Include confidence in agent context

- Pass low-confidence words to agent in user message metadata
- Update prompt: "The following words had low transcription confidence: {words}"

### 3. Agent behavior with low confidence

- If low-confidence word matches vocabulary item phonetically, offer alternatives
- If overall confidence low, ask for repetition: "I didn't catch that clearly. Could you repeat?"
- Avoid confidently misinterpreting garbled input

### 4. Confidence threshold tuning

- Start with 0.7 threshold
- Evaluate with LLM-as-judge for false positive/negative rate
- Adjust based on user experience

## Example Flow

```text
User says: "Tell me about Mary" (name in lesson)
STT transcribes: "merry" (confidence: 0.65)
Agent receives: {"text": "merry", "low_confidence_words": ["merry"]}
Agent responds: "Did you mean 'Mary' the name we're learning, or 'merry' meaning happy?"
```

## Implementation Dependencies

- STT service API update (expose confidence)
- Conversation router update (pass confidence to agent)
- Prompt update (include confidence guidance)
- Evaluation test cases for clarification behavior
