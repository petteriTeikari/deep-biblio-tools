"""Configuration management for Deep Biblio Tools."""

import os
from typing import Any

# Default configuration
DEFAULT_CONFIG = {
    "debug": False,
    "log_level": "INFO",
    "data_dir": "data",
    "output_dir": "output",
}


def load_config() -> dict[str, Any]:
    """Load configuration from environment and files."""
    config = DEFAULT_CONFIG.copy()

    # Load from environment variables
    env_prefix = "DEEP_BIBLIO_TOOLS"
    for key in config:
        env_key = f"{env_prefix}{key.upper()}"
        if env_key in os.environ:
            value = os.environ[env_key]
            # Convert string values to appropriate types
            if key in ["debug"]:
                config[key] = value.lower() in ("true", "1", "yes")
            else:
                config[key] = value

    return config


# Global config instance
config = load_config()
