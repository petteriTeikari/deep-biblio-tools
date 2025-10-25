#!/usr/bin/env python3
"""Debug bibliography entries to understand why metadata is incomplete."""

import sys
import time
from pathlib import Path

import bibtexparser
import requests


def check_doi_metadata(doi: str) -> tuple[bool, dict, str]:
    """Check if we can fetch metadata for a DOI."""
    url = f"https://api.crossref.org/works/{doi}"
    headers = {
        "User-Agent": "DeepBiblioTools/1.0 (mailto:petteri.teikari@gmail.com)"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            message = data.get("message", {})

            # Extract authors
            authors = []
            if "author" in message:
                for author in message["author"]:
                    family = author.get("family", "")
                    given = author.get("given", "")
                    if family and given:
                        authors.append(f"{family}, {given}")
                    elif family:
                        authors.append(family)

            return (
                True,
                {
                    "authors": authors,
                    "title": message.get("title", [""])[0]
                    if isinstance(message.get("title"), list)
                    else message.get("title", ""),
                    "journal": message.get("container-title", [""])[0]
                    if isinstance(message.get("container-title"), list)
                    else message.get("container-title", ""),
                },
                "Success",
            )
        elif response.status_code == 404:
            return False, {}, "DOI not found"
        elif response.status_code == 429:
            return False, {}, "Rate limited"
        else:
            return False, {}, f"HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        return False, {}, "Timeout"
    except Exception as e:
        return False, {}, f"Error: {str(e)}"


def check_url_accessibility(url: str) -> tuple[bool, str]:
    """Check if URL is accessible and what type of content it has."""
    if not url:
        return False, "No URL"

    try:
        response = requests.head(
            url,
            timeout=5,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; DeepBiblioTools/1.0)"
            },
        )

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            if "html" in content_type:
                return True, "HTML page"
            elif "pdf" in content_type:
                return True, "PDF document"
            else:
                return True, f"Other: {content_type}"
        elif response.status_code == 403:
            return False, "Blocked (403 Forbidden)"
        elif response.status_code == 404:
            return False, "Not found (404)"
        elif response.status_code == 429:
            return False, "Rate limited (429)"
        else:
            return False, f"HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except Exception as e:
        return False, f"Error: {str(e)}"


def analyze_entry(entry: dict) -> dict[str, any]:
    """Analyze a bibliography entry to understand its issues."""
    issues = []
    metadata_source = "Unknown"
    fixable = False

    # Check author issues
    if "author" in entry:
        authors = entry["author"].split(" and ")
        for author in authors:
            if author and "," not in author and " " not in author:
                issues.append(f"Single name author: '{author}'")
                fixable = True  # Could be fixed with DOI lookup
    else:
        issues.append("No author field")

    # Check if we have DOI
    has_doi = "doi" in entry

    # Check URL status
    if "url" in entry:
        accessible, url_status = check_url_accessibility(entry["url"])
        if not accessible:
            issues.append(f"URL issue: {url_status}")

        # Check if it's a known problematic source
        url = entry["url"].lower()
        if "researchgate.net" in url:
            metadata_source = "ResearchGate (often blocks scrapers)"
        elif "mdpi.com" in url:
            metadata_source = "MDPI (may block automated requests)"
        elif "arxiv.org" in url:
            metadata_source = "arXiv"
        elif "doi.org" in url or has_doi:
            metadata_source = "DOI/CrossRef"

    # If we have DOI, check if we can get better metadata
    if has_doi:
        doi = entry["doi"]
        success, metadata, reason = check_doi_metadata(doi)

        if success:
            # Compare with current entry
            if metadata["authors"] and len(metadata["authors"]) > len(
                entry.get("author", "").split(" and ")
            ):
                issues.append(
                    f"Better author data available from DOI: {', '.join(metadata['authors'])}"
                )
                fixable = True
        else:
            issues.append(f"DOI lookup failed: {reason}")

    # Check title
    if "title" not in entry or not entry.get("title"):
        issues.append("Missing title")
    elif (
        entry.get("title") == "Title not available - manual verification needed"
    ):
        issues.append("Title placeholder - needs manual verification")

    return {
        "id": entry.get("ID", "unknown"),
        "issues": issues,
        "metadata_source": metadata_source,
        "has_doi": has_doi,
        "fixable": fixable,
        "entry": entry,
    }


