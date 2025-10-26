#!/usr/bin/env python3
"""
Extract bibliography from markdown files with proper metadata fetching.

This script extracts citations in format [Author (Year)](URL) from markdown files
and fetches actual metadata from CrossRef API (for DOIs), arXiv API (for arXiv papers),
or attempts to fetch page titles for other URLs.
"""

import argparse
import json
import logging

# import re  # Banned - using string methods instead
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# API configuration
CROSSREF_API_URL = "https://api.crossref.org/works/{doi}"
ARXIV_API_URL = "https://export.arxiv.org/api/query"
USER_AGENT = "DeepBiblioTools/1.0 (https://github.com/github-personal/deep-biblio-tools; mailto:admin@example.com)"
HEADERS = {"User-Agent": USER_AGENT}

# Rate limiting
REQUEST_DELAY = 0.5  # seconds between API requests
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # seconds between retries


class Citation:
    """Represents a single citation with metadata."""

    def __init__(self, raw_text: str, authors: str, year: str, url: str):
        self.raw_text = raw_text
        self.authors = authors
        self.original_authors = authors  # Preserve original for key generation
        self.year = year
        self.url = url
        self.title = None
        self.journal = None
        self.volume = None
        self.pages = None
        self.doi = None
        self.arxiv_id = None
        self.publisher = None
        self.book_title = None
        self.metadata_source = None
        self.fetch_error = None

    def to_bibtex_key(self) -> str:
        """Generate a BibTeX key from authors and year."""
        # Extract first author's last name from the ORIGINAL markdown authors
        # This preserves the citation key expected by the LaTeX document
        first_author = self.original_authors.split()[0].strip()
        # Remove "et al." and other suffixes
        if first_author.endswith(","):
            first_author = first_author[:-1]
        # Clean the author name - keep only ASCII letters
        cleaned = ""
        for char in first_author:
            if char.isalpha() and ord(char) < 128:
                cleaned += char
        first_author = cleaned
        return f"{first_author.lower()}{self.year}"

    def to_bibtex(self) -> str:
        """Convert to BibTeX entry."""
        key = self.to_bibtex_key()

        # Determine entry type
        if self.journal:
            entry_type = "article"
        elif self.book_title:
            entry_type = "book"
        elif self.arxiv_id:
            entry_type = "misc"
        elif self.publisher:
            entry_type = "book"
        else:
            entry_type = "misc"

        # Build BibTeX entry
        lines = [f"@{entry_type}{{{key},"]

        # Always include author, title, year
        lines.append(f'  author = "{self.authors}",')

        if self.title:
            lines.append(f'  title = "{self.title}",')
        else:
            lines.append(
                '  title = "[Title not available - manual entry needed]",'
            )

        lines.append(f'  year = "{self.year}",')

        # Add other fields if available
        if self.journal:
            lines.append(f'  journal = "{self.journal}",')
        if self.volume:
            lines.append(f'  volume = "{self.volume}",')
        if self.pages:
            lines.append(f'  pages = "{self.pages}",')
        if self.doi:
            lines.append(f'  doi = "{self.doi}",')
        if self.arxiv_id:
            lines.append(f'  arxivId = "{self.arxiv_id}",')
            lines.append(f'  eprint = "{self.arxiv_id}",')
            lines.append('  archivePrefix = "arXiv",')
        if self.publisher:
            lines.append(f'  publisher = "{self.publisher}",')
        if self.url:
            lines.append(f'  url = "{self.url}",')
        if self.metadata_source:
            lines.append(f'  note = "Metadata from: {self.metadata_source}",')
        if self.fetch_error:
            lines.append(
                f'  note = "Metadata fetch error: {self.fetch_error}",'
            )

        lines.append("}")

        return "\n".join(lines)


