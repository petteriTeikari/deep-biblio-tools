"""Zotero API integration for fetching bibliographic data."""

import logging

# import re  # Banned - using string methods instead
from typing import Any

import requests

logger = logging.getLogger(__name__)


class ZoteroClient:
    """Client for interacting with Zotero API."""

    def __init__(
        self, api_key: str | None = None, library_id: str | None = None
    ):
        """Initialize Zotero client.

        Args:
            api_key: Zotero API key (optional for public libraries)
            library_id: Zotero library ID (user or group ID)
        """
        self.api_key = api_key
        self.library_id = library_id
        self.base_url = "https://api.zotero.org"

    def search_by_identifier(self, identifier: str) -> dict[str, Any] | None:
        """Search for an item by DOI, ISBN, arXiv ID, etc.

        Args:
            identifier: DOI, ISBN, arXiv ID, or other identifier

        Returns:
            Item data if found, None otherwise
        """
        logger.debug(
            f"ZoteroClient.search_by_identifier called with: {identifier}"
        )
        # Use Zotero translation server if available (for automatic metadata extraction)
        try:
            # First try the Zotero translation server
            translation_url = "https://translate.zotero.org/search"

            headers = {
                "Content-Type": "text/plain",
                "Accept": "application/json",
            }

            logger.debug(
                f"Sending identifier to Zotero translation server: {identifier}"
            )
            # Send identifier to translation server
            response = requests.post(
                translation_url, data=identifier, headers=headers, timeout=10
            )
            logger.debug(
                f"Zotero translation server response: status={response.status_code}"
            )

            if response.status_code == 200:
                items = response.json()
                logger.debug(
                    f"Zotero translation server returned {len(items) if items else 0} items"
                )
                if items and len(items) > 0:
                    logger.debug(
                        f"Returning first item with title: {items[0].get('title', 'No title')}"
                    )
                    return items[0]  # Return first match

        except Exception as e:
            logger.warning(
                f"Failed to fetch from Zotero translation server: {e}"
            )

        # If translation server fails, try library search if configured
        if self.library_id:
            return self._search_library(identifier)

        return None

    def _search_library(self, query: str) -> dict[str, Any] | None:
        """Search user's Zotero library.

        Args:
            query: Search query (DOI, title, etc.)

        Returns:
            Item data if found, None otherwise
        """
        if not self.library_id:
            return None

        # Determine library type (user or group)
        library_type = "users" if self.library_id.isdigit() else "groups"

        url = f"{self.base_url}/{library_type}/{self.library_id}/items"

        params = {"q": query, "format": "json", "limit": 1}

        headers = {}
        if self.api_key:
            headers["Zotero-API-Key"] = self.api_key

        try:
            response = requests.get(
                url, params=params, headers=headers, timeout=10
            )

            if response.status_code == 200:
                items = response.json()
                if items and len(items) > 0:
                    return items[0]["data"]

        except Exception as e:
            logger.warning(f"Failed to search Zotero library: {e}")

        return None

    def format_bibtex(self, item_data: dict[str, Any]) -> str:
        """Convert Zotero item data to BibTeX format.

        Args:
            item_data: Zotero item data

        Returns:
            BibTeX entry string
        """
        # Map Zotero item types to BibTeX types
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

        item_type = item_data.get("itemType", "misc")
        bibtex_type = type_map.get(item_type, "misc")

        # Generate citation key
        creators = item_data.get("creators", [])
        first_author = ""
        if creators:
            creator = creators[0]
            if "lastName" in creator:
                first_author = creator["lastName"]
            elif "name" in creator:
                first_author = creator["name"].split()[-1]

        year = self._extract_year(item_data.get("date", ""))
        title_word = self._get_first_title_word(item_data.get("title", ""))

        key = f"{first_author.lower()}{year}{title_word}"
        # Remove non-alphanumeric characters without regex
        clean_key = []
        for char in key:
            if char.isalnum():
                clean_key.append(char)
        key = "".join(clean_key)

        # Build BibTeX entry
        lines = [f"@{bibtex_type}{{{key},"]

        # Authors
        if creators:
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
                lines.append(f'  author = "{" and ".join(author_names)}",')

        # Title
        if "title" in item_data:
            title = item_data["title"].replace('"', '{"}')
            lines.append(f'  title = "{title}",')

        # Year
        if year:
            lines.append(f'  year = "{year}",')

        # Journal
        if "publicationTitle" in item_data:
            lines.append(f'  journal = "{item_data["publicationTitle"]}",')

        # Volume
        if "volume" in item_data:
            lines.append(f'  volume = "{item_data["volume"]}",')

        # Number/Issue
        if "issue" in item_data:
            lines.append(f'  number = "{item_data["issue"]}",')

        # Pages
        if "pages" in item_data:
            lines.append(f'  pages = "{item_data["pages"]}",')

        # DOI
        if "DOI" in item_data:
            lines.append(f'  doi = "{item_data["DOI"]}",')

        # URL
        if "url" in item_data:
            lines.append(f'  url = "{item_data["url"]}",')

        # ISBN
        if "ISBN" in item_data:
            lines.append(f'  isbn = "{item_data["ISBN"]}",')

        # Publisher
        if "publisher" in item_data:
            lines.append(f'  publisher = "{item_data["publisher"]}",')

        # Abstract
        if "abstractNote" in item_data:
            abstract = item_data["abstractNote"].replace('"', '{"}')
            abstract = abstract.replace("\n", " ")
            lines.append(f'  abstract = "{abstract}",')

        lines.append("}")

        return "\n".join(lines)

    def _extract_year(self, date_str: str) -> str:
        """Extract year from date string."""
        if not date_str:
            return ""

        # Try to find 4-digit year without regex
        # Look for years starting with 19 or 20
        for i in range(len(date_str) - 3):
            if date_str[i : i + 2] in ["19", "20"]:
                # Check if next 2 characters are digits
                if date_str[i + 2 : i + 4].isdigit():
                    # Check boundaries - should not be part of a longer number
                    if (i == 0 or not date_str[i - 1].isdigit()) and (
                        i + 4 >= len(date_str) or not date_str[i + 4].isdigit()
                    ):
                        return date_str[i : i + 4]

        return ""

    def _get_first_title_word(self, title: str) -> str:
        """Get first significant word from title."""
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

        # Clean title without regex
        clean_chars = []
        for char in title:
            if char.isalpha() or char.isspace():
                clean_chars.append(char)
            else:
                clean_chars.append(" ")

        clean_title = "".join(clean_chars)
        words = clean_title.split()

        for word in words:
            if word.lower() not in skip_words and len(word) > 2:
                return word[0].upper() + word[1:].lower()

        return ""
