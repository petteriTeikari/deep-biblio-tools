#!/usr/bin/env python3
"""
Verify that author names in markdown citations match Zotero library.

Checks that the last name(s) in markdown citations like [Smith et al., 2024]
match the actual authors in the Zotero JSON entry for that URL.
"""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def extract_citations_from_markdown(md_path: Path) -> list[dict]:
    """
    Extract all citations from markdown.

    Returns list of: {text: str, url: str, line: int}
    """
    citations = []

    with open(md_path) as f:
        for line_num, line in enumerate(f, 1):
            # Find all [text](url) patterns manually
            i = 0
            while i < len(line):
                if line[i] == "[":
                    # Find closing ]
                    j = i + 1
                    bracket_depth = 1
                    while j < len(line) and bracket_depth > 0:
                        if line[j] == "[":
                            bracket_depth += 1
                        elif line[j] == "]":
                            bracket_depth -= 1
                        j += 1

                    if bracket_depth == 0 and j < len(line) and line[j] == "(":
                        # Found [text](
                        text = line[i + 1 : j - 1]

                        # Find closing )
                        k = j + 1
                        paren_depth = 1
                        while k < len(line) and paren_depth > 0:
                            if line[k] == "(":
                                paren_depth += 1
                            elif line[k] == ")":
                                paren_depth -= 1
                            k += 1

                        if paren_depth == 0:
                            url = line[j + 1 : k - 1]

                            # Only include citations (have year and comma)
                            if "," in text and any(c.isdigit() for c in text):
                                citations.append(
                                    {
                                        "text": text,
                                        "url": url,
                                        "line": line_num,
                                    }
                                )
                            i = k
                        else:
                            i += 1
                    else:
                        i += 1
                else:
                    i += 1

    return citations


def normalize_url(url: str) -> str:
    """Normalize URL for matching."""
    url = url.lower()

    # Remove http/https
    url = url.replace("https://", "").replace("http://", "")

    # Remove www
    url = url.replace("www.", "")

    # Remove trailing slashes
    url = url.rstrip("/")

    # For arXiv, normalize to just the ID
    if "arxiv.org" in url:
        for pattern in ["/abs/", "/html/", "/pdf/"]:
            if pattern in url:
                arxiv_id = (
                    url.split(pattern)[-1]
                    .split("/")[0]
                    .split("?")[0]
                    .split("#")[0]
                )
                # Remove version suffix
                if "v" in arxiv_id:
                    v_pos = arxiv_id.rfind("v")
                    if arxiv_id[v_pos + 1 :].isdigit():
                        arxiv_id = arxiv_id[:v_pos]
                return f"arxiv:{arxiv_id}"

    # For DOIs, extract just the DOI
    if "doi.org" in url:
        doi = url.split("doi.org/")[-1]
        return f"doi:{doi}"

    return url


def load_zotero_library(json_path: Path) -> dict[str, dict]:
    """
    Load Zotero library and create URL -> entry mapping.

    Returns: {normalized_url: zotero_entry}
    """
    with open(json_path) as f:
        data = json.load(f)

    url_to_entry = {}

    for item in data:
        # Handle both Zotero JSON and CSL JSON formats
        item_data = item.get(
            "data", item
        )  # Zotero has "data" wrapper, CSL doesn't
        url = item_data.get("url") or item_data.get(
            "URL", ""
        )  # CSL uses uppercase URL

        if url:
            normalized = normalize_url(url)
            url_to_entry[normalized] = item_data

    logger.info(f"Loaded {len(url_to_entry)} entries from Zotero")
    return url_to_entry


def extract_last_names(citation_text: str) -> list[str]:
    """
    Extract last names from citation text like 'Smith et al., 2024' or 'Smith & Jones, 2024'.

    Returns list of last names.
    """
    # Remove year and everything after comma
    if "," in citation_text:
        names_part = citation_text.split(",")[0].strip()
    else:
        names_part = citation_text.strip()

    # Check for "et al."
    if "et al" in names_part.lower():
        # Extract first author
        first_author = names_part.split("et al")[0].strip()
        # Remove any trailing punctuation
        first_author = first_author.rstrip(".,; ")
        return [first_author]

    # Check for "&" or "and"
    if "&" in names_part:
        authors = names_part.split("&")
    elif " and " in names_part.lower():
        authors = names_part.lower().split(" and ")
    else:
        # Single author
        authors = [names_part]

    # Clean up
    last_names = []
    for author in authors:
        author = author.strip().rstrip(".,; ")
        if author:
            last_names.append(author)

    return last_names


