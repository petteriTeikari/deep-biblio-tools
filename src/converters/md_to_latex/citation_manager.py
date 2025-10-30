"""Citation extraction and management for markdown to LaTeX conversion."""

# Standard library imports
import html
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Third-party imports
import requests
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt
from markdown_it.token import Token
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
    normalize_arxiv_url,
    normalize_url,
    sanitize_latex,
)
from src.converters.md_to_latex.zotero_auto_add import ZoteroAutoAdd
from src.converters.md_to_latex.zotero_integration import ZoteroClient

logger = logging.getLogger(__name__)


class Citation:
    """Represents a single citation."""

    def __init__(
        self,
        authors: str,
        year: str,
        url: str,
        key: str,
        use_better_bibtex: bool = True,
    ):
        """Initialize Citation with required Better BibTeX key.

        Args:
            authors: Author string
            year: Publication year
            url: Citation URL
            key: Better BibTeX citation key (REQUIRED - from Zotero)
            use_better_bibtex: Deprecated - kept for compatibility

        Raises:
            ValueError: If key is not provided or invalid format
        """
        from src.converters.md_to_latex.utils import is_valid_zotero_key

        if not key:
            raise ValueError(
                "Citation key is REQUIRED. Must come from Zotero (Web API or Better BibTeX plugin).\n"
                "Use load_collection_with_keys() to get keys from Zotero."
            )

        # Validate Zotero key format (accepts both Web API and Better BibTeX)
        if not is_valid_zotero_key(key):
            logger.warning(
                f"Citation key '{key}' does not match Zotero format. "
                f"Expected: Web API (author_title_year) or Better BibTeX (authorTitleYear)"
            )

        self.key = key
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
        self.issue = ""
        self.full_authors = ""
        self.abstract = ""
        self.arxiv_category = ""
        self.use_better_bibtex = use_better_bibtex

    def regenerate_key_with_title(self) -> str:
        """DEPRECATED: Key regeneration is forbidden.

        Citation keys must come from Zotero Better BibTeX and never be regenerated.
        This method is kept for API compatibility but does nothing.

        Returns:
            The existing key (unchanged)
        """
        logger.debug(
            "regenerate_key_with_title() called but key regeneration is forbidden. "
            "Returning existing key."
        )
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
                # Fallback if extraction fails
                authors_to_use = "Anonymous"
        elif not authors_to_use or authors_to_use.strip() == "":
            # Empty author field
            authors_to_use = "Anonymous"

        clean_authors = self._escape_bibtex(authors_to_use)
        # Limit author field length to prevent malformed entries
        if len(clean_authors) > 500:  # Increased limit for full author lists
            clean_authors = clean_authors[:497] + "..."
        lines.append(f'  author = "{clean_authors}",')

        # Add title
        if self.title:
            lines.append(f'  title = "{self._escape_bibtex(self.title)}",')

        # Add year - use "1900" instead of "Unknown" for BibTeX compatibility
        # The .bst file has issues with year="0000" causing malformed natexlab
        year_to_use = (
            self.year if self.year and self.year != "Unknown" else "1900"
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
        zotero_collection: str | None = None,
        use_cache: bool = True,
        use_better_bibtex_keys: bool = True,
        enable_auto_add: bool = True,
        auto_add_dry_run: bool = True,
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
        self.zotero_collection = zotero_collection  # Store collection name

        # Initialize Zotero client if configured
        self.zotero_client = None
        self.zotero_entries = {}  # Dict mapping citation keys to BibTeX entries

        # CRITICAL: If Zotero keys are required, credentials MUST be configured
        if use_better_bibtex_keys and not (
            zotero_api_key and zotero_library_id
        ):
            error_msg = (
                "CRITICAL ERROR: Zotero keys are required but credentials are missing.\n"
                "Set ZOTERO_API_KEY and ZOTERO_LIBRARY_ID in .env file.\n\n"
                "Zotero keys prevent local key generation. Accepts two formats:\n"
                "  - Web API keys: author_title_year (e.g., niinimaki_environmental_2020)\n"
                "  - Better BibTeX plugin keys: authorTitleYear (e.g., adisornDigitalProductPassport2021)\n\n"
                "Both are deterministic and from Zotero."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        if zotero_api_key or zotero_library_id:
            self.zotero_client = ZoteroClient(
                api_key=zotero_api_key, library_id=zotero_library_id
            )
            logger.info(
                f"Initialized Zotero client with library_id: {zotero_library_id}"
            )

            # Load collection with Better BibTeX keys if specified
            if zotero_collection:
                try:
                    self.zotero_entries = (
                        self.zotero_client.load_collection_with_keys(
                            zotero_collection
                        )
                    )
                    logger.info(
                        f"Loaded {len(self.zotero_entries)} entries from Zotero collection '{zotero_collection}'"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to load Zotero collection '{zotero_collection}': {e}"
                    )
                    # Continue without Zotero collection (will fall back to API lookups)

        # No need to load cache explicitly - SQLite cache handles it

        # Phase 1: Auto-add and policy enforcement infrastructure
        self._doi_validation_cache: dict[
            str, bool
        ] = {}  # Cache DOI HEAD requests
        self._citation_errors: list[
            dict
        ] = []  # Track all errors for end report
        self.citation_matcher = None  # Will be set if auto-add is enabled

        # Initialize auto-add system (after zotero_client initialization)
        self.zotero_auto_add = None
        if enable_auto_add and self.zotero_client and zotero_collection:
            try:
                self.zotero_auto_add = ZoteroAutoAdd(
                    zotero_client=self.zotero_client,
                    collection_name=zotero_collection,
                    translation_server_url="http://localhost:1969",
                    dry_run=auto_add_dry_run,
                    max_auto_add=50,  # Threshold limit
                )
                mode = "DRY-RUN" if auto_add_dry_run else "REAL"
                logger.info(f"Auto-add initialized in {mode} mode")
            except Exception as e:
                logger.warning(f"Auto-add initialization failed: {e}")
                self.zotero_auto_add = None

    def _lookup_zotero_entry_by_url(
        self, url: str
    ) -> tuple[str, dict[str, Any]] | None:
        """Look up Zotero entry by URL or DOI.

        Args:
            url: The URL or DOI URL to lookup

        Returns:
            Tuple of (citation_key, entry_dict) if found, None otherwise
        """
        if not self.zotero_entries:
            return None

        # Extract DOI if present in URL
        doi = extract_doi_from_url(url)

        # Search through Zotero entries for matching URL or DOI
        for cite_key, entry in self.zotero_entries.items():
            entry_url = entry.get("url", "")
            entry_doi = entry.get("doi", "")

            # Match by DOI (most reliable)
            if doi and entry_doi and doi == entry_doi:
                logger.debug(
                    f"Found Zotero entry by DOI match: {cite_key} (DOI: {doi})"
                )
                return (cite_key, entry)

            # Match by URL (exact match)
            if url and entry_url and url == entry_url:
                logger.debug(f"Found Zotero entry by URL match: {cite_key}")
                return (cite_key, entry)

            # Match by normalized URL (handle trailing slashes, http vs https)
            if url and entry_url:
                normalized_url = url.rstrip("/").replace("http://", "https://")
                normalized_entry_url = entry_url.rstrip("/").replace(
                    "http://", "https://"
                )
                if normalized_url == normalized_entry_url:
                    logger.debug(
                        f"Found Zotero entry by normalized URL match: {cite_key}"
                    )
                    return (cite_key, entry)

        logger.debug(f"No Zotero entry found for URL: {url}")
        return None

    def _load_from_cache(self, url: str) -> Citation | None:
        """Load a citation from SQLite cache."""
        if not self.cache:
            return None
        cache_data = self.cache.get(url)
        if cache_data:
            # Create Citation object from cached data
            # UPDATED Oct 30, 2025: Reject cached entries without proper Zotero keys
            citation_key = cache_data.get("key")

            # Validate cache has a proper Zotero key (not a temp key)
            if not citation_key:
                logger.warning(
                    f"Cache entry for {url} has no key - invalidating cache"
                )
                return None  # Force re-fetch from Zotero

            # Check if cached key looks like a temp key (contains "Temp" or is too short)
            if "Temp" in citation_key or "temp" in citation_key or len(citation_key) < 15:
                logger.warning(
                    f"Cache entry for {url} has temp/invalid key '{citation_key}' - invalidating cache"
                )
                return None  # Force re-fetch from Zotero

            # Cache has valid key - use it
            citation = Citation(
                authors=cache_data.get("authors", ""),
                year=cache_data.get("year", ""),
                url=url,
                key=citation_key,
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

        # Phase 3: Look up Better BibTeX key from Zotero collection
        zotero_result = self._lookup_zotero_entry_by_url(url)

        if zotero_result:
            # Found in Zotero - use Better BibTeX key
            cite_key, zotero_entry = zotero_result
            logger.info(
                f"Using Better BibTeX key from Zotero: {cite_key} for {url}"
            )

            # Create Citation from Zotero entry
            citation = Citation(
                authors=zotero_entry.get("author", authors),
                year=zotero_entry.get("year", year),
                url=url,
                key=cite_key,
                use_better_bibtex=self.use_better_bibtex_keys,
            )

            # Populate additional fields from Zotero
            citation.title = zotero_entry.get("title", "")
            citation.journal = zotero_entry.get("journal", "")
            citation.volume = zotero_entry.get("volume", "")
            citation.pages = zotero_entry.get("pages", "")
            citation.doi = zotero_entry.get("doi", "")
            citation.bibtex_type = zotero_entry.get(
                "ENTRYTYPE", "misc"
            )  # BibTeX uses ENTRYTYPE

            key = cite_key

        else:
            # Not found in Zotero - try auto-add or create temporary key
            # This will happen if:
            # 1. No Zotero collection configured
            # 2. Citation not in Zotero collection
            logger.warning(
                f"Citation not found in Zotero collection: {url} - attempting auto-add"
            )

            # Create placeholder Citation object for _handle_missing_citation()
            placeholder_citation = Citation(
                authors,
                year,
                url,
                "temp",  # Will be replaced by _handle_missing_citation()
                use_better_bibtex=self.use_better_bibtex_keys,
            )

            # Try to auto-add to Zotero or generate appropriate temp key
            key = self._handle_missing_citation(placeholder_citation, url)

            # Create final Citation object with the determined key
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

                    # Only use format_bibtex() when Better BibTeX is disabled
                    # (format_bibtex generates keys, which violates Better BibTeX principle)
                    if not self.use_better_bibtex_keys:
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
                        f"arXiv:{arxiv_id_match}"
                    )
                    if zotero_data:
                        # Parse Zotero data to update citation fields
                        self._parse_zotero_data(citation, zotero_data)

                        # Only use format_bibtex() when Better BibTeX is disabled
                        # (format_bibtex generates keys, which violates Better BibTeX principle)
                        if not self.use_better_bibtex_keys:
                            citation.raw_bibtex = (
                                self.zotero_client.format_bibtex(zotero_data)
                            )
                            # Update citation key from BibTeX
                            # Extract key from BibTeX without regex
                            if (
                                citation.raw_bibtex
                                and "@" in citation.raw_bibtex
                                and "{" in citation.raw_bibtex
                            ):
                                at_pos = citation.raw_bibtex.find("@")
                                brace_pos = citation.raw_bibtex.find(
                                    "{", at_pos
                                )
                                comma_pos = citation.raw_bibtex.find(
                                    ",", brace_pos
                                )
                                if brace_pos > at_pos and comma_pos > brace_pos:
                                    citation.key = citation.raw_bibtex[
                                        brace_pos + 1 : comma_pos
                                    ].strip()
                        logger.info(
                            f"Fetched metadata from Zotero for arXiv: {arxiv_id_match}"
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

    def _build_normalized_url_lookup(self) -> dict[str, str]:
        """Build a lookup map from normalized URLs to citation keys.

        Returns:
            Dictionary mapping normalized URLs to citation keys
        """
        lookup = {}

        # H2 TEST: Track normalization inconsistencies
        normalization_log = []

        for key, citation in self.citations.items():
            if not citation.url.startswith("#orphan-"):
                original_url = citation.url

                # Test BOTH normalization paths
                arxiv_normalized = normalize_arxiv_url(original_url)
                general_normalized = normalize_url(original_url)

                # Log if they differ
                if arxiv_normalized != general_normalized:
                    normalization_log.append(
                        {
                            "key": key,
                            "original": original_url,
                            "arxiv_norm": arxiv_normalized,
                            "general_norm": general_normalized,
                            "stored_in_citation": citation.url,
                        }
                    )

                # Use the same logic as extraction (arxiv first, then general)
                normalized = normalize_url(normalize_arxiv_url(original_url))

                if normalized in lookup:
                    logger.warning(
                        f"URL collision: {normalized} maps to both {key} and {lookup[normalized]}"
                    )
                lookup[normalized] = key

        if normalization_log:
            logger.debug(
                f"Found {len(normalization_log)} URLs with different normalizations"
            )
            for item in normalization_log[:3]:
                logger.debug(f"{item}")
        else:
            logger.debug("All URLs normalize consistently")

        logger.info(f"Built normalized URL lookup with {len(lookup)} entries")
        return lookup

    def replace_citations_in_text_ast(self, content: str) -> tuple[str, int]:
        """Replace markdown citations with LaTeX cite commands using AST parsing.

        Uses markdown-it-py to parse the markdown into tokens, find link tokens,
        and replace them with citation commands. This is more robust than string
        manipulation as it properly handles nested brackets, special characters, etc.

        Returns:
            Tuple of (modified_content, replacement_count)
        """
        # Check if self.citations is populated
        logger.debug(f"self.citations dict has {len(self.citations)} entries")
        if len(self.citations) == 0:
            logger.warning(
                "CRITICAL: self.citations is EMPTY - no replacements possible"
            )
        else:
            sample_keys = list(self.citations.keys())[:5]
            logger.debug(f"Sample keys: {sample_keys}")
            sample_urls = [self.citations[k].url for k in sample_keys]
            logger.debug(f"Sample URLs: {sample_urls}")

        # Build normalized URL lookup
        url_to_key = self._build_normalized_url_lookup()

        # Parse markdown into tokens
        md = MarkdownIt()
        tokens = md.parse(content)

        replacements = 0
        failed_urls = []

        # H4 TEST: Track all lookup attempts
        logger.error(
            f"[H4-TEST] Starting citation replacement with {len(url_to_key)} URLs in lookup"
        )
        lookup_attempts = []

        logger.info(
            f"Starting AST-based citation replacement for {len(tokens)} tokens"
        )

        # Log token structure for debugging citation replacement
        token_types_found = {}
        for token in tokens:
            token_types_found[token.type] = (
                token_types_found.get(token.type, 0) + 1
            )
            if token.type == "inline" and token.children:
                for child in token.children:
                    child_key = f"inline > {child.type}"
                    token_types_found[child_key] = (
                        token_types_found.get(child_key, 0) + 1
                    )
        logger.debug(f"Token structure: {token_types_found}")

        # Process tokens to find and replace links
        # Links are nested inside inline tokens, not at top level
        links_processed = 0
        for token in tokens:
            if token.type == "inline" and token.children:
                i = 0
                while i < len(token.children):
                    child = token.children[i]
                    if child.type == "link_open":
                        links_processed += 1
                        # Extract href from token attributes
                        # attrs can be either a dict or a list of tuples
                        href = None
                        if hasattr(child, "attrs") and child.attrs:
                            if isinstance(child.attrs, dict):
                                href = child.attrs.get("href")
                            else:
                                # List of tuples format
                                for attr in child.attrs:
                                    if attr[0] == "href":
                                        href = attr[1]
                                        break

                        if href:
                            # Normalize the URL for lookup
                            normalized_href = normalize_url(href)

                            # Find the citation key
                            key = url_to_key.get(normalized_href)

                            # H4 TEST: Log every lookup attempt
                            lookup_attempts.append(
                                {
                                    "original": href,
                                    "normalized": normalized_href,
                                    "found_key": key,
                                    "success": key is not None,
                                }
                            )

                            if key:
                                # Find the closing link token
                                j = i + 1
                                depth = 1
                                link_text_parts = []

                                while j < len(token.children) and depth > 0:
                                    if token.children[j].type == "link_open":
                                        depth += 1
                                    elif token.children[j].type == "link_close":
                                        depth -= 1
                                        if depth == 0:
                                            break
                                    elif token.children[j].type == "text":
                                        link_text_parts.append(
                                            token.children[j].content
                                        )
                                    j += 1

                                link_text = "".join(link_text_parts)
                                citation = self.citations[key]

                                logger.debug(
                                    f"Replacing [{link_text}]({href}) -> \\citep{{{citation.key}}}"
                                )

                                # Create a new text token with the citation command
                                new_token = Token("text", "", 0)
                                new_token.content = f"\\citep{{{citation.key}}}"

                                # Replace children[i:j+1] with new_token
                                del token.children[i : j + 1]
                                token.children.insert(i, new_token)
                                replacements += 1
                            else:
                                logger.warning(
                                    f"No citation key found for URL: {href} (normalized: {normalized_href})"
                                )
                                failed_urls.append(href)
                                i += 1
                        else:
                            i += 1
                    else:
                        i += 1

        # Log citation replacement summary
        logger.debug(f"Links processed: {links_processed}")
        logger.debug(f"Lookup attempts: {len(lookup_attempts)}")
        logger.info(f"Successfully replaced {replacements} citations")
        if failed_urls:
            logger.warning(f"Failed to resolve {len(failed_urls)} URLs")
            logger.debug("First 3 failed URLs:")
            for url in failed_urls[:3]:
                logger.debug(f"  - {url}")

        # Render tokens back to markdown
        logger.debug("Starting token rendering with markdown-it renderer")

        # Use the markdown-it renderer to convert tokens back to markdown text
        # This preserves all markdown structure (headers, paragraphs, lists, etc.)
        output = md.renderer.render(tokens, md.options, {})

        # Strip ALL HTML tags (markdown-it renders everything as HTML by default)
        # We need markdown text, not HTML, for the rest of the pipeline
        # Remove HTML tags character by character (no regex)
        cleaned = []
        i = 0
        while i < len(output):
            if output[i] == "<":
                # Find closing >
                j = i + 1
                while j < len(output) and output[j] != ">":
                    j += 1
                if j < len(output):
                    # Skip the entire tag
                    i = j + 1
                    continue
            cleaned.append(output[i])
            i += 1

        output = "".join(cleaned)
        # Unescape HTML entities like &quot; &amp; etc.
        output = html.unescape(output)

        # Check rendering results
        logger.debug(
            f"Rendered output: {len(output)} chars (original: {len(content)})"
        )
        citations_in_output = output.count("\\citep{")
        logger.debug(f"Citations in rendered output: {citations_in_output}")
        logger.debug(f"Expected citations: {replacements}")

        logger.info(
            f"AST replacement: {replacements} citations replaced, {len(failed_urls)} failed"
        )
        if failed_urls:
            logger.error(f"Failed URLs: {failed_urls[:5]}...")  # Show first 5

        return output, replacements

    def replace_citations_in_text(self, content: str) -> str:
        """Replace markdown citations with LaTeX cite commands."""
        # Use AST-based replacement
        output, replacements = self.replace_citations_in_text_ast(content)
        logger.info(
            f"Completed citation replacement: {replacements} citations replaced"
        )
        return output.rstrip()

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

    # ==================================================================================
    # Phase 1: Auto-Add Integration and Policy Enforcement
    # ==================================================================================

    def _extract_doi_from_url(self, url: str) -> str | None:
        """Extract DOI from URL.

        Uses the existing utility function from utils module.

        Args:
            url: URL that may contain a DOI

        Returns:
            DOI string if found, None otherwise
        """
        return extract_doi_from_url(url)

    def _validate_doi(self, doi: str) -> bool:
        """Validate DOI via CrossRef HEAD request.

        Returns True if DOI exists (200 OK), False if not found (404).
        Results are cached to avoid repeated failed requests.

        Args:
            doi: DOI string to validate

        Returns:
            True if DOI is valid, False otherwise
        """
        # Check cache first
        if doi in self._doi_validation_cache:
            return self._doi_validation_cache[doi]

        # HEAD request to CrossRef
        url = f"https://api.crossref.org/works/{doi}"
        try:
            response = requests.head(url, timeout=5)
            is_valid = response.status_code == 200

            # Cache result (especially 404s to avoid repeated failures)
            self._doi_validation_cache[doi] = is_valid

            if not is_valid:
                logger.critical(
                    f"Invalid DOI detected: {doi} (HTTP {response.status_code})"
                )

            return is_valid
        except Exception as e:
            logger.warning(f"DOI validation failed for {doi}: {e}")
            # Don't cache network errors (might be transient)
            return False

    def _generate_temp_key(self, citation: Citation) -> str:
        """DEPRECATED (Oct 30, 2025): Temp keys should never be generated.

        This method is kept for backwards compatibility but will raise an error
        if called. All code paths should now fail-fast instead of generating
        temp keys.

        Args:
            citation: Citation object

        Raises:
            RuntimeError: Always - temp keys are no longer allowed
        """
        raise RuntimeError(
            "DEPRECATED: _generate_temp_key() should never be called.\n"
            f"Citation URL: {citation.url}\n"
            f"Authors: {citation.authors}\n\n"
            "Temp keys are no longer generated. Instead:\n"
            "  1. Enable auto-add (--auto-add-real)\n"
            "  2. Manually add citations to Zotero\n"
            "  3. Fix translation server if it's failing\n\n"
            "This error indicates a code path that still expects temp keys.\n"
            "Please report this as a bug."
        )

    def _fetch_newly_added_entry(self, doi: str) -> dict[str, Any] | None:
        """Fetch newly added Zotero entry by DOI.

        Args:
            doi: DOI of the entry to fetch

        Returns:
            Entry dict with 'key' field if found, None otherwise
        """
        if not self.zotero_client:
            return None

        try:
            # Re-fetch collection to get new keys
            # This is a simplified version - in production, we'd search by DOI
            # For now, just return None and rely on Temp key fallback
            logger.debug(f"Would fetch newly added entry for DOI: {doi}")
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch newly added entry for {doi}: {e}")
            return None

    def _fetch_metadata(self, doi: str, url: str) -> dict[str, Any] | None:
        """Fetch metadata from CrossRef or arXiv.

        Args:
            doi: DOI string
            url: Full URL

        Returns:
            Metadata dict with title, authors, etc. or None if failed
        """
        # Try CrossRef first
        try:
            crossref_url = f"https://api.crossref.org/works/{doi}"
            response = requests.get(crossref_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                message = data.get("message", {})

                # Extract metadata
                metadata = {
                    "title": message.get("title", [""])[0]
                    if message.get("title")
                    else "",
                    "authors": [],
                }

                # Extract authors
                for author in message.get("author", []):
                    family = author.get("family", "")
                    given = author.get("given", "")
                    if family:
                        metadata["authors"].append(
                            f"{family}, {given}" if given else family
                        )

                return metadata
        except Exception as e:
            logger.debug(f"CrossRef fetch failed for {doi}: {e}")

        # TODO: Add arXiv fetching if needed
        return None

    def _handle_missing_citation(self, citation: Citation, url: str) -> str:
        """Handle citation not found in Zotero.

        Flow (UPDATED Oct 30, 2025 - NO MORE TEMP KEYS):
        1. Attempt auto-add via ZoteroAutoAdd (if enabled)
        2. If successful, return Better BibTeX key
        3. If failed or disabled, FAIL immediately (no temp key fallback)

        Args:
            citation: Citation object
            url: Citation URL

        Returns:
            Better BibTeX key (if successfully added to Zotero)

        Raises:
            RuntimeError: If citation cannot be added to Zotero
        """
        # Try auto-add if enabled
        if self.zotero_auto_add:
            logger.info(f"Attempting auto-add for: {url}")

            key, warnings = self.zotero_auto_add.add_citation(
                url, citation.authors
            )

            if key:
                # Success! (either added or dry-run simulated)
                if warnings:
                    for warning in warnings:
                        logger.warning(f"  Auto-add warning: {warning}")
                return key
            else:
                # Validation failed or translation failed - FAIL IMMEDIATELY
                logger.error(f"❌ Auto-add FAILED for: {url}")
                error_details = "\n".join(f"  - {w}" for w in warnings) if warnings else "  - No details available"

                raise RuntimeError(
                    f"Failed to add citation to Zotero: {url}\n"
                    f"Reasons:\n{error_details}\n\n"
                    f"Possible fixes:\n"
                    f"  1. Check if translation server is running\n"
                    f"  2. Verify URL is accessible\n"
                    f"  3. Manually add to Zotero collection: {self.zotero_collection}\n"
                    f"  4. Check logs for validation errors"
                )

        # Auto-add disabled - FAIL IMMEDIATELY
        raise RuntimeError(
            f"Citation not in Zotero and auto-add is DISABLED: {url}\n\n"
            f"Possible fixes:\n"
            f"  1. Enable auto-add by removing --no-auto-add flag\n"
            f"  2. Manually add citation to Zotero collection: {self.zotero_collection}\n"
            f"  3. Run conversion again after adding to Zotero"
        )

    def _enforce_no_temp_key_for_valid_doi(self, citation: Citation) -> None:
        """Enforce policy: Temp keys only allowed for invalid/missing DOIs.

        Raises RuntimeError if a Temp key exists for a citation with valid DOI.
        This prevents "cheating" by using Temp keys as shortcuts.

        Args:
            citation: Citation to check

        Raises:
            RuntimeError: If policy violation detected
        """
        if "Temp" not in citation.key:
            return  # Not a temp key, all good

        doi = self._extract_doi_from_url(citation.url)

        if doi and self._validate_doi(doi):
            raise RuntimeError(
                f"Policy violation: Temp key '{citation.key}' created for valid DOI {doi}. "
                f"This citation should have been added to Zotero automatically."
            )

    def validate_no_temp_keys(
        self, fail_on_temp: bool = True, include_dryrun: bool = True
    ) -> list[dict[str, str]]:
        """Validate that no temporary citation keys exist.

        Temporary keys indicate citations missing from Zotero:
        - "Temp" keys: Generated when auto-add disabled or failed
        - "dryrun_" keys: Generated when auto-add in dry-run mode

        This is a CRITICAL validation step that should be run BEFORE
        BibTeX generation to ensure all citations are properly matched
        to Zotero entries.

        Args:
            fail_on_temp: Raise RuntimeError if temp keys found
            include_dryrun: Also flag dryrun_ keys (default: True)

        Returns:
            List of dicts with temp key details: {key, url, authors, year}

        Raises:
            RuntimeError: If fail_on_temp=True and temp keys exist

        Example:
            >>> manager.validate_no_temp_keys(fail_on_temp=True)
            # Raises RuntimeError if any Temp or dryrun_ keys found
        """
        temp_keys = []

        for key, citation in self.citations.items():
            # Check for temporary key patterns (NO REGEX - string checks only)
            is_temp = False

            # Case-insensitive check for "temp" anywhere in key
            if "Temp" in key or "temp" in key:
                is_temp = True
            elif include_dryrun and "dryrun_" in key:
                is_temp = True

            if is_temp:
                temp_keys.append(
                    {
                        "key": key,
                        "url": citation.url,
                        "authors": citation.authors,
                        "year": citation.year,
                    }
                )

        if temp_keys and fail_on_temp:
            # Build detailed error message
            msg_lines = [
                f"❌ VALIDATION FAILED: {len(temp_keys)} citations missing from Zotero",
                "",
                "Temporary keys found:",
            ]

            # Show first 10 entries
            for item in temp_keys[:10]:
                msg_lines.append(f"  - {item['key']}: {item['url']}")

            if len(temp_keys) > 10:
                msg_lines.append(f"  ... and {len(temp_keys) - 10} more")

            msg_lines.extend(
                [
                    "",
                    "Options to fix:",
                    "  1. Run with --auto-add-real to add missing citations to Zotero automatically",
                    "  2. Manually add these citations to your Zotero collection",
                    "  3. Run with --allow-temp-keys to proceed anyway (NOT recommended)",
                    "",
                    "Temporary keys indicate:",
                    "  - 'Temp' keys: Auto-add was disabled or metadata extraction failed",
                    "  - 'dryrun_' keys: Auto-add was in dry-run mode (safe test mode)",
                ]
            )

            raise RuntimeError("\n".join(msg_lines))

        return temp_keys

    def generate_error_report(self) -> str:
        """Generate human-readable error report.

        Groups errors by severity and provides actionable information.

        Returns:
            Formatted error report string
        """
        if not self._citation_errors:
            return "✅ All citations processed successfully (no errors)"

        report = [
            "",
            "=" * 80,
            "CITATION PROCESSING ERROR REPORT",
            "=" * 80,
            "",
        ]

        # Group by severity
        critical = [
            e for e in self._citation_errors if e["severity"] == "CRITICAL"
        ]
        errors = [e for e in self._citation_errors if e["severity"] == "ERROR"]
        warnings = [
            e for e in self._citation_errors if e["severity"] == "WARNING"
        ]

        # Report each severity level
        if critical:
            report.append(
                f"🔴 CRITICAL ({len(critical)} issues) - Invalid DOIs from LLM hallucinations"
            )
            for err in critical:
                report.append(
                    f"  - {err['issue']}: {err.get('doi', err.get('url', 'N/A'))}"
                )
                report.append(f"    Citation: {err.get('citation', 'Unknown')}")
            report.append("")

        if errors:
            report.append(
                f"⚠️  ERROR ({len(errors)} issues) - Missing/incomplete metadata"
            )
            for err in errors:
                report.append(
                    f"  - {err['issue']}: {err.get('doi', err.get('url', 'N/A'))}"
                )
            report.append("")

        if warnings:
            report.append(
                f"ℹ️  WARNING ({len(warnings)} issues) - Citations without DOI"
            )
            report.append(
                f"    {len(warnings)} citations could not be auto-added (web pages, etc.)"
            )
            report.append("")

        report.append("=" * 80)
        return "\n".join(report)
