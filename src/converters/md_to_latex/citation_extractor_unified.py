"""Citation extraction using the new AST parser infrastructure.

This module uses our unified MarkdownParser to extract citations
from markdown documents in a robust, maintainable way.
"""

# Standard library imports
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

# Local imports
from src.converters.md_to_latex.utils import normalize_arxiv_url, normalize_url
from src.parsers import MarkdownParser

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Represents a citation found in markdown."""

    text: str
    url: str
    line: int
    position: tuple[int, int]
    is_academic: bool = False


class UnifiedCitationExtractor:
    """Extract citations from markdown using our unified AST parser."""

    # Academic domains that indicate a citation
    ACADEMIC_DOMAINS = {
        "arxiv.org",
        "doi.org",
        "dx.doi.org",
        "papers.",
        "scholar.",
        "researchgate.",
        "academia.edu",
        "sciencedirect.",
        "springer.",
        "nature.",
        "ieee.",
        "acm.",
        "plos.",
        "frontiersin.",
        "mdpi.",
        "wiley.",
        "tandfonline.",
        "oup.",
        "cambridge.",
        "science.",
        "cell.",
        "pnas.",
        "bmj.",
        "nejm.",
        "jamanetwork.",
        "aaai.",
        "neurips.",
        "icml.",
        "iclr.",
        "cvpr.",
        "eccv.",
        "iccv.",
        "nips.cc",
        "openreview.net",
        "dl.acm.org",
        "proceedings.mlr.press",
        "jmlr.org",
        "aclweb.org",
        "semanticscholar.org",
        "pubmed.ncbi.nlm.nih.gov",
        "ncbi.nlm.nih.gov/pmc",
        "biorxiv.org",
        "medrxiv.org",
        "chemrxiv.org",
        "psyarxiv.com",
        "osf.io",
        "zenodo.org",
        "figshare.com",
        "dryad.org",
    }

    def __init__(self):
        """Initialize the citation extractor."""
        self.parser = MarkdownParser()

    def extract_citations(self, content: str) -> list[Citation]:
        """Extract all citations from markdown content.

        Args:
            content: Markdown content to parse

        Returns:
            List of Citation objects
        """
        citations = []

        # Extract all links using the parser
        links = self.parser.extract_links(content)
        logger.info(f"Extracted {len(links)} total links from markdown")

        for link_info in links:
            url = link_info["href"]

            # Skip internal cross-references (URLs starting with #)
            # These are references to sections within the document, not citations
            if url.startswith("#"):
                logger.debug(
                    f"Skipping internal cross-reference: {link_info['text']} -> {url}"
                )
                continue

            # Normalize arXiv URLs to remove version specifiers (v1, v2, etc.)
            # This prevents duplicate citations for the same paper
            original_url = url
            url = normalize_arxiv_url(url)
            if url != original_url:
                logger.debug(f"Normalized arXiv URL: {original_url} -> {url}")

            # Normalize URL for reliable matching (http/https, trailing slashes, etc.)
            normalized_url = normalize_url(url)
            if normalized_url != url:
                logger.debug(f"Normalized URL: {url} -> {normalized_url}")
                url = normalized_url

            # Check if this link is to an academic resource
            is_academic = self._is_academic_url(url)

            citation = Citation(
                text=link_info["text"],
                url=url,
                line=link_info["line"],
                position=link_info["position"],
                is_academic=is_academic,
            )
            citations.append(citation)

            if is_academic:
                logger.info(
                    f"Found academic citation at line {citation.line}: [{citation.text}]({citation.url})"
                )
            else:
                logger.debug(
                    f"Found non-academic link at line {citation.line}: [{citation.text}]({citation.url})"
                )

        logger.info(
            f"Extraction complete: {len([c for c in citations if c.is_academic])} academic citations, "
            f"{len([c for c in citations if not c.is_academic])} non-academic links"
        )

        return citations

    def extract_academic_citations(self, content: str) -> list[Citation]:
        """Extract only academic citations from markdown content.

        Args:
            content: Markdown content to parse

        Returns:
            List of Citation objects that point to academic resources
        """
        all_citations = self.extract_citations(content)
        return [c for c in all_citations if c.is_academic]

    def _is_academic_url(self, url: str) -> bool:
        """Check if a URL points to an academic resource.

        Args:
            url: URL to check

        Returns:
            True if URL appears to be academic
        """
        if not url:
            return False

        # Parse URL
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc

            # Check against known academic domains
            for academic_domain in self.ACADEMIC_DOMAINS:
                if academic_domain in domain:
                    return True

            # Check for .edu domains
            if domain.endswith(".edu"):
                return True

            # Check for PDF files (might be papers)
            if parsed.path.endswith(".pdf"):
                # More likely to be academic if from certain domains
                return any(
                    indicator in domain
                    for indicator in ["edu", "gov", "org", "ac."]
                )

            # Check URL path for academic indicators
            path_indicators = [
                "/paper/",
                "/papers/",
                "/pubs/",
                "/publications/",
                "/article/",
                "/articles/",
                "/abstract/",
                "/fulltext/",
                "/doi/",
                "/document/",
                "/download/pdf/",
            ]
            return any(
                indicator in parsed.path for indicator in path_indicators
            )

        except Exception as e:
            logger.debug(f"Error parsing URL {url}: {e}")
            return False

    def extract_citation_contexts(
        self, content: str, context_chars: int = 100
    ) -> list[dict[str, Any]]:
        """Extract citations with surrounding context.

        Args:
            content: Markdown content to parse
            context_chars: Number of characters of context to include

        Returns:
            List of dictionaries with citation info and context
        """
        citations = self.extract_academic_citations(content)
        results = []

        for citation in citations:
            start_pos = max(0, citation.position[0] - context_chars)
            end_pos = min(len(content), citation.position[1] + context_chars)

            context_before = content[start_pos : citation.position[0]]
            context_after = content[citation.position[1] : end_pos]

            results.append(
                {
                    "citation": citation,
                    "context_before": context_before.strip(),
                    "context_after": context_after.strip(),
                    "full_context": content[start_pos:end_pos].strip(),
                }
            )

        return results

    def group_citations_by_domain(
        self, content: str
    ) -> dict[str, list[Citation]]:
        """Group citations by their domain.

        Args:
            content: Markdown content to parse

        Returns:
            Dictionary mapping domains to lists of citations
        """
        citations = self.extract_academic_citations(content)
        grouped = {}

        for citation in citations:
            try:
                parsed = urlparse(citation.url)
                domain = parsed.netloc.lower()
                # Simplify domain (remove www., etc.)
                if domain.startswith("www."):
                    domain = domain[4:]

                if domain not in grouped:
                    grouped[domain] = []
                grouped[domain].append(citation)
            except Exception as e:
                logger.debug(f"Error parsing URL {citation.url}: {e}")
                if "unknown" not in grouped:
                    grouped["unknown"] = []
                grouped["unknown"].append(citation)

        return grouped

    def find_duplicate_citations(self, content: str) -> list[list[Citation]]:
        """Find citations that point to the same resource.

        Args:
            content: Markdown content to parse

        Returns:
            List of groups of duplicate citations
        """
        citations = self.extract_academic_citations(content)

        # Group by normalized URL
        url_groups = {}
        for citation in citations:
            # Normalize URL (remove fragments, trailing slashes, etc.)
            normalized = self._normalize_url(citation.url)
            if normalized not in url_groups:
                url_groups[normalized] = []
            url_groups[normalized].append(citation)

        # Return only groups with duplicates
        return [group for group in url_groups.values() if len(group) > 1]

    def _normalize_url(self, url: str) -> str:
        """Normalize a URL for comparison."""
        try:
            parsed = urlparse(url.lower())
            # Remove fragment and trailing slash
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if normalized.endswith("/"):
                normalized = normalized[:-1]
            return normalized
        except Exception:
            return url.lower()

    def extract_citations_from_markdown(
        self, content: str
    ) -> list[dict[str, str]]:
        """
        Extract citations in legacy dictionary format for backward compatibility.

        IMPORTANT: Only extracts links that follow citation format [Author (Year)](URL).
        Regular hyperlinks like [Text](URL) without a year are skipped.

        Args:
            content: Markdown content to parse

        Returns:
            List of citation dictionaries with keys: text, url, authors, year, raw_markdown
        """
        citations = self.extract_citations(content)
        result = []

        logger.info(
            f"Processing {len(citations)} extracted citations for year/author parsing"
        )

        for citation in citations:
            # ROBUST APPROACH: Look for ANY 4-digit year (1900-2100) in the text
            # If found, it's a citation. If not, it's a regular hyperlink.
            authors = "Unknown"
            year = "Unknown"
            year_found = False

            # Search for year anywhere in the text
            words = (
                citation.text.replace(",", " ")
                .replace("(", " ")
                .replace(")", " ")
                .split()
            )
            for word in words:
                clean_word = word.strip(".,;:()")
                if len(clean_word) == 4 and clean_word.isdigit():
                    year_int = int(clean_word)
                    if 1900 <= year_int <= 2100:
                        year = clean_word
                        year_found = True
                        # Extract authors (everything before year, cleaned up)
                        year_pos = citation.text.find(year)
                        if year_pos > 0:
                            author_part = citation.text[:year_pos]
                            # Remove common separators and punctuation
                            authors = author_part.strip().rstrip(".,;:()")
                        break

            # CRITICAL: Skip links without a year
            # This prevents regular hyperlinks like [Google Docs](URL) from being treated as citations
            if not year_found:
                logger.info(
                    f"Skipping non-citation hyperlink (no year found): [{citation.text}]({citation.url})"
                )
                continue

            logger.info(
                f"Parsed citation: authors='{authors}', year={year}, url={citation.url}"
            )

            result.append(
                {
                    "text": citation.text,
                    "url": citation.url,
                    "authors": authors,
                    "year": year,
                    "raw_markdown": f"[{citation.text}]({citation.url})",
                    "is_orphan": not citation.is_academic,  # Interpret non-academic as orphan
                }
            )

        logger.info(
            f"Filtered to {len(result)} citations (skipped {len(citations) - len(result)} non-citations)"
        )

        return result
