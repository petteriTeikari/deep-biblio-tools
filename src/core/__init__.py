"""
Core modules for bibliographic tools.
"""

from .biblio_checker import (
    BiblioChecker,
    BibtexEntry,
    Citation,
    ValidationResult,
)
from .error_reporter import (
    ASTErrorReporter,
    SourceLocation,
    StructuredError,
    create_parsing_error_from_position,
    create_validation_error_from_node,
)

__all__ = [
    "Citation",
    "BibtexEntry",
    "ValidationResult",
    "BiblioChecker",
    "ASTErrorReporter",
    "StructuredError",
    "SourceLocation",
    "create_validation_error_from_node",
    "create_parsing_error_from_position",
]
