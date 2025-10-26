"""Citation extraction and management for markdown to LaTeX conversion."""

# Standard library imports
import json
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Third-party imports
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# Local imports
from src.converters.md_to_latex.citation_cache import CitationCache
from src.converters.md_to_latex.citation_extractor_unified import (
    UnifiedCitationExtractor,
)
from src.converters.md_to_latex.utils import (
    convert_html_entities,
    convert_unicode_to_latex,
    extract_doi_from_url,
    generate_citation_key,
    sanitize_latex,
)
from src.converters.md_to_latex.zotero_integration import ZoteroClient

logger = logging.getLogger(__name__)


class Citation:
    """Represents a single citation."""

    def __init__(
        self,
        authors: str,
        year: str,
        url: str,
        key: str | None = None,
        use_better_bibtex: bool = True,
    ):
        self.authors = authors
        self.year = year
        self.url = url
        self.title = ""
        self.journal = ""
        self.volume = ""
        self.pages = ""
        self.doi = extract_doi_from_url(url)
        self.bibtex_type = "misc"
        self.raw_bibtex = None
        self.issue = ""  # Add issue number
        self.full_authors = ""  # Store full author list for BibTeX
        self.abstract = ""  # Store abstract for arXiv papers
        self.arxiv_category = ""  # Store arXiv category
        self.use_better_bibtex = use_better_bibtex

        # Generate key - will be regenerated after title is available if using Better BibTeX
        self.key = key or generate_citation_key(
            authors, year, "", use_better_bibtex=False
        )  # Start with simple key

    def regenerate_key_with_title(self) -> str:
        """Regenerate citation key using title if Better BibTeX is enabled."""
        if self.use_better_bibtex and self.title:
            new_key = generate_citation_key(
                self.authors, self.year, self.title, use_better_bibtex=True
            )
            self.key = new_key
        return self.key

    def _escape_bibtex(self, text: str) -> str:
        r"""Escape special characters for BibTeX.

        Pipeline:
            1. Convert HTML entities (&amp; → &)
            2. Convert Unicode to LaTeX (ε → $\epsilon$)
            3. Remove markdown links
            4. Escape LaTeX special characters (& → \&, _ → \_, etc.)
            5. Handle quotes
            6. Clean up whitespace
        """
        if not text:
            return text

        # Step 1: Convert HTML entities first
        text = convert_html_entities(text)

        # Step 2: Convert Unicode characters to LaTeX commands
        text = convert_unicode_to_latex(text)

        # Step 3: Remove markdown links (before escaping brackets)
        while "[" in text and "]" in text and "(" in text and ")" in text:
            start = text.find("[")
            end = text.find("]", start)
            if end > start and end + 1 < len(text) and text[end + 1] == "(":
                paren_end = text.find(")", end + 2)
                if paren_end > end:
                    text = text[:start] + text[paren_end + 1 :]
                else:
                    break
            else:
                break

        # Step 4: Escape LaTeX special characters
        text = sanitize_latex(text)

        # Step 5: Handle quotes (after escaping, to avoid double-escape)
        # Smart quotes in titles should become LaTeX quotes
        text = text.replace('"', "``")
        text = text.replace('"', "''")

        # Step 6: Clean up multiple spaces
        while "  " in text:
            text = text.replace("  ", " ")
        text = text.strip()

        return text

    def to_bibtex(self) -> str:
        """Convert citation to BibTeX format."""
        if self.raw_bibtex:
            return self.raw_bibtex

        # Build BibTeX entry
        lines = [f"@{self.bibtex_type}{{{self.key},"]

        # Add authors - use full author list if available
        authors_to_use = (
            self.full_authors if self.full_authors else self.authors
        )

        # CRITICAL FIX: Validate author data to prevent "et al" as sole author
        if (
            authors_to_use
            and " et al" in authors_to_use
            and not self.full_authors
        ):
            # We have "Author et al" but no full author list from metadata
            # Extract just the first author
            first_author = authors_to_use.split(" et al")[0].strip()
            if first_author:
                # Add "and others" to indicate multiple authors
                authors_to_use = f"{first_author} and others"
            else:
                # Fallback if extraction fails - use "{Anonymous}" to avoid BibTeX style issues
                authors_to_use = "{Anonymous}"
        elif not authors_to_use or authors_to_use.strip() == "":
            # Empty author field - use "{Anonymous}" (curly braces prevent case changes)
            authors_to_use = "{Anonymous}"

        clean_authors = self._escape_bibtex(authors_to_use)
        # Limit author field length to prevent malformed entries
        if len(clean_authors) > 500:  # Increased limit for full author lists
            clean_authors = clean_authors[:497] + "..."
        lines.append(f'  author = "{clean_authors}",')

        # Add title
        if self.title:
            lines.append(f'  title = "{self._escape_bibtex(self.title)}",')

        # Add year - use "0000" instead of "Unknown" for BibTeX compatibility
        # The .bst file has issues with non-numeric years like "n.d." or "Unknown"
        year_to_use = (
            self.year if self.year and self.year != "Unknown" else "0000"
        )
        lines.append(f'  year = "{year_to_use}",')

        # Add journal if available
        if self.journal:
            lines.append(f'  journal = "{self._escape_bibtex(self.journal)}",')

        # Add volume if available
        if self.volume:
            lines.append(f'  volume = "{self.volume}",')

        # Add issue if available
        if self.issue:
            lines.append(f'  number = "{self.issue}",')

        # Add pages if available
        if self.pages:
            lines.append(f'  pages = "{self.pages}",')

        # Add DOI if available
        if self.doi:
            lines.append(f'  doi = "{self.doi}",')

        # Add URL
        lines.append(f'  url = "{self.url}",')

        # Add access date
        lines.append(f'  urldate = "{datetime.now().strftime("%Y-%m-%d")}",')

        lines.append("}")

        return "\n".join(lines)