def verify_author_names(
    md_path: Path, zotero_json: Path, output_path: Path
) -> None:
    """Verify author names in markdown match Zotero library."""
    logger.info(f"Loading citations from {md_path.name}...")
    citations = extract_citations_from_markdown(md_path)

    logger.info(f"Loading Zotero library from {zotero_json.name}...")
    zotero_lib = load_zotero_library(zotero_json)

    logger.info(f"Found {len(citations)} citations to verify\n")
    logger.info("=" * 80)

    results = {
        "total": len(citations),
        "verified": 0,
        "mismatches": 0,
        "not_in_zotero": 0,
        "issues": [],
    }

    for i, citation in enumerate(citations, 1):
        text = citation["text"]
        url = citation["url"]
        line = citation["line"]

        # Skip internal anchors
        if url.startswith("#"):
            continue

        normalized_url = normalize_url(url)

        # Find in Zotero
        zotero_entry = zotero_lib.get(normalized_url)

        if not zotero_entry:
            logger.warning(
                f"\n[{i}/{len(citations)}] Line {line}: NOT IN ZOTERO"
            )
            logger.warning(f"  Citation: [{text}]({url})")
            results["not_in_zotero"] += 1
            results["issues"].append(
                {
                    "line": line,
                    "citation": text,
                    "url": url,
                    "issue": "Not found in Zotero library",
                    "severity": "WARNING",
                }
            )
            continue

        # Extract last names from citation
        citation_last_names = extract_last_names(text)

        # Extract last names from Zotero entry
        # Handle both Zotero format (creators with lastName) and CSL format (author with family)
        zotero_creators = zotero_entry.get("creators") or zotero_entry.get(
            "author", []
        )
        zotero_last_names = []
        for creator in zotero_creators:
            # Zotero format: creatorType, lastName
            if isinstance(creator, dict):
                if "lastName" in creator:
                    # Zotero JSON format
                    if creator.get("creatorType") in ["author", "editor"]:
                        last_name = creator.get("lastName", "")
                        if last_name:
                            zotero_last_names.append(last_name)
                elif "family" in creator:
                    # CSL JSON format
                    last_name = creator.get("family", "")
                    if last_name:
                        zotero_last_names.append(last_name)

        # Verify match
        if not zotero_last_names:
            logger.warning(
                f"\n[{i}/{len(citations)}] Line {line}: NO AUTHORS IN ZOTERO"
            )
            logger.warning(f"  Citation: [{text}]({url})")
            logger.warning(f"  Title: {zotero_entry.get('title', 'N/A')[:60]}")
            results["issues"].append(
                {
                    "line": line,
                    "citation": text,
                    "url": url,
                    "issue": "Zotero entry has no authors",
                    "severity": "WARNING",
                }
            )
            continue

        # Check if citation first author matches Zotero first author
        citation_first = (
            citation_last_names[0].lower() if citation_last_names else ""
        )
        zotero_first = zotero_last_names[0].lower()

        if (
            citation_first not in zotero_first
            and zotero_first not in citation_first
        ):
            logger.error(
                f"\n[{i}/{len(citations)}] Line {line}: AUTHOR MISMATCH"
            )
            logger.error(f"  Citation: [{text}]")
            logger.error(
                f"  Citation author(s): {', '.join(citation_last_names)}"
            )
            logger.error(
                f"  Zotero authors: {', '.join(zotero_last_names[:3])}"
            )
            logger.error(f"  Title: {zotero_entry.get('title', 'N/A')[:60]}")
            logger.error(f"  URL: {url}")
            results["mismatches"] += 1
            results["issues"].append(
                {
                    "line": line,
                    "citation": text,
                    "url": url,
                    "citation_authors": citation_last_names,
                    "zotero_authors": zotero_last_names,
                    "title": zotero_entry.get("title", ""),
                    "issue": "Author name mismatch",
                    "severity": "ERROR",
                }
            )
        else:
            results["verified"] += 1
            if i % 50 == 0:
                logger.info(f"Verified {i}/{len(citations)} citations...")

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("AUTHOR VERIFICATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total citations: {results['total']}")
    logger.info(f"Verified (correct): {results['verified']}")
    logger.info(f"Author mismatches: {results['mismatches']}")
    logger.info(f"Not in Zotero: {results['not_in_zotero']}")

    if results["issues"]:
        logger.info(f"\n{len(results['issues'])} ISSUES FOUND:")
        logger.info("=" * 80)
        for issue in results["issues"]:
            logger.info(f"\nLine {issue['line']}: [{issue['citation']}]")
            logger.info(f"  URL: {issue['url']}")
            logger.info(f"  {issue['severity']}: {issue['issue']}")
            if "citation_authors" in issue:
                logger.info(
                    f"  Citation: {', '.join(issue['citation_authors'])}"
                )
                logger.info(
                    f"  Zotero: {', '.join(issue['zotero_authors'][:5])}"
                )

    # Write results
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\nFull results written to: {output_path}")

    if results["mismatches"] > 0:
        logger.error(
            f"\nFAILED: {results['mismatches']} author name mismatches found"
        )
        sys.exit(1)
    else:
        logger.info("\nSUCCESS: All author names verified")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify author names in citations"
    )
    parser.add_argument("markdown", type=Path, help="Markdown file to check")
    parser.add_argument(
        "zotero_json", type=Path, help="Zotero library JSON export"
    )
    parser.add_argument(
        "--output", type=Path, default=Path("author-verification.json")
    )

    args = parser.parse_args()

    verify_author_names(args.markdown, args.zotero_json, args.output)
