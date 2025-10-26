#!/usr/bin/env python3
"""Test abstract extraction logic directly."""

import json
import re

# Read the HTML file
test_file = "/home/petteri/Dropbox/LABs/github-personal/github/deep-biblio-tools/data/elsevier_manual_scrape/2D–3D fusion approach for improved point cloud segmentation - ScienceDirect.html"

with open(test_file, encoding="utf-8") as f:
    html_content = f.read()

# Method 3: Look for __PRELOADED_STATE__ JavaScript object
print("Testing Method 3: Extracting from __PRELOADED_STATE__...")

# Find the script containing __PRELOADED_STATE__
script_match = re.search(
    r"<script[^>]*>.*?window\.__PRELOADED_STATE__\s*=\s*({.*?});.*?</script>",
    html_content,
    re.DOTALL,
)

if script_match:
    print("Found __PRELOADED_STATE__ script")

    # Extract the JSON data
    json_match = re.search(
        r"window\.__PRELOADED_STATE__\s*=\s*({.*?});",
        script_match.group(0),
        re.DOTALL,
    )

    if json_match:
        print("Extracted JSON data")

        try:
            preloaded_data = json.loads(json_match.group(1))
            print("Successfully parsed JSON")

            # Navigate through the nested structure
            abstracts = preloaded_data.get("abstracts", {})
            content = abstracts.get("content", [])

            print(f"Found {len(content)} content items")

            abstract_text = None
            for item in content:
                if item.get("$", {}).get("class") == "author":
                    print("Found author abstract section")
                    sections = item.get("$$", [])
                    for section in sections:
                        if section.get("$", {}).get("id") == "as0005":
                            print("Found as0005 section")
                            paras = section.get("$$", [])
                            for para in paras:
                                if para.get("$", {}).get("id") == "sp0140":
                                    print("Found sp0140 paragraph")
                                    # Extract text from the complex structure
                                    text_parts = []
                                    if isinstance(para.get("$$"), list):
                                        for part in para["$$"]:
                                            if part.get("#name") == "__text__":
                                                text_parts.append(
                                                    part.get("_", "")
                                                )
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
                                    elif isinstance(para.get("_"), str):
                                        text_parts.append(para["_"])
                                    abstract_text = " ".join(text_parts).strip()
                                    break

            if abstract_text:
                print(f"\nExtracted abstract ({len(abstract_text)} chars):")
                print(
                    abstract_text[:500] + "..."
                    if len(abstract_text) > 500
                    else abstract_text
                )
            else:
                print("\nNo abstract found in JSON structure")

        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
        except Exception as e:
            print(f"Error navigating JSON structure: {e}")
    else:
        print("Could not extract JSON from script")
else:
    print("__PRELOADED_STATE__ script not found")

# Also test simpler HTML pattern matching
print("\n\nTesting simple HTML pattern matching...")

# Look for the abstract section
abstract_match = re.search(
    r'<div[^>]*id="preview-section-abstract"[^>]*>.*?</div>',
    html_content,
    re.DOTALL,
)
if abstract_match:
    print("Found preview-section-abstract div")

    # Look for the actual abstract content
    content_match = re.search(
        r'<div[^>]*id="sp0140"[^>]*>(.*?)</div>', html_content, re.DOTALL
    )
    if content_match:
        print("Found sp0140 div")
        # Clean up the HTML
        text = re.sub(r"<[^>]+>", " ", content_match.group(1))
        text = re.sub(r"\s+", " ", text).strip()
        print(f"\nExtracted abstract from HTML ({len(text)} chars):")
        print(text[:500] + "..." if len(text) > 500 else text)
    else:
        print("sp0140 div not found")
