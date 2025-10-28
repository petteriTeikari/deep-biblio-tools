"""Analyze .bbl file to extract formatted bibliography entries and detect issues.

This script parses the .bbl file (output after BibTeX/Biber processing) to create
a CSV showing how each reference appears in the final document, and identifies
formatting glitches.
"""

import csv
import sys
from pathlib import Path


def parse_bibitem_entries(bbl_path: Path) -> list[dict]:
    """Parse .bbl file to extract all bibitem entries.

    Each entry is a dict with:
    - citation_key: The BibTeX key
    - label: The formatted author-year label
    - formatted_text: The full formatted citation
    - issues: List of detected issues
    """
    entries = []

    with open(bbl_path, encoding="utf-8") as f:
        content = f.read()

    # Find where bibliography starts
    bib_start = content.find("\\begin{thebibliography}")
    if bib_start == -1:
        print("ERROR: Could not find \\begin{thebibliography}")
        return entries

    # Extract just the bibliography section
    bib_end = content.find("\\end{thebibliography}", bib_start)
    if bib_end == -1:
        print("ERROR: Could not find \\end{thebibliography}")
        return entries

    bib_content = content[bib_start:bib_end]

    # Split into individual entries
    # Each entry starts with \bibitem
    lines = bib_content.split("\n")

    current_entry = None

    for line in lines:
        line = line.strip()

        # Skip empty lines and preamble
        if (
            not line
            or line.startswith("\\begin")
            or line.startswith("\\provide")
            or line.startswith("\\expandafter")
        ):
            continue

        if line.startswith("\\bibitem"):
            # Save previous entry if exists
            if current_entry is not None:
                entries.append(finalize_entry(current_entry))

            # Parse new bibitem
            # Format: \bibitem[{Label}]{citation_key}
            current_entry = parse_bibitem_line(line)

        elif current_entry is not None:
            # Accumulate formatted text
            current_entry["formatted_text"] += " " + line

    # Don't forget the last entry
    if current_entry is not None:
        entries.append(finalize_entry(current_entry))

    return entries


def parse_bibitem_line(line: str) -> dict:
    """Parse a \\bibitem line to extract label and citation key.

    Format: \\bibitem[{Label}]{citation_key} rest of text
    The label is in square brackets (optional)
    The citation key is in curly braces (required)
    """

    # First, extract label if it exists (in square brackets)
    label = ""
    label_start = line.find("[{")

    if label_start != -1:
        # Find the matching }]
        label_end = line.find("}]", label_start)
        if label_end != -1:
            label = line[label_start + 2 : label_end]
            # Citation key comes after the label
            key_start = line.find("{", label_end)
        else:
            # Malformed label, try to find key anyway
            key_start = line.find("{", label_start + 2)
    else:
        # No label, find first { after \bibitem
        bibitem_pos = line.find("\\bibitem")
        if bibitem_pos != -1:
            key_start = line.find("{", bibitem_pos)
        else:
            key_start = -1

    # Extract citation key
    if key_start == -1:
        return {
            "citation_key": "PARSE_ERROR",
            "label": "",
            "formatted_text": line,
            "issues": ["Failed to parse citation key"],
        }

    key_end = line.find("}", key_start)
    if key_end == -1:
        return {
            "citation_key": "PARSE_ERROR",
            "label": label,
            "formatted_text": line,
            "issues": ["Failed to find end of citation key"],
        }

    citation_key = line[key_start + 1 : key_end]

    # Extract any text after the citation key on the same line
    text_after = line[key_end + 1 :].strip()

    return {
        "citation_key": citation_key,
        "label": label,
        "formatted_text": text_after,
        "issues": [],
    }


def finalize_entry(entry: dict) -> dict:
    """Analyze entry for issues and clean up."""

    text = entry["formatted_text"].strip()
    entry["formatted_text"] = text

    # Detect issues
    issues = entry["issues"]

    # Issue 1: Empty or very short formatted text
    if len(text) < 10:
        issues.append("EMPTY_OR_TOO_SHORT")

    # Issue 2: Missing title (text ends right after year)
    # Pattern: ends with "(2021)" or "(2021) " with nothing after
    if text.endswith(")") and not any(c.isalpha() for c in text.split(")")[-1]):
        issues.append("MISSING_TITLE")

    # Issue 3: Contains "et~al" but very short (incomplete author list issue)
    if "et~al" in text and len(text) < 50:
        issues.append("INCOMPLETE_AUTHOR_SHORT")

    # Issue 4: Missing venue/journal (no lowercase words after year)
    # This is tricky, but we can check if there are capitalized words after the year
    year_markers = ["(2021)", "(2022)", "(2023)", "(2024)", "(2025)"]
    has_venue = False
    for marker in year_markers:
        if marker in text:
            after_year = text.split(marker, 1)[-1].strip()
            # Check if there's actual content after the year
            if len(after_year) > 5 and any(c.islower() for c in after_year):
                has_venue = True
                break

    if not has_venue and ")" in text:
        issues.append("MISSING_VENUE")

    # Issue 5: Contains "Unknown" or "Anonymous"
    if "Unknown" in text or "Anonymous" in text:
        issues.append("UNKNOWN_OR_ANONYMOUS")

    # Issue 6: Contains URL but no actual citation text
    if "\\href" in text and len(text) < 100:
        issues.append("URL_ONLY_NO_CONTENT")

    entry["issues"] = issues
    entry["issue_count"] = len(issues)
    entry["has_issues"] = len(issues) > 0

    return entry


def write_csv(entries: list[dict], output_path: Path):
    """Write entries to CSV file."""

    if not entries:
        print("ERROR: No entries to write")
        return

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "citation_key",
            "label",
            "formatted_text",
            "has_issues",
            "issue_count",
            "issues",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()

        for entry in entries:
            # Convert issues list to string
            entry_copy = entry.copy()
            entry_copy["issues"] = (
                "; ".join(entry["issues"]) if entry["issues"] else ""
            )
            writer.writerow(entry_copy)

    print(f"✅ Wrote {len(entries)} entries to {output_path}")

    # Print summary
    entries_with_issues = sum(1 for e in entries if e["has_issues"])
    print("\n📊 Summary:")
    print(f"  Total entries: {len(entries)}")
    print(f"  Entries with issues: {entries_with_issues}")
    print(f"  Clean entries: {len(entries) - entries_with_issues}")

    # Print issue breakdown
    issue_counts = {}
    for entry in entries:
        for issue in entry["issues"]:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    if issue_counts:
        print("\n⚠️  Issue breakdown:")
        for issue, count in sorted(
            issue_counts.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {issue}: {count}")


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python analyze_bbl_output.py <path_to_bbl_file> [output_csv]"
        )
        sys.exit(1)

    bbl_path = Path(sys.argv[1])

    if not bbl_path.exists():
        print(f"ERROR: File not found: {bbl_path}")
        sys.exit(1)

    # Default output path: same directory as input, with .csv extension
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = bbl_path.parent / f"{bbl_path.stem}_analysis.csv"

    print(f"📖 Parsing {bbl_path}...")
    entries = parse_bibitem_entries(bbl_path)

    print(f"💾 Writing analysis to {output_path}...")
    write_csv(entries, output_path)


if __name__ == "__main__":
    main()
