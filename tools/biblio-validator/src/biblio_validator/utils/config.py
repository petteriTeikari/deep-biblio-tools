"""Configuration utilities."""

from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load configuration from file."""
    if config_path:
        config_file = Path(config_path)
    else:
        # Look for config in standard locations
        search_paths = [
            Path(".biblio-validator.yml"),
            Path(".biblio-validator.yaml"),
            Path("~/.config/biblio-validator/config.yml").expanduser(),
            Path("~/.biblio-validator.yml").expanduser(),
        ]

        config_file = None
        for path in search_paths:
            if path.exists():
                config_file = path
                break

    if config_file and config_file.exists():
        with open(config_file) as f:
            return yaml.safe_load(f) or {}

    # Return default configuration
    return get_default_config()


def get_default_config() -> dict[str, Any]:
    """Get default configuration."""
    return {
        "cache": {
            "enabled": True,
            "directory": "~/.cache/biblio-validator",
            "ttl": 604800,  # 1 week
        },
        "validation": {
            "sources": ["crossref", "pubmed", "arxiv"],
            "timeout": 30,
            "parallel": True,
        },
        "reporting": {"format": "markdown", "include_suggestions": True},
        "api_keys": {
            # API keys can be configured here or via environment variables
            "crossref": None,
            "pubmed": None,
        },
    }