def extract_citations(content: str) -> list[Citation]:
    """Extract all citations from markdown content."""
    # Pattern to match [Author (Year)](URL)
    citations = []
    seen_urls = set()

    i = 0
    while i < len(content):
        # Look for pattern: [Author (Year)](URL)
        if content[i] == "[":
            # Find matching ]
            j = i + 1
            bracket_count = 1
            while j < len(content) and bracket_count > 0:
                if content[j] == "[":
                    bracket_count += 1
                elif content[j] == "]":
                    bracket_count -= 1
                j += 1

            if bracket_count == 0 and j < len(content) and content[j] == "(":
                # Found [text]( pattern, now extract the parts
                text_inside = content[i + 1 : j - 1]

                # Check if text contains (YYYY) pattern
                paren_start = text_inside.rfind(" (")
                if paren_start != -1 and text_inside.endswith(")"):
                    year_part = text_inside[paren_start + 2 : -1]
                    if len(year_part) == 4 and year_part.isdigit():
                        # Valid year found
                        authors = text_inside[:paren_start].strip()
                        year = year_part

                        # Now extract URL from (URL)
                        url_start = j + 1
                        url_end = url_start
                        paren_count = 1
                        while url_end < len(content) and paren_count > 0:
                            if content[url_end] == "(":
                                paren_count += 1
                            elif content[url_end] == ")":
                                paren_count -= 1
                            url_end += 1

                        if paren_count == 0:
                            url = content[url_start : url_end - 1].strip()
                            full_match = content[i:url_end]

                            # Skip duplicates
                            if url not in seen_urls:
                                seen_urls.add(url)
                                citation = Citation(
                                    full_match, authors, year, url
                                )
                                citations.append(citation)
                                logger.info(
                                    f"Found citation: {authors} ({year}) - {url}"
                                )

                            i = url_end
                            continue

        i += 1

    return citations


def extract_doi_from_url(url: str) -> str | None:
    """Extract DOI from various URL formats."""
    # Common DOI patterns
    url_lower = url.lower()

    # Look for doi.org/ or dx.doi.org/ or just doi/
    doi_start = -1
    if "doi.org/" in url_lower:
        doi_start = url_lower.find("doi.org/") + 8
    elif "dx.doi.org/" in url_lower:
        doi_start = url_lower.find("dx.doi.org/") + 11
    elif "doi/" in url_lower:
        doi_start = url_lower.find("doi/") + 4

    if doi_start == -1:
        return None

    # Extract the DOI
    doi = url[doi_start:]

    # Clean up the DOI
    doi = doi.strip("/")
    # Remove any query parameters
    if "?" in doi:
        doi = doi[: doi.find("?")]
    # Remove escape characters and fix malformed DOIs
    doi = doi.replace("\\(", "(").replace("\\)", ")")
    # Check if DOI looks malformed (ends with backslash or has incomplete parentheses)
    if doi.endswith("\\") or doi.count("(") != doi.count(")"):
        logger.warning(f"Malformed DOI detected: {doi}")
        return None

    return doi if doi else None


def extract_arxiv_id_from_url(url: str) -> str | None:
    """Extract arXiv ID from URL."""
    url_lower = url.lower()

    # Look for arxiv.org/abs/ or arxiv.org/pdf/
    arxiv_id = None
    if "arxiv.org/abs/" in url_lower:
        start = url_lower.find("arxiv.org/abs/") + 14
        arxiv_id = url[start:]
    elif "arxiv.org/pdf/" in url_lower:
        start = url_lower.find("arxiv.org/pdf/") + 14
        arxiv_id = url[start:]
        # Remove .pdf extension if present
        if arxiv_id.endswith(".pdf"):
            arxiv_id = arxiv_id[:-4]

    if arxiv_id:
        # Remove version if present (e.g., v1, v2)
        if "v" in arxiv_id:
            v_index = arxiv_id.rfind("v")
            if v_index > 0 and v_index < len(arxiv_id) - 1:
                # Check if what follows 'v' is a digit
                rest = arxiv_id[v_index + 1 :]
                if rest and all(c.isdigit() for c in rest):
                    arxiv_id = arxiv_id[:v_index]

        return arxiv_id if arxiv_id else None

    return None


def fetch_crossref_metadata(doi: str) -> dict | None:
    """Fetch metadata from CrossRef API."""
    url = CROSSREF_API_URL.format(doi=doi)

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            time.sleep(REQUEST_DELAY)

            if response.status_code == 200:
                data = response.json()
                metadata = data.get("message", {})
                # Check if we got meaningful author data
                if metadata and "author" in metadata and metadata["author"]:
                    return metadata
                else:
                    logger.error(
                        f"CrossRef returned incomplete data for DOI {doi}: missing author information"
                    )
                    return None
            elif response.status_code == 404:
                logger.warning(f"DOI not found: {doi}")
                return None
            else:
                logger.warning(
                    f"CrossRef API error {response.status_code} for DOI: {doi}"
                )

        except Exception as e:
            logger.error(f"Error fetching CrossRef metadata: {e}")

        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)

    logger.error(
        f"Failed to fetch CrossRef metadata after {MAX_RETRIES} attempts for DOI: {doi}"
    )
    return None


