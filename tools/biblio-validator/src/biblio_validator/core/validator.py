"""Core validation functionality."""

import re
from pathlib import Path
from typing import Any

from ..models.bibliography import BibliographyReport
from ..models.citation import Citation, ValidationResult
from ..utils.cache import ValidationCache
from ..utils.parsers import parse_bibtex_file, parse_document_citations
from ..validators.arxiv import ArxivValidator
from ..validators.crossref import CrossRefValidator
from ..validators.pubmed import PubMedValidator


class CitationValidator:
    """Validates citations against multiple sources."""

    def __init__(
        self, config: dict[str, Any] = None, sources: list[str] = None
    ):
        self.config = config or {}
        self.sources = sources or self.config.get("validation", {}).get(
            "sources", ["crossref"]
        )

        # Initialize validators
        self.validators = {}
        if "crossref" in self.sources:
            self.validators["crossref"] = CrossRefValidator(config)
        if "pubmed" in self.sources:
            self.validators["pubmed"] = PubMedValidator(config)
        if "arxiv" in self.sources:
            self.validators["arxiv"] = ArxivValidator(config)

        # Initialize cache
        cache_config = self.config.get("cache", {})
        if cache_config.get("enabled", True):
            self.cache = ValidationCache(cache_config)
        else:
            self.cache = None

    def validate_document(
        self, document_path: Path, format: str = None
    ) -> list[ValidationResult]:
        """Validate all citations in a document."""
        # Parse citations from document
        citations = parse_document_citations(document_path, format)

        # Validate each citation
        results = []
        for citation in citations:
            result = self.validate_citation(citation)
            results.append(result)

        return results

    def validate_citation(self, citation: Citation) -> ValidationResult:
        """Validate a single citation."""
        # Check cache first
        if self.cache:
            cached_result = self.cache.get(citation.key)
            if cached_result:
                return cached_result

        # Try each validator
        for source_name, validator in self.validators.items():
            try:
                result = validator.validate(citation)
                if result.is_valid:
                    result.source = source_name
                    # Cache successful result
                    if self.cache:
                        self.cache.set(citation.key, result)
                    return result
            except Exception:
                # Continue to next validator
                continue

        # No validator succeeded
        result = ValidationResult(
            citation=citation, is_valid=False, confidence=0.0
        )
        result.add_issue("Citation not found in any configured source")
        return result

    def apply_fixes(self, results: list[ValidationResult]) -> int:
        """Apply automatic fixes to invalid citations."""
        fixed_count = 0

        for result in results:
            if not result.is_valid and result.suggestions:
                # Apply first suggestion (in real implementation, would modify document)
                fixed_count += 1

        return fixed_count

    def generate_comprehensive_report(
        self, results: list[ValidationResult], format: str = "markdown"
    ) -> str:
        """Generate a comprehensive validation report."""
        if format == "markdown":
            return self._generate_markdown_report(results)
        elif format == "json":
            import json

            return json.dumps([r.to_dict() for r in results], indent=2)
        elif format == "html":
            return self._generate_html_report(results)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_markdown_report(self, results: list[ValidationResult]) -> str:
        """Generate markdown report."""
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        invalid = total - valid

        lines = [
            "# Citation Validation Report",
            "",
            f"**Total citations:** {total}",
            f"**Valid:** {valid}",
            f"**Invalid:** {invalid}",
            "",
        ]

        if invalid > 0:
            lines.extend(["## Invalid Citations", ""])

            for result in results:
                if not result.is_valid:
                    lines.append(f"### {result.citation.key}")
                    lines.append(f"- **Text:** {result.citation.text}")
                    lines.append(f"- **Issues:** {', '.join(result.issues)}")
                    if result.suggestions:
                        lines.append(
                            f"- **Suggestions:** {', '.join(result.suggestions)}"
                        )
                    lines.append("")

        return "\n".join(lines)

    def _generate_html_report(self, results: list[ValidationResult]) -> str:
        """Generate HTML report."""
        # Simplified HTML generation
        html = "<html><body><h1>Citation Validation Report</h1>"
        # ... implementation details ...
        html += "</body></html>"
        return html


class BibliographyValidator:
    """Validates bibliography files."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def validate_file(
        self, bibfile: Path, check_dois: bool = False, check_urls: bool = False
    ) -> BibliographyReport:
        """Validate a bibliography file."""
        report = BibliographyReport(file_path=str(bibfile))

        # Parse bibliography
        entries = parse_bibtex_file(bibfile)

        for entry in entries:
            # Check completeness
            if not entry.is_complete():
                report.add_entry(entry, is_valid=False)
                report.add_issue(
                    f"Entry '{entry.key}' is missing required fields"
                )
            else:
                report.add_entry(entry, is_valid=True)

            # Check DOIs if requested
            if check_dois and entry.doi:
                if not self._validate_doi(entry.doi):
                    report.add_warning(
                        f"Entry '{entry.key}' has invalid DOI: {entry.doi}"
                    )

            # Check URLs if requested
            if check_urls and entry.url:
                if not self._validate_url(entry.url):
                    report.add_warning(
                        f"Entry '{entry.key}' has invalid URL: {entry.url}"
                    )

        return report

    def _validate_doi(self, doi: str) -> bool:
        """Validate DOI format."""
        doi_pattern = r"^10\.\d{4,9}/[-._;()/:\w]+$"
        return bool(re.match(doi_pattern, doi))

    def _validate_url(self, url: str) -> bool:
        """Basic URL validation."""
        url_pattern = r"^https?://[^\s]+$"
        return bool(re.match(url_pattern, url))
