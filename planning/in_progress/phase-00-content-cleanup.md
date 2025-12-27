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

## Task 0.1: Audit All Lessons for Missing Sections

Before normalization, audit all 25 lessons to identify any MISSING sections (not just structural issues).

### Expected Sections Checklist (per lesson)
- [ ] `## **Memorize Vocabulary**` (or equivalent vocabulary section)
- [ ] Vocabulary table with English/Spanish columns
- [ ] `## **Practice Pattern 1**` with Q: and A: templates
- [ ] `## **Practice Pattern 2**` (most lessons have 2 patterns)
- [ ] Pattern examples (Q: ... A: ...)
- [ ] `## **Use the Patterns**` writing exercise
- [ ] `## **Evaluate Your Progress**` with "I can:" criteria

### Audit Script: `src/tools/audit_lessons.py`

Create a script that:
1. Reads each of the 25 lesson files
2. Checks for presence of each expected section
3. Reports missing sections per lesson
4. Flags lessons needing manual content recovery

### Audit Output Format
```
Lesson 01: MISSING - Memorize Vocabulary header, Practice Pattern 2
Lesson 02: OK
Lesson 05: MISSING - Use the Patterns (corrupted), Pattern examples incomplete
...
```

---

## Task 0.2: Define Standard Structure

All lessons should follow this structure:

```markdown
#### <span id="..."></span>**LESSON N**
# **Lesson Title**
**OBJETIVO: ...**

# Personal Study

## **Study the Principle of Learning: [Title]**
*[Principle content in italics]*

## **Ponder**
- Question 1
- Question 2

## **Memorize Vocabulary**
| English | Spanish |
|---------|---------|
| word1   | palabra1 |

### **Verbs**
| verb1 | verbo1 |

### **Nouns**
| noun1 | sustantivo1 |

### **Adjectives**
| adj1 | adjetivo1 |

## **Practice Pattern 1**
Q: [template] A: [template]

### **Examples**
Q: example1 A: answer1

## **Practice Pattern 2**
Q: [template] A: [template]

### **Examples**
Q: example1 A: answer1

## **Use the Patterns**
[Writing exercise instructions]

## **Additional Activities**
[Link to online resources]

## **Act in Faith to Practice English Daily**
[Quote]

# Conversation Group
[Rest of lesson...]

## **Evaluate Your Progress**
I can:
- Criterion 1
- Criterion 2
```

**Key changes**:
- Category sections (`Verbs`, `Nouns`, `Adjectives`) become `### ` (h3) subsections INSIDE `## **Memorize Vocabulary**`
- Consistent header levels throughout
- Pattern examples get explicit `### **Examples**` headers

---

## Task 0.3: Re-extract Corrupted Lessons

### Corrupted Lessons (OCR artifacts)
- lesson-05.md (lines 103-105)
- lesson-06.md
- lesson-07.md (lines 133-136 - Unicode garbage)
- lesson-09.md (lines 131-140)
- lesson-10.md (lines 126-132)

### Process
1. Re-run marker on `content/raw/ec1/books/englishconnect_1_para_los_alumnos.pdf`
2. Re-chunk to extract specific lessons
3. Save as `lesson-XX-v2.md` for comparison
4. If still corrupted, flag for manual text extraction from PDF

### Files
- Input: `content/raw/ec1/books/englishconnect_1_para_los_alumnos.pdf`
- Tool: `src/tools/marker_mcp/server.py` (convert_pdf)
- Tool: `src/tools/chunk_by_lesson.py`
- Output: `content/refined/ec1/books/englishconnect_1_para_los_alumnos/lessons/lesson-XX-v2.md`

---

## Task 0.4: Normalize Each Lesson

### Lesson-by-Lesson Changes

