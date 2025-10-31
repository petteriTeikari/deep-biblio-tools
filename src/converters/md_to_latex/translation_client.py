"""Client for Zotero translation-server (separate service).

The translation-server is a standalone service that converts web pages
to Zotero-compatible item JSON. It must be run separately:

    docker run -d -p 1969:1969 zotero/translation-server

Or via Node.js from https://github.com/zotero/translation-server
"""

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class TranslationClient:
    """Client for Zotero translation-server.

    This is a SEPARATE service from the Zotero Web API. It converts URLs
    to structured bibliographic metadata (Zotero item JSON format).

    The translation-server runs on http://localhost:1969 by default.
    """

    def __init__(self, server_url: str = "http://localhost:1969"):
        """Initialize translation client.

        Args:
            server_url: URL of the translation-server instance
        """
        self.server_url = server_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "deep-biblio-tools/1.0 (https://github.com/yourusername/deep-biblio-tools)"
            }
        )
        self.cache: dict[str, dict[str, Any]] = {}

    def check_health(self) -> bool:
        """Check if translation server is running and responsive.

        Returns:
            True if server is running, False otherwise
        """
        try:
            resp = self.session.get(f"{self.server_url}/", timeout=2)
            # Server returns 404 for root endpoint but that means it's alive
            return resp.status_code in (200, 404)
        except requests.RequestException as exc:
            logger.debug(f"Translation server health check failed: {exc}")
            return False

    def translate_url(
        self, url: str, retry: bool = True
    ) -> dict[str, Any] | None:
        """Fetch metadata from URL using translation-server.

        The translation-server uses site-specific translators to extract
        bibliographic metadata from web pages. Returns Zotero item JSON.

        Args:
            url: URL to translate (e.g., article, news page, etc.)
            retry: Whether to retry on failures with exponential backoff

        Returns:
            Zotero item JSON with fields like:
                - itemType: "webpage", "journalArticle", etc.
                - title: Document title
                - creators: List of author objects
                - date: Publication date
                - url: Original URL
            None if translation failed

        Example:
            >>> client = TranslationClient()
            >>> metadata = client.translate_url("https://www.bbc.com/news/...")
            >>> print(metadata["title"])
            'Burberry burns bags, clothes and perfume worth millions'
        """
        # Check cache first
        if url in self.cache:
            logger.debug(f"Translation cache hit for: {url}")
            return self.cache[url]

        # Determine retry parameters
        max_attempts = 3 if retry else 1
        delay = 1.0

        for attempt in range(max_attempts):
            try:
                # Translation-server expects POST to /web with URL as plain text
                resp = self.session.post(
                    f"{self.server_url}/web",
                    data=url,
                    headers={"Content-Type": "text/plain"},
                    timeout=15,
                )

                if resp.status_code == 200:
                    # Success - parse response
                    items = resp.json()

                    if not items or len(items) == 0:
                        logger.warning(
                            f"Translation returned no items for: {url}"
                        )
                        return None

                    # Use first item
                    metadata = items[0]

                    # Store in cache
                    self.cache[url] = metadata

                    logger.info(
                        f"Successfully translated: {url} → {metadata.get('itemType', 'unknown')}"
                    )
                    return metadata

                elif resp.status_code == 300:
                    # Multiple translators available - this is a more complex case
                    # For now, we'll just use the first option
                    logger.debug(f"Multiple translators available for: {url}")

                    # Response contains list of translator options
                    options = resp.json()
                    if not options or len(options) == 0:
                        logger.warning(
                            f"Got 300 but no translator options: {url}"
                        )
                        return None

                    # Select first translator (could be made smarter)
                    selected_translator = 0
                    session_id = resp.headers.get("X-Zotero-Session")

                    if not session_id:
                        logger.warning("Got 300 but no session ID in headers")
                        return None

                    # Make second request with selected translator
                    resp2 = self.session.post(
                        f"{self.server_url}/web",
                        data=url,
                        headers={
                            "Content-Type": "text/plain",
                            "X-Zotero-Session": session_id,
                        },
                        params={"translator": selected_translator},
                        timeout=15,
                    )

                    if resp2.status_code == 200:
                        items = resp2.json()
                        if items and len(items) > 0:
                            metadata = items[0]
                            self.cache[url] = metadata
                            logger.info(
                                f"Successfully translated (multi-step): {url}"
                            )
                            return metadata

                elif resp.status_code == 501:
                    # No translator available for this site
                    logger.warning(
                        f"No translator available for site: {url} (501)"
                    )
                    return None

                else:
                    logger.warning(
                        f"Translation server returned {resp.status_code} for: {url}"
                    )

            except requests.RequestException as exc:
                logger.debug(
                    f"Translation attempt {attempt + 1}/{max_attempts} failed: {exc}"
                )

                if attempt < max_attempts - 1:
                    # Wait before retry (exponential backoff)
                    logger.debug(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    delay *= 2.0

        # All attempts failed
        logger.warning(
            f"Translation failed after {max_attempts} attempts: {url}"
        )
        return None

    def clear_cache(self):
        """Clear the translation cache."""
        self.cache.clear()
        logger.debug("Translation cache cleared")
