"""
Modular bibliography source architecture.

Provides three independent sources for bibliography data:
1. ZoteroAPISource - Fetch from Zotero Web API
2. LocalFileSource - Load from CSL JSON/BibTeX/RDF export
3. LocalZoteroSource - Direct SQLite access (future)

This decouples citation matching logic from data source implementation.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pyzotero import zotero

logger = logging.getLogger(__name__)


class BiblographySource(ABC):
    """Abstract interface for bibliography data sources."""

    @abstractmethod
    def load_entries(self) -> list[dict[str, Any]]:
        """
        Load bibliography entries as CSL JSON format.

        Returns:
            List of CSL JSON entries with citation keys in 'id' field
        """
        pass

    @abstractmethod
    def requires_credentials(self) -> bool:
        """
        Whether this source requires authentication credentials.

        Returns:
            True if credentials needed, False otherwise
        """
        pass

    @abstractmethod
    def source_name(self) -> str:
        """
        Human-readable name of this source for logging.

        Returns:
            Source name (e.g., "Zotero Web API", "Local JSON file")
        """
        pass

    @abstractmethod
    def can_write_back(self) -> bool:
        """
        Whether this source supports adding new citations.

        Returns:
            True if write-back is supported, False otherwise
        """
        pass


class LocalFileSource(BiblographySource):
    """Load bibliography from local CSL JSON export."""

    def __init__(self, file_path: Path | str):
        """
        Initialize with path to local file.

        Args:
            file_path: Path to CSL JSON, BibTeX, or RDF file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is unsupported
        """
        self.file_path = Path(file_path)

        if not self.file_path.exists():
            raise FileNotFoundError(f"Bibliography file not found: {self.file_path}")

        # Determine format from extension
        suffix = self.file_path.suffix.lower()
        if suffix == ".json":
            self.format = "csl-json"
        elif suffix in {".bib", ".bibtex"}:
            self.format = "bibtex"
        elif suffix == ".rdf":
            self.format = "rdf"
        else:
            raise ValueError(
                f"Unsupported bibliography format: {suffix}. "
                f"Supported: .json (CSL JSON), .bib/.bibtex (BibTeX), .rdf (RDF)"
            )

        logger.info(
            f"Initialized LocalFileSource with {self.format} file: {self.file_path.name}"
        )

    def load_entries(self) -> list[dict[str, Any]]:
        """Load entries from file based on format."""
        if self.format == "csl-json":
            return self._load_csl_json()
        elif self.format == "bibtex":
            return self._load_bibtex()
        elif self.format == "rdf":
            return self._load_rdf()
        else:
            raise ValueError(f"Unsupported format: {self.format}")

    def _load_csl_json(self) -> list[dict[str, Any]]:
        """Load CSL JSON format."""
        with open(self.file_path, encoding="utf-8") as f:
            entries = json.load(f)

        # Validate that entries have 'id' field (citation key)
        valid_entries = []
        for entry in entries:
            if "id" not in entry:
                logger.warning(
                    f"Entry missing 'id' field, skipping: {entry.get('title', 'Unknown')}"
                )
                continue
            valid_entries.append(entry)

        logger.info(
            f"Loaded {len(valid_entries)} entries from CSL JSON "
            f"({len(entries) - len(valid_entries)} skipped due to missing 'id')"
        )
        return valid_entries

    def _load_bibtex(self) -> list[dict[str, Any]]:
        """Load BibTeX format and convert to CSL JSON."""
        import bibtexparser
        from bibtexparser.bparser import BibTexParser

        with open(self.file_path, encoding="utf-8") as f:
            parser = BibTexParser(common_strings=True, ignore_nonstandard_types=False)
            bib_database = bibtexparser.load(f, parser)

        # Convert BibTeX entries to CSL JSON format
        csl_entries = []
        for entry in bib_database.entries:
            # The citation key is the BibTeX ID
            cite_key = entry.get("ID", "")
            if not cite_key:
                logger.warning(f"Entry missing ID, skipping: {entry.get('title', 'Unknown')}")
                continue

            # Map BibTeX fields to CSL JSON
            csl_entry = {
                "id": cite_key,  # This is the Better BibTeX key!
                "type": self._map_bibtex_type(entry.get("ENTRYTYPE", "article")),
                "title": entry.get("title", ""),
            }

            # Author field
            if "author" in entry:
                csl_entry["author"] = self._parse_bibtex_authors(entry["author"])

            # Year
            if "year" in entry:
                csl_entry["issued"] = {"date-parts": [[int(entry["year"])]]}

            # DOI
            if "doi" in entry:
                csl_entry["DOI"] = entry["doi"]

            # URL
            if "url" in entry:
                csl_entry["URL"] = entry["url"]

            # ISBN (for books)
            if "isbn" in entry:
                csl_entry["ISBN"] = entry["isbn"]

            # Journal/container
            if "journal" in entry:
                csl_entry["container-title"] = entry["journal"]
            elif "booktitle" in entry:
                csl_entry["container-title"] = entry["booktitle"]

            # Volume
            if "volume" in entry:
                csl_entry["volume"] = entry["volume"]

            # Issue/number
            if "number" in entry:
                csl_entry["issue"] = entry["number"]

            # Pages
            if "pages" in entry:
                csl_entry["page"] = entry["pages"]

            # Abstract
            if "abstract" in entry:
                csl_entry["abstract"] = entry["abstract"]

            # Publisher
            if "publisher" in entry:
                csl_entry["publisher"] = entry["publisher"]

            # Institution (for tech reports)
            if "institution" in entry:
                csl_entry["publisher"] = entry["institution"]

            # arXiv note
            if "note" in entry and "arXiv:" in entry["note"]:
                csl_entry["note"] = entry["note"]

            csl_entries.append(csl_entry)

        logger.info(f"Loaded {len(csl_entries)} entries from BibTeX")
        return csl_entries

    def _map_bibtex_type(self, bibtex_type: str) -> str:
        """Map BibTeX entry type to CSL JSON type."""
        mapping = {
            "article": "article-journal",
            "inproceedings": "paper-conference",
            "conference": "paper-conference",
            "book": "book",
            "incollection": "chapter",
            "inbook": "chapter",
            "techreport": "report",
            "phdthesis": "thesis",
            "mastersthesis": "thesis",
            "misc": "article",
            "unpublished": "manuscript",
            "patent": "patent",  # NEW: Support patents
        }
        return mapping.get(bibtex_type.lower(), "article")

    def _parse_bibtex_authors(self, author_str: str) -> list[dict[str, str]]:
        """Parse BibTeX author string into CSL JSON author format."""
        # BibTeX format: "LastName, FirstName and LastName2, FirstName2"
        authors = []
        for author in author_str.split(" and "):
            author = author.strip()
            if "," in author:
                # Format: "LastName, FirstName"
                parts = author.split(",", 1)
                family = parts[0].strip()
                given = parts[1].strip() if len(parts) > 1 else ""
            else:
                # Format: "FirstName LastName" (fallback)
                parts = author.rsplit(" ", 1)
                given = parts[0].strip() if len(parts) > 1 else ""
                family = parts[-1].strip()

            authors.append({"family": family, "given": given})

        return authors

    def _load_rdf(self) -> list[dict[str, Any]]:
        """Load RDF format and convert to CSL JSON."""
        import xml.etree.ElementTree as ET

        # Define namespaces used in Zotero RDF export
        namespaces = {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "bib": "http://purl.org/net/biblio#",
            "dc": "http://purl.org/dc/elements/1.1/",
            "dcterms": "http://purl.org/dc/terms/",
            "foaf": "http://xmlns.com/foaf/0.1/",
            "z": "http://www.zotero.org/namespaces/export#",
            "link": "http://purl.org/rss/1.0/modules/link/",
        }

        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse RDF file: {e}") from e

        csl_entries = []
        seen_elements = set()  # Track element IDs to avoid duplicates

        # Valid bibliography item types (exclude attachments, collections, etc.)
        valid_item_types = {
            "journalArticle", "book", "bookSection", "conferencePaper",
            "thesis", "report", "webpage", "preprint", "article",
            "patent", "document", "recording",
            # Additional types found in RDF
            "magazineArticle", "newspaperArticle", "blogPost", "podcast",
        }

        # Metadata types to exclude (these are NOT bibliography items)
        excluded_bib_tags = {"Journal", "Series", "Periodical"}

        # Simpler approach: Find ALL top-level children and process each once
        # This includes both bib:* typed elements AND plain rdf:Description elements
        for child in root:
            # Get element memory ID to track if we've processed it
            elem_id = id(child)
            if elem_id in seen_elements:
                continue
            seen_elements.add(elem_id)

            # Skip metadata entries like bib:Journal, bib:Series
            if child.tag.startswith(f"{{{namespaces['bib']}}}"):
                tag_name = child.tag.split("}")[-1]
                if tag_name in excluded_bib_tags:
                    continue

            # Filter out non-bibliography entries
            # Check 1: Must have a non-empty title
            title_elem = child.find("dc:title", namespaces)
            if title_elem is None or not title_elem.text:
                continue

            # Check 2: If has z:itemType, it must be a bibliography type (not "attachment")
            item_type_elem = child.find("z:itemType", namespaces)
            has_valid_item_type = False
            if item_type_elem is not None:
                item_type = item_type_elem.text or ""
                if item_type.lower() not in valid_item_types:
                    continue  # Skip attachments, collections, etc.
                has_valid_item_type = True

            # Check 3: Must have at least ONE of:
            # - authors (bib:authors element)
            # - valid z:itemType (already checked above)
            # - OR be a specifically typed bib:* element (but not metadata)
            has_authors = child.find("bib:authors", namespaces) is not None
            is_bib_typed = child.tag.startswith(f"{{{namespaces['bib']}}}")

            if not (has_authors or has_valid_item_type or is_bib_typed):
                continue  # Not a real bibliography entry

            # Parse the entry
            entry = self._parse_rdf_item(child, namespaces)
            if entry:
                csl_entries.append(entry)
            else:
                # Debug: log why entry was skipped
                tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                url = child.get(f"{{{namespaces['rdf']}}}about", "NO_URL")
                logger.debug(f"Skipped {tag_name} entry with URL: {url}")

        logger.info(
            f"Loaded {len(csl_entries)} entries from RDF "
            f"({len(root)} total elements processed)"
        )
        return csl_entries

    def _parse_rdf_item(
        self, item: Any, namespaces: dict[str, str]
    ) -> dict[str, Any] | None:
        """Parse a single RDF bibliography item to CSL JSON."""

        # Extract rdf:about as the URL/identifier
        item_url = item.get(f"{{{namespaces['rdf']}}}about", "")

        # Extract title
        title_elem = item.find("dc:title", namespaces)
        title = title_elem.text if title_elem is not None else ""

        if not title:
            logger.warning(f"Skipping RDF item without title: {item_url}")
            return None

        # Create citation key from URL (will use this as 'id')
        # For Amazon URLs like .../dp/1138021016, extract the identifier
        citation_key = self._extract_citation_key_from_url(item_url, title)

        # Build CSL JSON entry
        csl_entry = {
            "id": citation_key,
            "title": title,
            "URL": item_url,
        }

        # Extract item type
        item_type_elem = item.find("z:itemType", namespaces)
        if item_type_elem is not None:
            zotero_type = item_type_elem.text or ""
            csl_entry["type"] = self._map_zotero_rdf_type(zotero_type, item.tag)
        else:
            # Infer from RDF tag (bib:Book -> book, bib:Article -> article-journal)
            tag_name = item.tag.split("}")[-1] if "}" in item.tag else item.tag
            csl_entry["type"] = self._map_rdf_tag_to_csl_type(tag_name)

        # Extract authors
        authors_elem = item.find("bib:authors", namespaces)
        if authors_elem is not None:
            authors = []
            # Authors are in rdf:Seq/rdf:li/foaf:Person
            seq = authors_elem.find("rdf:Seq", namespaces)
            if seq is not None:
                for li in seq.findall("rdf:li", namespaces):
                    person = li.find("foaf:Person", namespaces)
                    if person is not None:
                        surname_elem = person.find("foaf:surname", namespaces)
                        given_elem = person.find("foaf:givenName", namespaces)

                        author = {}
                        if surname_elem is not None:
                            author["family"] = surname_elem.text or ""
                        if given_elem is not None:
                            author["given"] = given_elem.text or ""

                        if author:
                            authors.append(author)

            if authors:
                csl_entry["author"] = authors

        # Extract date
        date_elem = item.find("dc:date", namespaces)
        if date_elem is not None and date_elem.text:
            # Try to extract year from various date formats
            date_text = date_elem.text
            year = self._extract_year_from_date(date_text)
            if year:
                csl_entry["issued"] = {"date-parts": [[year]]}

        # Extract publisher
        publisher_elem = item.find("dc:publisher", namespaces)
        if publisher_elem is not None:
            org = publisher_elem.find("foaf:Organization", namespaces)
            if org is not None:
                name_elem = org.find("foaf:name", namespaces)
                if name_elem is not None:
                    csl_entry["publisher"] = name_elem.text or ""

        # Extract abstract
        abstract_elem = item.find("dcterms:abstract", namespaces)
        if abstract_elem is not None:
            csl_entry["abstract"] = abstract_elem.text or ""

        # Extract DOI and URL from nested dcterms:URI/rdf:value structure
        # This is where Zotero stores the actual URL, not just in rdf:about!
        for identifier in item.findall("dc:identifier", namespaces):
            uri = identifier.find("dcterms:URI", namespaces)
            if uri is not None:
                value_elem = uri.find("rdf:value", namespaces)
                if value_elem is not None and value_elem.text:
                    url = value_elem.text
                    # Store URL if we don't have one yet or if this is more specific
                    if not item_url or len(url) > len(item_url):
                        item_url = url
                        csl_entry["URL"] = url
                    if "doi.org" in url:
                        # Extract DOI from URL
                        doi = url.split("doi.org/")[-1]
                        csl_entry["DOI"] = doi

        # Extract ISBN (for books)
        isbn_elem = item.find("dc:identifier[@{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource]", namespaces)
        if isbn_elem is not None:
            isbn_text = isbn_elem.get(f"{{{namespaces['rdf']}}}resource", "")
            if "isbn" in isbn_text.lower():
                # Extract ISBN from urn:isbn: format
                isbn = isbn_text.split(":")[-1]
                csl_entry["ISBN"] = isbn

        return csl_entry

    def _extract_citation_key_from_url(self, url: str, title: str) -> str:
        """Extract citation key from URL or generate from title."""
        # For Amazon URLs: extract the ASIN/ISBN
        if "amazon" in url and "/dp/" in url:
            parts = url.split("/dp/")
            if len(parts) > 1:
                asin = parts[1].split("/")[0].split("?")[0]
                return f"amazon_{asin}"

        # For DOI URLs: extract DOI
        if "doi.org/" in url:
            doi = url.split("doi.org/")[-1]
            # Sanitize DOI for use as key
            safe_doi = doi.replace("/", "_").replace(".", "_")
            return f"doi_{safe_doi}"

        # For arXiv: extract arXiv ID
        if "arxiv.org" in url:
            if "/abs/" in url:
                arxiv_id = url.split("/abs/")[-1]
                return f"arxiv_{arxiv_id}"

        # Fallback: create key from title
        # Take first 3 words, lowercase, remove special chars
        words = title.split()[:3]
        key_base = "_".join(w.lower() for w in words if w.isalnum())
        return key_base or "unknown_item"

    def _extract_year_from_date(self, date_text: str) -> int | None:
        """Extract year from various date format strings."""
        # Try to find 4-digit year
        for part in date_text.split():
            # Remove common separators
            part = part.replace(",", "").replace("-", "").replace("/", "")
            if part.isdigit() and len(part) == 4:
                year = int(part)
                if 1900 <= year <= 2100:
                    return year
        return None

    def _map_zotero_rdf_type(self, zotero_type: str, rdf_tag: str) -> str:
        """Map Zotero itemType to CSL JSON type."""
        mapping = {
            "book": "book",
            "journalArticle": "article-journal",
            "conferencePaper": "paper-conference",
            "thesis": "thesis",
            "report": "report",
            "webpage": "webpage",
            "article": "article",
            "patent": "patent",
        }
        return mapping.get(zotero_type.lower(), "article")

    def _map_rdf_tag_to_csl_type(self, tag_name: str) -> str:
        """Map RDF tag name to CSL JSON type."""
        mapping = {
            "Book": "book",
            "Article": "article-journal",
            "ArticleJournal": "article-journal",
            "ConferencePaper": "paper-conference",
            "Thesis": "thesis",
            "Report": "report",
            "WebPage": "webpage",
            "Document": "article",
        }
        return mapping.get(tag_name, "article")

    def requires_credentials(self) -> bool:
        """Local files don't need credentials."""
        return False

    def source_name(self) -> str:
        """Return source name for logging."""
        return f"Local {self.format.upper()} file ({self.file_path.name})"

    def can_write_back(self) -> bool:
        """Local files are read-only."""
        return False