| Lesson | Issues | Fix |
|--------|--------|-----|
| 01 | No `Memorize Vocabulary` header; vocabulary under "Part 1" | Add `## **Memorize Vocabulary**` section, restructure |
| 02 | `## **Adjectives**` and `## **Nouns**` are separate sections | Move inside `Memorize Vocabulary`, change to `### ` |
| 03 | `## **Nouns 1**`, `## **Nouns 2**`, `#### **Days**` outside | Move inside, normalize headers |
| 04 | `#### **Verbs**` inside but wrong level | Change to `### **Verbs**` |
| 05 | Corrupted tables + structure issues | Re-extract, then normalize |
| 06 | Corrupted + `## **Numbers**`, `## **Nouns**` outside | Re-extract, then normalize |
| 07 | Corrupted (Unicode garbage) + structure issues | Re-extract, then normalize |
| 08 | `## **Nouns**` outside | Move inside |
| 09 | Corrupted + `#### **Nouns**`, `#### **Adjectives**` | Re-extract, then normalize |
| 10 | Corrupted + `## **Nouns**`, `## **Verbs**` outside | Re-extract, then normalize |
| 11-24 | Various category sections outside | Move inside Memorize Vocabulary |
| 25 | Review lesson - different structure | Keep as-is or create custom handling |

### Transformation Script

Create `src/tools/normalize_lessons.py` that:
1. Reads each lesson markdown
2. Identifies vocabulary sections outside `Memorize Vocabulary`
3. Restructures by:
   - Moving category tables inside Memorize Vocabulary
   - Converting `## **Category**` to `### **Category**`
   - Converting `#### **Category**` to `### **Category**`
4. Validates the result has expected sections
5. Writes normalized version (or reports issues for manual review)

---

## Task 0.5: Update Ingestion Script

After markdown normalization, update `src/tools/content_ingestion.py`:

1. **_extract_vocabulary()**:
   - Expand regex to capture content until next `## ` that isn't a subsection
   - Or: after normalization, the simple regex should work

2. **_guess_category()**:
   - Look for `### **Category**` headers within captured section
   - Associate words with the category header that precedes them

3. **Handle Lesson 1**:
   - Either normalize its structure OR add special case handling

4. **Handle Lesson 25**:
   - Review lesson - may need special handling or explicit skip

---

## Task 0.6: Verify Database Alignment

1. Re-run ingestion: `python src/tools/content_ingestion.py`
2. Query database to verify:
   - All 25 lessons have vocabulary items
   - Category fields are populated (verb, noun, adjective)
   - Patterns are extracted with examples
   - Evaluation criteria are captured

### Verification Query
```sql
SELECT l.lesson_number, l.title,
       COUNT(DISTINCT v.id) as vocab_count,
       COUNT(DISTINCT CASE WHEN v.category IS NOT NULL THEN v.id END) as categorized_vocab,
       COUNT(DISTINCT p.id) as pattern_count
FROM lessons l
LEFT JOIN vocabulary_items v ON v.lesson_id = l.id
LEFT JOIN qa_patterns p ON p.lesson_id = l.id
GROUP BY l.lesson_number, l.title
ORDER BY l.lesson_number;
```

---

## Execution Order

1. [ ] Create `audit_lessons.py` script
2. [ ] Run audit on all 25 lessons - generate missing sections report
3. [ ] Create `normalize_lessons.py` script
4. [ ] Re-extract corrupted lessons (5, 6, 7, 9, 10) via marker
5. [ ] For lessons with missing sections: recover content from PDF or flag for manual entry
6. [ ] Run normalization on all 25 lessons
7. [ ] Manual review of any lessons that couldn't be auto-normalized
8. [ ] Test ingestion script on normalized files
9. [ ] Fix ingestion script if needed
10. [ ] Full re-ingestion to database
11. [ ] Verify with database queries

---

## Files to Modify

### Markdown Files (normalize structure)
- `content/refined/ec1/books/englishconnect_1_para_los_alumnos/lessons/lesson-01.md` through `lesson-25.md`

### New Scripts
- `src/tools/audit_lessons.py` - Check all lessons for missing sections
- `src/tools/normalize_lessons.py` - Markdown normalization

### Existing Scripts (may need updates)
- `src/tools/content_ingestion.py` - If normalization doesn't fully solve parsing

---

## Success Criteria

- [ ] Audit report generated showing all missing sections
- [ ] All missing sections recovered or documented as intentionally absent
- [ ] All 25 lessons normalized to standard structure
- [ ] All 25 lessons have vocabulary items in database
- [ ] Vocabulary items have category field populated where applicable
- [ ] Q&A patterns extracted for all lessons with patterns
- [ ] No garbage Unicode or corrupted content in markdown files
- [ ] Ingestion script runs without errors
- [ ] Database verification query shows expected counts per lesson
