"""Format conversion API endpoints."""

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

# Import from other tools
try:
    from format_converter import FormatConverter
except ImportError:
    FormatConverter = None

router = APIRouter()


@router.post("/convert")
async def convert_format(
    file: UploadFile = File(...),
    to_format: str = Query(..., description="Target format"),
    citation_style: str = Query("author-year", description="Citation style"),
    template: str | None = Query(None, description="Template to use"),
) -> dict[str, Any]:
    """Convert document between formats."""
    if not FormatConverter:
        raise HTTPException(
            status_code=503, detail="Format converter not available"
        )

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    # Create output file
    output_ext = {
        "markdown": ".md",
        "latex": ".tex",
        "html": ".html",
        "docx": ".docx",
        "rst": ".rst",
    }.get(to_format, f".{to_format}")

    output_path = tmp_path.with_suffix(output_ext)

    try:
        # Convert file
        converter = FormatConverter()
        converter.convert_file(
            tmp_path,
            output_path,
            to_format,
            template=template,
            citation_style=citation_style,
        )

        # Read converted content
        if to_format == "docx":
            # Binary format
            with open(output_path, "rb") as f:
                converted_content = f.read()
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            # Text format
            converted_content = output_path.read_text(encoding="utf-8")
            content_type = "text/plain"

        return {
            "original_format": converter.analyzer.detect_format(tmp_path),
            "target_format": to_format,
            "content": converted_content,
            "content_type": content_type,
            "filename": f"{tmp_path.stem}{output_ext}",
        }

    finally:
        # Cleanup
        tmp_path.unlink()
        if output_path.exists():
            output_path.unlink()


@router.post("/convert/extract-bib")
async def extract_bibliography(
    file: UploadFile = File(...),
    format: str = Query("bibtex", description="Bibliography format"),
) -> dict[str, Any]:
    """Extract bibliography from document."""
    if not FormatConverter:
        raise HTTPException(
            status_code=503, detail="Format converter not available"
        )

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # Extract bibliography
        converter = FormatConverter()
        references = converter.extract_bibliography(tmp_path)

        # Format bibliography
        if format == "json":
            output = references
        else:
            output = converter.format_bibliography(references, format)

        return {
            "reference_count": len(references),
            "format": format,
            "bibliography": output,
        }

    finally:
        # Cleanup
        tmp_path.unlink()


@router.get("/convert/formats")
async def get_supported_formats() -> dict[str, Any]:
    """Get supported conversion formats."""
    return {
        "input_formats": [
            {"name": "Markdown", "extensions": [".md", ".markdown"]},
            {"name": "LaTeX", "extensions": [".tex"]},
            {"name": "HTML", "extensions": [".html", ".htm"]},
            {"name": "Word", "extensions": [".docx"]},
            {"name": "reStructuredText", "extensions": [".rst"]},
        ],
        "output_formats": [
            {"name": "markdown", "extension": ".md"},
            {"name": "latex", "extension": ".tex"},
            {"name": "html", "extension": ".html"},
            {"name": "docx", "extension": ".docx"},
            {"name": "pdf", "extension": ".pdf"},
        ],
        "citation_styles": ["author-year", "numeric", "alpha"],
        "templates": ["ieee", "acm", "springer", "elsevier"],
    }
