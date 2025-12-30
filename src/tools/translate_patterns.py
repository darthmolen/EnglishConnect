#!/usr/bin/env python3
"""Translate Q&A patterns to Spanish using local Qwen2.5 via vLLM.

This script reads lesson markdown files, extracts Q:/A: lines that don't have
Spanish translations, translates them using the local LLM, and injects Q_es:/A_es:
lines below each original line.

Usage:
    python src/tools/translate_patterns.py                    # Translate all lessons
    python src/tools/translate_patterns.py --lesson 1         # Single lesson
    python src/tools/translate_patterns.py --dry-run          # Preview changes
    python src/tools/translate_patterns.py --lessons-dir PATH # Custom directory
"""

import argparse
import asyncio
import re
import sys
from pathlib import Path

from openai import AsyncOpenAI

# Default paths
DEFAULT_LESSONS_DIR = Path(__file__).parent.parent.parent / "content/refined/ec1/books/englishconnect_1_para_los_alumnos/lessons"
VLLM_BASE_URL = "http://localhost:8004/v1"
VLLM_MODEL = None  # Auto-detect from server

# Regex patterns
Q_LINE_PATTERN = re.compile(r"^(Q:\s*)(.+)$")
A_LINE_PATTERN = re.compile(r"^(A:\s*)(.+)$")
Q_ES_LINE_PATTERN = re.compile(r"^Q_es:\s*")
A_ES_LINE_PATTERN = re.compile(r"^A_es:\s*")

# Placeholder patterns to preserve
PLACEHOLDER_PATTERN = re.compile(r"(\(\*[\w\s]+\*?\)|\[[\w\s]+\])")

# Mapping of English placeholder terms to Spanish
PLACEHOLDER_TRANSLATIONS = {
    "noun": "sustantivo",
    "noun 1": "sustantivo 1",
    "noun 2": "sustantivo 2",
    "verb": "verbo",
    "verb past": "verbo pasado",
    "adjective": "adjetivo",
    "adverb": "adverbio",
    "day": "día",
    "time": "hora",
    "number": "número",
    "price": "precio",
    "preposition": "preposición",
    "answer": "respuesta",
}


def translate_placeholder(placeholder: str) -> str:
    """Translate a single placeholder from English to Spanish.

    Examples:
        (*noun*) -> (*sustantivo*)
        (*noun 1*) -> (*sustantivo 1*)
        [answer] -> [respuesta]
        (*verb* + ing) -> (*verbo* + ing)
    """
    # Handle (*...*) format
    if placeholder.startswith("(*") and "*)" in placeholder:
        # Extract content between (* and *)
        inner = placeholder[2:placeholder.rindex("*)")]
        suffix = placeholder[placeholder.rindex("*)") + 2:]  # Get anything after *)

        # Check for numbered placeholders like "noun 1"
        for eng, esp in PLACEHOLDER_TRANSLATIONS.items():
            if inner == eng or inner == eng + "*":
                # Handle case where * is inside
                if inner.endswith("*"):
                    return f"(*{esp}*){suffix}"
                return f"(*{esp}*){suffix}"

        # If no direct match, return as-is
        return placeholder

    # Handle [...] format
    if placeholder.startswith("[") and placeholder.endswith("]"):
        inner = placeholder[1:-1]
        if inner in PLACEHOLDER_TRANSLATIONS:
            return f"[{PLACEHOLDER_TRANSLATIONS[inner]}]"
        return placeholder

    return placeholder


def translate_placeholders_in_text(text: str) -> str:
    """Replace English placeholders with Spanish equivalents in text."""
    def replacer(match: re.Match) -> str:
        return translate_placeholder(match.group(0))

    return PLACEHOLDER_PATTERN.sub(replacer, text)


def extract_placeholders(text: str) -> list[str]:
    """Extract all placeholders from text."""
    return PLACEHOLDER_PATTERN.findall(text)


def validate_placeholders(original: str, translated: str) -> bool:
    """Check that all placeholders from original appear in translation."""
    original_placeholders = extract_placeholders(original)
    translated_placeholders = extract_placeholders(translated)
    return set(original_placeholders) == set(translated_placeholders)


