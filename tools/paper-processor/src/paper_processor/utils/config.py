"""Configuration utilities for paper-processor."""

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
            Path(".paper-processor.yml"),
            Path(".paper-processor.yaml"),
            Path("~/.config/paper-processor/config.yml").expanduser(),
            Path("~/.paper-processor.yml").expanduser(),
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
        "extraction": {
            "formats": ["html", "pdf", "latex"],
            "sections": [
                "abstract",
                "introduction",
                "methodology",
                "results",
                "discussion",
                "conclusion",
                "references",
            ],
        },
        "output": {
            "format": "markdown",
            "preserve_citations": True,
            "clean_text": True,
        },
        "processing": {"parallel": True, "max_workers": 4, "clean_text": True},
    }
