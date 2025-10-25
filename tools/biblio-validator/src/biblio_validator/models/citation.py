"""Citation models for validation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Citation:
    """Represents a citation found in a document."""

    key: str
    text: str
    document_path: str
    line_number: int | None = None
    context: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self):
        return f"Citation({self.key})"

    def __repr__(self):
        return f"Citation(key={self.key!r}, document={self.document_path})"


@dataclass
class ValidationResult:
    """Result of validating a citation."""

    citation: Citation
    is_valid: bool
    confidence: float = 1.0
    source: str | None = None
    matched_entry: dict[str, Any] | None = None
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def add_issue(self, issue: str):
        """Add an issue to the validation result."""
        self.issues.append(issue)
        self.is_valid = False

    def add_suggestion(self, suggestion: str):
        """Add a fix suggestion."""
        self.suggestions.append(suggestion)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "citation_key": self.citation.key,
            "is_valid": self.is_valid,
            "confidence": self.confidence,
            "source": self.source,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "timestamp": self.timestamp.isoformat(),
        }
