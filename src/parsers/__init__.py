"""
Paper parsing modules for extracting content from various sources.

This package contains parsers for:
- Markdown documents
- BibTeX bibliographies
- LaTeX documents
- ScienceDirect HTML papers
- General HTML papers
- Complete paper extraction
- Omni-Scan2BIM specific parsing
"""

# Import base classes first
from .base import ParsedDocument, ParsedNode, StructuredParser

# Import parsers - these may fail in some environments
# but tests should handle ImportError gracefully
# We use a single try block to avoid 'code before imports' issues
try:
    from .bibtex_parser import BibtexParser
    from .latex_parser import LatexParser
    from .markdown_parser import MarkdownParser

    __all__ = [
        "StructuredParser",
        "ParsedDocument",
        "ParsedNode",
        "BibtexParser",
        "LatexParser",
        "MarkdownParser",
    ]
except (ImportError, SyntaxError):
    # If any parser import fails, export only base classes
    BibtexParser = None
    LatexParser = None
    MarkdownParser = None

    __all__ = [
        "StructuredParser",
        "ParsedDocument",
        "ParsedNode",
    ]
