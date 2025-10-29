"""Extract author/publisher names from website domains.

For web pages without explicit authors (like BBC, Bloomberg, etc.),
we can infer the author from the domain name. This prevents "Unknown"
authors and provides better citations.

Example:
    >>> extract_author_from_url("https://www.bbc.com/news/business-44885983")
    'BBC'
"""

import logging
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Domain → Author/Publisher mapping
# Add more as you discover common sources
SITE_AUTHOR_MAPPINGS = {
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "bloomberg.com": "Bloomberg",
    "reuters.com": "Reuters",
    "theguardian.com": "The Guardian",
    "nytimes.com": "The New York Times",
    "wsj.com": "The Wall Street Journal",
    "ft.com": "Financial Times",
    # Government & EU
    "europa.eu": "European Commission",
    "europarl.europa.eu": "European Parliament",
    "ec.europa.eu": "European Commission",
    "gov.uk": "UK Government",
    "epa.gov": "US Environmental Protection Agency",
    # Industry & Standards
    "hmfoundation.com": "H&M Foundation",
    "gs1.eu": "GS1 Europe",
    "gs1.org": "GS1",
    "wbcsd.org": "World Business Council for Sustainable Development",
    "iso.org": "International Organization for Standardization",
    # Academic & Research
    "arxiv.org": "arXiv",
    "doi.org": "DOI",
    "unpaywall.org": "Unpaywall",
    # Fashion industry
    "commonobjective.co": "Common Objective",
    "fashionrevolution.org": "Fashion Revolution",
    "sustainable-fashion.com": "Sustainable Fashion",
    # Add more as needed
}


def extract_domain(url: str) -> str | None:
    """Extract domain from URL using urllib.parse (stdlib, no dependencies).

    Args:
        url: Full URL (e.g., "https://www.bbc.com/news/article")

    Returns:
        Domain name (e.g., "bbc.com") or None if parsing fails

    Example:
        >>> extract_domain("https://www.bbc.com/news/business-44885983")
        'bbc.com'
        >>> extract_domain("https://ec.europa.eu/environment/textiles")
        'ec.europa.eu'
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if not domain:
            return None

        # Remove 'www.' prefix if present
        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception as exc:
        logger.debug(f"Failed to parse domain from URL '{url}': {exc}")
        return None


def extract_author_from_url(url: str) -> str | None:
    """Map URL domain to author/publisher name.

    Args:
        url: Full URL of the web page

    Returns:
        Author/publisher name if known, None otherwise

    Example:
        >>> extract_author_from_url("https://www.bbc.com/news/business-44885983")
        'BBC'
        >>> extract_author_from_url("https://ec.europa.eu/environment/textiles")
        'European Commission'
        >>> extract_author_from_url("https://unknown-site.com/article")
        None
    """
    domain = extract_domain(url)
    if not domain:
        return None

    # Direct lookup
    if domain in SITE_AUTHOR_MAPPINGS:
        return SITE_AUTHOR_MAPPINGS[domain]

    # Handle subdomains: check if any known domain is a suffix
    # This handles cases like "ec.europa.eu" where we know "europa.eu"
    # or "news.bbc.co.uk" where we know "bbc.co.uk"
    for known_domain, author in SITE_AUTHOR_MAPPINGS.items():
        if domain.endswith(f".{known_domain}") or domain == known_domain:
            return author

    # No mapping found
    return None


def augment_metadata_with_site_author(
    metadata: dict[str, Any],
    url: str
) -> dict[str, Any]:
    """Add author from site name if missing.

    Args:
        metadata: Zotero item JSON (from translation server)
        url: Original URL

    Returns:
        Modified metadata with creators field populated if it was empty

    Example:
        >>> metadata = {"title": "Some Article", "creators": []}
        >>> augment_metadata_with_site_author(metadata, "https://www.bbc.com/news/...")
        {'title': 'Some Article', 'creators': [{'creatorType': 'author', 'lastName': 'BBC'}]}
    """
    # Check if metadata already has creators
    creators = metadata.get("creators", [])
    if creators and len(creators) > 0:
        # Already has authors, don't override
        return metadata

    # Try to extract author from URL
    site_author = extract_author_from_url(url)

    if site_author:
        # Add as single author with lastName = organization name
        metadata["creators"] = [
            {
                "creatorType": "author",
                "lastName": site_author
            }
        ]
        logger.info(f"Augmented metadata with site author: {site_author} from {url}")
    else:
        logger.debug(f"No site author mapping found for: {url}")

    return metadata


def get_known_domains() -> list[str]:
    """Get list of all known domains in the mapping.

    Useful for documentation and testing.

    Returns:
        List of domain names
    """
    return sorted(SITE_AUTHOR_MAPPINGS.keys())


def add_site_mapping(domain: str, author: str):
    """Add a new site mapping (useful for extending at runtime).

    Args:
        domain: Domain name (e.g., "example.com")
        author: Author/publisher name (e.g., "Example Corporation")
    """
    domain = domain.lower().strip()
    author = author.strip()

    if not domain or not author:
        raise ValueError("Both domain and author must be non-empty")

    SITE_AUTHOR_MAPPINGS[domain] = author
    logger.info(f"Added site mapping: {domain} → {author}")
