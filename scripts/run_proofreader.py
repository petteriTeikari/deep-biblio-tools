#!/usr/bin/env python3
"""
Helper script to run the Streamlit proofreading interface.

Usage: uv run python run_proofreader.py
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Run the Streamlit proofreading app"""
    # Path to the proofreader module
    proofreader_path = (
        Path(__file__).parent / "src" / "deep_biblio_tools" / "proofreader.py"
    )

    if not proofreader_path.exists():
        print(f"Error: Proofreader not found at {proofreader_path}")
        sys.exit(1)

    # Run streamlit
    cmd = [
        "uv",
        "run",
        "streamlit",
        "run",
        str(proofreader_path),
        "--server.address",
        "0.0.0.0",  # Bind to all interfaces
        "--server.port",
        "8502",
        "--browser.gatherUsageStats",
        "false",
        "--server.headless",
        "true",  # Prevent browser auto-open
        "--logger.level",
        "debug",  # Enable debug logging
    ]

    print("Starting Citation Proofreader...")
    print("Open your browser to: http://localhost:8502")
    print("Press Ctrl+C to stop")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nProofreader stopped")
    except subprocess.CalledProcessError as e:
        print(f"Error running streamlit: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
