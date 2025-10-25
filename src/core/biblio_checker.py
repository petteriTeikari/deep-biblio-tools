#!/usr/bin/env python3
"""
Bibliographic Entry Checker

A Python application for validating and correcting bibliographic entries in Markdown files by:
1. Extracting hyperlinks from Markdown files
2. Visiting each publisher's site to extract BibTeX data
3. Correcting citation formats based on actual author data
4. Converting publisher links to DOI links where possible
5. Generating corrected Markdown files and detailed JSON logs

Usage: python biblio_checker.py [markdown_file_or_directory]
"""

# Standard library imports
import argparse
import json
import logging
import os

# import re  # Banned - using string methods instead
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

# Third-party imports
import bibtexparser
import requests
from bibtexparser.bparser import BibTexParser
from bs4 import BeautifulSoup
from tqdm import tqdm

# Local imports
from ..parsers import MarkdownParser
from ..utils.abbreviation_checker import AbbreviationChecker
from ..utils.cache import BiblioCache
from ..utils.citation_style_fixer import CitationStyleFixer
from ..utils.content_classifier import ContentClassifier
from ..utils.mdpi_workaround import MDPIWorkaround
from ..utils.pdf_parser import PDFParser, is_pdf_url
from ..utils.researchgate_workaround import ResearchGateWorkaround


@dataclass
class Citation:
    """Represents a citation found in markdown"""

    text: str
    url: str
    line_number: int
    start_pos: int
    end_pos: int
    file_path: str
    context_before: str = ""  # Text before the citation (up to 100 chars)
    context_after: str = ""  # Text after the citation (up to 100 chars)
    full_line: str = ""  # Complete line containing the citation


@dataclass
class BibtexEntry:
    """Represents extracted BibTeX data"""

    entry_type: str
    key: str
    fields: dict[str, str]
    raw_bibtex: str
    source_url: str
    doi: str | None = None


@dataclass
class ValidationResult:
    """Result of validating a citation"""

    citation: Citation
    bibtex_entry: BibtexEntry | None
    corrected_text: str | None
    corrected_url: str | None
    errors: list[str]
    warnings: list[str]
    tags: list[str]  # For #GUESSED, #LAY, etc.
    confidence: float  # Confidence in the extraction (0.0 to 1.0)

    @property
    def is_valid(self) -> bool:
        """Return True if there are no errors"""
        return len(self.errors) == 0


