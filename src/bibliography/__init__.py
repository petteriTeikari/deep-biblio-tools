"""Bibliography processing module for Deep Biblio Tools.

This module provides comprehensive bibliography processing functionality including:
- Parsing and formatting BibTeX entries
- Validating and fixing bibliography data
- Merging and deduplicating entries
- Extracting citations from documents
- Resolving missing data from external sources
"""

from .core import Bibliography, BibliographyEntry, BibliographyProcessor
from .fixer import AuthorFixer, BibliographyFixer
from .formatter import CitationKeyFormatter
from .sorter import BibliographySorter
from .validator import BibliographyValidator, LLMCitationValidator

__all__ = [
    "Bibliography",
    "BibliographyEntry",
    "BibliographyProcessor",
    "BibliographyFixer",
    "AuthorFixer",
    "CitationKeyFormatter",
    "BibliographySorter",
    "BibliographyValidator",
    "LLMCitationValidator",
]
