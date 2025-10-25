"""
quality-guardian: Ensure high-quality academic writing.

This package provides tools for checking and improving academic writing quality.
"""

__version__ = "1.0.0"

from .core.guardian import QualityGuardian
from .core.report import QualityReport

__all__ = [
    "QualityGuardian",
    "QualityReport",
]
