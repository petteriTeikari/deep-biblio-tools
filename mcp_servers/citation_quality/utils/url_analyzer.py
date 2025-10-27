"""URL analysis utilities for citation quality checking.

This module provides URL categorization logic for distinguishing between:
- Academic paper URLs (ideal)
- Grey literature URLs (acceptable)
- Problematic URLs (need fixing)
- Questionable URLs (need review)
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class URLCategoryResult:
    """Result of URL categorization."""

    category: Literal[
        "academic", "grey_lit", "problematic", "questionable", "other"
    ]
    subcategory: str
    severity: Literal["ok", "warning", "error"]
    message: str
    suggestion: str | None = None


def categorize_citation_url(url: str) -> URLCategoryResult:
    """Categorize a citation URL to determine if it's acceptable.

    Args:
        url: The URL to categorize

    Returns:
        URLCategoryResult with category and severity information
    """
    if not url or url.strip() == "":
        return URLCategoryResult(
            category="problematic",
            subcategory="empty",
            severity="error",
            message="Empty URL",
            suggestion="Add valid URL to citation",
        )

    url_lower = url.lower()

    # Academic papers (GOOD) - reuses UnifiedCitationExtractor logic
    academic_domains = [
        "arxiv.org",
        "doi.org",
        "dx.doi.org",
        "dl.acm.org",
        "ieeexplore.ieee.org",
        "springer.com",
        "nature.com",
        "sciencedirect.com",
        "openreview.net",
        "aclanthology.org",
        "proceedings.mlr.press",
        "jmlr.org",
        "neurips.cc",
        "pubs.acs.org",
        "pubs.rsc.org",
        "iopscience.iop.org",
    ]

    if any(domain in url_lower for domain in academic_domains):
        return URLCategoryResult(
            category="academic",
            subcategory="paper",
            severity="ok",
            message="Valid academic paper URL",
        )

    # Grey literature (ACCEPTABLE)
    # Government/EU documents
    if any(
        domain in url_lower
        for domain in [
            "eur-lex.europa.eu",
            "ec.europa.eu",
            "commission.europa.eu",
            "europarl.europa.eu",
        ]
    ):
        return URLCategoryResult(
            category="grey_lit",
            subcategory="government",
            severity="ok",
            message="Government/EU document (acceptable grey literature)",
        )

    # Standards bodies
    if any(
        domain in url_lower
        for domain in ["gs1.org", "gs1.eu", "standardsmap.org"]
    ):
        return URLCategoryResult(
            category="grey_lit",
            subcategory="standards",
            severity="ok",
            message="Standards body document (acceptable grey literature)",
        )

    # Research institutions
    if any(
        domain in url_lower for domain in ["nist.gov/publications", "nber.org"]
    ):
        return URLCategoryResult(
            category="grey_lit",
            subcategory="research_institution",
            severity="ok",
            message="Research institution document (acceptable grey literature)",
        )

    # Non-profit foundations
    if any(
        domain in url_lower
        for domain in ["ellenmacarthurfoundation.org", "wbcsd.org"]
    ):
        return URLCategoryResult(
            category="grey_lit",
            subcategory="nonprofit",
            severity="ok",
            message="Non-profit foundation document (acceptable grey literature)",
        )

    # Books from legitimate sources
    if "oreilly.com/library" in url_lower:
        return URLCategoryResult(
            category="grey_lit",
            subcategory="book",
            severity="ok",
            message="O'Reilly book (acceptable grey literature)",
        )

    # PROBLEMATIC categories
    # Project pages and repos
    if "github.io" in url_lower:
        return URLCategoryResult(
            category="problematic",
            subcategory="project_page",
            severity="error",
            message="GitHub Pages project site - not a paper URL",
            suggestion="Find the actual paper URL (arXiv, DOI, conference proceedings)",
        )

    if "github.com" in url_lower and "/tree/" not in url_lower:
        return URLCategoryResult(
            category="problematic",
            subcategory="github_repo",
            severity="error",
            message="GitHub repository - not a paper URL",
            suggestion="Find the actual paper URL (arXiv, DOI, conference proceedings)",
        )

    # Personal/university pages (but NOT publications)
    if (
        any(pattern in url_lower for pattern in ["~", "/people/", "/staff/"])
        and "publications" not in url_lower
    ):
        return URLCategoryResult(
            category="problematic",
            subcategory="personal_page",
            severity="error",
            message="Personal/university website - not a paper URL",
            suggestion="Find the actual paper URL (arXiv, DOI, conference proceedings)",
        )

    # Amazon book links (should use proper publisher citation)
    if "amazon." in url_lower:
        return URLCategoryResult(
            category="problematic",
            subcategory="amazon",
            severity="error",
            message="Amazon book link - use proper publisher citation instead",
            suggestion="Use publisher's official URL or DOI",
        )

    # QUESTIONABLE categories
    # News sites
    if any(domain in url_lower for domain in ["bbc.com", "bloomberg.com"]):
        return URLCategoryResult(
            category="questionable",
            subcategory="news",
            severity="warning",
            message="News article - consider if appropriate for academic citation",
        )

    # YouTube
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return URLCategoryResult(
            category="questionable",
            subcategory="youtube",
            severity="warning",
            message="YouTube video - consider if appropriate for academic citation",
        )

    # Company marketing sites
    if any(
        domain in url_lower
        for domain in ["mckinsey.com", "ibm.com/thought-leadership"]
    ):
        return URLCategoryResult(
            category="questionable",
            subcategory="company_marketing",
            severity="warning",
            message="Company marketing site - consider if appropriate for academic citation",
        )

    # Technical documentation (borderline)
    if any(
        domain in url_lower
        for domain in [
            "modelcontextprotocol.io",
            "developers.google.com",
            "developer.okta.com",
        ]
    ):
        return URLCategoryResult(
            category="questionable",
            subcategory="technical_docs",
            severity="warning",
            message="Technical documentation - consider if appropriate for academic citation",
        )

    # University repositories
    if "researchdiscovery" in url_lower or "esploro" in url_lower:
        return URLCategoryResult(
            category="questionable",
            subcategory="university_repository",
            severity="warning",
            message="University repository - verify if direct paper link is available",
        )

    # Other uncategorized
    return URLCategoryResult(
        category="other",
        subcategory="uncategorized",
        severity="warning",
        message="Uncategorized URL - manual review recommended",
    )


def is_academic_url(url: str) -> bool:
    """Quick check if a URL is an academic paper URL.

    This wraps the categorize_citation_url function for simple boolean checks.

    Args:
        url: The URL to check

    Returns:
        True if the URL is categorized as academic
    """
    result = categorize_citation_url(url)
    return result.category == "academic"
