"""Deep Biblio Tools - Post-processing of LLM artifacts for scientific text"""

from .core import BiblioChecker, BibtexEntry, Citation, ValidationResult
from .utils import (
    classify_url,
    extract_dois_from_text,
    is_academic_domain,
    validate_doi,
)

__version__ = "0.1.0"
__author__ = "Petteri Teikari"
__email__ = "petteri.teikari@gmail.com"

__all__ = [
    "BiblioChecker",
    "Citation",
    "BibtexEntry",
    "ValidationResult",
    "extract_dois_from_text",
    "validate_doi",
    "classify_url",
    "is_academic_domain",
]