class ZoteroAPISource(BiblographySource):
    """Fetch bibliography from Zotero Web API."""

    def __init__(
        self,
        api_key: str,
        library_id: str,
        library_type: str = "user",
        collection_name: str | None = None,
    ):
        """
        Initialize Zotero API source.

        Args:
            api_key: Zotero API key
            library_id: Zotero library ID
            library_type: 'user' or 'group'
            collection_name: Optional collection name to fetch from

        Raises:
            ValueError: If credentials are invalid
        """
        if not api_key or not library_id:
            raise ValueError("Zotero API key and library ID are required")

        self.api_key = api_key
        self.library_id = library_id
        self.library_type = library_type
        self.collection_name = collection_name

        try:
            self.zot = zotero.Zotero(library_id, library_type, api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize Zotero client: {e}") from e

        logger.info(
            f"Initialized ZoteroAPISource with library_id: {library_id}, "
            f"collection: {collection_name or 'all items'}"
        )

    def load_entries(self) -> list[dict[str, Any]]:
        """
        Fetch entries from Zotero API.

        Returns:
            List of CSL JSON entries with Better BibTeX keys
        """
        try:
            if self.collection_name:
                # Get collection ID by name
                collections = self.zot.collections()
                collection_id = None
                for coll in collections:
                    if coll["data"]["name"] == self.collection_name:
                        collection_id = coll["data"]["key"]
                        break

                if not collection_id:
                    raise ValueError(
                        f"Collection '{self.collection_name}' not found. "
                        f"Available: {[c['data']['name'] for c in collections]}"
                    )

                logger.info(f"Fetching from collection: {self.collection_name}")
                # Fetch items from collection
                # Note: We need Better BibTeX keys, which requires special endpoint
                # For now, fetch regular items
                items = self.zot.collection_items(collection_id)
            else:
                logger.info("Fetching all items from library")
                items = self.zot.items()

            # Convert Zotero items to CSL JSON
            # Note: This is simplified - proper implementation needs Better BibTeX keys
            csl_entries = []
            for item in items:
                data = item.get("data", {})
                # Extract CSL JSON from Zotero item
                # This is a simplified conversion - proper implementation needs more work
                csl_entry = {
                    "id": data.get("key", ""),  # Temporary - should use Better BibTeX key
                    "type": self._map_item_type(data.get("itemType", "article")),
                    "title": data.get("title", ""),
                    # TODO: Add more field mappings
                }

                # Add DOI if present
                if "DOI" in data:
                    csl_entry["DOI"] = data["DOI"]

                # Add URL if present
                if "url" in data:
                    csl_entry["URL"] = data["url"]

                csl_entries.append(csl_entry)

            logger.info(f"Loaded {len(csl_entries)} entries from Zotero API")
            return csl_entries

        except Exception as e:
            logger.error(f"Failed to fetch from Zotero API: {e}")
            raise

    def _map_item_type(self, zotero_type: str) -> str:
        """Map Zotero item type to CSL JSON type."""
        # Simplified mapping - expand as needed
        mapping = {
            "journalArticle": "article-journal",
            "conferencePaper": "paper-conference",
            "book": "book",
            "bookSection": "chapter",
            "webpage": "webpage",
        }
        return mapping.get(zotero_type, "article")

    def requires_credentials(self) -> bool:
        """Zotero API requires credentials."""
        return True

    def source_name(self) -> str:
        """Return source name for logging."""
        return f"Zotero Web API (library: {self.library_id}, collection: {self.collection_name or 'all'})"

    def can_write_back(self) -> bool:
        """Zotero API supports adding new items."""
        return True

    def add_citation(self, url: str, metadata: dict[str, Any]) -> dict[str, Any] | None:
        """
        Add a new citation to Zotero.

        Args:
            url: Citation URL
            metadata: Citation metadata

        Returns:
            Created entry or None if failed
        """
        try:
            # Create Zotero item from metadata
            new_item = {
                "itemType": "webpage",
                "title": metadata.get("title", f"Auto-added: {url[:50]}..."),
                "url": url,
                # Add more fields from metadata
            }

            response = self.zot.create_items([new_item])
            if response.get("success"):
                logger.info(f"Added to Zotero: {url}")
                # Return CSL JSON representation
                return metadata
            else:
                logger.warning(f"Failed to add to Zotero: {response}")
                return None

        except Exception as e:
            logger.warning(f"Error adding to Zotero: {e}")
            return None


def create_bibliography_source(
    zotero_api_key: str | None = None,
    zotero_library_id: str | None = None,
    zotero_library_type: str = "user",
    collection_name: str | None = None,
    local_file_path: Path | str | None = None,
) -> BiblographySource:
    """
    Factory function to create appropriate bibliography source.

    Priority:
    1. Local file if provided (fastest, no network)
    2. Zotero API if credentials provided
    3. Error if neither provided

    Args:
        zotero_api_key: Optional Zotero API key
        zotero_library_id: Optional Zotero library ID
        zotero_library_type: 'user' or 'group'
        collection_name: Optional Zotero collection name
        local_file_path: Optional path to local bibliography file

    Returns:
        BiblographySource implementation

    Raises:
        ValueError: If no valid source can be created
    """
    # Priority 1: Local file (fastest, no credentials needed)
    if local_file_path:
        logger.info(f"Using local file source: {local_file_path}")
        return LocalFileSource(local_file_path)

    # Priority 2: Zotero API
    if zotero_api_key and zotero_library_id:
        logger.info("Using Zotero Web API source")
        return ZoteroAPISource(
            api_key=zotero_api_key,
            library_id=zotero_library_id,
            library_type=zotero_library_type,
            collection_name=collection_name,
        )

    # No valid source
    raise ValueError(
        "No bibliography source available. Provide either:\n"
        "  1. Local file path (--json, --bib, or --rdf), OR\n"
        "  2. Zotero API credentials (ZOTERO_API_KEY + ZOTERO_LIBRARY_ID)"
    )
