"""MCP tool for checking citation URL quality."""

import logging
from typing import Any

from mcp_servers.citation_quality.utils.url_analyzer import (
    categorize_citation_url,
)

logger = logging.getLogger(__name__)


async def check_citation_url_quality(
    url: str, citation_text: str
) -> dict[str, Any]:
    """Check if a citation URL points to a proper academic paper.

    Args:
        url: The URL to validate
        citation_text: The citation text (e.g., "Author et al., 2024")

    Returns:
        Dictionary with validation results including:
        - is_valid: Whether the URL is acceptable
        - category: URL category (academic, grey_lit, problematic, etc.)
        - severity: Issue severity (ok, warning, error)
        - issue: Description of any issues
        - suggestions: List of suggestions for improvement
    """
    try:
        # Analyze URL using shared utility
        result = categorize_citation_url(url)

        # Determine validity
        is_valid = result.severity == "ok"

        # Build response
        response: dict[str, Any] = {
            "is_valid": is_valid,
            "category": result.subcategory,
            "severity": result.severity,
            "issue": result.message,
            "citation_text": citation_text,
            "url": url,
        }

        # Add suggestions if available
        if result.suggestion:
            response["suggestions"] = [
                {
                    "description": result.suggestion,
                    "confidence": "high"
                    if result.category == "problematic"
                    else "medium",
                }
            ]
        else:
            response["suggestions"] = []

        return response

    except Exception as e:
        logger.exception(f"Error checking URL quality: {url}")
        return {
            "is_valid": False,
            "category": "error",
            "severity": "error",
            "issue": f"Error analyzing URL: {e!s}",
            "citation_text": citation_text,
            "url": url,
            "suggestions": [],
        }
