#!/usr/bin/env python3
"""Setup API key for literature reviewer."""

import os
from pathlib import Path

import yaml


def setup_api_key():
    """Setup the API key for the literature reviewer."""

    # Check if API key is in environment
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("ANTHROPIC_API_KEY environment variable not found.")
        api_key = input("Please enter your Anthropic API key: ").strip()

        if not api_key:
            print("No API key provided. Exiting.")
            return False

    # Create config directory and file
    config_dir = Path.home() / ".config" / "literature-reviewer"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = Path.home() / ".literature-reviewer.yml"

    # Create configuration
    config = {
        "ai": {
            "provider": "anthropic",
            "anthropic": {
                "api_key": api_key,
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.3,
                "max_tokens": 8192,
            },
        },
        "output": {"format": "markdown", "include_original": False},
    }

    # Write configuration
    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    print(f"Configuration saved to: {config_file}")

    # Also set environment variable for this session
    os.environ["ANTHROPIC_API_KEY"] = api_key

    return True


if __name__ == "__main__":
    print("Literature Reviewer API Key Setup")
    print("=" * 40)

    if setup_api_key():
        print("\nSetup completed successfully!")
        print("You can now run the rephrasing test.")
    else:
        print("\nSetup failed.")