def debug_bibliography_file(input_file: Path):
    """Debug issues in a bibliography file."""
    print(f"Debugging bibliography: {input_file}")
    print("=" * 60)

    with open(input_file, encoding="utf-8") as f:
        bib_database = bibtexparser.load(f)

    entries = bib_database.entries
    print(f"Total entries: {len(entries)}\n")

    # Categorize issues
    single_name_authors = []
    url_issues = []
    doi_fixable = []
    title_issues = []

    print("Analyzing entries...")
    for i, entry in enumerate(entries):
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(entries)} entries...")

        analysis = analyze_entry(entry)

        if any("Single name author" in issue for issue in analysis["issues"]):
            single_name_authors.append(analysis)

        if any("URL issue" in issue for issue in analysis["issues"]):
            url_issues.append(analysis)

        if analysis["fixable"] and analysis["has_doi"]:
            doi_fixable.append(analysis)

        if any("title" in issue.lower() for issue in analysis["issues"]):
            title_issues.append(analysis)

    # Report findings
    print("\n" + "=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)

    print(f"\n1. Single Name Authors: {len(single_name_authors)} entries")
    for item in single_name_authors[:10]:
        print(
            f"   - {item['id']}: {[i for i in item['issues'] if 'Single name' in i]}"
        )
        if item["has_doi"]:
            print(f"     DOI available: {item['entry'].get('doi')}")
        print(f"     Source: {item['metadata_source']}")

    print(f"\n2. URL Issues: {len(url_issues)} entries")
    for item in url_issues[:10]:
        print(f"   - {item['id']}: {[i for i in item['issues'] if 'URL' in i]}")
        print(f"     URL: {item['entry'].get('url', 'No URL')}")

    print(f"\n3. Potentially Fixable with DOI: {len(doi_fixable)} entries")
    for item in doi_fixable[:5]:
        print(f"   - {item['id']}: Has DOI {item['entry'].get('doi')}")
        for issue in item["issues"]:
            if "Better author data" in issue:
                print(f"     {issue}")

    print(f"\n4. Title Issues: {len(title_issues)} entries")
    for item in title_issues[:5]:
        print(
            f"   - {item['id']}: {[i for i in item['issues'] if 'title' in i.lower()]}"
        )

    # Sample check of specific problem entries
    print("\n" + "=" * 60)
    print("DETAILED CHECK OF PROBLEM ENTRIES")
    print("=" * 60)

    problem_ids = ["abdulsaheb2023", "ahmad2024", "alqudsi2025a"]
    for entry_id in problem_ids:
        entry = next((e for e in entries if e.get("ID") == entry_id), None)
        if entry:
            print(f"\n{entry_id}:")
            print(f"  Current author: {entry.get('author', 'N/A')}")
            print(f"  DOI: {entry.get('doi', 'N/A')}")
            print(f"  URL: {entry.get('url', 'N/A')}")

            if "doi" in entry:
                print("  Checking DOI metadata...")
                time.sleep(0.5)  # Rate limiting
                success, metadata, reason = check_doi_metadata(entry["doi"])
                if success:
                    print(
                        f"    Authors from DOI: {', '.join(metadata['authors'])}"
                    )
                    print(f"    Title from DOI: {metadata['title']}")
                else:
                    print(f"    DOI check failed: {reason}")


def main():
    """Main function."""
    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
    else:
        # Default to the most recent bibliography
        input_file = Path("drone_data/latex_output_improved/references.bib")

    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        return 1

    try:
        debug_bibliography_file(input_file)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
