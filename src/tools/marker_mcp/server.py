#!/usr/bin/env python3
"""Marker MCP Server for PDF to Markdown conversion."""

import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Lazy load marker to avoid slow startup
_converter = None


def get_converter():
    """Lazy-load the PDF converter (marker models are heavy)."""
    global _converter
    if _converter is None:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        _converter = PdfConverter(artifact_dict=create_model_dict())
    return _converter


mcp = FastMCP("marker")


@mcp.tool()
def convert_pdf(file_path: str, output_dir: str) -> str:
    """Convert a single PDF to markdown.

    Args:
        file_path: Absolute path to the PDF file
        output_dir: Directory where markdown and images will be saved

    Returns:
        JSON string with conversion result summary
    """
    try:
        from marker.output import text_from_rendered

        file_path = Path(file_path)
        output_dir = Path(output_dir)

        if not file_path.exists():
            return json.dumps({
                "status": "error",
                "error": f"File not found: {file_path}"
            })

        if not file_path.suffix.lower() == ".pdf":
            return json.dumps({
                "status": "error",
                "error": f"Not a PDF file: {file_path}"
            })

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Convert PDF
        converter = get_converter()
        rendered = converter(str(file_path))
        text, metadata, images = text_from_rendered(rendered)

        # Save markdown
        md_filename = file_path.stem + ".md"
        md_path = output_dir / md_filename
        md_path.write_text(text, encoding="utf-8")

        # Save images if any
        image_count = 0
        if images:
            images_dir = output_dir / (file_path.stem + "_images")
            images_dir.mkdir(exist_ok=True)
            for img_name, img_data in images.items():
                img_path = images_dir / img_name
                if isinstance(img_data, bytes):
                    img_path.write_bytes(img_data)
                else:
                    img_data.save(str(img_path))
                image_count += 1

        return json.dumps({
            "status": "success",
            "input_file": str(file_path),
            "output_file": str(md_path),
            "image_count": image_count,
            "markdown_length": len(text)
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
            "input_file": str(file_path)
        })


@mcp.tool()
def batch_convert(input_dir: str, output_dir: str) -> str:
    """Convert all PDFs in a directory to markdown.

    Args:
        input_dir: Directory containing PDF files (searches recursively)
        output_dir: Base directory for markdown output (preserves folder structure)

    Returns:
        JSON string with batch conversion summary
    """
    try:
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        if not input_dir.exists():
            return json.dumps({
                "status": "error",
                "error": f"Input directory not found: {input_dir}"
            })

        # Find all PDFs
        pdf_files = list(input_dir.rglob("*.pdf")) + list(input_dir.rglob("*.PDF"))

        if not pdf_files:
            return json.dumps({
                "status": "error",
                "error": f"No PDF files found in: {input_dir}"
            })

        results = {
            "status": "success",
            "total": len(pdf_files),
            "converted": 0,
            "failed": [],
            "output_dir": str(output_dir)
        }

        for pdf_path in pdf_files:
            # Preserve relative folder structure
            rel_path = pdf_path.relative_to(input_dir)
            target_dir = output_dir / rel_path.parent

            result = json.loads(convert_pdf(str(pdf_path), str(target_dir)))

            if result["status"] == "success":
                results["converted"] += 1
            else:
                results["failed"].append({
                    "file": str(pdf_path),
                    "error": result.get("error", "Unknown error")
                })

        if results["failed"]:
            results["status"] = "partial"

        return json.dumps(results)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        })


if __name__ == "__main__":
    mcp.run()
