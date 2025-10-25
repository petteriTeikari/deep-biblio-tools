"""Paper processing API endpoints."""

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

# Import from other tools
try:
    from paper_processor import PaperProcessor
except ImportError:
    PaperProcessor = None

router = APIRouter()


@router.post("/process/extract")
async def extract_paper(
    file: UploadFile = File(...),
    format: str = Query("markdown", description="Output format"),
    sections: list[str] | None = Query(None, description="Sections to extract"),
) -> dict[str, Any]:
    """Extract content from a paper."""
    if not PaperProcessor:
        raise HTTPException(
            status_code=503, detail="Paper processor not available"
        )

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # Process paper
        processor = PaperProcessor()
        paper = processor.process_file(tmp_path, sections=sections)

        # Format output
        if format == "markdown":
            output = paper.to_markdown()
        elif format == "json":
            output = paper.to_dict()
        elif format == "latex":
            output = paper.to_latex()
        else:
            output = paper.to_text()

        return {
            "title": paper.title,
            "authors": paper.authors,
            "word_count": paper.word_count,
            "sections": len(paper.sections),
            "references": len(paper.references),
            "content": output,
            "format": format,
        }

    finally:
        # Cleanup
        tmp_path.unlink()


@router.post("/process/batch")
async def batch_process(
    files: list[UploadFile] = File(...),
    format: str = Query("markdown", description="Output format"),
) -> dict[str, Any]:
    """Process multiple papers."""
    results = []

    for file in files:
        try:
            result = await extract_paper(file, format)
            results.append(
                {
                    "filename": file.filename,
                    "status": "success",
                    "result": result,
                }
            )
        except Exception as e:
            results.append(
                {"filename": file.filename, "status": "error", "error": str(e)}
            )

    return {
        "processed": len(results),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "results": results,
    }


@router.get("/process/info")
async def get_processor_info() -> dict[str, Any]:
    """Get information about the paper processor."""
    return {
        "available": PaperProcessor is not None,
        "supported_formats": ["html", "pdf", "latex"],
        "output_formats": ["markdown", "json", "latex", "text"],
        "extractable_sections": [
            "abstract",
            "introduction",
            "methodology",
            "results",
            "discussion",
            "conclusion",
            "references",
        ],
    }
