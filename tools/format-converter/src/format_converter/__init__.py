"""
format-converter: Convert between academic document formats.

This package provides tools for converting between various academic
formats while preserving citations and bibliographies.
"""

__version__ = "1.0.0"

from .converters.latex_to_markdown import LatexToMarkdownConverter
from .converters.markdown_to_latex import MarkdownToLatexConverter
from .core.converter import FormatConverter

__all__ = [
    "FormatConverter",
    "MarkdownToLatexConverter",
    "LatexToMarkdownConverter",
]
