"""MCP tool for comprehensive citation auditing."""

import logging
import os
from pathlib import Path
from typing import Any

from src.converters.md_to_latex.citation_extractor_unified import (
    UnifiedCitationExtractor,
)

from mcp_servers.citation_quality.tools.link_health import check_link_health
from mcp_servers.citation_quality.utils.url_analyzer import (
    categorize_citation_url,
)

logger = logging.getLogger(__name__)


async def audit_markdown_citations(
    file_path: str,
    zotero_collection: str | None = None,
    check_link_health_enabled: bool = False,
    validate_metadata: bool = True,
) -> dict[str, Any]:
    """Comprehensive audit of all citations in a markdown file.

    Args:
        file_path: Path to the markdown file to audit
        zotero_collection: Zotero collection name (defaults to ZOTERO_COLLECTION env var)
        check_link_health_enabled: Whether to check if HTTP links are reachable
        validate_metadata: Whether to validate metadata against Zotero

    Returns:
        Dictionary with:
        - summary: Citation counts by category
        - issues: List of problematic citations with details
        - recommendations: List of suggested actions
    """
    try:
        # Use collection from env if not provided
        if zotero_collection is None:
            zotero_collection = os.getenv("ZOTERO_COLLECTION", "dpp-fashion")

        # Read markdown file
        filepath = Path(file_path)
        if not filepath.exists():
            return {
                "error": f"File not found: {file_path}",
                "summary": {},
                "issues": [],
                "recommendations": [],
            }

        content = filepath.read_text(encoding="utf-8")

        # Extract citations using UnifiedCitationExtractor
        extractor = UnifiedCitationExtractor()
        citations = extractor.extract_citations(content)

        # Categorize citations
        academic = []
        grey_lit = []
        problematic = []
        questionable = []
        other = []

        for citation in citations:
            result = categorize_citation_url(citation.url)

            if result.category == "academic":
                academic.append(citation)
            elif result.category == "grey_lit":
                grey_lit.append(citation)
            elif result.category == "problematic":
                problematic.append((citation, result))
            elif result.category == "questionable":
                questionable.append((citation, result))
            else:
                other.append((citation, result))

        # Build summary
        summary = {
            "total_links": len(citations),
            "academic_citations": len(academic),
            "grey_literature": len(grey_lit),
            "problematic": len(problematic),
            "questionable": len(questionable),
            "other": len(other),
        }

        # Build issues list
        issues = []

        # Add problematic citations as errors
        for citation, result in problematic:
            issue = {
                "line": citation.line,
                "type": result.subcategory,
                "severity": "error",
                "citation": f"[{citation.text}]({citation.url})",
                "issue": result.message,
            }
            if result.suggestion:
                issue["suggestion"] = result.suggestion
            issues.append(issue)

        # Add questionable citations as warnings
        for citation, result in questionable:
            issues.append(
                {
                    "line": citation.line,
                    "type": result.subcategory,
                    "severity": "warning",
                    "citation": f"[{citation.text}]({citation.url})",
                    "issue": result.message,
                }
            )

        # Check link health if requested
        if check_link_health_enabled:
            all_urls = [c.url for c in citations]
            health_results = await check_link_health(all_urls)

            for result in health_results["results"]:
                if not result["reachable"]:
                    # Find the citation with this URL
                    matching_cit = next(
                        (c for c in citations if c.url == result["url"]), None
                    )
                    if matching_cit:
                        issues.append(
                            {
                                "line": matching_cit.line,
                                "type": "broken_link",
                                "severity": "error",
                                "url": result["url"],
                                "http_status": result["status"],
                                "error": result["error"],
                            }
                        )
                        summary["broken_links"] = (
                            summary.get("broken_links", 0) + 1
                        )

        # Build recommendations
        recommendations = []
        if problematic:
            recommendations.append(
                f"Fix {len(problematic)} problematic URL(s) to point to actual papers"
            )
        if questionable:
            recommendations.append(
                f"Review {len(questionable)} questionable citation(s) for appropriateness"
            )
        if check_link_health_enabled and summary.get("broken_links", 0) > 0:
            recommendations.append(
                f"Verify {summary['broken_links']} broken link(s)"
            )

        if not issues:
            recommendations.append("All citations look good!")

        return {
            "summary": summary,
            "issues": issues,
            "recommendations": recommendations,
        }

    except Exception as e:
        logger.exception(f"Error auditing citations in {file_path}")
        return {
            "error": f"Error auditing citations: {e!s}",
            "summary": {},
            "issues": [],
            "recommendations": [],
        }
