"""Automatically add missing citations to Zotero with quality validation.

This module orchestrates the auto-add workflow:
1. Fetch metadata from translation-server
2. Validate quality (prevent October 26 garbage incident!)
3. Augment with site-derived authors if needed
4. Add to Zotero collection via API
5. Fetch Better BibTeX keys
6. Generate comprehensive reports

CRITICAL: This module MUST validate entries before adding to prevent
garbage entries like the October 26 incident (truncated titles, no authors, etc.)
"""

import logging
import time
from typing import Any

import bibtexparser
import requests

from src.converters.md_to_latex.entry_validator import EntryValidator
from src.converters.md_to_latex.site_author_mapping import augment_metadata_with_site_author
from src.converters.md_to_latex.translation_client import TranslationClient
from src.converters.md_to_latex.zotero_integration import ZoteroClient

logger = logging.getLogger(__name__)


class ZoteroAutoAdd:
    """Automatically add missing citations to Zotero with quality validation.

    This class orchestrates the entire auto-add workflow with multiple
    safety guardrails to prevent garbage entries.

    Key Features:
    - Translation server integration for metadata fetching
    - Comprehensive quality validation (blocks bad entries)
    - Site-derived author augmentation (BBC, Bloomberg, etc.)
    - Dry-run mode for safe testing
    - Threshold limits to prevent runaway additions
    - Detailed audit trail for debugging
    - Human-readable reports grouped by status
    """

    def __init__(
        self,
        zotero_client: ZoteroClient,
        collection_name: str,
        translation_server_url: str = "http://localhost:1969",
        dry_run: bool = True,  # Default to safe mode!
        max_auto_add: int = 50
    ):
        """Initialize auto-add system.

        Args:
            zotero_client: Existing ZoteroClient instance
            collection_name: Name of Zotero collection to add items to
            translation_server_url: URL of translation-server (default: localhost:1969)
            dry_run: If True, simulate additions without actually adding (SAFE!)
            max_auto_add: Maximum number of items to add (safety threshold)
        """
        self.zotero_client = zotero_client
        self.collection_name = collection_name
        self.dry_run = dry_run
        self.max_auto_add = max_auto_add

        # Initialize subsystems
        self.translation_client = TranslationClient(translation_server_url)
        self.validator = EntryValidator()

        # Check translation server health
        if not self.translation_client.check_health():
            logger.warning(
                f"Translation server not responding at {translation_server_url}"
            )
            logger.warning("Auto-add will fail. Start translation server with:")
            logger.warning("  docker run -d -p 1969:1969 zotero/translation-server")

        # Statistics and audit trail
        self.audit: list[dict[str, Any]] = []
        self.added_count = 0

        # Mode indicator
        mode_str = "DRY-RUN" if self.dry_run else "REAL"
        logger.info(
            f"ZoteroAutoAdd initialized in {mode_str} mode "
            f"(max_auto_add={self.max_auto_add})"
        )

    def add_citation(
        self,
        url: str,
        citation_text: str
    ) -> tuple[str | None, list[str]]:
        """Attempt to auto-add URL to Zotero collection.

        This is the main entry point for adding a single citation.
        It handles the full workflow: fetch → validate → augment → add.

        Args:
            url: URL of the web page/article to add
            citation_text: Original citation text from markdown (for logging)

        Returns:
            (better_bibtex_key_or_none, warnings) where:
                - key is None if addition failed or was skipped
                - warnings is list of issue descriptions

        Example:
            >>> auto_add = ZoteroAutoAdd(client, "dpp-fashion", dry_run=True)
            >>> key, warnings = auto_add.add_citation(
            ...     "https://www.bbc.com/news/business-44885983",
            ...     "BBC (2018)"
            ... )
            >>> print(key)
            'dryrun_1234567890'
            >>> print(warnings)
            []
        """
        warnings: list[str] = []

        logger.info(f"Auto-add request: {url}")
        logger.debug(f"  Original citation text: {citation_text}")

        # Guardrail 1: Check threshold
        if self.added_count >= self.max_auto_add:
            warning = (
                f"Hit max_auto_add threshold ({self.max_auto_add}). "
                f"Increase threshold or review added entries before continuing."
            )
            warnings.append(warning)
            logger.warning(warning)
            self._record_audit(url, "threshold_exceeded", warnings)
            return None, warnings

        # Step 1: Fetch metadata from translation server
        logger.debug("Step 1: Fetching metadata from translation server...")
        metadata = self.translation_client.translate_url(url, retry=True)

        if not metadata:
            warnings.append(
                "Translation server failed to extract metadata. "
                "Site may not be supported or translation server may be down."
            )
            logger.warning(f"Translation failed for: {url}")
            self._record_audit(url, "translation_failed", warnings)
            return None, warnings

        logger.info(
            f"Translation successful: {metadata.get('itemType', 'unknown')} - "
            f"{metadata.get('title', 'No title')[:60]}..."
        )

        # Step 2: Augment with site-derived author if missing
        logger.debug("Step 2: Checking for missing authors...")
        original_creators = metadata.get("creators", [])
        metadata = augment_metadata_with_site_author(metadata, url)
        new_creators = metadata.get("creators", [])

        if not original_creators and new_creators:
            author_name = new_creators[0].get("lastName", "Unknown")
            warnings.append(
                f"Author was missing - added site-derived author: {author_name}"
            )
            logger.info(f"  Augmented with site author: {author_name}")
        elif not new_creators:
            warnings.append(
                "No author available from translation or site mapping. "
                "Will use 'Unknown' if entry passes validation."
            )
            # Add Unknown as last resort (will trigger WARNING in validation)
            metadata["creators"] = [
                {"creatorType": "author", "lastName": "Unknown"}
            ]

        # Step 3: CRITICAL - Validate quality
        logger.debug("Step 3: Validating entry quality...")
        is_valid, issues = self.validator.validate(metadata)

        if issues:
            for issue in issues:
                logger.warning(f"  {issue}")
            warnings.extend(issues)

        # Check for CRITICAL issues (block addition)
        critical_issues = [i for i in issues if i.startswith("CRITICAL")]
        if critical_issues:
            logger.error(
                f"BLOCKED: Entry has {len(critical_issues)} CRITICAL issues. "
                f"Will NOT add to Zotero."
            )
            logger.error(f"  Title: {metadata.get('title', 'N/A')}")
            for issue in critical_issues:
                logger.error(f"  - {issue}")

            self._record_audit(url, "validation_failed", warnings, metadata)
            return None, warnings

        if not is_valid:
            # Shouldn't happen if we check critical issues, but safety check
            logger.error(f"Validation failed but no critical issues? Blocking anyway.")
            self._record_audit(url, "validation_failed", warnings, metadata)
            return None, warnings

        # Validation passed! Entry is acceptable (may have warnings but no critical issues)
        logger.info("  Validation PASSED (entry acceptable for addition)")
        if warnings:
            logger.info(f"  {len(warnings)} warnings (non-blocking)")

        # Step 4: Add to Zotero (or simulate if dry-run)
        if self.dry_run:
            # Simulate addition
            fake_key = f"dryrun_{int(time.time() * 1000)}"
            logger.info(f"  [DRY-RUN] Would add entry. Simulated key: {fake_key}")
            self._record_audit(url, "dry_run_added", warnings, metadata, fake_key)
            return fake_key, warnings

        # REAL MODE: Actually add to Zotero
        try:
            logger.info("Step 4: Adding to Zotero collection...")
            item_key = self._add_to_zotero_collection(metadata)
            self.added_count += 1

            logger.info(f"  Successfully added! Zotero item key: {item_key}")

            # Step 5: Fetch Better BibTeX key
            logger.debug("Step 5: Fetching Better BibTeX key...")
            # Wait briefly for Better BibTeX to sync (if plugin installed)
            time.sleep(0.5)

            better_bibtex_key = self._get_better_bibtex_key_for_item(item_key)
            logger.info(f"  Better BibTeX key: {better_bibtex_key}")

            self._record_audit(url, "added", warnings, metadata, better_bibtex_key)
            return better_bibtex_key, warnings

        except Exception as exc:
            error_msg = f"Failed to add to Zotero: {exc}"
            warnings.append(error_msg)
            logger.error(f"  {error_msg}")
            self._record_audit(url, "add_failed", warnings, metadata)
            return None, warnings

    def _add_to_zotero_collection(self, metadata: dict[str, Any]) -> str:
        """POST item to Zotero and add to collection.

        Args:
            metadata: Zotero item JSON (from translation server)

        Returns:
            Zotero item key

        Raises:
            RuntimeError: If API calls fail
        """
        # Step 1: Find collection ID
        collection_id = self.zotero_client._find_collection_id(self.collection_name)
        if not collection_id:
            raise RuntimeError(
                f"Collection '{self.collection_name}' not found in Zotero library"
            )

        # Step 2: POST item to /users/{id}/items or /groups/{id}/items
        url = (
            f"{self.zotero_client.base_url}/"
            f"{self.zotero_client.library_type}s/"
            f"{self.zotero_client.library_id}/items"
        )

        headers = {
            "Zotero-API-Key": self.zotero_client.api_key,
            "Content-Type": "application/json"
        }

        # Zotero API accepts array of items
        payload = [metadata]

        logger.debug(f"POST {url}")
        resp = requests.post(url, json=payload, headers=headers, timeout=15)

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Zotero API returned {resp.status_code}: {resp.text[:300]}"
            )

        # Parse response to extract item key
        result = resp.json()

        # Zotero response format: {"successful": {"0": {"key": "ABC123", ...}}, ...}
        if "successful" not in result or "0" not in result["successful"]:
            raise RuntimeError(
                f"Unexpected Zotero API response format: {result}"
            )

        item_data = result["successful"]["0"]
        item_key = item_data.get("key")

        if not item_key:
            raise RuntimeError(
                f"Could not extract item key from response: {item_data}"
            )

        logger.debug(f"Item created with key: {item_key}")

        # Step 3: Add item to collection
        # PATCH /users/{id}/collections/{collectionKey}/items
        collection_url = (
            f"{self.zotero_client.base_url}/"
            f"{self.zotero_client.library_type}s/"
            f"{self.zotero_client.library_id}/"
            f"collections/{collection_id}/items"
        )

        # Send item key to add to collection
        resp2 = requests.post(
            collection_url,
            json=[item_key],
            headers=headers,
            timeout=10
        )

        if resp2.status_code not in (200, 204):
            logger.warning(
                f"Failed to add item to collection: {resp2.status_code}"
            )
            # Non-fatal - item was created successfully

        return item_key

    def _get_better_bibtex_key_for_item(self, item_key: str) -> str:
        """Fetch Better BibTeX key by re-exporting collection.

        NOTE: Better BibTeX keys are generated by the Zotero plugin and
        are not immediately available via the API. We need to re-fetch
        the entire collection's BibTeX export to get the key.

        This is inefficient but only happens once per add, and ensures
        we get the correct Better BibTeX key format.

        Args:
            item_key: Zotero item key (8-character alphanumeric)

        Returns:
            Better BibTeX citation key (or Zotero key as fallback)
        """
        try:
            # Re-fetch collection BibTeX export
            bibtex_content = self.zotero_client.get_collection_bibtex(
                self.collection_name
            )

            # Parse to find the most recently added entry
            # (Better BibTeX should have generated a key for it)
            parser = bibtexparser.bparser.BibTexParser()
            parser.ignore_nonstandard_types = False
            bib_db = bibtexparser.loads(bibtex_content, parser=parser)

            if not bib_db.entries:
                logger.warning("No entries in BibTeX export after add")
                return item_key

            # Heuristic: Use the LAST entry's cite key
            # (assuming entries are in chronological order, with newest last)
            last_entry = bib_db.entries[-1]
            cite_key = last_entry.get("ID")

            if cite_key:
                logger.debug(
                    f"Extracted Better BibTeX key: {cite_key} "
                    f"(for Zotero key: {item_key})"
                )
                return cite_key

        except Exception as exc:
            logger.warning(
                f"Failed to extract Better BibTeX key: {exc}. "
                f"Falling back to Zotero key."
            )

        # Fallback: return Zotero key
        return item_key

    def _record_audit(
        self,
        url: str,
        status: str,
        warnings: list[str],
        metadata: dict[str, Any] | None = None,
        key: str | None = None
    ):
        """Record action in audit trail for reporting.

        Args:
            url: Source URL
            status: Status code (added, translation_failed, validation_failed, etc.)
            warnings: List of warning/issue messages
            metadata: Zotero item JSON (if available)
            key: Citation key (if added successfully)
        """
        entry = {
            "url": url,
            "status": status,
            "warnings": warnings,
            "metadata_sample": {
                "title": metadata.get("title") if metadata else None,
                "itemType": metadata.get("itemType") if metadata else None,
                "creators": metadata.get("creators") if metadata else None
            },
            "key": key,
            "timestamp": time.time()
        }
        self.audit.append(entry)

    def generate_report(self) -> str:
        """Generate human-readable report grouped by status.

        Returns:
            Formatted report string
        """
        # Group by status
        added = [a for a in self.audit if a["status"] == "added"]
        dry_run = [a for a in self.audit if a["status"] == "dry_run_added"]
        failed = [a for a in self.audit if a["status"] in (
            "translation_failed",
            "validation_failed",
            "add_failed",
            "threshold_exceeded"
        )]
        with_warnings = [a for a in self.audit if a["warnings"]]

        # Build report
        lines = []
        lines.append("=" * 70)
        lines.append("ZOTERO AUTO-ADD REPORT")
        lines.append("=" * 70)
        lines.append(f"Mode: {'DRY-RUN (no actual changes)' if self.dry_run else 'REAL (added to Zotero)'}")
        lines.append(f"Collection: {self.collection_name}")
        lines.append("")
        lines.append(f"Total processed: {len(self.audit)}")
        lines.append(f"Successfully added: {len(added)}")
        lines.append(f"Dry-run simulated: {len(dry_run)}")
        lines.append(f"Failed: {len(failed)}")
        lines.append(f"With warnings: {len(with_warnings)}")
        lines.append("")

        if added:
            lines.append("✅ SUCCESSFULLY ADDED TO ZOTERO:")
            lines.append("")
            for a in added:
                title = a["metadata_sample"].get("title", "No title")[:60]
                lines.append(f"  {a['url']}")
                lines.append(f"    Title: {title}")
                lines.append(f"    Key: {a['key']}")
                if a["warnings"]:
                    lines.append(f"    Warnings: {len(a['warnings'])}")
                    for w in a["warnings"]:
                        lines.append(f"      - {w}")
                lines.append("")

        if dry_run:
            lines.append("🔍 DRY-RUN SIMULATED (would be added in real mode):")
            lines.append("")
            for a in dry_run:
                title = a["metadata_sample"].get("title", "No title")[:60]
                lines.append(f"  {a['url']}")
                lines.append(f"    Title: {title}")
                lines.append(f"    Simulated key: {a['key']}")
                if a["warnings"]:
                    lines.append(f"    Warnings: {len(a['warnings'])}")
                    for w in a["warnings"]:
                        if not w.startswith("WARNING"):
                            lines.append(f"      - {w}")
                lines.append("")

        if failed:
            lines.append("❌ FAILED TO ADD:")
            lines.append("")
            for a in failed:
                title = a["metadata_sample"].get("title", "No title")[:60] if a["metadata_sample"].get("title") else "N/A"
                lines.append(f"  {a['url']}")
                lines.append(f"    Status: {a['status']}")
                lines.append(f"    Title: {title}")
                if a["warnings"]:
                    for w in a["warnings"]:
                        lines.append(f"    - {w}")
                lines.append("")

        lines.append("=" * 70)
        lines.append("END OF REPORT")
        lines.append("=" * 70)

        return "\n".join(lines)

    def get_statistics(self) -> dict[str, int]:
        """Get statistics summary.

        Returns:
            Dict with counts for different statuses
        """
        return {
            "total": len(self.audit),
            "added": len([a for a in self.audit if a["status"] == "added"]),
            "dry_run": len([a for a in self.audit if a["status"] == "dry_run_added"]),
            "translation_failed": len([a for a in self.audit if a["status"] == "translation_failed"]),
            "validation_failed": len([a for a in self.audit if a["status"] == "validation_failed"]),
            "add_failed": len([a for a in self.audit if a["status"] == "add_failed"]),
            "threshold_exceeded": len([a for a in self.audit if a["status"] == "threshold_exceeded"]),
        }
