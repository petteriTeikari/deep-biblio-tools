"""
literature-reviewer: Generate comprehensive literature reviews with smart summarization.

This package provides tools for creating high-quality literature reviews
and summaries from academic papers.
"""

__version__ = "1.0.0"

from .core.reviewer import LiteratureReviewer
from .core.summarizer import Summarizer
from .models.summary import LiteratureReview, Summary

__all__ = [
    "Summarizer",
    "LiteratureReviewer",
    "Summary",
    "LiteratureReview",
]
