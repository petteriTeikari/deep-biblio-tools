"""
Utility modules for bibliographic tools.
"""

from .cache import BiblioCache, CacheEntry
from .content_classifier import (
    ContentClassifier,
    classify_url,
    is_layperson_url,
)
from .extractors import (
    clean_author_name,
    extract_dois_from_text,
    extract_urls_from_markdown,
    extract_year_from_citation,
    is_academic_domain,
)
from .mdpi_workaround import (
    MDPIWorkaround,
    extract_doi_from_mdpi_url,
    process_mdpi_link,
)
from .pdf_parser import PDFParser, extract_pdf_metadata, is_pdf_url
from .researchgate_workaround import (
    ResearchGateWorkaround,
    extract_title_from_researchgate_url,
    process_researchgate_link,
)
from .validators import (
    ValidationError,
    detect_potential_hallucination,
    validate_bibtex_entry,
    validate_citation_format,
    validate_doi,
    validate_latex_citation,
    validate_markdown_link,
    validate_url,
)
from .validators_enhanced import (
    validate_bibtex_with_structured_errors,
    validate_latex_document_with_structured_errors,
    validate_markdown_with_structured_errors,
)

__all__ = [
    # cache
    "BiblioCache",
    "CacheEntry",
    # extractors
    "extract_dois_from_text",
    "extract_urls_from_markdown",
    "is_academic_domain",
    "clean_author_name",
    "extract_year_from_citation",
    # validators
    "ValidationError",
    "validate_doi",
    "validate_url",
    "validate_citation_format",
    "validate_bibtex_entry",
    "validate_latex_citation",
    "detect_potential_hallucination",
    "validate_markdown_link",
    # enhanced validators with structured errors
    "validate_latex_document_with_structured_errors",
    "validate_bibtex_with_structured_errors",
    "validate_markdown_with_structured_errors",
    # pdf_parser
    "PDFParser",
    "is_pdf_url",
    "extract_pdf_metadata",
    # content_classifier
    "ContentClassifier",
    "classify_url",
    "is_layperson_url",
    # researchgate_workaround
    "ResearchGateWorkaround",
    "process_researchgate_link",
    "extract_title_from_researchgate_url",
    # mdpi_workaround
    "MDPIWorkaround",
    "process_mdpi_link",
    "extract_doi_from_mdpi_url",
]
