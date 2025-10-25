#!/usr/bin/env python3
"""Fix bibliography and add notes explaining why metadata is incomplete."""

import sys
import time
from pathlib import Path

import bibtexparser
import requests
from bibtexparser.bwriter import BibTexWriter


def check_doi_metadata(doi: str) -> tuple[bool, dict, str]:
    """Check if we can fetch metadata for a DOI and return the reason if not."""
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

            # Extract other metadata
            title = (
                message.get("title", [""])[0]
                if isinstance(message.get("title"), list)
                else message.get("title", "")
            )
            journal = (
                message.get("container-title", [""])[0]
                if isinstance(message.get("container-title"), list)
                else message.get("container-title", "")
            )

            return (
                True,
                {
                    "authors": authors,
                    "title": title,
                    "journal": journal,
                    "volume": str(message.get("volume", ""))
                    if message.get("volume")
                    else "",
                    "issue": str(message.get("issue", ""))
                    if message.get("issue")
                    else "",
                    "pages": message.get("page", ""),
                    "year": str(
                        message.get("published-print", {}).get(
                            "date-parts", [[]]
                        )[0][0]
                    )
                    if message.get("published-print")
                    else "",
                },
                "Success",
            )
        elif response.status_code == 404:
            return False, {}, "DOI not found (404)"
        elif response.status_code == 429:
            return False, {}, "CrossRef rate limit (429)"
        else:
            return False, {}, f"CrossRef HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        return False, {}, "CrossRef timeout"
    except requests.exceptions.ConnectionError:
        return False, {}, "CrossRef connection error"
    except Exception as e:
        return False, {}, f"CrossRef error: {str(e)[:50]}"


def check_url_status(url: str) -> tuple[bool, str]:
    """Check URL accessibility and return status."""
    if not url:
        return True, ""

    # Check for known problematic domains
    problematic_domains = {
        "researchgate.net": "ResearchGate often blocks automated access",
        "mdpi.com": "MDPI may block automated requests",
        "linkedin.com": "LinkedIn blocks automated access",
        "medium.com": "Medium blocks automated access",
    }

    for domain, message in problematic_domains.items():
        if domain in url.lower():
            return False, message

    # Try to access the URL
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
            return True, ""
        elif response.status_code == 403:
            return False, "URL blocked (403 Forbidden)"
        elif response.status_code == 404:
            return False, "URL not found (404)"
        elif response.status_code == 429:
            return False, "URL rate limited (429)"
        else:
            return False, f"URL returned HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "URL timeout"
    except Exception as e:
        return False, f"URL error: {str(e)[:30]}"


def has_incomplete_authors(entry: dict) -> bool:
    """Check if entry has incomplete author information."""
    if "author" not in entry:
        return True

    authors = entry["author"].split(" and ")
    for author in authors:
        author = author.strip()
        if not author:
            continue
        # Check for single name (no comma, no space)
        if "," not in author and " " not in author:
            return True
        # Check for missing first name (has comma but nothing after)
        if "," in author and not author.split(",")[1].strip():
            return True

    return False


def enhance_entry_with_notes(entry: dict) -> tuple[dict, list[str]]:
    """Enhance entry and add notes explaining any issues."""
    fixes = []
    notes = []

    # Check if authors are incomplete
    if has_incomplete_authors(entry):
        # Try to fetch from DOI if available
        if "doi" in entry and entry["doi"]:
            print(f"  Checking DOI for {entry.get('ID', 'unknown')}...")
            time.sleep(0.3)  # Rate limiting

            success, metadata, reason = check_doi_metadata(entry["doi"])

            if success and metadata.get("authors"):
                # Update with full author names
                entry["author"] = " and ".join(metadata["authors"])
                fixes.append("authors_from_doi")

                # Update other fields if better
                if metadata.get("title") and not entry.get("title"):
                    entry["title"] = metadata["title"]
                    fixes.append("title_from_doi")
                if metadata.get("journal") and not entry.get("journal"):
                    entry["journal"] = metadata["journal"]
                    fixes.append("journal_from_doi")
            else:
                # Add note explaining why we couldn't get full names
                notes.append(
                    f"Incomplete authors - DOI lookup failed: {reason}"
                )
        else:
            # No DOI available
            notes.append(
                "Incomplete authors - no DOI available for verification"
            )

    # Check URL status
    if "url" in entry:
        accessible, url_status = check_url_status(entry["url"])
        if not accessible:
            notes.append(f"URL issue: {url_status}")

    # Check for placeholder title
    if entry.get("title") == "Title not available - manual verification needed":
        notes.append("Title needs manual verification")

    # Check for specific publisher issues
    if "doi" in entry:
        doi = entry["doi"]
        if "10.3390/" in doi:  # MDPI
            if has_incomplete_authors(entry):
                notes.append(
                    "MDPI journal - may have blocked metadata extraction"
                )
        elif "10.1155/" in doi:  # Hindawi
            if has_incomplete_authors(entry):
                notes.append("Hindawi journal - metadata may be incomplete")

    # Add notes to entry
    if notes:
        existing_note = entry.get("note", "")
        if existing_note:
            entry["note"] = existing_note + "; " + "; ".join(notes)
        else:
            entry["note"] = "; ".join(notes)
        fixes.append("added_notes")

    return entry, fixes


def fix_bibliography_with_notes(
    input_file: Path, output_file: Path | None = None
) -> Path:
    """Fix bibliography and add notes explaining issues."""
    print(f"Reading bibliography from: {input_file}")

    with open(input_file, encoding="utf-8") as f:
        bib_database = bibtexparser.load(f)

    entries = bib_database.entries
    print(f"Total entries: {len(entries)}")
    print("\nAnalyzing entries and fetching missing metadata...")

    # Track statistics
    stats = {
        "incomplete_authors": 0,
        "doi_lookups": 0,
        "doi_success": 0,
        "url_issues": 0,
        "notes_added": 0,
        "total_fixed": 0,
    }

    # Process each entry
    for i, entry in enumerate(entries):
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(entries)} entries...")

        # Check if entry needs attention
        if has_incomplete_authors(entry):
            stats["incomplete_authors"] += 1

        entry, fixes = enhance_entry_with_notes(entry)

        if fixes:
            stats["total_fixed"] += 1
            for fix in fixes:
                if fix == "authors_from_doi":
                    stats["doi_success"] += 1
                elif fix == "added_notes":
                    stats["notes_added"] += 1

    # Write output
    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}_with_notes.bib"

    writer = BibTexWriter()
    writer.indent = "  "
    writer.order_entries_by = "ID"
    writer.align_values = True

    with open(output_file, "w", encoding="utf-8") as f:
        bibtexparser.dump(bib_database, f, writer)

    print(f"\nEnhanced bibliography written to: {output_file}")
    print("\nStatistics:")
    print(f"  Entries with incomplete authors: {stats['incomplete_authors']}")
    print(f"  Successful DOI lookups: {stats['doi_success']}")
    print(f"  Notes added: {stats['notes_added']}")
    print(f"  Total entries modified: {stats['total_fixed']}")

    # Show examples of entries with notes
    print("\nExamples of entries with notes:")
    examples_shown = 0
    for entry in entries:
        if "note" in entry and examples_shown < 5:
            print(f"  - {entry.get('ID')}: {entry['note'][:80]}...")
            examples_shown += 1

    return output_file


def main():
    """Main function."""
    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
    else:
        print(
            "Usage: python fix_bibliography_with_notes.py <input.bib> [output.bib]"
        )
        return 1

    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        return 1

    output_file = None
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])

    try:
        fix_bibliography_with_notes(input_file, output_file)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
