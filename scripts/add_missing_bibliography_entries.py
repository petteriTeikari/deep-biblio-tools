#!/usr/bin/env python3
"""Add missing bibliography entries from references.bib to LaTeX document."""

import argparse

# import re  # Banned - using string methods instead
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode


def format_authors(authors_str):
    """Format author names from BibTeX format."""
    if not authors_str:
        return "Unknown"

    # Handle "and others"
    authors_str = authors_str.replace(" and others", " et al.")

    # Split by 'and'
    authors = [a.strip() for a in authors_str.split(" and ")]

    # Format each author
    formatted = []
    for author in authors:
        # Handle "Last, First" format
        if "," in author:
            parts = author.split(",", 1)
            author = f"{parts[1].strip()} {parts[0].strip()}"
        formatted.append(author)

    # Join authors
    if len(formatted) > 2:
        return ", ".join(formatted[:-1]) + ", " + formatted[-1]
    elif len(formatted) == 2:
        return " and ".join(formatted)
    else:
        return formatted[0] if formatted else "Unknown"


def format_bibitem(key, entry):
    """Format a bibliography entry as \bibitem."""

    # Extract basic fields
    authors = format_authors(entry.get("author", entry.get("editor", "")))
    year = entry.get("year", "")
    if not year and "date" in entry:
        # Extract year from date
        date_str = entry["date"]
        if len(date_str) >= 4 and date_str[:4].isdigit():
            year = date_str[:4]

    title = entry.get("title", "").replace("{", "").replace("}", "")

    # Get URL
    url = entry.get("url", "")
    if not url and "doi" in entry:
        url = f"https://doi.org/{entry['doi']}"
    elif not url and "eprint" in entry and entry.get("eprinttype") == "arXiv":
        url = f"https://arxiv.org/abs/{entry['eprint']}"

    # Start building the entry
    if url:
        result = (
            f"\\bibitem{{{key}}} \\href{{{url}}}{{{authors} ({year})}} {title}"
        )
    else:
        result = f"\\bibitem{{{key}}} {authors} ({year}) {title}"

    # Add journal/venue info
    entry_type = entry.get("ENTRYTYPE", "misc")

    if entry_type == "article":
        journal = entry.get("journaltitle", entry.get("journal", ""))
        if journal:
            result += f" {{\\em {journal}"
            if "volume" in entry:
                result += f" {entry['volume']}}}"
                if "number" in entry:
                    result += f"({entry['number']})"
            else:
                result += "}"
            if "pages" in entry:
                pages = entry["pages"].replace("-", "--")
                result += f":{pages}"

    elif entry_type in ["inproceedings", "conference"]:
        booktitle = entry.get("booktitle", entry.get("series", ""))
        if booktitle:
            result += f" {{\\em {booktitle}}}"
            if "pages" in entry:
                pages = entry["pages"].replace("-", "--")
                result += f":{pages}"

    elif "eprint" in entry and entry.get("eprinttype") == "arXiv":
        result += f" {{\\em arXiv:{entry['eprint']}}}"

    elif entry_type in ["online", "misc", "webpage"]:
        if "urldate" in entry:
            result += f" (accessed {entry['urldate']})"

    # Ensure it ends with period
    if not result.rstrip().endswith("."):
        result += "."

    return result


