"""
Common extraction utilities for bibliographic tools.

Shared functionality for extracting citations, DOIs, and other
bibliographic information from various sources.
"""

# import re  # Banned - using string methods instead
from urllib.parse import urlparse


def extract_dois_from_text(text: str) -> list[str]:
    """
    Extract DOI patterns from text.

    Args:
        text: Text to search for DOIs

    Returns:
        List of DOI strings found
    """
    dois = []
    # Look for patterns starting with "10." followed by numbers, then "/", then non-whitespace
    i = 0
    while i < len(text) - 3:
        if text[i : i + 3] == "10.":
            # Check if followed by at least one digit
            j = i + 3
            if j < len(text) and text[j].isdigit():
                # Continue while we have digits
                while j < len(text) and text[j].isdigit():
                    j += 1
                # Check for "/"
                if j < len(text) and text[j] == "/":
                    # Collect the rest of the DOI
                    j += 1
                    start = i
                    while j < len(text) and text[j] not in " \n\t\r]).,;":
                        j += 1
                    doi = text[start:j]
                    # Clean trailing punctuation
                    while doi and doi[-1] in ".,;":
                        doi = doi[:-1]
                    if doi and "/" in doi:
                        dois.append(doi)
                    i = j
                else:
                    i += 1
            else:
                i += 1
        else:
            i += 1
    return dois


def extract_urls_from_markdown(text: str) -> list[tuple]:
    """
    Extract URLs from markdown link syntax.

    Args:
        text: Markdown text

    Returns:
        List of (link_text, url) tuples
    """
    links = []
    i = 0
    while i < len(text):
        # Find opening [
        bracket_start = text.find("[", i)
        if bracket_start == -1:
            break

        # Find closing ]
        bracket_end = text.find("]", bracket_start + 1)
        if bracket_end == -1:
            i = bracket_start + 1
            continue

        # Check if followed by (
        if bracket_end + 1 < len(text) and text[bracket_end + 1] == "(":
            # Find closing )
            paren_end = text.find(")", bracket_end + 2)
            if paren_end == -1:
                i = bracket_end + 1
                continue

            # Extract link text and URL
            link_text = text[bracket_start + 1 : bracket_end]
            url = text[bracket_end + 2 : paren_end]
            links.append((link_text, url))
            i = paren_end + 1
        else:
            i = bracket_end + 1

    return links


def is_academic_domain(url: str) -> bool:
    """
    Check if a URL points to an academic domain.

    Args:
        url: URL to check

    Returns:
        True if the domain is academic
    """
    academic_domains = {
        "doi.org",
        "researchgate.net",
        "ieee.org",
        "acm.org",
        "springer.com",
        "sciencedirect.com",
        "wiley.com",
        "nature.com",
        "cambridge.org",
        "oxford.org",
        "oup.com",
        "tandfonline.com",
        "sagepub.com",
        "frontiersin.org",
        "mdpi.com",
        "arxiv.org",
        "pubmed.ncbi.nlm.nih.gov",
        "scholar.google.com",
        "semanticscholar.org",
        "jstor.org",
    }

    try:
        domain = urlparse(url).netloc.lower()
        return any(
            academic_domain in domain for academic_domain in academic_domains
        )
    except Exception:
        return False


def clean_author_name(name: str) -> str:
    """
    Clean and standardize author name format.

    Args:
        name: Author name to clean

    Returns:
        Cleaned author name
    """
    # Remove extra whitespace and standardize format
    return " ".join(name.strip().split())


def extract_year_from_citation(citation: str) -> str | None:
    """
    Extract year from citation text.

    Args:
        citation: Citation text

    Returns:
        Year string if found, None otherwise
    """
    # Look for 4-digit years starting with 19 or 20
    words = citation.split()
    for word in words:
        # Clean punctuation from the word
        clean_word = word.strip("()[]{}.,;:!?")
        if len(clean_word) == 4 and clean_word.isdigit():
            if clean_word.startswith("19") or clean_word.startswith("20"):
                return clean_word

    # Also check within the text without splitting
    for i in range(len(citation) - 3):
        if citation[i : i + 2] in ["19", "20"]:
            # Check if next 2 chars are digits
            if citation[i + 2 : i + 4].isdigit():
                # Make sure it's not part of a longer number
                if (i == 0 or not citation[i - 1].isdigit()) and (
                    i + 4 >= len(citation) or not citation[i + 4].isdigit()
                ):
                    return citation[i : i + 4]

    return None
