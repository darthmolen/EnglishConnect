# Phase 0: Content Cleanup - Normalize 25 Lesson Markdown Files

## Status: COMPLETED (2025-12-27)

## Problem Summary

The lesson markdown files have structural inconsistencies causing the ingestion script to miss vocabulary and patterns:

1. **Lesson 1**: No `## **Memorize Vocabulary**` section (vocabulary is under "Part 1")
2. **Lessons 2-24**: Category sections (`## **Verbs**`, `## **Nouns**`, etc.) are OUTSIDE the Memorize Vocabulary section, so they're not captured
3. **Header inconsistencies**: Mix of `##`, `###`, `####` for the same type of content
4. **Corrupted content**: Lessons 5, 6, 7, 9, 10 have OCR artifacts (garbage Unicode in tables)
5. **Lesson 25**: Review lesson with different structure

## Approach

**Normalize markdown files, keep parser simple**

Standardize all 25 markdown files to follow a consistent structure, then the existing simple parser will work.

---

## Completed Tasks

### Task 0.1: Audit All Lessons for Missing Sections ✓

Created `src/tools/audit_lessons.py` script that:
- Reads each of the 25 lesson files
- Checks for presence of each expected section
- Reports missing sections per lesson
- Flags lessons needing manual content recovery

### Task 0.2: Define Standard Structure ✓

Established consistent structure:
- `## **Memorize Vocabulary**` as main section
- `### **Category**` as subsections (Verbs, Nouns, Adjectives, etc.)
- Consistent header levels throughout

### Task 0.3: Re-extract Corrupted Lessons ✓

Fixed lessons 5, 6, 7, 9, 10, 11 with OCR artifacts and structural issues.

### Task 0.4: Normalize Each Lesson ✓

- Fixed Lesson 1 structure (added `## **Memorize Vocabulary**` section)
- Added category headers (`### **Pronouns**`, `### **Verbs**`, etc.) to all 24 lessons
- Moved category sections inside Memorize Vocabulary where needed

### Task 0.5: Update Ingestion Script ✓

Updated `src/tools/content_ingestion.py`:
- Added `CATEGORY_PATTERNS` class attribute with 22 category patterns
- Created `_guess_category_at_pos()` method for position-based category detection
- Fixed issue where short words like "at", "on", "in" were getting NULL categories
- Result: **470/470 vocabulary items now have categories (100%)**

### Task 0.6: Verify Database Alignment ✓

- Re-ran ingestion successfully
- All 25 lessons have vocabulary items with categories
- All patterns extracted correctly

---

## Files Modified

### Markdown Files (normalized structure)
- `content/refined/ec1/books/englishconnect_1_para_los_alumnos/lessons/lesson-01.md` through `lesson-24.md`

### Scripts Created
- `src/tools/audit_lessons.py` - Audit script for checking lesson structure
- `src/tools/normalize_lessons.py` - Markdown normalization

### Scripts Updated
- `src/tools/content_ingestion.py` - Position-based category detection

---

## Success Criteria - All Met ✓

- [x] Audit report generated showing all missing sections
- [x] All missing sections recovered or documented as intentionally absent
- [x] All 25 lessons normalized to standard structure
- [x] All 25 lessons have vocabulary items in database
- [x] Vocabulary items have category field populated (470/470 = 100%)
- [x] Q&A patterns extracted for all lessons with patterns
- [x] No garbage Unicode or corrupted content in markdown files
- [x] Ingestion script runs without errors
- [x] Database verification shows expected counts per lesson