def get_missing_entries(tex_path, bib_path):
    """Find citations in tex file that are missing from bibliography."""

    # Read tex content
    tex_content = tex_path.read_text(encoding="utf-8")

    # Extract all citations (both \cite and \citep)
    citations = set()

    # Find all \cite{...} and \citep{...} commands
    i = 0
    while i < len(tex_content):
        # Look for \cite or \citep
        if tex_content[i : i + 5] == "\\cite":
            # Check if it's \cite{ or \citep{
            start_idx = i + 5
            if start_idx < len(tex_content) and tex_content[start_idx] == "p":
                start_idx += 1

            if start_idx < len(tex_content) and tex_content[start_idx] == "{":
                # Find closing brace
                brace_count = 1
                j = start_idx + 1
                while j < len(tex_content) and brace_count > 0:
                    if tex_content[j] == "{":
                        brace_count += 1
                    elif tex_content[j] == "}":
                        brace_count -= 1
                    j += 1

                if brace_count == 0:
                    # Extract citation keys
                    cite_content = tex_content[start_idx + 1 : j - 1]
                    # Split by comma for multiple citations
                    keys = [k.strip() for k in cite_content.split(",")]
                    citations.update(keys)
                    i = j
                    continue

        i += 1

    # Extract existing bibitem keys
    existing = set()
    i = 0
    while i < len(tex_content):
        if tex_content[i : i + 8] == "\\bibitem":
            j = i + 8

            # Skip optional [...] part
            if j < len(tex_content) and tex_content[j] == "[":
                bracket_count = 1
                j += 1
                while j < len(tex_content) and bracket_count > 0:
                    if tex_content[j] == "[":
                        bracket_count += 1
                    elif tex_content[j] == "]":
                        bracket_count -= 1
                    j += 1

            # Now look for {key}
            if j < len(tex_content) and tex_content[j] == "{":
                brace_start = j + 1
                brace_count = 1
                j += 1
                while j < len(tex_content) and brace_count > 0:
                    if tex_content[j] == "{":
                        brace_count += 1
                    elif tex_content[j] == "}":
                        brace_count -= 1
                    j += 1

                if brace_count == 0:
                    key = tex_content[brace_start : j - 1].strip()
                    if key:
                        existing.add(key)

                i = j
                continue

        i += 1

    # Find missing
    missing = citations - existing

    # Parse bib file (with custom parser that accepts all entry types)
    parser = BibTexParser()
    parser.customization = convert_to_unicode
    # Don't ignore any entry types
    parser.ignore_nonstandard_types = False

    with open(bib_path, encoding="utf-8") as bibfile:
        bib_content = bibfile.read()
        # Manually handle all entry types by replacing them with @misc temporarily
        # This is a workaround for bibtexparser limitations
        modified_content = bib_content
        for entry_type in [
            "@online",
            "@software",
            "@report",
            "@thesis",
            "@patent",
        ]:
            modified_content = modified_content.replace(
                entry_type + "{", "@misc{"
            )

        bib_database = bibtexparser.loads(modified_content, parser=parser)

    # Create entries for missing citations
    missing_entries = {}
    for entry in bib_database.entries:
        if entry.get("ID", "") in missing:
            missing_entries[entry["ID"]] = entry

    return missing, missing_entries


def main():
    parser = argparse.ArgumentParser(
        description="Add missing bibliography entries from references.bib"
    )
    parser.add_argument(
        "tex_file", type=Path, help="LaTeX file with bibliography"
    )
    parser.add_argument(
        "bib_file", type=Path, help="BibTeX file with references"
    )
    parser.add_argument("-o", "--output", type=Path, help="Output file")

    args = parser.parse_args()

    if not args.tex_file.exists():
        print(f"Error: TeX file not found: {args.tex_file}")
        return 1

    if not args.bib_file.exists():
        print(f"Error: Bib file not found: {args.bib_file}")
        return 1

    # Find missing entries
    missing_keys, missing_entries = get_missing_entries(
        args.tex_file, args.bib_file
    )

    print(f"Found {len(missing_keys)} missing citations")
    print(f"Found {len(missing_entries)} of them in references.bib")

    if not missing_entries:
        print("No missing entries to add.")
        return 0

    # Read tex content
    tex_content = args.tex_file.read_text(encoding="utf-8")

    # Find where to insert (before \end{thebibliography})
    end_tag = "\\end{thebibliography}"
    end_idx = tex_content.find(end_tag)

    if end_idx == -1:
        print("Error: Could not find \\end{thebibliography}")
        return 1

    before_end = tex_content[:end_idx].rstrip()

    # Format missing entries
    new_entries = []
    for key in sorted(missing_entries.keys()):
        entry = missing_entries[key]
        formatted = format_bibitem(key, entry)
        new_entries.append(formatted)
        print(f"Adding: {key}")

    # Insert new entries
    new_content = (
        before_end
        + "\n\n"
        + "\n\n".join(new_entries)
        + "\n\n"
        + end_tag
        + tex_content[end_idx + len(end_tag) :]
    )

    # Write output
    output_path = args.output or args.tex_file.with_stem(
        args.tex_file.stem + "_complete"
    )
    output_path.write_text(new_content, encoding="utf-8")

    print(f"\nAdded {len(new_entries)} missing entries to: {output_path}")

    return 0


if __name__ == "__main__":
    exit(main())