class BiblioChecker:
    """Main class for checking and correcting bibliographic entries"""

    def __init__(
        self,
        verbose: bool = False,
        delay: float = 1.0,
        use_cache: bool = True,
        cache_ttl_days: int = 30,
    ):
        self.verbose = verbose
        self.delay = delay
        self.use_cache = use_cache
        self.setup_logging()

        # Initialize cache
        if self.use_cache:
            self.cache = BiblioCache(cache_ttl_days=cache_ttl_days)
        else:
            self.cache = None

        # Common user agent to avoid blocking
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Session for connection reuse
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Initialize utility modules
        self.pdf_parser = PDFParser()
        self.researchgate_workaround = ResearchGateWorkaround(delay=delay)
        self.mdpi_workaround = MDPIWorkaround(delay=delay)
        self.content_classifier = ContentClassifier()
        self.markdown_parser = MarkdownParser()

        # Academic domain patterns
        self.academic_domains = {
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

    def setup_logging(self):
        """Set up logging configuration"""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # File handler
        file_handler = logging.FileHandler("biblio_checker.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(
            logging.INFO if self.verbose else logging.WARNING
        )
        console_handler.setFormatter(logging.Formatter(log_format))

        # Configure root logger
        logging.basicConfig(
            level=logging.DEBUG, handlers=[file_handler, console_handler]
        )

        self.logger = logging.getLogger(__name__)

    def extract_citations_from_markdown(self, file_path: str) -> list[Citation]:
        """Extract citations from a markdown file using AST parser"""
        self.logger.info(f"Extracting citations from {file_path}")

        citations = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Use the new Markdown parser to extract links
            links = self.markdown_parser.extract_links(content)
            lines = content.split("\n")

            for link_info in links:
                url = link_info["href"]

                # Only process academic URLs
                if self._is_academic_url(url):
                    start_pos = link_info["position"][0]
                    end_pos = link_info["position"][1]
                    line_num = link_info["line"]

                    # Extract context around the citation
                    context_before = content[
                        max(0, start_pos - 100) : start_pos
                    ]
                    context_after = content[
                        end_pos : min(len(content), end_pos + 100)
                    ]

                    # Clean up context (remove excessive whitespace)
                    # Simple whitespace normalization, not parsing
                    context_before = " ".join(context_before.split())
                    context_after = " ".join(context_after.split())

                    # Get the full line containing the citation
                    full_line = (
                        lines[line_num - 1].strip()
                        if line_num <= len(lines)
                        else ""
                    )

                    citation = Citation(
                        text=link_info["text"],
                        url=url,
                        line_number=line_num,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        file_path=file_path,
                        context_before=context_before,
                        context_after=context_after,
                        full_line=full_line,
                    )
                    citations.append(citation)
                    self.logger.debug(
                        f"Found citation: {link_info['text']} -> {url}"
                    )

        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
            # Fallback to regex if parser fails
            self.logger.warning("Falling back to regex extraction")
            return self._extract_citations_from_markdown_regex(file_path)

        self.logger.info(f"Found {len(citations)} citations in {file_path}")
        return citations

    def _extract_citations_from_markdown_regex(
        self, file_path: str
    ) -> list[Citation]:
        """Legacy regex-based citation extraction as fallback"""
        self.logger.info(f"Using regex extraction for {file_path}")
        citations = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            # Pattern for markdown links: [text](url)
            # Simple link extraction as fallback, not AST parsing
            current_pos = 0
            for line_num, line in enumerate(lines, 1):
                # Find all citations in line without regex
                line_offset = 0
                while "[" in line[line_offset:] and "]" in line[line_offset:]:
                    bracket_start = line.find("[", line_offset)
                    bracket_end = line.find("]", bracket_start)
                    if bracket_end == -1 or bracket_end < bracket_start:
                        break

                    # Check if there's a URL part
                    if (
                        bracket_end + 1 < len(line)
                        and line[bracket_end + 1] == "("
                    ):
                        paren_end = line.find(")", bracket_end + 2)
                        if paren_end == -1:
                            line_offset = bracket_end + 1
                            continue

                        text = line[bracket_start + 1 : bracket_end]
                        url = line[bracket_end + 2 : paren_end]

                        # Only process academic URLs
                        if self._is_academic_url(url):
                            start_pos = current_pos + bracket_start
                            end_pos = current_pos + paren_end + 1

                            # Extract context around the citation
                            context_before = (
                                line[:bracket_start][-100:]
                                if bracket_start > 0
                                else ""
                            )
                            context_after = (
                                line[paren_end + 1 :][:100]
                                if paren_end + 1 < len(line)
                                else ""
                            )

                            # Clean up context (remove excessive whitespace)
                            # Simple whitespace normalization, not parsing
                            context_before = " ".join(context_before.split())
                            context_after = " ".join(context_after.split())

                            citation = Citation(
                                text=text,
                                url=url,
                                line_number=line_num,
                                start_pos=start_pos,
                                end_pos=end_pos,
                                file_path=file_path,
                                context_before=context_before,
                                context_after=context_after,
                                full_line=line.strip(),
                            )
                            citations.append(citation)
                            self.logger.debug(
                                f"Found citation: {text} -> {url}"
                            )

                        line_offset = paren_end + 1
                    else:
                        line_offset = bracket_end + 1

                current_pos += len(line) + 1  # +1 for newline

        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")

        self.logger.info(f"Found {len(citations)} citations in {file_path}")
        return citations

    def _is_academic_url(self, url: str) -> bool:
        """Check if URL points to an academic/publisher domain"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check against known academic domains
            for academic_domain in self.academic_domains:
                if academic_domain in domain:
                    return True

            # Check for .edu domains
            if ".edu" in domain:
                return True

            # Check for PDFs (might be academic papers)
            if url.lower().endswith(".pdf"):
                return True

            return False
        except Exception:
            return False

    def extract_bibtex_from_url(
        self, url: str
    ) -> tuple[BibtexEntry | None, list[str], float]:
        """
        Extract BibTeX data from a URL

        Returns:
            Tuple of (BibtexEntry or None, list of tags, confidence score)
        """
        self.logger.info(f"Extracting BibTeX from: {url}")

        # Check cache first
        if self.cache:
            cached_entry = self.cache.get(url)
            if cached_entry:
                self.logger.debug(f"Found cached entry for {url}")
                if cached_entry.error_message:
                    # Return cached error
                    error_tags = (
                        ["CACHE", "FETCH_ERROR"]
                        if "fetch" in cached_entry.error_message.lower()
                        else ["CACHE", "PARSE_ERROR"]
                    )
                    return None, error_tags, 0.0
                elif cached_entry.bibtex_data:
                    # Convert cached data back to BibtexEntry - filter out extra fields
                    bibtex_data = cached_entry.bibtex_data.copy()

                    # Remove fields that aren't part of BibtexEntry dataclass
                    extra_fields = [
                        "manual_correction",
                        "corrected_citation_text",
                    ]
                    for field in extra_fields:
                        bibtex_data.pop(field, None)

                    bibtex_entry = BibtexEntry(**bibtex_data)
                    tags = ["CACHE"]

                    # Check if this is a manual correction
                    if cached_entry.bibtex_data.get("manual_correction"):
                        tags.append("MANUAL")
                        confidence = (
                            1.0  # Perfect confidence for manual corrections
                        )
                    else:
                        confidence = 0.9  # High confidence for cached results

                    return bibtex_entry, tags, confidence

        tags = []
        confidence = 0.0

        # Check for PDFs first
        if is_pdf_url(url):
            self.logger.debug("URL is a PDF, attempting PDF extraction")
            pdf_info = self.pdf_parser.extract_pdf_info(url)
            if pdf_info:
                tags.append("PDF")
                if "year" not in pdf_info or "authors" not in pdf_info:
                    tags.append("#GUESSED")
                    confidence = 0.5
                else:
                    confidence = 0.7
                bibtex_entry = self._create_bibtex_from_pdf_info(pdf_info, url)

                # Cache PDF result
                if self.cache and bibtex_entry:
                    self.cache.put(url=url, bibtex_data=asdict(bibtex_entry))

                return bibtex_entry, tags, confidence

        # Check for ResearchGate
        if "researchgate.net" in url:
            self.logger.debug("ResearchGate URL detected, using workaround")
            rg_info = self.researchgate_workaround.process_researchgate_url(url)
            if rg_info:
                tags.extend(["BLOCKED_RG", "#GUESSED"])
                confidence = 0.6
                bibtex_entry = self._create_bibtex_from_rg_info(rg_info, url)

                # Cache ResearchGate result
                if self.cache and bibtex_entry:
                    self.cache.put(url=url, bibtex_data=asdict(bibtex_entry))

                return bibtex_entry, tags, confidence

        # Check for MDPI
        if "mdpi.com" in url:
            self.logger.debug("MDPI URL detected, using workaround")
            mdpi_info = self.mdpi_workaround.process_mdpi_url(url)
            if mdpi_info:
                tags.extend(["BLOCKED_MDPI", "#GUESSED"])
                confidence = 0.7
                bibtex_entry = self._create_bibtex_from_mdpi_info(
                    mdpi_info, url
                )

                # Cache MDPI result
                if self.cache and bibtex_entry:
                    self.cache.put(url=url, bibtex_data=asdict(bibtex_entry))

                return bibtex_entry, tags, confidence

        # Check content classification
        classification = self.content_classifier.classify_content(url)
        if classification["is_layperson"]:
            if classification["is_press_release"]:
                tags.append("#PRESS")
            elif classification["is_news"]:
                tags.append("#LAY")
            elif classification["is_blog"]:
                tags.append("#LAY")

        try:
            # Add delay to be respectful
            time.sleep(self.delay)

            # Try to fetch the page
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Try various extraction methods
            bibtex_entry = None

            # Method 1: Check for DOI and use content negotiation
            if not bibtex_entry:
                bibtex_entry = self._extract_bibtex_from_doi(url, soup)
                if bibtex_entry:
                    confidence = 0.9

            # Method 2: Look for direct BibTeX links/content
            if not bibtex_entry:
                bibtex_entry = self._extract_bibtex_direct(soup, url)
                if bibtex_entry:
                    confidence = 0.8

            # Method 3: Site-specific extraction
            if not bibtex_entry:
                bibtex_entry = self._extract_bibtex_site_specific(soup, url)
                if bibtex_entry:
                    confidence = 0.7

            # Method 4: Create basic entry from metadata
            if not bibtex_entry:
                self.logger.warning(
                    f"Could not extract BibTeX, creating basic entry for: {url}"
                )
                title_elem = soup.find("title")
                title = (
                    title_elem.text.strip() if title_elem else "Unknown Title"
                )
                bibtex_entry = self._create_basic_bibtex_entry(title, url)
                tags.append("#GUESSED")
                confidence = 0.3

            # Cache successful result
            if self.cache and bibtex_entry:
                self.cache.put(url=url, bibtex_data=asdict(bibtex_entry))

            return bibtex_entry, tags, confidence

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching URL {url}: {e}")
            tags.append("FETCH_ERROR")

            # Cache error result
            if self.cache:
                self.cache.put(
                    url=url, error_message=f"Request error: {str(e)}"
                )

            return None, tags, 0.0
        except Exception as e:
            self.logger.error(f"Unexpected error processing URL {url}: {e}")
            tags.append("PARSE_ERROR")

            # Cache error result
            if self.cache:
                self.cache.put(url=url, error_message=f"Parse error: {str(e)}")

            return None, tags, 0.0

    def _extract_bibtex_from_doi(
        self, url: str, soup: BeautifulSoup = None
    ) -> BibtexEntry | None:
        """Extract BibTeX using DOI content negotiation"""
        doi = None

        # Check if URL is already a DOI
        if "doi.org" in url:
            # Simple DOI extraction from URL, not parsing structured format
            # Extract DOI from URL without regex
            doi_pos = url.find("doi.org/")
            if doi_pos != -1:
                doi = url[doi_pos + 8 :].strip()

        # Look for DOI in page metadata
        elif soup:
            # Check meta tags
            doi_meta = soup.find("meta", {"name": "citation_doi"}) or soup.find(
                "meta", {"name": "DC.Identifier"}
            )
            if doi_meta:
                doi = doi_meta.get("content", "")
                if doi.startswith("doi:"):
                    doi = doi[4:]
                elif doi.startswith("10."):
                    pass  # Already in correct format
                else:
                    doi = None

        if doi:
            try:
                # Use content negotiation to get BibTeX
                doi_url = f"https://doi.org/{doi}"
                headers = {
                    "Accept": "application/x-bibtex",
                    "User-Agent": self.headers["User-Agent"],
                }

                response = self.session.get(
                    doi_url, headers=headers, timeout=10
                )
                response.raise_for_status()

                if response.text.strip():
                    return self._parse_bibtex_text(response.text, url)

            except Exception as e:
                self.logger.debug(f"DOI content negotiation failed: {e}")

        return None

    def _extract_bibtex_direct(
        self, soup: BeautifulSoup, url: str
    ) -> BibtexEntry | None:
        """Look for direct BibTeX content in the page"""
        # Look for BibTeX download links
        # Simple case-insensitive text search, not parsing
        # Find links containing "bibtex" (case-insensitive) without regex
        bibtex_links = []
        for link in soup.find_all("a"):
            if link.string and "bibtex" in link.string.lower():
                bibtex_links.append(link)

        for link in bibtex_links:
            href = link.get("href", "")
            if href:
                try:
                    # Construct absolute URL
                    bibtex_url = urljoin(url, href)
                    response = self.session.get(bibtex_url, timeout=10)
                    response.raise_for_status()

                    if response.text.strip():
                        return self._parse_bibtex_text(response.text, url)

                except Exception as e:
                    self.logger.debug(f"Failed to fetch BibTeX from link: {e}")

        # Look for BibTeX in script tags or pre elements
        for elem in soup.find_all(["pre", "code", "script"]):
            text = elem.get_text()
            if (
                "@article" in text
                or "@inproceedings" in text
                or "@book" in text
            ):
                return self._parse_bibtex_text(text, url)

        return None

    def _extract_bibtex_site_specific(
        self, soup: BeautifulSoup, url: str
    ) -> BibtexEntry | None:
        """Extract BibTeX using site-specific methods"""
        domain = urlparse(url).netloc.lower()

        if "frontiersin.org" in domain:
            return self._extract_frontiers_bibtex(soup, url)
        elif "arxiv.org" in domain:
            return self._extract_arxiv_bibtex(soup, url)
        elif "mdpi.com" in domain:
            return self._extract_mdpi_bibtex(soup, url)
        elif "researchgate.net" in domain:
            return self._extract_researchgate_bibtex(soup, url)
        elif "ieee.org" in domain:
            return self._extract_ieee_bibtex(soup, url)

        return None

    def _extract_frontiers_bibtex(
        self, soup: BeautifulSoup, url: str
    ) -> BibtexEntry | None:
        """Extract BibTeX from Frontiers articles"""
        try:
            # Frontiers specific extraction logic
            title_elem = soup.find("h1", class_="article-title")
            if not title_elem:
                return None

            title = title_elem.text.strip()

            # Extract authors
            authors = []
            author_elems = soup.find_all("div", class_="author-name")
            for elem in author_elems:
                name = elem.text.strip()
                if name:
                    authors.append(name)

            # Extract other metadata
            journal = "Frontiers"  # Default
            journal_elem = soup.find("div", class_="journal-title")
            if journal_elem:
                journal = journal_elem.text.strip()

            year = ""
            date_elem = soup.find("div", class_="published-date")
            if date_elem:
                # Simple year extraction, not parsing
                # Extract year without regex
                text_parts = date_elem.text.split()
                for part in text_parts:
                    if (
                        len(part) == 4
                        and part.isdigit()
                        and part.startswith("20")
                    ):
                        year = part
                        break

            # Extract DOI
            doi = None
            doi_elem = soup.find("div", class_="doi")
            if doi_elem:
                doi_text = doi_elem.text.strip()
                # Simple DOI pattern matching, not parsing
                # Extract DOI without regex
                if "10." in doi_text:
                    start = doi_text.find("10.")
                    # Find end of DOI (whitespace or end of string)
                    end = start
                    while end < len(doi_text) and not doi_text[end].isspace():
                        end += 1
                    potential_doi = doi_text[start:end]
                    # Basic DOI validation
                    if "/" in potential_doi and len(potential_doi) > 7:
                        doi = potential_doi

            if title and authors:
                return self._create_bibtex_from_metadata(
                    title=title,
                    authors=authors,
                    journal=journal,
                    year=year,
                    volume="",
                    url=url,
                    doi=doi,
                )

        except Exception as e:
            self.logger.debug(f"Frontiers extraction failed: {e}")

        return None

    def _extract_arxiv_bibtex(
        self, soup: BeautifulSoup, url: str
    ) -> BibtexEntry | None:
        """Extract BibTeX from arXiv"""
        try:
            # Extract arXiv ID from URL
            # Simple ID extraction, not parsing
            # Extract arXiv ID without regex
            if "arxiv.org/abs/" not in url:
                return None

            arxiv_pos = url.find("arxiv.org/abs/")
            arxiv_id_start = arxiv_pos + 14
            arxiv_id = url[arxiv_id_start:]

            # Validate it's a proper arXiv ID (digits.digits)
            if "." not in arxiv_id:
                return None

            # Extract just the ID part
            parts = arxiv_id.split("/")
            arxiv_id = parts[0] if parts else arxiv_id

            # Basic validation
            id_parts = arxiv_id.split(".")
            if len(id_parts) != 2 or not all(
                part.isdigit() for part in id_parts
            ):
                return None

            # arxiv_id already extracted above

            # arXiv provides export links
            export_url = f"https://arxiv.org/bibtex/{arxiv_id}"

            response = self.session.get(export_url, timeout=10)
            response.raise_for_status()

            if response.text.strip():
                return self._parse_bibtex_text(response.text, url)

        except Exception as e:
            self.logger.debug(f"arXiv extraction failed: {e}")

        return None

    def _extract_mdpi_bibtex(
        self, soup: BeautifulSoup, url: str
    ) -> BibtexEntry | None:
        """Extract BibTeX from MDPI - usually blocked, so this is a fallback"""
        # This should rarely be called as we handle MDPI with the workaround
        self.logger.debug("MDPI extraction attempted (fallback)")
        return None

    def _extract_researchgate_bibtex(
        self, soup: BeautifulSoup, url: str
    ) -> BibtexEntry | None:
        """Extract BibTeX from ResearchGate - usually blocked"""
        # This should rarely be called as we handle RG with the workaround
        self.logger.debug("ResearchGate extraction attempted (fallback)")
        return None

    def _extract_ieee_bibtex(
        self, soup: BeautifulSoup, url: str
    ) -> BibtexEntry | None:
        """Extract BibTeX from IEEE Xplore"""
        try:
            # IEEE specific extraction logic
            # Look for citation download button/link
            cite_link = soup.find("a", {"class": "stats-cite-modal"})
            if cite_link:
                # IEEE requires more complex interaction, often JavaScript-based
                self.logger.debug(
                    "IEEE citation link found but requires JavaScript"
                )

            # Try to extract from metadata
            title_elem = soup.find("meta", {"property": "og:title"})
            title = title_elem.get("content", "") if title_elem else ""

            # Extract authors from meta tags
            authors = []
            author_elems = soup.find_all("meta", {"name": "citation_author"})
            for elem in author_elems:
                author = elem.get("content", "")
                if author:
                    authors.append(author)

            if title and authors:
                return self._create_bibtex_from_metadata(
                    title=title,
                    authors=authors,
                    journal="IEEE",
                    year="",
                    volume="",
                    url=url,
                )

        except Exception as e:
            self.logger.debug(f"IEEE extraction failed: {e}")

        return None

    def _create_bibtex_from_metadata(
        self,
        title: str,
        authors: list[str],
        journal: str,
        year: str,
        volume: str,
        url: str,
        doi: str = None,
        extra_fields: dict = None,
    ) -> BibtexEntry:
        """Create a BibTeX entry from extracted metadata"""
        # Generate BibTeX key
        first_author = authors[0].split()[-1] if authors else "Unknown"
        key = (
            f"{first_author.lower()}{year}"
            if year
            else f"{first_author.lower()}"
        )

        # Determine entry type
        entry_type = "@article" if journal else "@misc"

        # Build fields
        fields = {
            "title": title,
            "author": " and ".join(authors),
            "year": year,
            "url": url,
        }

        if journal:
            fields["journal"] = journal
        if volume:
            fields["volume"] = volume
        if doi:
            fields["doi"] = doi

        if extra_fields:
            fields.update(extra_fields)

        # Remove empty fields
        fields = {k: v for k, v in fields.items() if v}

        # Create raw BibTeX
        raw_bibtex = f"{entry_type}{{{key},\n"
        for field, value in fields.items():
            raw_bibtex += f"  {field} = {{{value}}},\n"
        raw_bibtex = raw_bibtex.rstrip(",\n") + "\n}"

        return BibtexEntry(
            entry_type=entry_type.replace("@", ""),
            key=key,
            fields=fields,
            raw_bibtex=raw_bibtex,
            source_url=url,
            doi=doi,
        )

    def _create_bibtex_from_pdf_info(
        self, pdf_info: dict, url: str
    ) -> BibtexEntry:
        """Create BibTeX entry from PDF extraction results"""
        return self._create_bibtex_from_metadata(
            title=pdf_info.get("title", "Unknown Title"),
            authors=pdf_info.get("authors", []),
            journal=pdf_info.get("publisher", ""),
            year=pdf_info.get("year", ""),
            volume="",
            url=url,
            extra_fields={"note": "Extracted from PDF"},
        )

    def _create_bibtex_from_rg_info(
        self, rg_info: dict, url: str
    ) -> BibtexEntry:
        """Create BibTeX entry from ResearchGate workaround results"""
        doi = rg_info.get("doi", "")
        doi_url = rg_info.get("doi_url", url)

        return self._create_bibtex_from_metadata(
            title=rg_info.get(
                "title", rg_info.get("extracted_title", "Unknown Title")
            ),
            authors=rg_info.get("authors", []),
            journal="",
            year=rg_info.get("year", ""),
            volume="",
            url=doi_url if doi else url,
            doi=doi,
            extra_fields={"note": "Retrieved via Google Scholar"},
        )

    def _create_bibtex_from_mdpi_info(
        self, mdpi_info: dict, url: str
    ) -> BibtexEntry:
        """Create BibTeX entry from MDPI workaround results"""
        doi = mdpi_info.get("doi", "")
        doi_url = f"https://doi.org/{doi}" if doi else url

        return self._create_bibtex_from_metadata(
            title=mdpi_info.get("title", "Unknown Title"),
            authors=mdpi_info.get("authors", []),
            journal=mdpi_info.get("journal", "MDPI"),
            year=mdpi_info.get("year", ""),
            volume=mdpi_info.get("volume", ""),
            url=doi_url,
            doi=doi,
            extra_fields={"publisher": "MDPI", "note": "Retrieved via DOI"},
        )

    def _create_basic_bibtex_entry(self, title: str, url: str) -> BibtexEntry:
        """Create a minimal BibTeX entry"""
        # Simple key generation, not parsing
        # Create key without regex - keep only alphanumeric chars
        key_chars = []
        for char in title[:20]:
            if char.isalnum():
                key_chars.append(char.lower())
        key = "".join(key_chars)

        fields = {
            "title": title,
            "url": url,
            "note": "Minimal extraction - please verify",
        }

        raw_bibtex = f"@misc{{{key},\n"
        for field, value in fields.items():
            raw_bibtex += f"  {field} = {{{value}}},\n"
        raw_bibtex = raw_bibtex.rstrip(",\n") + "\n}"

        return BibtexEntry(
            entry_type="misc",
            key=key,
            fields=fields,
            raw_bibtex=raw_bibtex,
            source_url=url,
            doi=None,
        )

    def _parse_bibtex_text(
        self, bibtex_text: str, source_url: str
    ) -> BibtexEntry | None:
        """Parse BibTeX text into BibtexEntry"""
        try:
            parser = BibTexParser()
            parser.ignore_nonstandard_types = False
            bib_database = bibtexparser.loads(bibtex_text, parser)

            if bib_database.entries:
                entry = bib_database.entries[0]

                # Extract DOI if present
                doi = entry.get("doi", None)

                return BibtexEntry(
                    entry_type=entry.get("ENTRYTYPE", "misc"),
                    key=entry.get("ID", "unknown"),
                    fields={
                        k: v
                        for k, v in entry.items()
                        if k not in ["ENTRYTYPE", "ID"]
                    },
                    raw_bibtex=bibtex_text.strip(),
                    source_url=source_url,
                    doi=doi,
                )

        except Exception as e:
            self.logger.error(f"Error parsing BibTeX: {e}")

        return None

    def _parse_authors(self, authors_str: str) -> list[str]:
        """Parse author string into list of surnames"""
        # Normalize whitespace and newlines first
        authors_str = " ".join(authors_str.split())

        # Handle "and" separator
        if " and " in authors_str:
            author_parts = authors_str.split(" and ")
        else:
            author_parts = [authors_str]

        surnames = []
        for author in author_parts:
            author = author.strip()
            if "," in author:
                # Format: "Lastname, Firstname"
                surname = author.split(",")[0].strip()
            else:
                # Format: "Firstname Lastname"
                parts = author.split()
                if parts:
                    surname = parts[-1]
                else:
                    continue

            surnames.append(surname)

        return surnames

    def format_citation_text(
        self, bibtex_entry: BibtexEntry, tags: list[str] = None
    ) -> str:
        """Format a citation text from BibTeX entry"""
        # Check if this is a manual correction with pre-formatted citation text
        if hasattr(bibtex_entry, "fields") and bibtex_entry.fields.get(
            "corrected_citation_text"
        ):
            citation = bibtex_entry.fields["corrected_citation_text"]
        else:
            # Use standard formatting
            authors_str = bibtex_entry.fields.get("author", "")
            year = bibtex_entry.fields.get("year", "")

            if not authors_str:
                return "Unknown"

            authors = self._parse_authors(authors_str)

            if not authors:
                return "Unknown"

            # Format based on number of authors
            if len(authors) == 1:
                citation = authors[0]
            elif len(authors) == 2:
                citation = f"{authors[0]} and {authors[1]}"
            else:
                citation = f"{authors[0]} et al."

            # Add year
            if year:
                citation = f"{citation} ({year})"

        # Add tags
        if tags:
            tag_str = " ".join(tags)
            citation = f"{citation} {tag_str}"

        return citation

    def validate_citation(
        self, citation: Citation, pbar=None
    ) -> ValidationResult:
        """Validate a single citation"""
        self.logger.info(
            f"Validating citation: {citation.text} -> {citation.url}"
        )

        errors = []
        warnings = []

        # Extract BibTeX
        bibtex_entry, tags, confidence = self.extract_bibtex_from_url(
            citation.url
        )

        if not bibtex_entry:
            errors.append("Failed to extract bibliographic information")
            return ValidationResult(
                citation=citation,
                bibtex_entry=None,
                corrected_text=None,
                corrected_url=None,
                errors=errors,
                warnings=warnings,
                tags=tags,
                confidence=confidence,
            )

        # Format corrected citation text
        corrected_text = self.format_citation_text(bibtex_entry, tags)

        # Determine corrected URL (prefer DOI)
        corrected_url = citation.url
        if bibtex_entry.doi:
            corrected_url = f"https://doi.org/{bibtex_entry.doi}"

        # MANDATORY AUTHOR VERIFICATION
        # Check if citation text matches - this is now CRITICAL
        if citation.text != corrected_text:
            # Clean both texts for comparison (remove tags and extra spaces)
            clean_original = self._clean_citation_text(citation.text).strip()
            clean_corrected = self._clean_citation_text(corrected_text).strip()

            if clean_original.lower() != clean_corrected.lower():
                # This is a CRITICAL error - author names don't match!
                errors.append(
                    f"AUTHOR VERIFICATION FAILED: Citation has incorrect authors! "
                    f"Found '{clean_original}' but should be '{clean_corrected}' based on {citation.url}"
                )
                # Also add as warning for backward compatibility
                warnings.append(
                    f"Citation text mismatch: '{citation.text}' should be '{corrected_text}'"
                )

        # Check if URL should be updated
        if citation.url != corrected_url:
            warnings.append(f"URL can be updated to DOI: {corrected_url}")

        return ValidationResult(
            citation=citation,
            bibtex_entry=bibtex_entry,
            corrected_text=corrected_text,
            corrected_url=corrected_url,
            errors=errors,
            warnings=warnings,
            tags=tags,
            confidence=confidence,
        )

    def _preprocess_markdown(self, content: str) -> str:
        """
        Preprocess markdown content to fix common formatting issues.

        Fixes:
        1. Remove Claude thinking tags (<thinking>...</thinking>)
        2. Fix author-citation redundancy (e.g., "Smith (Smith 2023)" -> "Smith (2023)")
        3. Check for undefined abbreviations
        4. Missing spaces before hyperlinks (e.g., "text[link]" -> "text [link]")
        5. Trailing whitespace on lines
        6. Multiple consecutive blank lines
        7. Other common markdown formatting issues
        """
        if not content:
            return content

        # Fix 0: Remove Claude thinking tags
        # This is a simple tag removal, regex is acceptable here
        # Simple tag removal, not parsing structured format
        # Remove thinking tags without regex
        while "<thinking>" in content:
            start = content.find("<thinking>")
            end = content.find("</thinking>", start)
            if end == -1:
                break
            content = content[:start] + content[end + 11 :]

        # Fix 1: Fix author-citation redundancy
        citation_fixer = CitationStyleFixer()
        content, style_issues = citation_fixer.fix_document(content)
        if style_issues:
            self.logger.info(f"Fixed {len(style_issues)} citation style issues")

        # Fix 2: Check for undefined abbreviations
        abbreviation_checker = AbbreviationChecker()
        abbr_issues, abbr_definitions = abbreviation_checker.check_document(
            content
        )
        if abbr_issues:
            self.logger.warning(
                f"Found {len(abbr_issues)} undefined abbreviations"
            )
            self._report_abbreviation_issues(abbr_issues, abbr_definitions)

        # Fix 3: Add space before hyperlinks if missing
        # This is a simple text substitution, regex is acceptable
        # Simple text formatting, not parsing
        # Add space between text and brackets without regex
        result = []
        for i, char in enumerate(content):
            result.append(char)
            if i < len(content) - 1 and content[i + 1] == "[":
                if char.isalnum() or char in ".,;:!?)]":
                    result.append(" ")
        content = "".join(result)

        # Fix 4: Clean up list formatting
        lines = content.split("\n")
        processed_lines = []

        for line in lines:
            # Fix numbered lists: "1.Item" -> "1. Item"
            # Simple list formatting, not parsing
            # Fix numbered lists without regex
            stripped = line.lstrip()
            if stripped and stripped[0].isdigit():
                # Find the period
                period_pos = stripped.find(".")
                if (
                    period_pos > 0
                    and period_pos + 1 < len(stripped)
                    and not stripped[period_pos + 1].isspace()
                ):
                    # Add space after period
                    indent = line[: len(line) - len(stripped)]
                    line = (
                        indent
                        + stripped[: period_pos + 1]
                        + " "
                        + stripped[period_pos + 1 :]
                    )

            # Fix bullet lists: "-Item" -> "- Item"
            # Simple list formatting, not parsing
            # Fix bullet lists without regex
            stripped = line.lstrip()
            if (
                stripped
                and stripped[0] in "-*"
                and len(stripped) > 1
                and not stripped[1].isspace()
            ):
                # Add space after bullet
                indent = line[: len(line) - len(stripped)]
                line = indent + stripped[0] + " " + stripped[1:]

            processed_lines.append(line.rstrip())  # Remove trailing whitespace

        # Fix 5: Collapse multiple blank lines
        final_lines = []
        consecutive_blanks = 0

        for line in processed_lines:
            if line.strip() == "":
                consecutive_blanks += 1
                if consecutive_blanks <= 2:
                    final_lines.append(line)
            else:
                consecutive_blanks = 0
                final_lines.append(line)

        return "\n".join(final_lines)

    def _report_abbreviation_issues(self, issues, definitions):
        """Report abbreviation issues to console with formatting"""
        if not issues:
            return

        print("\n" + "=" * 80)
        print("ABBREVIATION CHECK REPORT")
        print("=" * 80)
        print(f"\nFound {len(issues)} undefined abbreviation(s):")
        print("-" * 80)

        for issue in issues:
            print(f"\n[X] Line {issue.line_number}: '{issue.abbreviation}'")
            print(f"  Context: {issue.context}")
            if issue.suggested_definition:
                print(
                    f"  Suggestion: {issue.abbreviation} = {issue.suggested_definition}"
                )

        if definitions:
            print(f"\n\nFound {len(definitions)} defined abbreviation(s):")
            print("-" * 80)
            for defn in definitions:
                print(
                    f"\n[OK] Line {defn.line_number}: '{defn.abbreviation}' = '{defn.full_form}'"
                )

        print("\n" + "=" * 80)
        print("TIP: Define abbreviations when first used, e.g.:")
        print(
            "  'Machine Learning (ML) is a field...' or 'ML (Machine Learning) is a field...'"
        )
        print("=" * 80 + "\n")

    def process_markdown_file(
        self, file_path: str, show_progress: bool = True
    ) -> tuple[str, list[ValidationResult]]:
        """Process a markdown file and return corrected content"""
        self.logger.info(f"Processing file: {file_path}")

        # Read original content
        with open(file_path, encoding="utf-8") as f:
            original_content = f.read()

        # Apply preprocessing to fix common markdown issues
        preprocessed_content = self._preprocess_markdown(original_content)

        # Temporarily write preprocessed content for citation extraction
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as temp_file:
            temp_file.write(preprocessed_content)
            temp_path = temp_file.name

        try:
            # Pass 1: Extract all citations from preprocessed content
            citations = self.extract_citations_from_markdown(temp_path)
            self.logger.info(f"Found {len(citations)} citations in {file_path}")

            if not citations:
                return preprocessed_content, []
        finally:
            # Clean up temp file
            os.unlink(temp_path)

        # Pass 2: Validate each citation with progress tracking
        results = []

        if show_progress and len(citations) > 1:
            # Use tqdm progress bar for multiple citations
            with tqdm(
                total=len(citations),
                desc="Processing citations",
                unit="url",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}",
                dynamic_ncols=True,
            ) as pbar:
                for i, citation in enumerate(citations):
                    # Update progress bar description with current URL
                    domain = self._extract_domain(citation.url)
                    pbar.set_postfix_str(f"Fetching: {domain}")

                    result = self.validate_citation(citation, pbar=pbar)
                    results.append(result)

                    # Update progress bar with detailed result status
                    status = self._format_progress_status(result, domain)
                    pbar.set_postfix_str(status)
                    pbar.update(1)
        else:
            # No progress bar for single citation or when disabled
            for citation in citations:
                result = self.validate_citation(citation)
                results.append(result)

        # Apply corrections to preprocessed content (in reverse order to maintain positions)
        corrected_content = preprocessed_content
        for result in reversed(results):
            if result.corrected_text and result.corrected_url:
                old_link = f"[{result.citation.text}]({result.citation.url})"
                # Clean the corrected text by removing internal tags like "CACHE"
                clean_corrected_text = self._clean_citation_text(
                    result.corrected_text
                )
                new_link = f"[{clean_corrected_text}]({result.corrected_url})"
                corrected_content = corrected_content.replace(
                    old_link, new_link
                )

        return corrected_content, results

    def _clean_citation_text(self, citation_text: str) -> str:
        """
        Clean citation text by removing internal processing tags.

        Removes tags like 'CACHE', 'PDF', '#GUESSED', etc. that are used
        for internal tracking but shouldn't appear in final output.
        """
        if not citation_text:
            return citation_text

        # Remove common internal tags
        internal_tags = [
            " CACHE",
            "CACHE ",
            "CACHE",
            " PDF",
            "PDF ",
            "PDF",
            " #GUESSED",
            "#GUESSED ",
            "#GUESSED",
            " BLOCKED_RG",
            "BLOCKED_RG ",
            "BLOCKED_RG",
            " BLOCKED_MDPI",
            "BLOCKED_MDPI ",
            "BLOCKED_MDPI",
            " PARSE_ERROR",
            "PARSE_ERROR ",
            "PARSE_ERROR",
            " FETCH_ERROR",
            "FETCH_ERROR ",
            "FETCH_ERROR",
        ]

        cleaned_text = citation_text
        for tag in internal_tags:
            cleaned_text = cleaned_text.replace(tag, "")

        # Clean up any extra spaces
        cleaned_text = " ".join(cleaned_text.split())

        return cleaned_text

    def _extract_domain(self, url: str) -> str:
        """Extract a readable domain name from URL for progress display"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            # Simplify common domains
            if domain.startswith("www."):
                domain = domain[4:]
            # Truncate long domains
            if len(domain) > 20:
                domain = domain[:17] + "..."
            return domain
        except (AttributeError, TypeError):
            return url[:20] + "..." if len(url) > 20 else url

    def _format_progress_status(
        self, result: ValidationResult, domain: str
    ) -> str:
        """Format validation result for progress bar display"""
        # Check if result came from cache
        is_cached = "CACHE" in result.tags
        cache_indicator = "[CACHED]" if is_cached else ""

        if result.errors:
            # Show error with type indication
            error_msg = result.errors[0]
            if "AUTHOR VERIFICATION FAILED" in error_msg:
                return f"[!] AUTHOR ERROR{cache_indicator} {domain} - Wrong authors cited!"
            elif "403" in error_msg or "Forbidden" in error_msg:
                return f"ERROR{cache_indicator} {domain} - Access denied (403)"
            elif "404" in error_msg or "Not Found" in error_msg:
                return f"ERROR{cache_indicator} {domain} - Not found (404)"
            elif "timeout" in error_msg.lower():
                return f"ERROR{cache_indicator} {domain} - Timeout"
            elif "Failed to extract" in error_msg:
                return f"WARNING{cache_indicator} {domain} - No metadata found"
            else:
                # Truncate long error messages
                short_error = (
                    error_msg[:30] + "..." if len(error_msg) > 30 else error_msg
                )
                return f"ERROR{cache_indicator} {domain} - {short_error}"

        elif result.corrected_text:
            # Show successful correction
            corrected = (
                result.corrected_text[:25] + "..."
                if len(result.corrected_text) > 25
                else result.corrected_text
            )
            return f"SUCCESS{cache_indicator} {domain} - Fixed: {corrected}"

        else:
            # Show successful processing with tags
            if result.tags:
                # Filter out CACHE tag for display since we show the icon
                display_tags = [tag for tag in result.tags if tag != "CACHE"]
                if display_tags:
                    tags_str = " ".join(display_tags[:2])  # Show max 2 tags
                    return f"SUCCESS{cache_indicator} {domain} - {tags_str}"

            return f"SUCCESS{cache_indicator} {domain} - OK"

    def save_corrected_file(
        self, original_path: str, corrected_content: str
    ) -> str:
        """Save corrected content to a new file"""
        path = Path(original_path)
        corrected_path = path.parent / f"{path.stem}_corrected{path.suffix}"

        with open(corrected_path, "w", encoding="utf-8") as f:
            f.write(corrected_content)

        self.logger.info(f"Saved corrected file: {corrected_path}")
        return str(corrected_path)

    def save_log(self, results: list[ValidationResult], log_path: str):
        """Save validation results to a JSON log"""
        log_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_citations": len(results),
            "errors": sum(1 for r in results if r.errors),
            "warnings": sum(1 for r in results if r.warnings),
            "results": [],
        }

        for result in results:
            result_data = {
                "citation": asdict(result.citation),
                "bibtex": asdict(result.bibtex_entry)
                if result.bibtex_entry
                else None,
                "corrected_text": result.corrected_text,
                "corrected_url": result.corrected_url,
                "errors": result.errors,
                "warnings": result.warnings,
                "tags": result.tags,
                "confidence": result.confidence,
            }
            log_data["results"].append(result_data)

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2)

        self.logger.info(f"Saved log file: {log_path}")

    def _print_author_verification_report(
        self, results: list[ValidationResult]
    ):
        """Print a prominent report of author verification results"""
        author_errors = []
        for result in results:
            for error in result.errors:
                if "AUTHOR VERIFICATION FAILED" in error:
                    author_errors.append((result.citation, error))

        if author_errors:
            print("\n" + "=" * 80)
            print("[!] CRITICAL: AUTHOR VERIFICATION REPORT [!]")
            print("=" * 80)
            print(
                f"\nFound {len(author_errors)} citation(s) with INCORRECT AUTHORS:"
            )
            print("-" * 80)

            for citation, error in author_errors:
                print(f"\nLine {citation.line_number}: {error}")
                print(
                    f"  Context: {citation.context_before}[...]{citation.context_after}"
                )

            print("\n" + "=" * 80)
            print(
                "[!] These citations MUST be corrected! The authors in the text do not match"
            )
            print(
                "   the actual authors from the source URLs. Never trust author names without"
            )
            print("   verification against the actual publication source!")
            print("=" * 80 + "\n")

    def process_files(self, paths: list[str]):
        """Process multiple files or directories"""
        files_to_process = []

        for path in paths:
            if os.path.isfile(path):
                if path.endswith(".md"):
                    files_to_process.append(path)
            elif os.path.isdir(path):
                # Find all markdown files in directory
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.endswith(".md"):
                            files_to_process.append(os.path.join(root, file))

        self.logger.info(
            f"Found {len(files_to_process)} markdown files to process"
        )

        for file_path in files_to_process:
            try:
                # Process file
                corrected_content, results = self.process_markdown_file(
                    file_path
                )

                # Save corrected file
                corrected_path = self.save_corrected_file(
                    file_path, corrected_content
                )

                # Save log
                log_path = Path(file_path).with_suffix(".json")
                self.save_log(results, str(log_path))

                # Print summary
                print(f"\nProcessed: {file_path}")
                print(f"  Citations found: {len(results)}")
                print(f"  Errors: {sum(1 for r in results if r.errors)}")
                print(f"  Warnings: {sum(1 for r in results if r.warnings)}")
                print(f"  Corrected file: {corrected_path}")
                print(f"  Log file: {log_path}")

                # Print prominent author verification report
                self._print_author_verification_report(results)

            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {e}")
                print(f"Error processing {file_path}: {e}")


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description="Check and correct bibliographic entries in Markdown files"
    )
    parser.add_argument(
        "paths", nargs="+", help="Markdown files or directories to process"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "-d",
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    # Create checker instance
    checker = BiblioChecker(verbose=args.verbose, delay=args.delay)

    # Process files
    checker.process_files(args.paths)


if __name__ == "__main__":
    main()
