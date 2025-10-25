#!/usr/bin/env python3
"""Create a clean, deduplicated bibliography for uadReview."""

# import re  # Banned - using string methods instead
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.customization import convert_to_unicode


def extract_citations_from_tex(tex_path):
    """Extract all unique citations from the tex file."""
    content = tex_path.read_text(encoding="utf-8")
    citations = set()

    # Find all \cite{...} and \citep{...} commands using string methods
    i = 0
    while i < len(content):
        # Look for \cite or \citep
        cite_pos = content.find("\\cite", i)
        if cite_pos == -1:
            break

        # Check if it's \cite or \citep
        start_pos = cite_pos + 5  # len("\\cite")
        if start_pos < len(content) and content[start_pos] == "p":
            start_pos += 1  # Skip the 'p' in \citep

        # Look for the opening brace
        if start_pos < len(content) and content[start_pos] == "{":
            # Find the matching closing brace
            brace_count = 1
            end_pos = start_pos + 1
            while end_pos < len(content) and brace_count > 0:
                if content[end_pos] == "{":
                    brace_count += 1
                elif content[end_pos] == "}":
                    brace_count -= 1
                end_pos += 1

            if brace_count == 0:
                # Extract the citation keys
                citation_content = content[start_pos + 1 : end_pos - 1]
                # Split by comma for multiple citations
                keys = [k.strip() for k in citation_content.split(",")]
                citations.update(keys)

        i = cite_pos + 1

    return citations


def parse_bib_file(bib_path):
    """Parse a bib file and return entries as a dictionary."""
    parser = BibTexParser()
    parser.customization = convert_to_unicode
    parser.ignore_nonstandard_types = False

    with open(bib_path, encoding="utf-8") as bibfile:
        bib_database = bibtexparser.load(bibfile, parser=parser)

    # Create dictionary keyed by citation key
    entries = {}
    for entry in bib_database.entries:
        key = entry.get("ID", "")
        if key:
            entries[key] = entry

    return entries


def main():
    # Paths
    tex_path = Path("uadReview/main.tex")
    ref_bib_path = Path("uadReview/references.bib")
    uad_bib_path = Path("uadReview/uad_1st.bib")
    output_path = Path("uadReview/references_clean.bib")

    print("=== Creating Clean Bibliography for uadReview ===\n")

    # Extract all citations
    print("1. Extracting citations from main.tex...")
    citations = extract_citations_from_tex(tex_path)
    print(f"   Found {len(citations)} unique citations")

    # Parse both bib files
    print("\n2. Parsing bibliography files...")
    ref_entries = parse_bib_file(ref_bib_path)
    print(f"   references.bib: {len(ref_entries)} entries")

    uad_entries = parse_bib_file(uad_bib_path)
    print(f"   uad_1st.bib: {len(uad_entries)} entries")

    # Merge entries, preferring references.bib
    print("\n3. Merging entries...")
    all_entries = {}
    all_entries.update(uad_entries)  # First add uad entries
    all_entries.update(
        ref_entries
    )  # Then override with ref entries (preferred)
    print(f"   Total unique entries: {len(all_entries)}")

    # Create new database with only cited entries
    print("\n4. Creating clean bibliography with only cited entries...")
    cited_entries = []
    missing_citations = []

    for citation in sorted(citations):
        if citation in all_entries:
            cited_entries.append(all_entries[citation])
        else:
            missing_citations.append(citation)

    print(f"   Cited entries: {len(cited_entries)}")
    print(f"   Missing citations: {len(missing_citations)}")

    if missing_citations:
        print("\n   Missing citations:")
        for cite in missing_citations:
            print(f"     - {cite}")

    # Create new bib database
    new_bib_database = bibtexparser.bibdatabase.BibDatabase()
    new_bib_database.entries = cited_entries

    # Write to file
    writer = BibTexWriter()
    writer.indent = "  "
    writer.order_entries_by = "ID"
    writer.align_values = True

    with open(output_path, "w", encoding="utf-8") as bibfile:
        bibfile.write(writer.write(new_bib_database))

    print(f"\n5. Clean bibliography written to: {output_path}")
    print(f"   Contains {len(cited_entries)} entries (only cited ones)")

    # Also create a full merged bibliography
    full_output_path = Path("uadReview/references_merged_full.bib")
    full_bib_database = bibtexparser.bibdatabase.BibDatabase()
    full_bib_database.entries = list(all_entries.values())

    with open(full_output_path, "w", encoding="utf-8") as bibfile:
        bibfile.write(writer.write(full_bib_database))

    print(f"\n6. Full merged bibliography written to: {full_output_path}")
    print(
        f"   Contains {len(all_entries)} entries (all entries from both files)"
    )


if __name__ == "__main__":
    main()
