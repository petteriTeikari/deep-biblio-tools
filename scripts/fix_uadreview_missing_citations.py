#!/usr/bin/env python3
"""Find and fix missing citations in uadReview manuscript."""

# import re  # Banned - using string methods instead
from pathlib import Path


def extract_citations_from_tex(tex_path):
    """Extract all unique citations from the tex file."""
    content = tex_path.read_text(encoding="utf-8")
    citations = set()

    # Find all \cite{...} and \citep{...} commands using string methods
    # Process content to find citations
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


def extract_entries_from_bib(bib_path):
    """Extract all entry keys from a bib file."""
    content = bib_path.read_text(encoding="utf-8")
    entries = set()

    # Find all @type{key, patterns using string methods
    i = 0
    while i < len(content):
        # Look for @ symbol
        at_pos = content.find("@", i)
        if at_pos == -1:
            break

        # Skip whitespace after @
        j = at_pos + 1
        while j < len(content) and content[j].isspace():
            j += 1

        # Extract entry type (letters)
        type_start = j
        while j < len(content) and content[j].isalpha():
            j += 1

        if j > type_start:  # Found entry type
            # Skip whitespace
            while j < len(content) and content[j].isspace():
                j += 1

            # Check for opening brace
            if j < len(content) and content[j] == "{":
                # Extract key (up to comma or whitespace)
                key_start = j + 1
                key_end = key_start
                while (
                    key_end < len(content) and content[key_end] not in r",\s}"
                ):
                    key_end += 1

                if key_end > key_start:
                    key = content[key_start:key_end].strip()
                    if key:
                        entries.add(key)

        i = at_pos + 1

    return entries


def get_entry_from_bib(bib_content, key):
    """Extract a specific entry from bib content."""
    # Find the entry using string methods
    # Look for @type{key,
    search_pattern = f"{{{key}"

    # Try to find the key in the content
    key_pos = 0
    while True:
        key_pos = bib_content.find(search_pattern, key_pos)
        if key_pos == -1:
            return None

        # Check if this is inside a bib entry (go backward to find @)
        # Find the @ before this position
        at_pos = key_pos
        while at_pos > 0 and bib_content[at_pos] != "@":
            at_pos -= 1

        if at_pos >= 0 and bib_content[at_pos] == "@":
            # Verify this is the start of an entry
            # Check if there's an entry type after @
            j = at_pos + 1
            while (
                j < key_pos
                and j < len(bib_content)
                and bib_content[j].isalpha()
            ):
                j += 1

            # Skip whitespace
            while (
                j < key_pos
                and j < len(bib_content)
                and bib_content[j].isspace()
            ):
                j += 1

            # Check if we have a { before our key
            if (
                j < key_pos
                and bib_content[j] == "{"
                and j + 1 + len(key) <= key_pos
            ):
                # This looks like our entry, now find the closing brace
                brace_count = 0
                entry_start = at_pos
                i = at_pos

                while i < len(bib_content):
                    if bib_content[i] == "{":
                        brace_count += 1
                    elif bib_content[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            # Found the closing brace
                            return bib_content[entry_start : i + 1]
                    i += 1

        key_pos += 1

    return None


def main():
    # Paths
    tex_path = Path("uadReview/main.tex")
    ref_bib_path = Path("uadReview/references.bib")
    uad_bib_path = Path("uadReview/uad_1st.bib")

    print("=== Fixing Missing Citations in uadReview ===\n")

    # Extract citations and entries
    citations = extract_citations_from_tex(tex_path)
    ref_entries = extract_entries_from_bib(ref_bib_path)
    uad_entries = extract_entries_from_bib(uad_bib_path)

    # Find missing citations
    missing_from_ref = citations - ref_entries

    print(f"Total citations in main.tex: {len(citations)}")
    print(f"Entries in references.bib: {len(ref_entries)}")
    print(f"Entries in uad_1st.bib: {len(uad_entries)}")
    print(f"Missing citations: {len(missing_from_ref)}")

    if not missing_from_ref:
        print("\nAll citations are found in references.bib!")
        return

    # Check which missing citations are in uad_1st.bib
    found_in_uad = missing_from_ref & uad_entries
    not_found_anywhere = missing_from_ref - uad_entries

    print(f"\nFound in uad_1st.bib: {len(found_in_uad)}")
    print(f"Not found anywhere: {len(not_found_anywhere)}")

    if found_in_uad:
        print("\n--- Citations to copy from uad_1st.bib to references.bib ---")

        # Read bib files
        ref_content = ref_bib_path.read_text(encoding="utf-8")
        uad_content = uad_bib_path.read_text(encoding="utf-8")

        # Collect entries to add
        entries_to_add = []
        for key in sorted(found_in_uad):
            entry = get_entry_from_bib(uad_content, key)
            if entry:
                entries_to_add.append(entry)
                print(f"  - {key}")
            else:
                print(f"  - {key} (ERROR: couldn't extract entry)")

        if entries_to_add:
            # Add entries to references.bib
            backup_path = ref_bib_path.with_suffix(".bib.backup")
            ref_bib_path.rename(backup_path)
            print(f"\nBacked up references.bib to {backup_path}")

            # Write updated content
            new_content = (
                ref_content.rstrip()
                + "\n\n% Entries added from uad_1st.bib\n\n"
                + "\n\n".join(entries_to_add)
                + "\n"
            )
            ref_bib_path.write_text(new_content, encoding="utf-8")
            print(f"Added {len(entries_to_add)} entries to references.bib")

    if not_found_anywhere:
        print("\n--- Citations not found in any .bib file ---")
        print(
            "These need to be added manually or might be typos in the tex file:"
        )
        for key in sorted(not_found_anywhere):
            print(f"  - {key}")

        # Write missing citations to a file for manual review
        missing_file = Path("uadReview/missing_citations.txt")
        missing_file.write_text(
            "\n".join(sorted(not_found_anywhere)), encoding="utf-8"
        )
        print(f"\nWrote missing citations to {missing_file}")


if __name__ == "__main__":
    main()
