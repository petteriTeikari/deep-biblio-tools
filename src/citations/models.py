"""Data models for deterministic citation processing."""

# Standard library imports
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DataSource(Enum):
    """Source of citation data with implied trust levels.

    Order matters - higher in the list = more trusted.
    """

    CROSSREF = "crossref"  # Most trusted for DOIs
    PUBMED = "pubmed"  # Trusted for biomedical
    ARXIV = "arxiv"  # Trusted for arXiv papers
    SEMANTIC_SCHOLAR = "s2"  # Good coverage
    ZOTERO = "zotero"  # Translation server
    USER_PROVIDED = "user"  # Manual corrections
    LLM_OUTPUT = "llm"  # Least trusted

    @property
    def trust_score(self) -> float:
        """Get trust score (0-1) for this source."""
        scores = {
            self.CROSSREF: 1.0,
            self.PUBMED: 0.95,
            self.ARXIV: 0.95,
            self.SEMANTIC_SCHOLAR: 0.8,
            self.ZOTERO: 0.7,
            self.USER_PROVIDED: 0.9,
            self.LLM_OUTPUT: 0.1,
        }
        return scores.get(self, 0.5)


@dataclass
class AuthorData:
    """Verified author information with provenance."""

    given_name: str
    family_name: str
    full_name: str | None = None
    orcid: str | None = None
    affiliation: str | None = None
    source: DataSource = DataSource.LLM_OUTPUT
    confidence: float = 0.0

    def __post_init__(self):
        """Set confidence based on source if not provided."""
        if self.confidence == 0.0:
            self.confidence = self.source.trust_score

        # Generate full name if not provided
        if not self.full_name:
            if self.given_name and self.family_name:
                self.full_name = f"{self.given_name} {self.family_name}"

    def to_bibtex_name(self) -> str:
        """Format author name for BibTeX."""
        if self.family_name and self.given_name:
            return f"{self.family_name}, {self.given_name}"
        return self.full_name or "Unknown"


@dataclass
class ValidationIssue:
    """Issue found during validation."""

    field: str
    severity: str  # "error", "warning", "info"
    message: str
    expected: Any | None = None
    actual: Any | None = None


@dataclass
class ValidationLog:
    """Single validation step in the audit trail."""

    timestamp: datetime
    action: str
    source: DataSource
    success: bool
    message: str
    data: dict[str, Any] | None = None


@dataclass
class CitationData:
    """Deterministic citation data with full provenance tracking."""

    # Identifiers (most reliable)
    doi: str | None = None
    arxiv_id: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    isbn: str | None = None
    url: str | None = None

    # Core metadata
    title: str | None = None
    authors: list[AuthorData] = field(default_factory=list)
    year: int | None = None

    # Publication details
    journal: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    publisher: str | None = None

    # For conferences/proceedings
    booktitle: str | None = None
    conference: str | None = None

    # Entry type
    entry_type: str = "article"

    # Tracking and provenance
    source: DataSource = DataSource.LLM_OUTPUT
    confidence: float = 0.0
    validation_log: list[ValidationLog] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    # Original data for comparison
    original_data: dict[str, Any] | None = None

    def __post_init__(self):
        """Initialize confidence from source."""
        if self.confidence == 0.0:
            self.confidence = self.source.trust_score

    def add_validation_step(
        self,
        action: str,
        source: DataSource,
        success: bool,
        message: str,
        data: dict[str, Any] | None = None,
    ):
        """Add a validation step to the audit trail."""
        self.validation_log.append(
            ValidationLog(
                timestamp=datetime.now(),
                action=action,
                source=source,
                success=success,
                message=message,
                data=data,
            )
        )

    def add_issue(
        self,
        field: str,
        severity: str,
        message: str,
        expected: Any = None,
        actual: Any = None,
    ):
        """Add a validation issue."""
        self.issues.append(
            ValidationIssue(
                field=field,
                severity=severity,
                message=message,
                expected=expected,
                actual=actual,
            )
        )

    def get_primary_identifier(self) -> str | None:
        """Get the most reliable identifier available."""
        if self.doi:
            return f"doi:{self.doi}"
        elif self.arxiv_id:
            return f"arxiv:{self.arxiv_id}"
        elif self.pmid:
            return f"pmid:{self.pmid}"
        elif self.isbn:
            return f"isbn:{self.isbn}"
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "identifiers": {
                "doi": self.doi,
                "arxiv": self.arxiv_id,
                "pmid": self.pmid,
                "pmcid": self.pmcid,
                "isbn": self.isbn,
                "url": self.url,
            },
            "metadata": {
                "title": self.title,
                "authors": [
                    {
                        "given": a.given_name,
                        "family": a.family_name,
                        "orcid": a.orcid,
                        "source": a.source.value,
                        "confidence": a.confidence,
                    }
                    for a in self.authors
                ],
                "year": self.year,
                "journal": self.journal,
                "volume": self.volume,
                "issue": self.issue,
                "pages": self.pages,
                "publisher": self.publisher,
                "booktitle": self.booktitle,
                "entry_type": self.entry_type,
            },
            "validation": {
                "source": self.source.value,
                "confidence": self.confidence,
                "issues": [
                    {
                        "field": i.field,
                        "severity": i.severity,
                        "message": i.message,
                    }
                    for i in self.issues
                ],
                "log": [
                    {
                        "timestamp": log.timestamp.isoformat(),
                        "action": log.action,
                        "source": log.source.value,
                        "success": log.success,
                        "message": log.message,
                    }
                    for log in self.validation_log
                ],
            },
        }


@dataclass
class ValidationResult:
    """Result of validating a set of citations."""

    total_citations: int = 0
    validated_citations: int = 0
    citations_with_issues: int = 0
    hallucinations_detected: int = 0

    # Detailed results
    citations: list[CitationData] = field(default_factory=list)

    # Summary statistics
    sources_used: dict[str, int] = field(default_factory=dict)
    issue_types: dict[str, int] = field(default_factory=dict)

    # Timing
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def success_rate(self) -> float:
        """Calculate validation success rate."""
        if self.total_citations == 0:
            return 0.0
        return self.validated_citations / self.total_citations

    @property
    def duration_seconds(self) -> float | None:
        """Calculate processing duration."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def add_citation(self, citation: CitationData):
        """Add a validated citation to results."""
        self.citations.append(citation)
        self.total_citations += 1

        if citation.confidence > 0.5:
            self.validated_citations += 1

        if citation.issues:
            self.citations_with_issues += 1

        # Track source
        source = citation.source.value
        self.sources_used[source] = self.sources_used.get(source, 0) + 1

        # Track issue types
        for issue in citation.issues:
            if issue.severity == "error":
                self.issue_types[issue.field] = (
                    self.issue_types.get(issue.field, 0) + 1
                )
