#!/usr/bin/env python3
"""Chunk a markdown file into separate lesson files."""

import re
import sys
from pathlib import Path


def chunk_by_lesson(md_path: Path, output_dir: Path):
    """Split markdown into separate files by lesson/unit headers."""
    content = md_path.read_text(encoding="utf-8")

    # Find where appendix/vocabulary/answer key sections start (to exclude them)
    appendix_patterns = [
        r'###\s+\*{0,2}EnglishConnect \d+:\s*Vocabulary',  # Workbook vocabulary index
        r'###\s+\*{0,2}ANSWER KEY',
    ]
    content_end = len(content)
    for ap in appendix_patterns:
        match = re.search(ap, content, re.IGNORECASE)
        if match and match.start() < content_end:
            content_end = match.start()
            print(f"  Excluding appendix starting at position {content_end}")

    # Only process content before appendix
    main_content = content[:content_end]

    # Try multiple patterns for different book formats
    patterns = [
        # Student book: <span id="page-X-0"></span>**LESSON X** or **UNIT X:**
        r'((?:####\s+)?<span id="page-\d+-0"></span>\*\*(LESSON \d+|UNIT \d+[^*]*)\*\*)',
        # Workbook: ### **ENGLISHCONNECT 1 LESSON X:** or ### ENGLISHCONNECT 1 LESSON X:
        # Also matches ### **LESSON X:** without ENGLISHCONNECT prefix
        r'^(###\s+\*{0,2}(?:ENGLISHCONNECT \d+\s+)?(LESSON \d+)[:\s][^*\n]*\*{0,2})',
    ]

    matches = []
    for pattern in patterns:
        matches = list(re.finditer(pattern, main_content, re.IGNORECASE | re.MULTILINE))
        if len(matches) > 5:  # Found a good match
            print(f"  Using pattern: {pattern[:50]}...")
            break

    # Filter out vocabulary index entries (usually very short sections at the end)
    # by checking if matches are reasonably spaced apart
    if matches:
        filtered = [matches[0]]
        for m in matches[1:]:
            # Only keep if at least 500 chars from previous match
            if m.start() - filtered[-1].start() > 500:
                filtered.append(m)
        matches = filtered

    if not matches:
        print(f"No lesson/unit markers found in {md_path}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract front matter (everything before first lesson/unit)
    front_matter_end = matches[0].start()
    if front_matter_end > 0:
        front_matter = content[:front_matter_end].strip()
        if front_matter:
            (output_dir / "00-front-matter.md").write_text(front_matter, encoding="utf-8")
            print(f"  Created: 00-front-matter.md")

    # Extract each section
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else content_end

        section_content = main_content[start:end].strip()
        header_text = match.group(2).strip()

        # Create filename from header
        # "LESSON 1" -> "lesson-01"
        # "UNIT 1: INTRODUCTION" -> "unit-01-introduction"
        if header_text.upper().startswith("LESSON"):
            num = re.search(r'\d+', header_text).group()
            filename = f"lesson-{int(num):02d}.md"
        elif header_text.upper().startswith("UNIT"):
            num_match = re.search(r'\d+', header_text)
            num = num_match.group() if num_match else str(i)
            # Get unit name after colon if present
            name_match = re.search(r':\s*(.+)', header_text)
            name = name_match.group(1).strip().lower().replace(' ', '-') if name_match else ""
            filename = f"unit-{int(num):02d}{'-' + name if name else ''}.md"
        else:
            filename = f"section-{i:02d}.md"

        (output_dir / filename).write_text(section_content, encoding="utf-8")
        print(f"  Created: {filename}")

    print(f"\nChunked into {len(matches) + (1 if front_matter_end > 0 else 0)} files")


def main():
    if len(sys.argv) < 2:
        print("Usage: chunk_by_lesson.py <markdown_file> [output_dir]")
        sys.exit(1)

    md_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else md_path.parent / "chunked"

    if not md_path.exists():
        print(f"File not found: {md_path}")
        sys.exit(1)

    print(f"Chunking {md_path.name}...")
    chunk_by_lesson(md_path, output_dir)


if __name__ == "__main__":
    main()
