#!/usr/bin/env python3
"""Generate QR codes for EnglishConnect deep links.

Usage:
    # Single lesson
    python generate_qr.py --course ec1 --lesson 5 --section vocabulary

    # All lessons for a course (one QR per lesson, links to principle)
    python generate_qr.py --course ec2 --all

    # Custom base URL
    python generate_qr.py --course ec1 --lesson 3 --base-url https://englishconnect.vozloop.com

    # Just a raw URL
    python generate_qr.py --url "https://example.com/whatever"
"""

import argparse
import sys
from pathlib import Path

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer

DEFAULT_BASE = "https://englishconnect.vozloop.com"
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "content" / "qr-codes"

VALID_COURSES = ["ec1", "ec2"]
VALID_SECTIONS = ["principle", "vocabulary", "patterns", "examples", "practice", "evaluate"]
MAX_LESSON = 25


def build_url(base: str, course: str, lesson: int | None = None, section: str | None = None) -> str:
    params = [f"c={course}"]
    if lesson is not None:
        params.append(f"l={lesson}")
    if section is not None:
        params.append(f"s={section}")
    return f"{base}?{'&'.join(params)}"


def generate_qr(url: str, output_path: Path) -> None:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(image_factory=StyledPilImage, module_drawer=RoundedModuleDrawer())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path))
    print(f"  {output_path.name}  →  {url}")


def main():
    parser = argparse.ArgumentParser(description="Generate QR codes for EnglishConnect deep links")
    parser.add_argument("--course", "-c", choices=VALID_COURSES, help="Course ID (ec1 or ec2)")
    parser.add_argument("--lesson", "-l", type=int, help="Lesson number (1-25)")
    parser.add_argument("--section", "-s", choices=VALID_SECTIONS, help="Section name")
    parser.add_argument("--all", action="store_true", help="Generate QR for every lesson in the course")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help=f"Base URL (default: {DEFAULT_BASE})")
    parser.add_argument("--url", help="Raw URL (ignores --course/--lesson/--section)")
    parser.add_argument("--output-dir", "-o", type=Path, default=OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    if args.url:
        name = args.url.split("//")[-1].replace("/", "_").replace("?", "_").replace("&", "_")[:60]
        out = args.output_dir / f"{name}.png"
        generate_qr(args.url, out)
        return

    if not args.course:
        parser.error("--course is required (or use --url for a raw URL)")

    if args.all:
        print(f"Generating QR codes for {args.course.upper()} lessons 1-{MAX_LESSON}:")
        for lesson_num in range(1, MAX_LESSON + 1):
            url = build_url(args.base_url, args.course, lesson_num)
            out = args.output_dir / args.course / f"{args.course}-lesson{lesson_num:02d}.png"
            generate_qr(url, out)
        print(f"\nDone. {MAX_LESSON} QR codes saved to {args.output_dir / args.course}/")
    else:
        if args.lesson is not None and not (1 <= args.lesson <= MAX_LESSON):
            parser.error(f"--lesson must be between 1 and {MAX_LESSON}")
        url = build_url(args.base_url, args.course, args.lesson, args.section)
        parts = [args.course]
        if args.lesson is not None:
            parts.append(f"lesson{args.lesson:02d}")
        if args.section:
            parts.append(args.section)
        out = args.output_dir / args.course / f"{'-'.join(parts)}.png"
        generate_qr(url, out)


if __name__ == "__main__":
    main()
