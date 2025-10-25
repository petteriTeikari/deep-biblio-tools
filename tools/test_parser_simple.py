#!/usr/bin/env python3
"""Test the parser without using BeautifulSoup directly."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Manually extract abstract using the logic from scraper_standalone
import json
import re


def extract_abstract_from_html(html_content):
    """Extract abstract using multiple methods."""
    # Method 1: Look for div with id="sp0140"
    match = re.search(
        r'<div[^>]*id="sp0140"[^>]*>(.*?)</div>', html_content, re.DOTALL
    )
    if match:
        # Clean HTML tags
        text = re.sub(r"<[^>]+>", " ", match.group(1))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            return text

    # Method 2: Look in __PRELOADED_STATE__
    script_match = re.search(
        r"window\.__PRELOADED_STATE__\s*=\s*({.*?});", html_content, re.DOTALL
    )
    if script_match:
        try:
            preloaded_data = json.loads(script_match.group(1))
            abstracts = preloaded_data.get("abstracts", {})
            content = abstracts.get("content", [])

            for item in content:
                if item.get("$", {}).get("class") == "author":
                    sections = item.get("$$", [])
                    for section in sections:
                        if section.get("$", {}).get("id") == "as0005":
                            paras = section.get("$$", [])
                            for para in paras:
                                if para.get("$", {}).get("id") == "sp0140":
                                    # Extract text
                                    if isinstance(para.get("_"), str):
                                        return para["_"]
                                    # Handle complex structure
                                    text_parts = []
                                    for part in para.get("$$", []):
                                        if part.get("#name") == "__text__":
                                            text_parts.append(part.get("_", ""))
                                        elif part.get("#name") == "topic-link":
                                            text_parts.append(part.get("_", ""))
                                        elif part.get(
                                            "#name"
                                        ) == "text" and isinstance(
                                            part.get("$$"), list
                                        ):
                                            for subpart in part["$$"]:
                                                if (
                                                    subpart.get("#name")
                                                    == "__text__"
                                                ):
                                                    text_parts.append(
                                                        subpart.get("_", "")
                                                    )
                                    if text_parts:
                                        return " ".join(text_parts).strip()
        except Exception:
            pass

    return None


# Test with the HTML file
test_file = "/home/petteri/Dropbox/LABs/KusiKasa/github/deep-biblio-tools/data/elsevier_manual_scrape/2D–3D fusion approach for improved point cloud segmentation - ScienceDirect.html"

with open(test_file, encoding="utf-8") as f:
    html_content = f.read()

abstract = extract_abstract_from_html(html_content)

if abstract:
    print(f"Successfully extracted abstract ({len(abstract)} characters):\n")
    print(abstract)
else:
    print("Failed to extract abstract")

# Also test title extraction
title_match = re.search(
    r'<span[^>]*class="title-text"[^>]*>(.*?)</span>', html_content, re.DOTALL
)
if title_match:
    title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
    print(f"\n\nTitle: {title}")

# DOI extraction
doi_match = re.search(
    r'<a[^>]*class="[^"]*doi[^"]*"[^>]*>(.*?)</a>', html_content, re.DOTALL
)
if doi_match:
    doi = re.sub(r"<[^>]+>", "", doi_match.group(1)).strip()
    print(f"\nDOI: {doi}")
