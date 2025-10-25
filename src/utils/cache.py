"""
URL cache system for bibliographic data extraction.

This module provides a local SQLite-based cache to avoid re-fetching the same URLs
and to handle URL normalization, DOI resolution, and duplicate detection.
"""

# Standard library imports
import hashlib
import json
import logging

# import re  # Banned - using string methods instead
import shutil
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached bibliographic entry"""

    url: str
    normalized_url: str
    doi: str | None
    bibtex_data: dict | None
    error_message: str | None
    timestamp: float
    response_headers: dict | None = None


class BiblioCache:
    """
    Local cache for bibliographic data fetching.

    Features:
    - URL normalization and DOI extraction
    - Duplicate detection across different URL formats
    - SQLite storage for persistence
    - Configurable cache expiry
    """

    def __init__(self, cache_dir: Path | None = None, cache_ttl_days: int = 30):
        """
        Initialize the cache.

        Args:
            cache_dir: Directory to store cache database. Defaults to ~/.deep-biblio-cache
            cache_ttl_days: Number of days to keep cached entries
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".deep-biblio-cache"

        self.cache_dir = cache_dir
        cache_dir.mkdir(exist_ok=True)
        self.db_path = cache_dir / "biblio_cache.db"
        self.backup_dir = cache_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.cache_ttl_seconds = cache_ttl_days * 24 * 3600

        self._init_database()
        self._create_automatic_backup()

    def _init_database(self):
        """Initialize the SQLite database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    normalized_url TEXT NOT NULL,
                    url_hash TEXT NOT NULL UNIQUE,
                    doi TEXT,
                    bibtex_data TEXT,  -- JSON serialized
                    error_message TEXT,
                    timestamp REAL NOT NULL,
                    response_headers TEXT,  -- JSON serialized
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(url_hash)
                )
            """)

            # Create indexes for efficient lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_normalized_url
                ON cache_entries(normalized_url)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_doi
                ON cache_entries(doi)
                WHERE doi IS NOT NULL
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON cache_entries(timestamp)
            """)

    def normalize_url(self, url: str) -> tuple[str, str | None]:
        """
        Normalize URL and extract DOI if present.

        Returns:
            Tuple of (normalized_url, doi_if_found)
        """
        # Handle common URL patterns that resolve to DOIs
        url = url.strip()

        # Extract DOI from various URL formats
        doi = self._extract_doi_from_url(url)

        # If we found a DOI, normalize to the standard DOI URL format
        if doi:
            normalized_url = f"https://doi.org/{doi}"
        else:
            # Normalize the URL by removing common tracking parameters
            parsed = urlparse(url)
            # Remove common tracking parameters
            normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                # Keep query parameters but remove tracking ones
                query_params = []
                for param in parsed.query.split("&"):
                    if not any(
                        tracker in param.lower()
                        for tracker in ["utm_", "fbclid", "gclid", "_ga", "ref"]
                    ):
                        query_params.append(param)
                if query_params:
                    normalized_url += "?" + "&".join(query_params)

        return normalized_url, doi

    def _extract_doi_from_url(self, url: str) -> str | None:
        """Extract DOI from various URL formats"""
        # Direct DOI URLs - check using string methods
        url_lower = url.lower()

        # Check for doi.org URLs
        if "doi.org/" in url_lower:
            # Find position after doi.org/
            doi_pos = url_lower.find("doi.org/") + 8
            if doi_pos < len(url):
                # Check for dx.doi.org redirect chains
                if url[doi_pos : doi_pos + 11] == "dx.doi.org/":
                    doi_pos += 11

                # Extract DOI starting with 10.
                if url[doi_pos : doi_pos + 3] == "10.":
                    # Find end of DOI (ends at ?, #, or end of string)
                    end_pos = len(url)
                    for char in ["?", "#", " "]:
                        pos = url.find(char, doi_pos)
                        if pos != -1 and pos < end_pos:
                            end_pos = pos

                    doi = url[doi_pos:end_pos].rstrip("/")
                    return doi

        # Check for dx.doi.org URLs
        if "dx.doi.org/" in url_lower:
            doi_pos = url_lower.find("dx.doi.org/") + 11
            if doi_pos < len(url) and url[doi_pos : doi_pos + 3] == "10.":
                # Find end of DOI
                end_pos = len(url)
                for char in ["?", "#", " "]:
                    pos = url.find(char, doi_pos)
                    if pos != -1 and pos < end_pos:
                        end_pos = pos

                doi = url[doi_pos:end_pos].rstrip("/")
                return doi

        # Check for /doi/ paths
        if "/doi/" in url_lower:
            doi_pos = url_lower.find("/doi/") + 5
            # Skip optional abs/ or full/
            if url[doi_pos : doi_pos + 4] == "abs/":
                doi_pos += 4
            elif url[doi_pos : doi_pos + 5] == "full/":
                doi_pos += 5

            # Check if it starts with 10.
            if doi_pos + 3 <= len(url) and url[doi_pos : doi_pos + 3] == "10.":
                # Find end of DOI
                end_pos = len(url)
                for char in ["?", "#", " "]:
                    pos = url.find(char, doi_pos)
                    if pos != -1 and pos < end_pos:
                        end_pos = pos

                doi = url[doi_pos:end_pos].rstrip("/")
                return doi

        # Check for doi: or doi= in query parameters
        for prefix in ["doi:", "doi="]:
            if prefix in url_lower:
                doi_pos = url_lower.find(prefix) + len(prefix)
                if (
                    doi_pos + 3 <= len(url)
                    and url[doi_pos : doi_pos + 3] == "10."
                ):
                    # Find end of DOI
                    end_pos = len(url)
                    for char in ["&", "?", "#", " "]:
                        pos = url.find(char, doi_pos)
                        if pos != -1 and pos < end_pos:
                            end_pos = pos

                    doi = url[doi_pos:end_pos].rstrip("/")
                    return doi

        # Check if URL belongs to known publishers using string methods
        if "sciencedirect.com/science/article/" in url_lower:
            # ScienceDirect PII format
            return None

        if "link.springer.com/" in url_lower and any(
            x in url_lower for x in ["/article/", "/book/", "/chapter/"]
        ):
            # Springer content
            return None

        if "ieeexplore.ieee.org/document/" in url_lower:
            # IEEE document
            return None

        if "nature.com/articles/" in url_lower:
            # Nature articles
            return None

        if "wiley.com/doi/" in url_lower:
            # Wiley might have DOI in URL
            doi_pos = url_lower.find("/doi/") + 5
            # Skip optional abs/ or full/
            if url[doi_pos : doi_pos + 4] == "abs/":
                doi_pos += 4
            elif url[doi_pos : doi_pos + 5] == "full/":
                doi_pos += 5

            # Check if it starts with 10.
            if doi_pos + 3 <= len(url) and url[doi_pos : doi_pos + 3] == "10.":
                # Find end of DOI
                end_pos = len(url)
                for char in ["?", "#", " "]:
                    pos = url.find(char, doi_pos)
                    if pos != -1 and pos < end_pos:
                        end_pos = pos

                doi = url[doi_pos:end_pos].rstrip("/")
                return doi

        return None

    def _generate_url_hash(self, normalized_url: str) -> str:
        """Generate a hash for the normalized URL for efficient lookups"""
        return hashlib.sha256(normalized_url.encode()).hexdigest()[:16]

    def get(self, url: str) -> CacheEntry | None:
        """
        Get cached entry for a URL.

        Args:
            url: The URL to look up

        Returns:
            CacheEntry if found and not expired, None otherwise
        """
        normalized_url, doi = self.normalize_url(url)
        url_hash = self._generate_url_hash(normalized_url)

        current_time = time.time()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # First try exact URL hash match
            cursor = conn.execute(
                """
                SELECT * FROM cache_entries
                WHERE url_hash = ? AND timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 1
            """,
                (url_hash, current_time - self.cache_ttl_seconds),
            )

            row = cursor.fetchone()
            if row:
                return self._row_to_cache_entry(row)

            # If we have a DOI, also try DOI-based lookup
            if doi:
                cursor = conn.execute(
                    """
                    SELECT * FROM cache_entries
                    WHERE doi = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """,
                    (doi, current_time - self.cache_ttl_seconds),
                )

                row = cursor.fetchone()
                if row:
                    return self._row_to_cache_entry(row)

        return None

    def put(
        self,
        url: str,
        bibtex_data: dict | None = None,
        error_message: str | None = None,
        response_headers: dict | None = None,
    ) -> None:
        """
        Store entry in cache.

        Args:
            url: Original URL
            bibtex_data: Extracted BibTeX data (if successful)
            error_message: Error message (if failed)
            response_headers: HTTP response headers
        """
        normalized_url, doi = self.normalize_url(url)
        url_hash = self._generate_url_hash(normalized_url)
        current_time = time.time()

        with sqlite3.connect(self.db_path) as conn:
            # Use INSERT OR REPLACE to handle duplicates
            conn.execute(
                """
                INSERT OR REPLACE INTO cache_entries
                (url, normalized_url, url_hash, doi, bibtex_data, error_message,
                 timestamp, response_headers)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    url,
                    normalized_url,
                    url_hash,
                    doi,
                    json.dumps(bibtex_data) if bibtex_data else None,
                    error_message,
                    current_time,
                    json.dumps(response_headers) if response_headers else None,
                ),
            )

        logger.debug(f"Cached entry for {url} -> {normalized_url} (DOI: {doi})")

    def _row_to_cache_entry(self, row: sqlite3.Row) -> CacheEntry:
        """Convert database row to CacheEntry"""
        return CacheEntry(
            url=row["url"],
            normalized_url=row["normalized_url"],
            doi=row["doi"],
            bibtex_data=json.loads(row["bibtex_data"])
            if row["bibtex_data"]
            else None,
            error_message=row["error_message"],
            timestamp=row["timestamp"],
            response_headers=json.loads(row["response_headers"])
            if row["response_headers"]
            else None,
        )

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_threshold = current_time - self.cache_ttl_seconds

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                DELETE FROM cache_entries
                WHERE timestamp < ?
            """,
                (expired_threshold,),
            )

            removed_count = cursor.rowcount

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired cache entries")

        return removed_count

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) as total FROM cache_entries")
            total = cursor.fetchone()[0]

            cursor = conn.execute(
                """
                SELECT COUNT(*) as valid FROM cache_entries
                WHERE timestamp > ?
            """,
                (time.time() - self.cache_ttl_seconds,),
            )
            valid = cursor.fetchone()[0]

            cursor = conn.execute(
                """
                SELECT COUNT(*) as with_doi FROM cache_entries
                WHERE doi IS NOT NULL AND timestamp > ?
            """,
                (time.time() - self.cache_ttl_seconds,),
            )
            with_doi = cursor.fetchone()[0]

            cursor = conn.execute(
                """
                SELECT COUNT(*) as errors FROM cache_entries
                WHERE error_message IS NOT NULL AND timestamp > ?
            """,
                (time.time() - self.cache_ttl_seconds,),
            )
            errors = cursor.fetchone()[0]

        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": total - valid,
            "entries_with_doi": with_doi,
            "entries_with_errors": errors,
            "cache_file": str(self.db_path),
            "cache_ttl_days": self.cache_ttl_seconds / (24 * 3600),
        }

    def clear_all(self, force: bool = False) -> int:
        """
        Clear all cache entries with safety confirmation.

        Args:
            force: If True, skip confirmation (dangerous!)

        Returns:
            Number of entries removed
        """
        if not force:
            # Create automatic backup before clearing
            backup_file = self.create_backup()
            logger.warning(
                f"Created backup before clearing cache: {backup_file}"
            )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM cache_entries")
            removed_count = cursor.rowcount

        logger.info(f"Cleared all {removed_count} cache entries")
        return removed_count

    def _create_automatic_backup(self) -> None:
        """Create automatic backup if database exists and was modified recently"""
        if not self.db_path.exists():
            return

        # Get the most recent backup
        backup_files = sorted(self.backup_dir.glob("cache_backup_*.db"))
        if not backup_files:
            # No backups exist, create one
            self.create_backup()
            return

        latest_backup = backup_files[-1]
        backup_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)

        # Create backup if latest is older than 24 hours
        if (datetime.now() - backup_time).total_seconds() > 24 * 3600:
            self.create_backup()

    def create_backup(self, backup_name: str | None = None) -> Path:
        """
        Create a backup of the cache database.

        Args:
            backup_name: Optional custom name for backup

        Returns:
            Path to the created backup file
        """
        if not self.db_path.exists():
            raise ValueError("Cache database does not exist")

        if backup_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"cache_backup_{timestamp}.db"

        backup_path = self.backup_dir / backup_name

        # Use SQLite backup API for consistency
        with sqlite3.connect(self.db_path) as source:
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)

        logger.info(f"Created cache backup: {backup_path}")

        # Cleanup old backups (keep last 10)
        self._cleanup_old_backups()

        return backup_path

    def restore_backup(self, backup_path: Path) -> None:
        """
        Restore cache from backup.

        Args:
            backup_path: Path to backup file
        """
        if not backup_path.exists():
            raise ValueError(f"Backup file does not exist: {backup_path}")

        # Create safety backup of current state
        current_backup = self.create_backup("pre_restore_backup.db")
        logger.info(f"Created safety backup before restore: {current_backup}")

        try:
            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Restored cache from backup: {backup_path}")
        except Exception as e:
            # Restore the safety backup if restore failed
            shutil.copy2(current_backup, self.db_path)
            logger.error(f"Restore failed, rolled back to previous state: {e}")
            raise

    def list_backups(self) -> list[dict]:
        """
        List available backups.

        Returns:
            List of backup info dictionaries
        """
        backups = []
        for backup_file in sorted(self.backup_dir.glob("*.db")):
            stat = backup_file.stat()
            backups.append(
                {
                    "name": backup_file.name,
                    "path": backup_file,
                    "size_mb": stat.st_size / (1024 * 1024),
                    "created": datetime.fromtimestamp(stat.st_mtime),
                    "is_automatic": backup_file.name.startswith(
                        "cache_backup_"
                    ),
                }
            )
        return backups

    def _cleanup_old_backups(self, keep_count: int = 10) -> None:
        """Clean up old automatic backups, keeping the most recent ones"""
        automatic_backups = sorted(
            [f for f in self.backup_dir.glob("cache_backup_*.db")],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        # Remove old backups beyond keep_count
        for old_backup in automatic_backups[keep_count:]:
            try:
                old_backup.unlink()
                logger.debug(f"Removed old backup: {old_backup}")
            except Exception as e:
                logger.warning(f"Failed to remove old backup {old_backup}: {e}")

    def add_manual_entry(
        self,
        url: str,
        citation_text: str,
        author: str = "",
        title: str = "",
        year: str = "",
        journal: str = "",
        doi: str = "",
    ) -> None:
        """
        Manually add a corrected citation to the cache.

        This is useful for the proofreading interface to store manual corrections.

        Args:
            url: Original URL
            citation_text: Corrected citation text (e.g., "Smith et al. (2023)")
            author: Author information
            title: Paper title
            year: Publication year
            journal: Journal name
            doi: DOI if available
        """
        # Create BibTeX-like data structure for manual entries
        bibtex_data = {
            "entry_type": "article",
            "key": f"manual_{int(time.time())}",
            "fields": {
                "author": author or "Unknown",
                "title": title or "Unknown Title",
                "year": year or "",
                "journal": journal or "",
                "url": url,
            },
            "raw_bibtex": f"@article{{manual,\n  author={{{author or 'Unknown'}}},\n  title={{{title or 'Unknown Title'}}},\n  year={{{year or ''}}},\n  url={{{url}}}\n}}",
            "source_url": url,
            "doi": doi or None,
            "manual_correction": True,
            "corrected_citation_text": citation_text,
        }

        if doi:
            bibtex_data["fields"]["doi"] = doi

        self.put(url, bibtex_data=bibtex_data)
        logger.info(f"Added manual cache entry for {url}: {citation_text}")

    def get_failed_entries(self, source_file: str | None = None) -> list[dict]:
        """
        Get all cached entries that failed to extract bibliographic information.

        Args:
            source_file: Optional filter by source file

        Returns:
            List of failed entries with metadata
        """
        current_time = time.time()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = """
                SELECT * FROM cache_entries
                WHERE error_message IS NOT NULL
                AND timestamp > ?
                ORDER BY timestamp DESC
            """
            params = [current_time - self.cache_ttl_seconds]

            cursor = conn.execute(query, params)

            failed_entries = []
            for row in cursor.fetchall():
                failed_entries.append(
                    {
                        "url": row["url"],
                        "normalized_url": row["normalized_url"],
                        "doi": row["doi"],
                        "error_message": row["error_message"],
                        "timestamp": datetime.fromtimestamp(row["timestamp"]),
                        "needs_manual_review": True,
                    }
                )

        return failed_entries

    def remove(self, url: str) -> bool:
        """
        Remove an entry from the cache.

        Args:
            url: URL to remove from cache

        Returns:
            True if entry was removed, False if not found
        """
        normalized_url, doi = self.normalize_url(url)
        url_hash = hashlib.sha256(normalized_url.encode()).hexdigest()

        with sqlite3.connect(self.db_path) as conn:
            # Remove by URL hash
            cursor = conn.execute(
                "DELETE FROM cache_entries WHERE url_hash = ?", (url_hash,)
            )

            # If no rows affected and we have a DOI, try removing by DOI
            if cursor.rowcount == 0 and doi:
                cursor = conn.execute(
                    "DELETE FROM cache_entries WHERE doi = ?", (doi,)
                )

            removed = cursor.rowcount > 0
            if removed:
                conn.commit()
                logger.info(f"Removed cache entry for {url}")

            return removed
