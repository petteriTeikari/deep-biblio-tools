"""SQLite-based citation cache for persistent storage of bibliographic metadata."""

# Standard library imports
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CitationCache:
    """SQLite-based cache for citation metadata."""

    def __init__(self, cache_dir: Path | None = None, cache_ttl_days: int = 30):
        """Initialize the citation cache.

        Args:
            cache_dir: Directory to store the cache database
            cache_ttl_days: Time-to-live for cache entries in days
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "deep-biblio-tools"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "citations.db"
        self.cache_ttl_days = cache_ttl_days

        self._init_database()

    def _init_database(self) -> None:
        """Initialize the SQLite database with the citations table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS citations (
                    url TEXT PRIMARY KEY,
                    authors TEXT,
                    year TEXT,
                    title TEXT,
                    journal TEXT,
                    volume TEXT,
                    issue TEXT,
                    pages TEXT,
                    doi TEXT,
                    bibtex_type TEXT,
                    raw_bibtex TEXT,
                    full_authors TEXT,
                    abstract TEXT,
                    arxiv_category TEXT,
                    metadata_json TEXT,
                    fetched_at TIMESTAMP,
                    source TEXT
                )
            """)

            # Create index on DOI for faster lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_doi ON citations(doi)
                WHERE doi IS NOT NULL
            """)

            # Create index on fetched_at for TTL queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fetched_at ON citations(fetched_at)
            """)

            conn.commit()

    def get(self, url: str) -> dict[str, Any] | None:
        """Get citation metadata from cache.

        Args:
            url: The URL of the citation

        Returns:
            Dictionary of citation metadata or None if not found/expired
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM citations
                WHERE url = ?
                AND datetime(fetched_at) > datetime('now', '-' || ? || ' days')
            """,
                (url, self.cache_ttl_days),
            )

            row = cursor.fetchone()
            if row:
                # Convert SQLite row to dictionary
                citation_data = dict(row)

                # Parse JSON metadata if present
                if citation_data.get("metadata_json"):
                    try:
                        citation_data["metadata"] = json.loads(
                            citation_data["metadata_json"]
                        )
                    except json.JSONDecodeError:
                        pass

                # Remove the JSON string field
                citation_data.pop("metadata_json", None)

                logger.debug(f"Cache hit for URL: {url}")
                return citation_data

            logger.debug(f"Cache miss for URL: {url}")
            return None

    def get_by_doi(self, doi: str) -> dict[str, Any] | None:
        """Get citation metadata by DOI.

        Args:
            doi: The DOI of the citation

        Returns:
            Dictionary of citation metadata or None if not found/expired
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM citations
                WHERE doi = ?
                AND datetime(fetched_at) > datetime('now', '-' || ? || ' days')
                ORDER BY fetched_at DESC
                LIMIT 1
            """,
                (doi, self.cache_ttl_days),
            )

            row = cursor.fetchone()
            if row:
                citation_data = dict(row)

                # Parse JSON metadata if present
                if citation_data.get("metadata_json"):
                    try:
                        citation_data["metadata"] = json.loads(
                            citation_data["metadata_json"]
                        )
                    except json.JSONDecodeError:
                        pass

                citation_data.pop("metadata_json", None)

                logger.debug(f"Cache hit for DOI: {doi}")
                return citation_data

            logger.debug(f"Cache miss for DOI: {doi}")
            return None

    def put(
        self, url: str, citation_data: dict[str, Any], source: str = "unknown"
    ) -> None:
        """Store citation metadata in cache.

        Args:
            url: The URL of the citation
            citation_data: Dictionary of citation metadata
            source: Source of the metadata (e.g., "crossref", "arxiv", "web")
        """
        # Prepare metadata JSON
        metadata_json = None
        if "metadata" in citation_data:
            metadata_json = json.dumps(citation_data["metadata"])

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO citations (
                    url, authors, year, title, journal, volume, issue, pages,
                    doi, bibtex_type, raw_bibtex, full_authors, abstract,
                    arxiv_category, metadata_json, fetched_at, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
            """,
                (
                    url,
                    citation_data.get("authors"),
                    citation_data.get("year"),
                    citation_data.get("title"),
                    citation_data.get("journal"),
                    citation_data.get("volume"),
                    citation_data.get("issue"),
                    citation_data.get("pages"),
                    citation_data.get("doi"),
                    citation_data.get("bibtex_type"),
                    citation_data.get("raw_bibtex"),
                    citation_data.get("full_authors"),
                    citation_data.get("abstract"),
                    citation_data.get("arxiv_category"),
                    metadata_json,
                    source,
                ),
            )
            conn.commit()

        logger.debug(f"Cached citation for URL: {url} (source: {source})")

    def clear(self, older_than_days: int | None = None) -> int:
        """Clear cache entries.

        Args:
            older_than_days: Only clear entries older than this many days.
                           If None, clear all entries.

        Returns:
            Number of entries cleared
        """
        with sqlite3.connect(self.db_path) as conn:
            if older_than_days is None:
                cursor = conn.execute("DELETE FROM citations")
            else:
                cursor = conn.execute(
                    """
                    DELETE FROM citations
                    WHERE datetime(fetched_at) < datetime('now', '-' || ? || ' days')
                """,
                    (older_than_days,),
                )

            count = cursor.rowcount
            conn.commit()

        logger.info(f"Cleared {count} cache entries")
        return count

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            # Total entries
            total = conn.execute("SELECT COUNT(*) FROM citations").fetchone()[0]

            # Entries by source
            by_source = {}
            for row in conn.execute("""
                SELECT source, COUNT(*) as count
                FROM citations
                GROUP BY source
            """):
                by_source[row[0] or "unknown"] = row[1]

            # Expired entries
            expired = conn.execute(
                """
                SELECT COUNT(*) FROM citations
                WHERE datetime(fetched_at) < datetime('now', '-' || ? || ' days')
            """,
                (self.cache_ttl_days,),
            ).fetchone()[0]

            # Valid entries
            valid = total - expired

            # Oldest and newest entries
            dates = conn.execute("""
                SELECT
                    MIN(fetched_at) as oldest,
                    MAX(fetched_at) as newest
                FROM citations
            """).fetchone()

        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": expired,
            "by_source": by_source,
            "oldest_entry": dates[0] if dates[0] else None,
            "newest_entry": dates[1] if dates[1] else None,
            "database_path": str(self.db_path),
            "cache_ttl_days": self.cache_ttl_days,
        }

    def export_to_json(self, output_path: Path) -> None:
        """Export cache to JSON file.

        Args:
            output_path: Path to write the JSON file
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM citations")

            citations = []
            for row in cursor:
                citation = dict(row)
                # Parse JSON metadata
                if citation.get("metadata_json"):
                    try:
                        citation["metadata"] = json.loads(
                            citation["metadata_json"]
                        )
                    except json.JSONDecodeError:
                        pass
                citation.pop("metadata_json", None)
                citations.append(citation)

        with open(output_path, "w") as f:
            json.dump(citations, f, indent=2)

        logger.info(f"Exported {len(citations)} citations to {output_path}")

    def import_from_json(self, input_path: Path) -> int:
        """Import cache from JSON file.

        Args:
            input_path: Path to read the JSON file

        Returns:
            Number of entries imported
        """
        with open(input_path) as f:
            citations = json.load(f)

        count = 0
        for citation in citations:
            # Extract URL as key
            url = citation.get("url")
            if url:
                self.put(url, citation, citation.get("source", "imported"))
                count += 1

        logger.info(f"Imported {count} citations from {input_path}")
        return count