async def translate_text(client: AsyncOpenAI, english: str, model: str, max_retries: int = 3) -> str:
    """Translate English text to Spanish, preserving placeholders.

    After translation, English placeholders are converted to Spanish equivalents:
    (*noun*) -> (*sustantivo*), [answer] -> [respuesta], etc.
    """
    prompt = f"""Translate this English sentence to natural conversational Spanish.
Preserve any placeholders like (*noun*), (*verb*), [answer] exactly as they appear.
Only output the Spanish translation, nothing else.

English: {english}
Spanish:"""

    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=256,
            )
            translation = response.choices[0].message.content.strip()

            # Remove any "Spanish:" prefix if the model added it
            if translation.lower().startswith("spanish:"):
                translation = translation[8:].strip()

            # Validate placeholders
            if validate_placeholders(english, translation):
                # Translate English placeholders to Spanish equivalents
                translation = translate_placeholders_in_text(translation)
                return translation

            # If placeholders missing, try again with stricter prompt
            if attempt < max_retries - 1:
                print(f"    Warning: Placeholders missing, retrying ({attempt + 1}/{max_retries})...")
                prompt = f"""Translate this English sentence to Spanish.
CRITICAL: You MUST preserve these exact placeholders: {extract_placeholders(english)}
Do not translate or modify placeholders. Only translate the English words.
Output ONLY the Spanish translation.

English: {english}
Spanish:"""
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"    Error: {e}, retrying ({attempt + 1}/{max_retries})...")
                await asyncio.sleep(1)
            else:
                raise

    # Even on best-effort, translate placeholders
    return translate_placeholders_in_text(translation)


def find_pattern_section_ranges(lines: list[str]) -> list[tuple[int, int]]:
    """Find line ranges for Practice Pattern sections (including Examples).

    Returns list of (start_line, end_line) tuples for each pattern section.
    """
    ranges = []
    pattern_header = re.compile(r"^##\s*\*\*Practice Pattern", re.IGNORECASE)
    next_section = re.compile(r"^##\s+(?!\*\*Examples)")  # ## header that isn't Examples

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if pattern_header.match(line):
            start = i
            # Find end of this pattern section (next ## header or end of file)
            end = len(lines)
            for j in range(i + 1, len(lines)):
                if next_section.match(lines[j].strip()):
                    end = j
                    break
            ranges.append((start, end))
            i = end
        else:
            i += 1

    return ranges


def find_lines_to_translate(lines: list[str]) -> list[tuple[int, str, str, str]]:
    """Find Q:/A: lines that need translation.

    Only looks within Practice Pattern sections (not Activity dialogue sections).
    Returns list of (line_index, prefix_type, prefix, text) tuples.
    prefix_type is 'Q' or 'A'.
    """
    to_translate = []

    # Find which lines are within Practice Pattern sections
    pattern_ranges = find_pattern_section_ranges(lines)

    def is_in_pattern_section(line_idx: int) -> bool:
        return any(start <= line_idx < end for start, end in pattern_ranges)

    for i, line in enumerate(lines):
        # Skip lines outside Practice Pattern sections
        if not is_in_pattern_section(i):
            continue

        line_stripped = line.strip()

        # Check for Q: line
        q_match = Q_LINE_PATTERN.match(line_stripped)
        if q_match:
            # Check if next non-empty line is Q_es:
            has_translation = False
            for j in range(i + 1, min(i + 3, len(lines))):
                next_line = lines[j].strip()
                if next_line:
                    has_translation = Q_ES_LINE_PATTERN.match(next_line) is not None
                    break

            if not has_translation:
                to_translate.append((i, 'Q', q_match.group(1), q_match.group(2)))
            continue

        # Check for A: line
        a_match = A_LINE_PATTERN.match(line_stripped)
        if a_match:
            # Check if next non-empty line is A_es:
            has_translation = False
            for j in range(i + 1, min(i + 3, len(lines))):
                next_line = lines[j].strip()
                if next_line:
                    has_translation = A_ES_LINE_PATTERN.match(next_line) is not None
                    break

            if not has_translation:
                to_translate.append((i, 'A', a_match.group(1), a_match.group(2)))

    return to_translate


def inject_translations(lines: list[str], translations: dict[int, tuple[str, str]]) -> list[str]:
    """Insert translation lines after original Q:/A: lines.

    translations is a dict of {line_index: (prefix_type, spanish_text)}
    """
    result = []
    sorted_indices = sorted(translations.keys())

    for i, line in enumerate(lines):
        result.append(line)

        if i in translations:
            prefix_type, spanish = translations[i]
            # Determine indentation from original line
            indent = len(line) - len(line.lstrip())
            indent_str = line[:indent] if indent > 0 else ""

            # Create translation line
            es_prefix = f"{prefix_type}_es: "
            es_line = f"{indent_str}{es_prefix}{spanish}\n"
            result.append(es_line)

    return result