class CitationManager:
    """Manages citation extraction, fetching, and caching."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        prefer_arxiv: bool = False,
        zotero_api_key: str | None = None,
        zotero_library_id: str | None = None,
        use_cache: bool = True,
        use_better_bibtex_keys: bool = True,
    ):
        self.citations: dict[str, Citation] = {}
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        self.use_better_bibtex_keys = use_better_bibtex_keys
        # Initialize SQLite cache only if enabled
        self.cache = (
            CitationCache(cache_dir=self.cache_dir) if use_cache else None
        )
        self.prefer_arxiv = prefer_arxiv  # Option to prefer arXiv metadata

        # Initialize Zotero client if configured
        self.zotero_client = None
        if zotero_api_key or zotero_library_id:
            self.zotero_client = ZoteroClient(
                api_key=zotero_api_key, library_id=zotero_library_id
            )
            logger.info(
                f"Initialized Zotero client with library_id: {zotero_library_id}"
            )

        # No need to load cache explicitly - SQLite cache handles it

    def _load_from_cache(self, url: str) -> Citation | None:
        """Load a citation from SQLite cache."""
        if not self.cache:
            return None
        cache_data = self.cache.get(url)
        if cache_data:
            # Create Citation object from cached data
            citation = Citation(
                authors=cache_data.get("authors", ""),
                year=cache_data.get("year", ""),
                url=url,
                use_better_bibtex=self.use_better_bibtex_keys,
            )
            citation.title = cache_data.get("title", "")
            citation.journal = cache_data.get("journal", "")
            citation.volume = cache_data.get("volume", "")
            citation.pages = cache_data.get("pages", "")
            citation.doi = cache_data.get("doi", "")
            citation.bibtex_type = cache_data.get("bibtex_type", "misc")
            citation.raw_bibtex = cache_data.get("raw_bibtex")
            citation.issue = cache_data.get("issue", "")
            citation.full_authors = cache_data.get("full_authors", "")
            citation.abstract = cache_data.get("abstract", "")
            citation.arxiv_category = cache_data.get("arxiv_category", "")
            return citation
        return None
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    cache_data = json.load(f)
                    logger.info(f"Loaded {len(cache_data)} cached citations")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load citation cache: {e}")

    def _save_to_cache(
        self, citation: Citation, source: str = "unknown"
    ) -> None:
        """Save a citation to SQLite cache."""
        if not self.cache:
            return
        cache_data = {
            "authors": citation.authors,
            "year": citation.year,
            "title": citation.title,
            "journal": citation.journal,
            "volume": citation.volume,
            "pages": citation.pages,
            "doi": citation.doi,
            "bibtex_type": citation.bibtex_type,
            "raw_bibtex": citation.raw_bibtex,
            "issue": citation.issue,
            "full_authors": citation.full_authors,
            "abstract": citation.abstract,
            "arxiv_category": citation.arxiv_category,
        }
        self.cache.put(citation.url, cache_data, source)

    def extract_citations(self, content: str) -> list[Citation]:
        """Extract all citations from markdown content using AST parsing."""
        # Use mistletoe AST-based extractor for robust parsing
        extractor = UnifiedCitationExtractor()

        citations_found = []
        seen_urls = {}  # Track citations by URL to avoid duplicates
        seen_dois = {}  # Track citations by DOI to avoid duplicates

        # Extract all citations using AST (includes orphan citations)
        all_citations = extractor.extract_citations_from_markdown(content)
        logger.debug(f"Extractor found {len(all_citations)} citations")

        # Process each citation
        for cit_data in all_citations:
            url = cit_data["url"]
            authors = cit_data["authors"] or "Unknown"
            year = cit_data["year"] or str(datetime.now().year)

            # Skip if we've already processed this URL
            if url and url in seen_urls:
                continue

            # For orphan citations without URL, create a placeholder
            if not url and cit_data.get("is_orphan"):
                # Try to find a URL by searching for the authors/year combination
                # This is a fallback for cases like "[IBISWorld], 2023"
                url = f"#orphan-{authors.lower().replace(' ', '-')}-{year}"

            self._add_citation(
                authors, year, url, citations_found, seen_urls, seen_dois
            )

        logger.info(
            f"Extracted {len(citations_found)} unique citations from content"
        )
        return citations_found

    def _add_citation(
        self,
        authors: str,
        year: str,
        url: str,
        citations_found: list,
        seen_urls: dict,
        seen_dois: dict,
    ):
        """Helper to add a citation with deduplication."""
        # Clean up authors
        # Remove embedded links without regex
        while "]" in authors and "(" in authors:
            bracket_end = authors.find("]")
            paren_start = authors.find("(", bracket_end)
            if paren_start > bracket_end:
                paren_end = authors.find(")", paren_start)
                if paren_end > paren_start:
                    authors = (
                        authors[: bracket_end + 1] + authors[paren_end + 1 :]
                    )
                else:
                    break
            else:
                break
        # Remove brackets
        while "[" in authors and "]" in authors:
            start = authors.find("[")
            end = authors.find("]", start)
            if end > start:
                authors = authors[:start] + authors[end + 1 :]
            else:
                break
        authors = authors.strip()

        if not authors:
            authors = "Unknown"

        # Extract DOI if present
        doi = extract_doi_from_url(url)
        if doi and doi in seen_dois:
            return  # Already have this DOI

        # Generate citation key (simple version first, will regenerate with title later)
        base_key = generate_citation_key(
            authors, year, "", use_better_bibtex=False
        )
        key = base_key

        # Handle duplicate keys with alphabetic suffixes (a, b, c, ..., z, aa, ab, ...)
        counter = 1
        while key in self.citations:
            # Generate alphabetic suffix: 1→a, 2→b, ..., 26→z, 27→aa, 28→ab, etc.
            suffix = ""
            temp = counter
            while temp > 0:
                temp -= 1  # Make it 0-indexed
                suffix = chr(ord("a") + (temp % 26)) + suffix
                temp //= 26
            key = f"{base_key}{suffix}"
            counter += 1

        citation = Citation(
            authors,
            year,
            url,
            key,
            use_better_bibtex=self.use_better_bibtex_keys,
        )
        citations_found.append(citation)
        self.citations[key] = citation

        # Track this citation
        seen_urls[url] = key
        if doi:
            seen_dois[doi] = key

    def fetch_citation_metadata(self, citation: Citation) -> None:
        """Fetch additional metadata for a citation."""
        # Check SQLite cache first
        cached_citation = self._load_from_cache(citation.url)
        if cached_citation:
            # Update citation with cached data
            citation.title = cached_citation.title
            citation.journal = cached_citation.journal
            citation.volume = cached_citation.volume
            citation.pages = cached_citation.pages
            citation.doi = cached_citation.doi or citation.doi
            citation.bibtex_type = cached_citation.bibtex_type
            citation.raw_bibtex = cached_citation.raw_bibtex
            citation.issue = cached_citation.issue
            citation.full_authors = cached_citation.full_authors
            citation.abstract = cached_citation.abstract
            citation.arxiv_category = cached_citation.arxiv_category
            logger.debug(f"Loaded citation from cache: {citation.url}")
            return

        # Try Zotero first if available (usually has the best metadata)
        if self.zotero_client:
            logger.debug(
                f"Attempting Zotero search for citation: {citation.doi or citation.url}"
            )
            # Try with DOI first
            if citation.doi:
                logger.debug(f"Searching Zotero with DOI: {citation.doi}")
                zotero_data = self.zotero_client.search_by_identifier(
                    citation.doi
                )
                if zotero_data:
                    # Parse Zotero data to update citation fields
                    self._parse_zotero_data(citation, zotero_data)
                    citation.raw_bibtex = self.zotero_client.format_bibtex(
                        zotero_data
                    )
                    # Update citation key from BibTeX
                    # Extract key from BibTeX without regex
                    if (
                        citation.raw_bibtex
                        and "@" in citation.raw_bibtex
                        and "{" in citation.raw_bibtex
                    ):
                        at_pos = citation.raw_bibtex.find("@")
                        brace_pos = citation.raw_bibtex.find("{", at_pos)
                        comma_pos = citation.raw_bibtex.find(",", brace_pos)
                        if brace_pos > at_pos and comma_pos > brace_pos:
                            citation.key = citation.raw_bibtex[
                                brace_pos + 1 : comma_pos
                            ].strip()
                    logger.info(
                        f"Fetched metadata from Zotero for DOI: {citation.doi}"
                    )
                    # Save to cache
                    self._save_to_cache(citation, "zotero")
                    return

            # Try with arXiv ID
            elif "arxiv.org" in citation.url:
                # Extract arXiv ID without regex
                arxiv_id_match = None
                if "arxiv.org/abs/" in citation.url:
                    abs_pos = citation.url.find("arxiv.org/abs/")
                    arxiv_id = citation.url[abs_pos + 14 :]
                    # Validate format (YYYY.NNNNN)
                    if len(arxiv_id) >= 9 and arxiv_id[4] == ".":
                        if arxiv_id[:4].isdigit() and arxiv_id[5:9].isdigit():
                            arxiv_id_match = arxiv_id[:9]
                if arxiv_id_match:
                    zotero_data = self.zotero_client.search_by_identifier(
                        f"arXiv:{arxiv_id_match.group(1)}"
                    )
                    if zotero_data:
                        # Parse Zotero data to update citation fields
                        self._parse_zotero_data(citation, zotero_data)
                        citation.raw_bibtex = self.zotero_client.format_bibtex(
                            zotero_data
                        )
                        # Update citation key from BibTeX
                        # Extract key from BibTeX without regex
                        if (
                            citation.raw_bibtex
                            and "@" in citation.raw_bibtex
                            and "{" in citation.raw_bibtex
                        ):
                            at_pos = citation.raw_bibtex.find("@")
                            brace_pos = citation.raw_bibtex.find("{", at_pos)
                            comma_pos = citation.raw_bibtex.find(",", brace_pos)
                            if brace_pos > at_pos and comma_pos > brace_pos:
                                citation.key = citation.raw_bibtex[
                                    brace_pos + 1 : comma_pos
                                ].strip()
                        logger.info(
                            f"Fetched metadata from Zotero for arXiv: {arxiv_id_match.group(1)}"
                        )
                        # Save to cache
                        self._save_to_cache(citation, "zotero")
                        return

        # If Zotero didn't work, fall back to other sources
        # Determine fetch order based on preference
        if self.prefer_arxiv and "arxiv.org" in citation.url:
            # Prefer arXiv metadata when available
            self._fetch_from_arxiv(citation)
            # Fall back to CrossRef if arXiv didn't provide good data
            if citation.doi and (not citation.title or citation.title == ""):
                self._fetch_from_crossref(citation)
        elif citation.doi:
            # Default behavior: prefer CrossRef for DOI
            self._fetch_from_crossref(citation)
            # If we didn't get a good title, also try arXiv
            if "arxiv.org" in citation.url and (
                not citation.title or len(citation.title) < 10
            ):
                # Store CrossRef data temporarily
                crossref_title = citation.title
                crossref_authors = citation.authors

                # Fetch from arXiv
                self._fetch_from_arxiv(citation)

                # If arXiv didn't provide better title, keep CrossRef data
                if not citation.title or len(citation.title) < len(
                    crossref_title or ""
                ):
                    citation.title = crossref_title
                    citation.authors = crossref_authors
        elif "arxiv.org" in citation.url:
            # Only arXiv URL available
            self._fetch_from_arxiv(citation)
        else:
            # For web sources, try to determine appropriate type
            self._determine_web_source_type(citation)

        # Save to SQLite cache
        source = "unknown"
        if citation.doi:
            source = "crossref"
        elif "arxiv.org" in citation.url:
            source = "arxiv"
        elif citation.url.startswith("http"):
            source = "web"

        # Regenerate citation key with title if using Better BibTeX
        if self.use_better_bibtex_keys and citation.title:
            # Find the current registry key for this citation object
            current_registry_key = None
            for key, stored_citation in self.citations.items():
                if stored_citation is citation:  # Same object reference
                    current_registry_key = key
                    break

            # Generate new key
            new_key = citation.regenerate_key_with_title()

            # Update the citation registry if key changed and we found the current key
            if current_registry_key and current_registry_key != new_key:
                self.citations[new_key] = self.citations.pop(
                    current_registry_key
                )

        self._save_to_cache(citation, source)

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        if not self.cache:
            return {"error": "Cache is disabled"}
        return self.cache.get_stats()

    def clear_cache(self, older_than_days: int | None = None) -> int:
        """Clear cache entries."""
        if not self.cache:
            return 0
        return self.cache.clear(older_than_days)

    def _fetch_from_crossref(self, citation: Citation) -> None:
        """Fetch citation metadata from CrossRef."""
        try:
            # CrossRef API endpoint
            url = f"https://api.crossref.org/works/{citation.doi}"
            headers = {
                "User-Agent": "deep-biblio-tools/1.0 (https://github.com/petteriTeikari/deep-biblio-tools)"
            }

            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                work = data.get("message", {})

                # Extract full title
                titles = work.get("title", [])
                if titles:
                    citation.title = titles[0]

                # Extract authors properly
                authors_list = work.get("author", [])
                if authors_list:
                    author_names = []
                    for author in authors_list:
                        family = author.get("family", "")
                        given = author.get("given", "")
                        if family:
                            full_name = f"{given} {family}" if given else family
                            author_names.append(full_name)

                    if author_names:
                        # Format authors properly
                        if len(author_names) == 1:
                            citation.authors = author_names[0]
                        elif len(author_names) == 2:
                            citation.authors = (
                                f"{author_names[0]} and {author_names[1]}"
                            )
                        else:
                            # Use first author et al. for display, but store all authors
                            citation.authors = f"{author_names[0]} et al."
                            # Store full author list for BibTeX
                            citation.full_authors = " and ".join(author_names)

                        # Regenerate key with proper author name
                        new_key = generate_citation_key(
                            citation.authors,
                            citation.year,
                            citation.title,
                            use_better_bibtex=self.use_better_bibtex_keys,
                        )
                        if citation.title:
                            # Add first significant word from title
                            title_word = self._get_first_significant_word(
                                citation.title
                            )
                            if title_word:
                                new_key = new_key + title_word
                        citation.key = new_key

                # Extract other metadata
                container_titles = work.get("container-title", [])
                if container_titles:
                    citation.journal = container_titles[0]
                citation.volume = str(work.get("volume", ""))
                citation.pages = work.get("page", "")

                # Add issue number if available
                issue = work.get("issue", "")
                if issue:
                    citation.issue = str(issue)

                # Determine type
                work_type = work.get("type", "")
                if work_type == "journal-article":
                    citation.bibtex_type = "article"
                elif work_type == "book-chapter":
                    citation.bibtex_type = "incollection"
                elif work_type == "proceedings-article":
                    citation.bibtex_type = "inproceedings"
                elif work_type == "book":
                    citation.bibtex_type = "book"
                elif work_type == "thesis":
                    citation.bibtex_type = "phdthesis"
                else:
                    citation.bibtex_type = "misc"

                logger.info(
                    f"Fetched metadata from CrossRef for DOI: {citation.doi}"
                )

        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to fetch from CrossRef: {e}")

    def _parse_zotero_data(self, citation: Citation, zotero_data: dict) -> None:
        """Parse Zotero data and update citation fields."""
        # Update title
        if "title" in zotero_data:
            citation.title = zotero_data["title"]

        # Update authors
        if "creators" in zotero_data:
            creators = zotero_data["creators"]
            author_names = []
            for creator in creators:
                if creator.get("creatorType") == "author":
                    if "firstName" in creator and "lastName" in creator:
                        name = f"{creator['firstName']} {creator['lastName']}"
                    elif "name" in creator:
                        name = creator["name"]
                    else:
                        continue
                    author_names.append(name)

            if author_names:
                if len(author_names) == 1:
                    citation.authors = author_names[0]
                elif len(author_names) == 2:
                    citation.authors = (
                        f"{author_names[0]} and {author_names[1]}"
                    )
                else:
                    citation.authors = f"{author_names[0]} et al."
                    citation.full_authors = " and ".join(author_names)

        # Update year
        if "date" in zotero_data:
            # Extract year without regex
            date_str = zotero_data["date"]
            for i in range(len(date_str) - 3):
                if date_str[i : i + 4].isdigit():
                    year_candidate = date_str[i : i + 4]
                    if year_candidate.startswith(("19", "20")):
                        citation.year = year_candidate
                        break

        # Update journal/publication
        if "publicationTitle" in zotero_data:
            citation.journal = zotero_data["publicationTitle"]

        # Update volume, issue, pages
        if "volume" in zotero_data:
            citation.volume = str(zotero_data["volume"])
        if "issue" in zotero_data:
            citation.issue = str(zotero_data["issue"])
        if "pages" in zotero_data:
            citation.pages = zotero_data["pages"]

        # Update DOI if provided
        if "DOI" in zotero_data:
            citation.doi = zotero_data["DOI"]

        # Update abstract
        if "abstractNote" in zotero_data:
            citation.abstract = zotero_data["abstractNote"]

        # Determine BibTeX type
        item_type = zotero_data.get("itemType", "misc")
        type_map = {
            "journalArticle": "article",
            "book": "book",
            "bookSection": "incollection",
            "conferencePaper": "inproceedings",
            "thesis": "phdthesis",
            "report": "techreport",
            "webpage": "misc",
            "preprint": "article",
        }
        citation.bibtex_type = type_map.get(item_type, "misc")

    def _get_first_significant_word(self, title: str) -> str:
        """Extract first significant word from title for Better BibTeX key."""
        # Skip common words
        skip_words = {
            "a",
            "an",
            "the",
            "of",
            "in",
            "on",
            "at",
            "to",
            "for",
            "with",
            "by",
        }

        # Clean title and split into words
        # Clean title without regex - keep only letters and spaces
        clean_chars = []
        for char in title:
            if char.isalpha() or char.isspace():
                clean_chars.append(char)
        clean_title = "".join(clean_chars)
        words = clean_title.split()

        # Find first significant word
        for word in words:
            if word.lower() not in skip_words and len(word) > 2:
                # Return in camelCase for Better BibTeX style
                return word[0].upper() + word[1:].lower()

        return ""

    def _fetch_from_arxiv(self, citation: Citation) -> None:
        """Fetch citation metadata from arXiv."""
        try:
            # Extract arXiv ID from URL (handle both old and new format)
            # Extract arXiv ID without regex
            arxiv_id = None
            if "arxiv.org/abs/" in citation.url:
                abs_pos = citation.url.find("arxiv.org/abs/")
                remaining = citation.url[abs_pos + 14 :]

                # Try new format (YYYY.NNNNN)
                if len(remaining) >= 9 and remaining[4] == ".":
                    if remaining[:4].isdigit() and remaining[5:9].isdigit():
                        # Check for version
                        end_pos = 9
                        if (
                            len(remaining) > 10
                            and remaining[9] == "v"
                            and remaining[10:]
                            .split("/")[0]
                            .split("?")[0]
                            .isdigit()
                        ):
                            version_end = 10
                            while (
                                version_end < len(remaining)
                                and remaining[version_end].isdigit()
                            ):
                                version_end += 1
                            end_pos = version_end
                        arxiv_id = remaining[:end_pos]

                # Try old format (subject/NNNNNNN)
                if not arxiv_id:
                    slash_pos = remaining.find("/")
                    if slash_pos > 0:
                        subject = remaining[:slash_pos]
                        # Check if subject is valid (letters and hyphens)
                        if all(c.isalpha() or c == "-" for c in subject):
                            number_part = (
                                remaining[slash_pos + 1 :]
                                .split("v")[0]
                                .split("/")[0]
                                .split("?")[0]
                            )
                            if number_part.isdigit():
                                arxiv_id = remaining[
                                    : slash_pos + 1 + len(number_part)
                                ]
                                # Check for version
                                if "v" in remaining[slash_pos + 1 :]:
                                    v_pos = remaining.find("v", slash_pos + 1)
                                    version_part = (
                                        remaining[v_pos + 1 :]
                                        .split("/")[0]
                                        .split("?")[0]
                                    )
                                    if version_part.isdigit():
                                        arxiv_id = remaining[
                                            : v_pos + 1 + len(version_part)
                                        ]

            if not arxiv_id:
                return

            # arXiv API endpoint
            url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"

            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Parse XML response properly
                content = response.text

                # Extract entry
                # Extract entry without regex
                entry_start = content.find("<entry>")
                entry_end = content.find("</entry>", entry_start)
                entry_match = None
                if entry_start >= 0 and entry_end > entry_start:
                    entry_match = content[entry_start + 7 : entry_end]
                if not entry_match:
                    return

                entry_content = entry_match

                # Extract title (clean up newlines and extra spaces)
                # Extract title without regex
                title_start = entry_content.find("<title>")
                title_end = entry_content.find("</title>", title_start)
                if title_start >= 0 and title_end > title_start:
                    title = entry_content[title_start + 7 : title_end].strip()
                    # Clean up title - remove newlines and extra spaces
                    title = " ".join(title.split())
                    citation.title = title

                    # Update key with title word for Better BibTeX style
                    if citation.title:
                        title_word = self._get_first_significant_word(
                            citation.title
                        )
                        if title_word and not citation.key.endswith(title_word):
                            citation.key = citation.key + title_word

                # Extract authors
                authors = []
                # Extract authors without regex
                search_pos = 0
                while True:
                    name_start = entry_content.find("<name>", search_pos)
                    if name_start == -1:
                        break
                    name_end = entry_content.find("</name>", name_start)
                    if name_end == -1:
                        break
                    author_name = entry_content[
                        name_start + 6 : name_end
                    ].strip()
                    authors.append(author_name)
                    search_pos = name_end + 7

                if authors:
                    if len(authors) == 1:
                        citation.authors = authors[0]
                    elif len(authors) == 2:
                        citation.authors = f"{authors[0]} and {authors[1]}"
                    else:
                        # Store all authors for BibTeX
                        citation.full_authors = " and ".join(authors)
                        citation.authors = f"{authors[0]} et al."

                # Extract published date (year)
                # Extract published year without regex
                published_start = entry_content.find("<published>")
                if published_start >= 0:
                    year_start = published_start + 11
                    # Extract 4-digit year
                    if (
                        year_start + 4 <= len(entry_content)
                        and entry_content[year_start : year_start + 4].isdigit()
                    ):
                        citation.year = entry_content[
                            year_start : year_start + 4
                        ]

                # Extract abstract if needed
                # Extract abstract without regex
                summary_start = entry_content.find("<summary>")
                summary_end = entry_content.find("</summary>", summary_start)
                if summary_start >= 0 and summary_end > summary_start:
                    abstract = entry_content[
                        summary_start + 9 : summary_end
                    ].strip()
                    # Clean up abstract - remove extra spaces
                    abstract = " ".join(abstract.split())
                    # Store abstract as a note (optional)
                    citation.abstract = abstract

                # Set journal and type
                citation.journal = "arXiv"
                citation.bibtex_type = "article"

                # Extract arXiv category
                # Extract category without regex
                category_match = None
                cat_pos = entry_content.find("<category")
                if cat_pos >= 0:
                    term_pos = entry_content.find('term="', cat_pos)
                    if term_pos >= 0:
                        term_start = term_pos + 6
                        term_end = entry_content.find('"', term_start)
                        if term_end > term_start:
                            category_match = entry_content[term_start:term_end]
                if category_match:
                    citation.arxiv_category = category_match

                logger.info(f"Fetched metadata from arXiv for ID: {arxiv_id}")

        except (requests.RequestException, AttributeError, ValueError) as e:
            logger.warning(f"Failed to fetch from arXiv: {e}")

    def _fetch_web_page_metadata(self, citation: Citation) -> None:
        """Fetch metadata from web page including title, authors, and dates."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(citation.url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.warning(
                    f"Failed to fetch {citation.url}: HTTP {response.status_code}"
                )
                return

            soup = BeautifulSoup(response.content, "lxml")

            # Extract title
            title = None
            # Try multiple methods to get the title
            # 1. Open Graph title
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"]
            # 2. Twitter title
            elif soup.find("meta", {"name": "twitter:title"}):
                title = soup.find("meta", {"name": "twitter:title"})["content"]
            # 3. Regular title tag
            elif soup.find("title"):
                title = soup.find("title").string

            if title:
                citation.title = title.strip()

            # Extract authors
            authors = []
            # Try JSON-LD structured data
            json_ld_scripts = soup.find_all(
                "script", type="application/ld+json"
            )
            for script in json_ld_scripts:
                try:
                    if script.string is None:
                        continue
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        # Check for author field
                        if "author" in data:
                            author_data = data["author"]
                            if (
                                isinstance(author_data, dict)
                                and "name" in author_data
                            ):
                                authors.append(author_data["name"])
                            elif isinstance(author_data, list):
                                for author in author_data:
                                    if (
                                        isinstance(author, dict)
                                        and "name" in author
                                    ):
                                        authors.append(author["name"])
                            elif isinstance(author_data, str):
                                authors.append(author_data)
                except json.JSONDecodeError:
                    pass

            # Try meta tags for authors
            if not authors:
                author_meta = soup.find("meta", {"name": "author"})
                if author_meta and author_meta.get("content"):
                    authors.append(author_meta["content"])

            # Try article:author
            if not authors:
                article_authors = soup.find_all(
                    "meta", property="article:author"
                )
                for author_meta in article_authors:
                    if author_meta.get("content"):
                        authors.append(author_meta["content"])

                # Try to find authors in page text
                # NOTE: Regex-based pattern matching was removed to comply with no-regex policy
                # For now, we rely on structured data (JSON-LD, meta tags) for author extraction
                # If needed, implement AST-based parsing or string matching for specific patterns

                # Filter out common false positives
                authors = [
                    a
                    for a in authors
                    if len(a.split()) <= 4
                    and not any(
                        word in a.lower()
                        for word in [
                            "click",
                            "here",
                            "more",
                            "read",
                            "view",
                            "see",
                        ]
                    )
                ][:3]  # Limit to first 3 authors

            if authors:
                if len(authors) == 1:
                    citation.authors = authors[0]
                elif len(authors) == 2:
                    citation.authors = f"{authors[0]} and {authors[1]}"
                else:
                    citation.authors = f"{authors[0]} et al."
                    citation.full_authors = " and ".join(authors)

            # Extract publication date
            pub_date = None
            # Try multiple date sources
            date_meta_names = [
                "article:published_time",
                "datePublished",
                "publish_date",
                "publication_date",
                "date",
                "DC.date.issued",
            ]

            for date_name in date_meta_names:
                date_meta = soup.find(
                    "meta", {"property": date_name}
                ) or soup.find("meta", {"name": date_name})
                if date_meta and date_meta.get("content"):
                    pub_date = date_meta["content"]
                    break

            # Extract year from date
            if pub_date:
                # Extract year without regex
                for i in range(len(pub_date) - 3):
                    if pub_date[i : i + 4].isdigit():
                        year_candidate = pub_date[i : i + 4]
                        if year_candidate.startswith(("19", "20")):
                            citation.year = year_candidate
                            break

            logger.info(
                f"Fetched web metadata for {citation.url}: title='{citation.title}', authors='{citation.authors}'"
            )

        except (requests.RequestException, AttributeError, ValueError) as e:
            logger.warning(
                f"Failed to fetch web page metadata for {citation.url}: {e}"
            )

    def _determine_web_source_type(self, citation: Citation) -> None:
        """Determine the appropriate BibTeX type for web sources."""
        url = citation.url.lower()

        # Skip metadata fetching for PDF URLs
        if not url.endswith(".pdf"):
            # First try to fetch actual metadata from the web page
            self._fetch_web_page_metadata(citation)

        # Check for specific patterns in URL or domain
        if "blog" in url or "/blog/" in url:
            citation.bibtex_type = (
                "misc"  # BibTeX doesn't have blogPost, use misc
            )
            citation.journal = "Blog post"
        elif any(news in url for news in ["news", "press", "article", "story"]):
            citation.bibtex_type = "misc"
            citation.journal = "Web article"
        elif any(
            govt in url for govt in [".gov", "government", "federal", "state"]
        ):
            citation.bibtex_type = "techreport"
            citation.journal = "Government report"
        elif "github.com" in url:
            citation.bibtex_type = "misc"
            citation.journal = "Software repository"
        elif any(report in url for report in ["report", "whitepaper", "paper"]):
            citation.bibtex_type = "techreport"
        else:
            citation.bibtex_type = "misc"
            citation.journal = "Web page"

        # Set a generic title if we still don't have one
        if not citation.title:
            if citation.authors and citation.authors != "Unknown":
                citation.title = f"{citation.journal} by {citation.authors}"
            else:
                citation.title = citation.journal

        # Try to extract organization from URL if no author
        if citation.authors == "Unknown" or not citation.authors:
            # Extract domain name as organization
            try:
                domain = urlparse(citation.url).netloc
                domain = (
                    domain.replace("www.", "")
                    .replace(".com", "")
                    .replace(".org", "")
                )
                domain = domain.replace(".", " ").title()
                citation.authors = domain
            except (AttributeError, ImportError):
                pass

    def replace_citations_in_text(self, content: str) -> str:
        """Replace markdown citations with LaTeX cite commands."""
        # Create a list of replacements to make
        replacements = []

        # For each citation we've stored, find it in the content and prepare replacement
        for key, citation in self.citations.items():
            if not citation.url.startswith("#orphan-"):
                # Regular citation with URL - create the markdown pattern
                # We need to find [some text](exact_url)
                # Since we have the exact URL, we can be precise
                search_pattern = f"]({citation.url})"

                # Find all occurrences of this URL pattern
                pos = 0
                while True:
                    pos = content.find(search_pattern, pos)
                    if pos == -1:
                        break

                    # Find the opening bracket by going backwards
                    bracket_pos = pos - 1
                    depth = 0
                    while bracket_pos >= 0:
                        if content[bracket_pos] == "]":
                            depth += 1
                        elif content[bracket_pos] == "[":
                            if depth == 0:
                                # Found the matching opening bracket
                                replacements.append(
                                    {
                                        "start": bracket_pos,
                                        "end": pos + len(search_pattern),
                                        "replacement": f"\\citep{{{citation.key}}}",
                                    }
                                )
                                break
                            else:
                                depth -= 1
                        bracket_pos -= 1

                    pos += len(search_pattern)
            else:
                # Orphan citation - these are trickier
                # For now, log them
                logger.info(
                    f"Orphan citation to be handled manually: {citation.authors} ({citation.year})"
                )

        # Sort replacements by position (descending) to avoid position shifts
        replacements.sort(key=lambda x: x["start"], reverse=True)

        # Apply replacements
        for repl in replacements:
            content = (
                content[: repl["start"]]
                + repl["replacement"]
                + content[repl["end"] :]
            )

        return content

    def generate_bibtex_file(
        self, output_path: Path, show_progress: bool = False
    ) -> None:
        """Generate BibTeX file with all citations."""
        bibtex_entries = []
        citations_list = sorted(self.citations.items())

        # Create progress bar for metadata fetching if requested
        if show_progress and citations_list:
            citation_pbar = tqdm(
                citations_list,
                desc="Fetching citation metadata",
                unit="citations",
                leave=False,  # Don't leave the bar after completion
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            )
        else:
            citation_pbar = citations_list

        for key, citation in citation_pbar:
            # Update description with current citation being processed
            if show_progress and citations_list:
                citation_pbar.set_description(
                    f"Fetching: {citation.authors[:30]}..."
                )

            # Fetch metadata if not already done
            self.fetch_citation_metadata(citation)
            bibtex_entries.append(citation.to_bibtex())

        # Cache is now saved automatically after each citation fetch

        # Write BibTeX file
        with open(output_path, "w") as f:
            f.write("\n\n".join(bibtex_entries))

        logger.info(
            f"Generated BibTeX file with {len(bibtex_entries)} entries: {output_path}"
        )
