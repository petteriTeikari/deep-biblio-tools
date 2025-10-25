"""Configuration utilities for quality-guardian."""

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
            Path(".quality-guardian.yml"),
            Path(".quality-guardian.yaml"),
            Path("~/.config/quality-guardian/config.yml").expanduser(),
            Path("~/.quality-guardian.yml").expanduser(),
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
        "checks": {
            "grammar": True,
            "style": True,
            "plagiarism": False,
            "readability": True,
            "consistency": True,
        },
        "standards": {
            "min_readability_score": 30,
            "max_sentence_length": 40,
            "passive_voice_percentage": 20,
        },
        "style_guide": "apa",
        "reporting": {
            "format": "html",
            "include_suggestions": True,
            "highlight_issues": True,
        },
    }