def strip_existing_translations(lines: list[str]) -> list[str]:
    """Remove all Q_es: and A_es: lines from the file."""
    result = []
    for line in lines:
        stripped = line.strip()
        if not (Q_ES_LINE_PATTERN.match(stripped) or A_ES_LINE_PATTERN.match(stripped)):
            result.append(line)
    return result


async def process_lesson_file(
    filepath: Path,
    client: AsyncOpenAI,
    model: str,
    dry_run: bool = False,
    verbose: bool = True,
    force: bool = False,
) -> int:
    """Process a single lesson file, return count of translations added."""
    if verbose:
        print(f"\nProcessing: {filepath.name}")

    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    # Handle files without trailing newlines
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'

    # If force mode, strip existing translations first
    if force:
        original_count = len(lines)
        lines = strip_existing_translations(lines)
        removed = original_count - len(lines)
        if verbose and removed > 0:
            print(f"  Removed {removed} existing translation lines")

    # Find lines needing translation
    to_translate = find_lines_to_translate([l.rstrip('\n') for l in lines])

    if not to_translate:
        if verbose:
            print("  No translations needed (already translated or no Q:/A: lines)")
        return 0

    if verbose:
        print(f"  Found {len(to_translate)} lines to translate")

    # Translate each line
    translations = {}
    for line_idx, prefix_type, prefix, english_text in to_translate:
        if verbose:
            print(f"  Translating: {prefix}{english_text}")

        if dry_run:
            spanish = f"[SPANISH: {english_text}]"
        else:
            spanish = await translate_text(client, english_text, model)

        if verbose:
            print(f"    -> {prefix_type}_es: {spanish}")

        translations[line_idx] = (prefix_type, spanish)

    # Inject translations
    new_lines = inject_translations(lines, translations)
    new_content = "".join(new_lines)

    if not dry_run:
        filepath.write_text(new_content, encoding="utf-8")
        if verbose:
            print(f"  Saved {len(translations)} translations")
    else:
        if verbose:
            print(f"  [DRY RUN] Would save {len(translations)} translations")

    return len(translations)


async def main():
    parser = argparse.ArgumentParser(
        description="Translate Q&A patterns to Spanish using local Qwen2.5 LLM"
    )
    parser.add_argument(
        "--lessons-dir",
        type=Path,
        default=DEFAULT_LESSONS_DIR,
        help="Directory containing lesson markdown files",
    )
    parser.add_argument(
        "--lesson",
        type=int,
        help="Process only this lesson number",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove existing translations and re-translate all lines",
    )
    args = parser.parse_args()

    # Validate lessons directory
    if not args.lessons_dir.exists():
        print(f"Error: Lessons directory not found: {args.lessons_dir}", file=sys.stderr)
        sys.exit(1)

    # Find lesson files
    if args.lesson:
        lesson_files = list(args.lessons_dir.glob(f"lesson-{args.lesson:02d}.md"))
        if not lesson_files:
            # Try without leading zero
            lesson_files = list(args.lessons_dir.glob(f"lesson-{args.lesson}.md"))
    else:
        lesson_files = sorted(args.lessons_dir.glob("lesson-*.md"))

    if not lesson_files:
        print("Error: No lesson files found", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(lesson_files)} lesson file(s)")
    if args.dry_run:
        print("[DRY RUN MODE - no files will be modified]")

    # Initialize OpenAI client for vLLM
    client = AsyncOpenAI(
        base_url=VLLM_BASE_URL,
        api_key="local",  # vLLM doesn't require auth
    )

    # Test connection and get model name
    model_name = VLLM_MODEL
    if not args.dry_run:
        try:
            models_response = await client.models.list()
            if models_response.data:
                model_name = models_response.data[0].id
                print(f"Connected to vLLM at {VLLM_BASE_URL}")
                print(f"Using model: {model_name}")
            else:
                print("Error: No models available on vLLM server", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"Error: Cannot connect to vLLM at {VLLM_BASE_URL}: {e}", file=sys.stderr)
            print("Make sure the local LLM server is running: ./start.sh llm", file=sys.stderr)
            sys.exit(1)
    else:
        model_name = "dry-run-model"

    # Process files
    total_translations = 0
    for filepath in lesson_files:
        count = await process_lesson_file(
            filepath,
            client,
            model_name,
            dry_run=args.dry_run,
            verbose=not args.quiet,
            force=args.force,
        )
        total_translations += count

    print(f"\nTotal translations: {total_translations}")
    if args.dry_run:
        print("[DRY RUN] No files were modified")


if __name__ == "__main__":
    asyncio.run(main())
