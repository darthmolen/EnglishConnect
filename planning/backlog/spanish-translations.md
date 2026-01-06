# Backlog: Spanish Translations for Patterns

**Priority**: Medium
**Dependencies**: None
**Related**: Content ingestion, PatternsView component

## Context

The EC1 books have all content in Spanish, but pattern Q&A templates and examples are in English only. Adding Spanish translations would help students with exploration and comprehension.

## Problem

Students can see patterns like:
- Q: What is your name?
- A: My name is _____.

But have no Spanish translation to help them understand what they're practicing.

## Proposed Solution

1. Add `question_template_es` and `answer_template_es` fields to the QAPattern model
2. Update content ingestion to extract Spanish translations (if available in source PDFs)
3. Update PatternsView to display Spanish under each Q/A line in parentheses
4. Example display:
   ```
   Q: What is your name?
      (¿Cómo te llamas?)
   A: My name is _____.
      (Mi nombre es _____.)
   ```

## Scope

- Database migration to add new columns
- Content ingestion regex updates
- Frontend component updates
- Manual review/entry if translations not in source PDFs

## Notes

Enhances comprehension but not blocking core functionality.
