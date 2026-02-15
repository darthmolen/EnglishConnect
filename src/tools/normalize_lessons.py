#!/usr/bin/env python3
"""Normalize lesson markdown files to a consistent structure.

This script ensures vocabulary category sections (Verbs, Nouns, Adjectives, etc.)
are properly nested inside the Memorize Vocabulary section with consistent header levels.

Usage:
    python src/tools/normalize_lessons.py [--lessons-dir PATH] [--dry-run]
"""

import argparse
import re
from pathlib import Path


# Category headers to normalize (pattern, normalized name)
CATEGORY_PATTERNS = [
    (r"##?\s*#{0,2}\s*\*{0,2}(Verbs?(?:\s*/\s*Verbs?\s*\+?\s*ing)?)\*{0,2}", "Verbs"),
    (r"##?\s*#{0,2}\s*\*{0,2}(Nouns?\s*\d*)\*{0,2}", None),  # Keep original name (Nouns, Nouns 1, Nouns 2)
    (r"##?\s*#{0,2}\s*\*{0,2}(Adjectives?)\*{0,2}", "Adjectives"),
    (r"##?\s*#{0,2}\s*\*{0,2}(Adverbs?)\*{0,2}", "Adverbs"),
    (r"##?\s*#{0,2}\s*\*{0,2}(Prepositions?)\*{0,2}", "Prepositions"),
    (r"##?\s*#{0,2}\s*\*{0,2}(Pronouns?)\*{0,2}", "Pronouns"),
    (r"##?\s*#{0,2}\s*\*{0,2}(Days?)\*{0,2}", "Days"),
    (r"##?\s*#{0,2}\s*\*{0,2}(Time)\*{0,2}", "Time"),
    (r"##?\s*#{0,2}\s*\*{0,2}(Numbers?)\*{0,2}", "Numbers"),
    (r"##?\s*#{0,2}\s*\*{0,2}(Price)\*{0,2}", "Price"),
]


def find_section_boundaries(content: str) -> dict:
    """Find the start positions of key sections in the markdown."""
    boundaries = {}

    # Find Memorize Vocabulary section (## to #### header levels)
    vocab_match = re.search(r"^#{1,4}\s*\*{0,2}Memorize Vocabulary\*{0,2}", content, re.MULTILINE | re.IGNORECASE)
    if vocab_match:
        boundaries["vocab_start"] = vocab_match.start()

    # Find Practice Pattern 1 section (end of vocabulary area)
    pattern1_match = re.search(r"^#{1,4}\s*\*{0,2}Practice Pattern 1\*{0,2}", content, re.MULTILINE | re.IGNORECASE)
    if pattern1_match:
        boundaries["pattern1_start"] = pattern1_match.start()

    return boundaries


def normalize_lesson(content: str, lesson_num: int) -> tuple[str, list[str]]:
    """Normalize a single lesson's markdown content.

    Returns:
        tuple of (normalized_content, list of changes made)
    """
    changes = []

    # Skip lessons without standard vocabulary+pattern structure
    if "Memorize Vocabulary" not in content and "Practice Pattern" not in content:
        changes.append("Skipping (no Memorize Vocabulary or Practice Pattern sections)")
        return content, changes

    boundaries = find_section_boundaries(content)

    if "vocab_start" not in boundaries:
        changes.append("WARNING: No 'Memorize Vocabulary' section found")
        return content, changes

    if "pattern1_start" not in boundaries:
        changes.append("WARNING: No 'Practice Pattern 1' section found")
        return content, changes

    # Process content in the vocabulary area (between Memorize Vocabulary and Practice Pattern 1)
    vocab_start = boundaries["vocab_start"]
    pattern1_start = boundaries["pattern1_start"]

    # Extract the vocabulary section
    vocab_section = content[vocab_start:pattern1_start]
    before_vocab = content[:vocab_start]
    after_vocab = content[pattern1_start:]

    # Normalize category headers within the vocabulary section
    normalized_vocab = vocab_section

    for pattern, normalized_name in CATEGORY_PATTERNS:
        def replace_header(match):
            original = match.group(0)
            category_name = match.group(1).strip()

            # Use normalized name if provided, otherwise keep original
            name = normalized_name if normalized_name else category_name

            # Already correct format?
            if original.startswith("### **") and original.endswith("**"):
                return original

            changes.append(f"Normalized header: '{original}' -> '### **{name}**'")
            return f"### **{name}**"

        normalized_vocab = re.sub(pattern, replace_header, normalized_vocab, flags=re.MULTILINE | re.IGNORECASE)

    # Reconstruct content
    normalized_content = before_vocab + normalized_vocab + after_vocab

    if not changes:
        changes.append("No changes needed")

    return normalized_content, changes


def normalize_all_lessons(lessons_dir: Path, dry_run: bool = False) -> dict:
    """Normalize all lesson files in the directory.

    Returns:
        dict mapping lesson number to list of changes
    """
    results = {}

    lesson_files = sorted(lessons_dir.glob("lesson-*.md"))

    for lesson_file in lesson_files:
        # Extract lesson number
        match = re.search(r"lesson-(\d+)\.md", lesson_file.name)
        if not match:
            continue

        lesson_num = int(match.group(1))

        # Read content
        content = lesson_file.read_text(encoding="utf-8")

        # Normalize
        normalized_content, changes = normalize_lesson(content, lesson_num)

        results[lesson_num] = changes

        # Write if not dry run and changes were made
        if not dry_run and content != normalized_content:
            lesson_file.write_text(normalized_content, encoding="utf-8")

    return results


def main():
    parser = argparse.ArgumentParser(description="Normalize lesson markdown files")
    parser.add_argument(
        "--lessons-dir",
        default="content/refined/ec1/books/englishconnect_1_para_los_alumnos/lessons",
        help="Path to lessons directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )
    args = parser.parse_args()

    lessons_dir = Path(args.lessons_dir)
    if not lessons_dir.exists():
        print(f"Error: Lessons directory not found: {lessons_dir}")
        return 1

    print("=" * 70)
    print("LESSON NORMALIZATION" + (" (DRY RUN)" if args.dry_run else ""))
    print("=" * 70)
    print()

    results = normalize_all_lessons(lessons_dir, args.dry_run)

    # Print results
    changes_count = 0
    for lesson_num in sorted(results.keys()):
        changes = results[lesson_num]
        if changes and changes[0] != "No changes needed":
            print(f"Lesson {lesson_num:02d}:")
            for change in changes:
                print(f"  - {change}")
            changes_count += 1
        else:
            print(f"Lesson {lesson_num:02d}: OK")

    print()
    print("-" * 70)
    print(f"Total lessons processed: {len(results)}")
    print(f"Lessons with changes: {changes_count}")

    if args.dry_run:
        print("\n(Dry run - no files were modified)")

    return 0


if __name__ == "__main__":
    exit(main())
