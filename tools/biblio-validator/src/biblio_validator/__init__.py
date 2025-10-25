"""
biblio-validator: Professional citation validation tool for academic documents.

This package provides comprehensive validation of citations and bibliographies
against multiple publisher databases including CrossRef, PubMed, and arXiv.
"""

__version__ = "1.0.0"

from .core.validator import BibliographyValidator, CitationValidator
from .models.bibliography import BibEntry, BibliographyReport
from .models.citation import Citation, ValidationResult

__all__ = [
    "CitationValidator",
    "BibliographyValidator",
    "Citation",
    "ValidationResult",
    "BibEntry",
    "BibliographyReport",
]
