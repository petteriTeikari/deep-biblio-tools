"""Configuration utilities for literature-reviewer."""

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
            Path(".literature-reviewer.yml"),
            Path(".literature-reviewer.yaml"),
            Path("~/.config/literature-reviewer/config.yml").expanduser(),
            Path("~/.literature-reviewer.yml").expanduser(),
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
        "summarization": {
            "compression_ratio": 0.25,
            "preserve_citations": True,
            "preserve_references": True,
        },
        "review": {
            "include_methodology": True,
            "include_findings": True,
            "deduplicate_references": True,
        },
        "ai": {
            "model": "claude-3.5-sonnet",
            "temperature": 0.3,
            "max_retries": 3,
        },
    }
