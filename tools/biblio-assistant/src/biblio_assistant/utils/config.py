"""Configuration utilities for biblio-assistant."""

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
            Path(".biblio-assistant.yml"),
            Path(".biblio-assistant.yaml"),
            Path("~/.config/biblio-assistant/config.yml").expanduser(),
            Path("~/.biblio-assistant.yml").expanduser(),
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
        "server": {"host": "0.0.0.0", "port": 8000, "debug": False},
        "ui": {"theme": "light", "language": "en"},
        "features": {"enable_ai": True, "enable_collaboration": False},
        "storage": {"type": "local", "path": "~/.biblio-assistant/data"},
    }
