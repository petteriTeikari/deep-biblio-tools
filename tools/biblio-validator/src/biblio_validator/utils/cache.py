"""Caching utilities for API responses."""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..models.citation import Citation, ValidationResult


class ValidationCache:
    """Cache for validation results to avoid repeated API calls."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}
        self.cache_dir = Path(
            self.config.get("directory", "~/.cache/biblio-validator")
        ).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = self.config.get("ttl", 604800)  # Default 1 week

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key."""
        # Use hash to avoid filesystem issues with special characters
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    def get(self, key: str) -> ValidationResult | None:
        """Get cached validation result."""
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path) as f:
                data = json.load(f)

            # Check if cache is expired
            cached_time = datetime.fromisoformat(data["cached_at"])
            if datetime.now() - cached_time > timedelta(seconds=self.ttl):
                cache_path.unlink()
                return None

            # Reconstruct ValidationResult
            citation = Citation(
                key=data["citation_key"],
                text=data.get("citation_text", ""),
                document_path=data.get("document_path", ""),
            )

            result = ValidationResult(
                citation=citation,
                is_valid=data["is_valid"],
                confidence=data.get("confidence", 1.0),
                source=data.get("source"),
                matched_entry=data.get("matched_entry"),
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
            )

            return result

        except (json.JSONDecodeError, KeyError, ValueError):
            # Invalid cache entry, remove it
            cache_path.unlink()
            return None

    def set(self, key: str, result: ValidationResult):
        """Cache a validation result."""
        cache_path = self._get_cache_path(key)

        data = {
            "cached_at": datetime.now().isoformat(),
            "citation_key": result.citation.key,
            "citation_text": result.citation.text,
            "document_path": result.citation.document_path,
            "is_valid": result.is_valid,
            "confidence": result.confidence,
            "source": result.source,
            "matched_entry": result.matched_entry,
            "issues": result.issues,
            "suggestions": result.suggestions,
        }

        with open(cache_path, "w") as f:
            json.dump(data, f, indent=2)

    def clear(self):
        """Clear all cached entries."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

    def clear_expired(self):
        """Clear only expired cache entries."""
        now = datetime.now()
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                cached_time = datetime.fromisoformat(data["cached_at"])
                if now - cached_time > timedelta(seconds=self.ttl):
                    cache_file.unlink()
            except (json.JSONDecodeError, KeyError, ValueError):
                # Invalid cache file, remove it
                cache_file.unlink()
