"""Validation API endpoints."""

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

# Import from other tools (would be installed as dependencies)
try:
    from biblio_validator import BibliographyValidator, CitationValidator
except ImportError:
    CitationValidator = None
    BibliographyValidator = None

router = APIRouter()


@router.post("/validate/citations")
async def validate_citations(file: UploadFile = File(...)) -> dict[str, Any]:
    """Validate citations in a document."""
    if not CitationValidator:
        raise HTTPException(
            status_code=503, detail="Citation validator not available"
        )

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # Validate citations
        validator = CitationValidator()
        results = validator.validate_document(tmp_path)

        # Format results
        return {
            "total": len(results),
            "valid": sum(1 for r in results if r.is_valid),
            "invalid": sum(1 for r in results if not r.is_valid),
            "results": [r.to_dict() for r in results],
        }

    finally:
        # Cleanup
        tmp_path.unlink()


@router.post("/validate/bibliography")
async def validate_bibliography(file: UploadFile = File(...)) -> dict[str, Any]:
    """Validate a bibliography file."""
    if not BibliographyValidator:
        raise HTTPException(
            status_code=503, detail="Bibliography validator not available"
        )

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # Validate bibliography
        validator = BibliographyValidator()
        report = validator.validate_file(
            tmp_path, check_dois=True, check_urls=True
        )

        # Format results
        return {
            "total_entries": report.total_entries,
            "valid_entries": report.valid_entries,
            "invalid_entries": report.invalid_entries,
            "issues": report.issues,
            "warnings": report.warnings,
        }

    finally:
        # Cleanup
        tmp_path.unlink()


@router.post("/validate/match")
async def match_citations(
    document: UploadFile = File(...), bibliography: UploadFile = File(...)
) -> dict[str, Any]:
    """Match citations in document to bibliography entries."""
    # Implementation would use CitationMatcher
    return {
        "message": "Citation matching endpoint",
        "status": "not_implemented",
    }
