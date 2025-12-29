# Bug Fix: Incorrect Pattern Conjugation

**Date**: 2025-12-29
**Status**: Complete

## Problem Statement

When the teacher agent gives examples of patterns, it incorrectly conjugates and adds unnecessary words.

**User prompt**: "Dígame un ejemplo en español y inglés de Patrón 1"

**Pattern 1 (Lesson 7)**:
- Q: Tell me about your (*noun*).
- A: They have (*adjective*) (*noun*).

**LLM Response** (incorrect):
```
Q: "Tell me about your dog."
A: "They have a big dog."
```

**Expected Response**:
```
Q: "Tell me about your dog."
A: "They have a dog."
```

## Root Cause

The LLM was taking the pattern template literally, forcing an adjective ("big") when the template shows `(*adjective*)` as a placeholder. The placeholders in patterns are meant to show the structure, not mandate every element.

Additionally, the LLM wasn't given guidance on:
1. Pronoun agreement (He/She/It/They based on subject)
2. When adjectives are optional vs required
3. Keeping examples simple without over-elaborating

## Solution

Added "Pattern Usage Rules" directive to the teacher prompts:

### File: `src/backend/app/prompts/teacher/phase_patterns.md`

```markdown
## Pattern Usage Rules

- Match pronouns to the subject: your brother→He, your sister→She, your parents→They, your dog→It
- Placeholders like (*adjective*) are OPTIONAL - only include when natural
- "Tell me about your dog" → "They have a dog" (not "They have a big dog")
- "Tell me about your brother" → "He has black hair" (adjective describes characteristic)
- Keep examples simple and grammatically correct - don't force extra words
```

### File: `src/backend/app/prompts/teacher/focus_patterns.md`

Added reminder:
```markdown
Remember: Match pronouns to subject, placeholders like (*adjective*) are optional.
```

## Token Cost

Minimal - approximately 80 tokens added to the system prompt. This is a reasonable trade-off for correct grammar in pattern examples.

## Testing

This is a prompt engineering fix. Manual verification required:

1. Restart backend to pick up prompt changes
2. Navigate to Lesson 7 > Patterns
3. Ask: "Dígame un ejemplo de Patrón 1"
4. Verify the example uses correct pronoun and doesn't force unnecessary adjectives

## Notes

- GPT-4o-mini tends to be literal with templates; explicit rules help
- This pattern of over-applying placeholders may occur elsewhere - monitor for similar issues
- Future consideration: Include curriculum examples in the prompt to demonstrate correct usage
