"""Literature review API endpoints."""

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

# Import from other tools
try:
    from literature_reviewer import LiteratureReviewer, Summarizer
except ImportError:
    Summarizer = None
    LiteratureReviewer = None

router = APIRouter()


@router.post("/review/summarize")
async def summarize_paper(
    file: UploadFile = File(...),
    compression: float = Query(0.25, description="Compression ratio"),
    format: str = Query("markdown", description="Output format"),
) -> dict[str, Any]:
    """Create a summary of a paper."""
    if not Summarizer:
        raise HTTPException(status_code=503, detail="Summarizer not available")

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # Create summary
        summarizer = Summarizer()
        summary = summarizer.summarize_file(
            tmp_path, compression_ratio=compression
        )

        # Format output
        if format == "markdown":
            output = summary.to_markdown()
        elif format == "json":
            output = summary.to_dict()
        else:
            output = summary.to_latex()

        return {
            "title": summary.title,
            "authors": summary.authors,
            "original_word_count": summary.word_count_original,
            "summary_word_count": summary.word_count_summary,
            "compression_achieved": summary.actual_compression,
            "citation_count": len(summary.citations),
            "content": output,
            "format": format,
        }

    finally:
        # Cleanup
        tmp_path.unlink()


@router.post("/review/create")
async def create_literature_review(
    files: list[UploadFile] = File(...),
    theme: str = Form(...),
    context: str = Form(...),
    format: str = Query("markdown", description="Output format"),
) -> dict[str, Any]:
    """Create a literature review from multiple papers."""
    if not LiteratureReviewer:
        raise HTTPException(
            status_code=503, detail="Literature reviewer not available"
        )

    # Save uploaded files temporarily
    temp_files = []

    try:
        for file in files:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=file.filename
            ) as tmp:
                content = await file.read()
                tmp.write(content)
                temp_files.append(Path(tmp.name))

        # Create literature review
        reviewer = LiteratureReviewer()
        review = reviewer.create_review(
            temp_files, theme=theme, context=context
        )

        # Format output
        if format == "markdown":
            output = review.to_markdown()
        else:
            output = review.to_dict()

        return {
            "theme": review.theme,
            "paper_count": review.paper_count,
            "total_citations": review.total_citations,
            "key_findings": len(review.key_findings),
            "research_gaps": len(review.research_gaps),
            "content": output,
            "format": format,
        }

    finally:
        # Cleanup
        for tmp_file in temp_files:
            tmp_file.unlink()


@router.post("/review/analyze")
async def analyze_summary(file: UploadFile = File(...)) -> dict[str, Any]:
    """Analyze a summary for quality metrics."""
    if not Summarizer:
        raise HTTPException(status_code=503, detail="Summarizer not available")

    # Read content
    content = await file.read()
    text = content.decode("utf-8")

    # Analyze
    summarizer = Summarizer()
    metrics = summarizer.analyze_summary(text)

    return metrics


@router.get("/review/info")
async def get_review_info() -> dict[str, Any]:
    """Get information about the review tools."""
    return {
        "summarizer_available": Summarizer is not None,
        "reviewer_available": LiteratureReviewer is not None,
        "compression_ratios": [0.1, 0.25, 0.5, 0.75],
        "output_formats": ["markdown", "json", "latex"],
        "features": [
            "Smart summarization",
            "Citation preservation",
            "Reference deduplication",
            "Theme-based synthesis",
            "Research gap identification",
        ],
    }
