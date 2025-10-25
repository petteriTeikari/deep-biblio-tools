#!/usr/bin/env python3
"""Test Zotero API connection."""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Load environment variables from .env file
load_dotenv(project_root / ".env")


def test_zotero_connection():
    """Test if we can connect to Zotero API."""
    api_key = os.getenv("ZOTERO_API_KEY")
    library_id = os.getenv("ZOTERO_LIBRARY_ID")

    if not api_key or not library_id:
        print("Error: Missing Zotero credentials")
        return False

    # Test connection to Zotero API
    url = f"https://api.zotero.org/users/{library_id}/items"
    headers = {"Zotero-API-Key": api_key}
    params = {"limit": 1, "format": "json"}

    try:
        print(f"Testing connection to Zotero library {library_id}...")
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            print(" Successfully connected to Zotero API")
            print(" Library accessible with API key")

            # Check rate limit headers
            if "X-Rate-Limit-Limit" in response.headers:
                limit = response.headers["X-Rate-Limit-Limit"]
                remaining = response.headers.get("X-Rate-Limit-Remaining", "?")
                print(f" Rate limit: {remaining}/{limit} requests remaining")

            return True

        elif response.status_code == 403:
            print(" Error 403: Invalid API key or insufficient permissions")
            return False

        elif response.status_code == 404:
            print(" Error 404: Library not found")
            return False

        else:
            print(f" Error {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f" Connection error: {e}")
        return False


if __name__ == "__main__":
    success = test_zotero_connection()
    sys.exit(0 if success else 1)
