#!/usr/bin/env python3
"""Audit lesson markdown files for missing or corrupted sections.

Usage:
    python src/tools/audit_lessons.py [--lessons-dir PATH]
"""

import argparse
import re
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class SectionCheck:
    """Result of checking for a section."""
    name: str
    found: bool
    pattern: str
    notes: str = ""


@dataclass
class LessonAudit:
    """Audit result for a single lesson."""
    lesson_number: int
    filename: str
    sections: list[SectionCheck] = field(default_factory=list)
    corrupted_content: list[str] = field(default_factory=list)

    @property
    def missing_sections(self) -> list[str]:
        return [s.name for s in self.sections if not s.found]

    @property
    def has_issues(self) -> bool:
        return len(self.missing_sections) > 0 or len(self.corrupted_content) > 0

    def status(self) -> str:
        if not self.has_issues:
            return "OK"

        issues = []
        if self.missing_sections:
            issues.append(f"MISSING: {', '.join(self.missing_sections)}")
        if self.corrupted_content:
            issues.append(f"CORRUPTED: {', '.join(self.corrupted_content)}")
        return "; ".join(issues)


class LessonAuditor:
    """Audit lesson markdown files for expected sections."""

    # Expected sections with regex patterns (flexible header levels for EC1+EC2)
    SECTION_PATTERNS = [
        ("Memorize Vocabulary", r"#{1,4}\s*\*{0,2}(Memorize Vocabulary|Part 1:.*vocabulario)", "Main vocabulary section"),
        ("Vocabulary Table", r"\|[^|]+\|[^|]+\|", "At least one vocabulary table row"),
        ("Practice Pattern 1", r"#{1,4}\s*\*{0,2}Practice Pattern 1", "First practice pattern"),
        ("Practice Pattern 2", r"#{1,4}\s*\*{0,2}Practice Pattern 2", "Second practice pattern (optional for some lessons)"),
        ("Pattern Q&A Template", r"Q:\s*.+?\s*A:", "Pattern Q: ... A: template"),
        ("Pattern Examples", r"(#{1,4}\s*\*{0,2}Examples|#{1,4}\s*\*?Example)", "Examples section or Example header"),
        ("Use the Patterns", r"#{1,4}\s*\*{0,2}Use the Patterns", "Writing exercise section"),
        ("Evaluate Your Progress", r"#{1,4}\s*\*{0,2}Evaluate Your Progress", "Evaluation criteria section"),
        ("I can statements", r"I can:", "Evaluation 'I can:' statements"),
    ]

    # Patterns that indicate corrupted content (be specific to avoid false positives)
    CORRUPTION_PATTERNS = [
        ("Cyrillic/Greek in tables", r"\|[^|\n]*[ЫΔΣΙΩΘΞΛΠΦΨЫШБع][^|\n]*\|"),  # Cyrillic/Greek/Arabic chars
        ("LaTeX remnants", r"\$\\overline"),  # LaTeX formatting
        ("Garbled table row", r"\|[^|\n]{0,3}\|[^|\n]{0,3}\|[^|\n]{0,3}\|[^|\n]{0,3}\|"),  # Many tiny cells
    ]

    def __init__(self, lessons_dir: Path):
        self.lessons_dir = lessons_dir

    def audit_lesson(self, lesson_path: Path) -> LessonAudit:
        """Audit a single lesson file."""
        # Extract lesson number from filename
        match = re.search(r"lesson-(\d+)\.md", lesson_path.name)
        lesson_number = int(match.group(1)) if match else 0

        content = lesson_path.read_text(encoding="utf-8")

        audit = LessonAudit(
            lesson_number=lesson_number,
            filename=lesson_path.name,
        )

        # Check for expected sections
        for name, pattern, description in self.SECTION_PATTERNS:
            found = bool(re.search(pattern, content, re.IGNORECASE | re.MULTILINE))
            audit.sections.append(SectionCheck(
                name=name,
                found=found,
                pattern=pattern,
                notes=description,
            ))

        # Check for corrupted content
        for name, pattern in self.CORRUPTION_PATTERNS:
            if re.search(pattern, content):
                # Find the line numbers with corruption
                lines_with_issue = []
                for i, line in enumerate(content.split('\n'), 1):
                    if re.search(pattern, line):
                        lines_with_issue.append(str(i))
                audit.corrupted_content.append(f"{name} (lines {', '.join(lines_with_issue[:3])})")

        return audit

    def audit_all(self) -> list[LessonAudit]:
        """Audit all lesson files in the directory."""
        lesson_files = sorted(self.lessons_dir.glob("lesson-*.md"))
        return [self.audit_lesson(f) for f in lesson_files]

    def generate_report(self, audits: list[LessonAudit]) -> str:
        """Generate a human-readable audit report."""
        lines = [
            "=" * 70,
            "LESSON CONTENT AUDIT REPORT",
            "=" * 70,
            "",
        ]

        # Summary
        ok_count = sum(1 for a in audits if not a.has_issues)
        issue_count = len(audits) - ok_count

        lines.extend([
            f"Total lessons: {len(audits)}",
            f"OK: {ok_count}",
            f"With issues: {issue_count}",
            "",
            "-" * 70,
            "DETAILED RESULTS",
            "-" * 70,
            "",
        ])

        # Per-lesson results
        for audit in audits:
            status = audit.status()
            lines.append(f"Lesson {audit.lesson_number:02d}: {status}")

            if audit.has_issues:
                # Show details for problem lessons
                if audit.missing_sections:
                    for section in audit.sections:
                        if not section.found:
                            lines.append(f"    - Missing: {section.name}")
                if audit.corrupted_content:
                    for corruption in audit.corrupted_content:
                        lines.append(f"    - Corrupted: {corruption}")
                lines.append("")

        # Section coverage summary
        lines.extend([
            "",
            "-" * 70,
            "SECTION COVERAGE SUMMARY",
            "-" * 70,
            "",
        ])

        for name, _, description in self.SECTION_PATTERNS:
            found_count = sum(1 for a in audits for s in a.sections if s.name == name and s.found)
            lines.append(f"{name}: {found_count}/{len(audits)} lessons")

        # Lessons needing manual intervention
        manual_review = [a for a in audits if a.corrupted_content]
        if manual_review:
            lines.extend([
                "",
                "-" * 70,
                "LESSONS NEEDING MANUAL REVIEW (corrupted content)",
                "-" * 70,
                "",
            ])
            for audit in manual_review:
                lines.append(f"  - lesson-{audit.lesson_number:02d}.md: {', '.join(audit.corrupted_content)}")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit lesson markdown files")
    parser.add_argument(
        "--lessons-dir",
        default="content/refined/ec1/books/englishconnect_1_para_los_alumnos/lessons",
        help="Path to lessons directory",
    )
    parser.add_argument(
        "--output",
        help="Output file for report (default: stdout)",
    )
    args = parser.parse_args()

    lessons_dir = Path(args.lessons_dir)
    if not lessons_dir.exists():
        print(f"Error: Lessons directory not found: {lessons_dir}")
        return 1

    auditor = LessonAuditor(lessons_dir)
    audits = auditor.audit_all()
    report = auditor.generate_report(audits)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report written to: {args.output}")
    else:
        print(report)

    # Return exit code based on issues found
    return 1 if any(a.has_issues for a in audits) else 0


if __name__ == "__main__":
    exit(main())
