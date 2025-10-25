"""Configuration utilities for format-converter."""

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
            Path(".format-converter.yml"),
            Path(".format-converter.yaml"),
            Path("~/.config/format-converter/config.yml").expanduser(),
            Path("~/.format-converter.yml").expanduser(),
        ]

        config_file = None
        for path in search_paths:
            if path.exists():
                config_file = path
                break

    if config_file and config_file.exists():
        with open(config_file) as f:
            return yaml.safe_load(f) or {}

    return get_default_config()


def get_default_config() -> dict[str, Any]:
    """Get default configuration."""
    return {
        "conversion": {
            "preserve_citations": True,
            "include_bibliography": True,
            "citation_style": "author-year",
        },
        "latex": {
            "document_class": "article",
            "packages": ["hyperref", "natbib"],
        },
        "templates": {"ieee": "templates/ieee.tex", "acm": "templates/acm.tex"},
    }
