"""Bibliography models for validation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class BibEntry:
    """Represents a bibliography entry."""

    key: str
    entry_type: str
    fields: dict[str, str]
    raw_text: str | None = None

    @property
    def title(self) -> str | None:
        return self.fields.get("title")

    @property
    def author(self) -> str | None:
        return self.fields.get("author")

    @property
    def year(self) -> str | None:
        return self.fields.get("year")

    @property
    def doi(self) -> str | None:
        return self.fields.get("doi")

    @property
    def url(self) -> str | None:
        return self.fields.get("url")

    def is_complete(self) -> bool:
        """Check if entry has all required fields for its type."""
        required_fields = {
            "article": ["author", "title", "journal", "year"],
            "book": ["author", "title", "publisher", "year"],
            "inproceedings": ["author", "title", "booktitle", "year"],
            "misc": ["author", "title", "year"],
            "phdthesis": ["author", "title", "school", "year"],
            "techreport": ["author", "title", "institution", "year"],
        }

        required = required_fields.get(
            self.entry_type.lower(), ["author", "title", "year"]
        )
        return all(field in self.fields for field in required)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "type": self.entry_type,
            "fields": self.fields,
            "is_complete": self.is_complete(),
        }


@dataclass
class BibliographyReport:
    """Report from bibliography validation."""

    file_path: str
    total_entries: int = 0
    valid_entries: int = 0
    invalid_entries: int = 0
    entries: list[BibEntry] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def add_entry(self, entry: BibEntry, is_valid: bool = True):
        """Add an entry to the report."""
        self.entries.append(entry)
        self.total_entries += 1
        if is_valid:
            self.valid_entries += 1
        else:
            self.invalid_entries += 1

    def add_issue(self, issue: str):
        """Add an issue to the report."""
        self.issues.append(issue)

    def add_warning(self, warning: str):
        """Add a warning to the report."""
        self.warnings.append(warning)

    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            "# Bibliography Validation Report",
            "",
            f"**File:** `{self.file_path}`",
            f"**Generated:** {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- Total entries: {self.total_entries}",
            f"- Valid entries: {self.valid_entries}",
            f"- Invalid entries: {self.invalid_entries}",
            "",
        ]

        if self.issues:
            lines.extend([f"## Issues ({len(self.issues)})", ""])
            for issue in self.issues:
                lines.append(f"- {issue}")
            lines.append("")

        if self.warnings:
            lines.extend([f"## Warnings ({len(self.warnings)})", ""])
            for warning in self.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        return "\n".join(lines)