def fetch_arxiv_metadata(arxiv_id: str) -> dict | None:
    """Fetch metadata from arXiv API."""
    params = {"id_list": arxiv_id, "max_results": 1}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                ARXIV_API_URL, params=params, headers=HEADERS, timeout=10
            )
            time.sleep(REQUEST_DELAY)

            if response.status_code == 200:
                # Parse XML response
                import xml.etree.ElementTree as ET

                root = ET.fromstring(response.text)

                # Extract metadata from the first entry
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                entry = root.find(".//atom:entry", ns)

                if entry is not None:
                    authors = [
                        author.find("atom:name", ns).text
                        for author in entry.findall("atom:author", ns)
                        if author.find("atom:name", ns) is not None
                    ]

                    # Check if we got meaningful author data
                    if not authors:
                        logger.error(
                            f"arXiv returned no author information for ID: {arxiv_id}"
                        )
                        return None

                    metadata = {
                        "title": entry.find("atom:title", ns).text.strip()
                        if entry.find("atom:title", ns) is not None
                        else None,
                        "authors": authors,
                        "published": entry.find("atom:published", ns).text
                        if entry.find("atom:published", ns) is not None
                        else None,
                        "summary": entry.find("atom:summary", ns).text
                        if entry.find("atom:summary", ns) is not None
                        else None,
                    }
                    return metadata
                else:
                    logger.error(f"arXiv returned no entry for ID: {arxiv_id}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching arXiv metadata: {e}")

        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)

    logger.error(
        f"Failed to fetch arXiv metadata after {MAX_RETRIES} attempts for ID: {arxiv_id}"
    )
    return None


