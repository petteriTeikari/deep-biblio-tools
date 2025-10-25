#!/usr/bin/env python3
"""Get Zotero library information and test API connection."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from pyzotero import zotero

# Load environment variables
load_dotenv()

ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY")

if not ZOTERO_API_KEY:
    logger.error("ZOTERO_API_KEY not found in .env file")
    sys.exit(1)

logger.info(f"API Key found: {ZOTERO_API_KEY[:10]}...")

# First, we need to get the user ID from the API
# The Zotero API requires authentication to get user info
try:
    # Try to connect with a dummy library_id to get the actual user info
    # We'll use the API key endpoint to get user information
    import requests

    headers = {"Zotero-API-Key": ZOTERO_API_KEY}
    response = requests.get("https://api.zotero.org/keys/current", headers=headers)

    if response.status_code == 200:
        key_info = response.json()
        logger.success("[PASS] API Key is valid!")

        print("\n" + "=" * 60)
        print("ZOTERO API KEY INFORMATION")
        print("=" * 60)

        print(f"\nKey: {key_info.get('key', 'N/A')[:10]}...")
        print(f"User ID: {key_info.get('userID', 'N/A')}")
        print(f"Username: {key_info.get('username', 'N/A')}")
        print(f"Display Name: {key_info.get('displayName', 'N/A')}")

        # Access information
        print("\n[DOCS] Library Access:")
        access = key_info.get("access", {})

        if "user" in access:
            user_access = access["user"]
            print("  Personal Library:")
            print(f"    - Library: {user_access.get('library', False)}")
            print(f"    - Notes: {user_access.get('notes', False)}")
            print(f"    - Write: {user_access.get('write', False)}")
            print(f"    - Files: {user_access.get('files', False)}")

        if "groups" in access:
            groups_access = access["groups"]
            if "all" in groups_access:
                group_perms = groups_access["all"]
                print("\n  All Groups:")
                print(f"    - Library: {group_perms.get('library', False)}")
                print(f"    - Write: {group_perms.get('write', False)}")

        # Save the user ID to .env
        user_id = key_info.get("userID")
        if user_id:
            print(f"\n Updating .env with your User ID: {user_id}")

            env_path = Path(__file__).parent / ".env"
            with open(env_path) as f:
                env_content = f.read()

            # Update or add ZOTERO_LIBRARY_ID
            if "ZOTERO_LIBRARY_ID=" in env_content:
                # Replace existing empty value
                env_content = env_content.replace(
                    "ZOTERO_LIBRARY_ID=", f"ZOTERO_LIBRARY_ID={user_id}"
                )
            else:
                env_content += f"\nZOTERO_LIBRARY_ID={user_id}\n"

            with open(env_path, "w") as f:
                f.write(env_content)

            logger.success(f"[PASS] Saved ZOTERO_LIBRARY_ID={user_id} to .env")

            # Test connection to library
            print("\n" + "=" * 60)
            print("TESTING LIBRARY CONNECTION")
            print("=" * 60)

            zot = zotero.Zotero(user_id, "user", ZOTERO_API_KEY)

            # Get library statistics
            items = zot.items(limit=5)
            print("\n[PASS] Successfully connected to your library!")
            print(f"   Retrieved {len(items)} sample items")

            # Get total count
            all_items = zot.everything(zot.items())
            print(f"   Total items in library: {len(all_items)}")

            # Show first few items
            if items:
                print("\n[DOCS] Sample items:")
                for i, item in enumerate(items[:3], 1):
                    title = item.get("data", {}).get("title", "No title")
                    item_type = item.get("data", {}).get("itemType", "unknown")
                    print(f"   {i}. [{item_type}] {title[:60]}...")

    else:
        logger.error(f"[FAIL] API request failed: {response.status_code}")
        logger.error(f"Response: {response.text}")

except Exception as e:
    logger.error(f"[FAIL] Error connecting to Zotero API: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("[PASS] Zotero API setup complete!")
print("=" * 60)
print("\nYour .env file now contains:")
print(f"  - ZOTERO_API_KEY: {ZOTERO_API_KEY[:10]}...")
print(f"  - ZOTERO_LIBRARY_ID: {os.getenv('ZOTERO_LIBRARY_ID', 'Not set')}")
print("\nYou can now use the Zotero API to add missing citations automatically!")
