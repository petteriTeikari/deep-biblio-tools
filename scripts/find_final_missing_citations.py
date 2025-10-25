#!/usr/bin/env python3
"""Find the final missing citations that are still undefined."""

# import re  # Banned - using string methods instead
from pathlib import Path


def extract_undefined_citations(log_content):
    """Extract undefined citations from LaTeX log."""
    undefined = set()
    # Look for pattern: Citation `something' on page N undefined
    search_text = "Citation `"
    i = 0
    while i < len(log_content):
        idx = log_content.find(search_text, i)
        if idx == -1:
            break

        # Find the closing quote
        start = idx + len(search_text)
        end = log_content.find("'", start)
        if end != -1:
            # Check if it follows the pattern "on page N undefined"
            rest = log_content[end : end + 50]  # Look ahead a bit
            if "' on page" in rest and "undefined" in rest:
                citation = log_content[start:end]
                undefined.add(citation)

        i = idx + 1

    return undefined


def check_in_bib_files(citation, bib_files):
    """Check if citation exists in any bib file."""
    found_in = []
    for bib_path in bib_files:
        content = bib_path.read_text(encoding="utf-8")
        if "@" in content and f"{{{citation}," in content:
            found_in.append(bib_path.name)
    return found_in


def main():
    # Read the compilation output
    undefined_citations = [
        "hover2025",
        "spahn2025",
        "polycam2025",
        "magicplan2025",
        "locometric2025",
        "metaroom2025",
        "wescan2025",
        "recond2025",
        "acsr2025",
        "cubicasa2025",
        "iguide2025",
        "plnar2025",
        "hosta2025",
        "canvas2025",
        "imagespace2025",
        "held2024",
        "liu2025",
        "zhu2025",
        "liu2024",
        "held2025",
        "li2025",
        "yang2024",
        "tang2024",
    ]

    # Remove duplicates
    undefined_citations = sorted(set(undefined_citations))

    print("=== Final Missing Citations Analysis ===\n")
    print(f"Total undefined citations: {len(undefined_citations)}")

    # Check in all bib files
    bib_files = [
        Path("uadReview/references.bib"),
        Path("uadReview/uad_1st.bib"),
        Path("uadReview/references_clean.bib"),
        Path("uadReview/references_merged_full.bib"),
    ]

    print("\nChecking each citation:")
    not_found_anywhere = []

    for citation in undefined_citations:
        found_in = check_in_bib_files(citation, bib_files)
        if found_in:
            print(f"  {citation}: found in {', '.join(found_in)}")
        else:
            print(f"  {citation}: NOT FOUND in any bib file")
            not_found_anywhere.append(citation)

    if not_found_anywhere:
        print(
            f"\n{len(not_found_anywhere)} citations not found in any bib file:"
        )
        for cite in not_found_anywhere:
            print(f"  - {cite}")

        # Try to guess what these might be
        print("\nPossible issues:")
        for cite in not_found_anywhere:
            if cite.endswith("2025") or cite.endswith("2024"):
                print(f"  {cite}: Likely a website/software citation")
            elif "held" in cite or "liu" in cite:
                print(
                    f"  {cite}: Might be an author-year key that needs different formatting"
                )


if __name__ == "__main__":
    main()