def fetch_webpage_title(url: str) -> str | None:
    """Attempt to fetch webpage title."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        time.sleep(REQUEST_DELAY)

        if response.status_code == 200:
            # Simple title extraction
            text_lower = response.text.lower()
            title_start = text_lower.find("<title")
            if title_start != -1:
                # Find the end of the opening tag
                tag_end = text_lower.find(">", title_start)
                if tag_end != -1:
                    # Find the closing tag
                    title_end = text_lower.find("</title>", tag_end)
                    if title_end != -1:
                        title = response.text[tag_end + 1 : title_end].strip()
                        # Clean up common title suffixes (|, –, -)
                        for separator in ["|", "–", "-"]:
                            if separator in title:
                                # Find the last occurrence and remove everything after it
                                last_sep = title.rfind(separator)
                                if last_sep != -1:
                                    title = title[:last_sep].strip()
                                    break
                        return title

    except Exception as e:
        logger.error(f"Error fetching webpage title: {e}")

    return None


def enrich_citation_metadata(citation: Citation) -> None:
    """Fetch and add metadata to a citation."""
    logger.info(f"Fetching metadata for: {citation.url}")

    # Try to extract DOI
    doi = extract_doi_from_url(citation.url)
    if doi:
        citation.doi = doi
        metadata = fetch_crossref_metadata(doi)
        if metadata:
            citation.metadata_source = "CrossRef"

            # Extract title
            if "title" in metadata and metadata["title"]:
                citation.title = (
                    metadata["title"][0]
                    if isinstance(metadata["title"], list)
                    else metadata["title"]
                )

            # Extract full author list
            if "author" in metadata and metadata["author"]:
                authors = []
                for author in metadata["author"]:
                    if "family" in author and "given" in author:
                        authors.append(f"{author['given']} {author['family']}")
                    elif "family" in author:
                        authors.append(author["family"])
                    elif "given" in author:
                        authors.append(author["given"])

                if authors:
                    # Format authors properly: "First Author, Second Author, and Third Author"
                    if len(authors) == 1:
                        citation.authors = authors[0]
                    elif len(authors) == 2:
                        citation.authors = f"{authors[0]} and {authors[1]}"
                    else:
                        citation.authors = (
                            ", ".join(authors[:-1]) + f", and {authors[-1]}"
                        )

            # Extract journal
            if "container-title" in metadata and metadata["container-title"]:
                citation.journal = (
                    metadata["container-title"][0]
                    if isinstance(metadata["container-title"], list)
                    else metadata["container-title"]
                )

            # Extract volume and pages
            citation.volume = metadata.get("volume")
            citation.pages = metadata.get("page")

            # Extract publisher
            citation.publisher = metadata.get("publisher")

            logger.info(f"Successfully fetched CrossRef metadata for: {doi}")
            return
        else:
            # API failed - log error but continue with original authors
            citation.fetch_error = (
                "CrossRef API failed or returned incomplete data"
            )
            logger.error(
                f"CrossRef API failed for DOI: {doi}. Using original author information."
            )
            # Don't update authors - keep the original from markdown

    # Try to extract arXiv ID
    arxiv_id = extract_arxiv_id_from_url(citation.url)
    if arxiv_id:
        citation.arxiv_id = arxiv_id
        metadata = fetch_arxiv_metadata(arxiv_id)
        if metadata:
            citation.metadata_source = "arXiv"
            citation.title = metadata.get("title")

            # Update authors with full list
            if metadata.get("authors"):
                authors = metadata["authors"]
                if len(authors) == 1:
                    citation.authors = authors[0]
                elif len(authors) == 2:
                    citation.authors = f"{authors[0]} and {authors[1]}"
                else:
                    citation.authors = (
                        ", ".join(authors[:-1]) + f", and {authors[-1]}"
                    )

            logger.info(f"Successfully fetched arXiv metadata for: {arxiv_id}")
            return
        else:
            # API failed - log error but continue with original authors
            citation.fetch_error = (
                "arXiv API failed or returned incomplete data"
            )
            logger.error(
                f"arXiv API failed for ID: {arxiv_id}. Using original author information."
            )
            # Don't update authors - keep the original from markdown

    # Try to fetch webpage title as last resort
    if citation.url.startswith("http"):
        title = fetch_webpage_title(citation.url)
        if title:
            citation.title = title
            citation.metadata_source = "webpage"
            logger.info(
                f"Successfully fetched webpage title for: {citation.url}"
            )
            return

    # If all else fails, mark as needing manual entry
    citation.fetch_error = "Could not fetch metadata automatically"
    logger.warning(f"Failed to fetch metadata for: {citation.url}")


def process_markdown_file(
    file_path: Path, output_path: Path | None = None
) -> None:
    """Process a markdown file and extract bibliography."""
    logger.info(f"Processing file: {file_path}")

    # Read the markdown file
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return

    # Extract citations
    citations = extract_citations(content)
    logger.info(f"Found {len(citations)} unique citations")

    # Fetch metadata for each citation
    for i, citation in enumerate(citations):
        logger.info(f"Processing citation {i + 1}/{len(citations)}")
        try:
            enrich_citation_metadata(citation)
        except Exception as e:
            logger.error(f"Critical error during metadata extraction: {e}")
            logger.error("Stopping bibliography extraction due to API failure.")
            logger.error("Please check your network connection and API access.")
            # Write partial results with error message
            if output_path is None:
                output_path = file_path.with_suffix(".bib")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(
                    f"% Bibliography extraction FAILED from: {file_path.name}\n"
                )
                f.write(f"% Error: {e}\n")
                f.write(
                    f"% Only {i} of {len(citations)} citations processed before failure\n"
                )
                f.write("% Please check API access and retry\n")
            return

    # Generate output
    if output_path is None:
        output_path = file_path.with_suffix(".bib")

    # Write BibTeX file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"% Bibliography extracted from: {file_path.name}\n")
        f.write(f"% Extraction date: {datetime.now().isoformat()}\n")
        f.write(f"% Total citations: {len(citations)}\n\n")

        # Group by metadata source
        by_source = defaultdict(list)
        for citation in citations:
            source = citation.metadata_source or "manual"
            by_source[source].append(citation)

        # Write citations grouped by source
        for source, source_citations in sorted(by_source.items()):
            f.write(
                f"\n% {source.upper()} SOURCES ({len(source_citations)} entries)\n"
            )
            f.write("% " + "=" * 60 + "\n\n")

            for citation in sorted(
                source_citations, key=lambda c: c.to_bibtex_key()
            ):
                f.write(citation.to_bibtex())
                f.write("\n\n")

    logger.info(f"Bibliography written to: {output_path}")

    # Generate summary report
    summary_path = output_path.with_suffix(".json")
    summary = {
        "source_file": str(file_path),
        "extraction_date": datetime.now().isoformat(),
        "total_citations": len(citations),
        "metadata_sources": {
            source: len(source_citations)
            for source, source_citations in by_source.items()
        },
        "citations": [
            {
                "authors": c.authors,
                "year": c.year,
                "title": c.title,
                "url": c.url,
                "metadata_source": c.metadata_source,
                "fetch_error": c.fetch_error,
            }
            for c in citations
        ],
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Summary report written to: {summary_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract bibliography from markdown files with metadata fetching"
    )
    parser.add_argument(
        "input_file", type=Path, help="Path to the markdown file to process"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output BibTeX file path (default: same name as input with .bib extension)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.input_file.exists():
        logger.error(f"Input file not found: {args.input_file}")
        return 1

    process_markdown_file(args.input_file, args.output)
    return 0


if __name__ == "__main__":
    exit(main())
