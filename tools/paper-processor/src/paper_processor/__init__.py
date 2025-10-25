"""
paper-processor: Extract and process content from academic papers.

This package provides tools for extracting content from various academic
paper formats and converting them to clean, structured output.
"""

__version__ = "1.0.0"

from .core.processor import PaperProcessor
from .models.paper import Paper, Reference, Section

__all__ = [
    "PaperProcessor",
    "Paper",
    "Section",
    "Reference",
]
