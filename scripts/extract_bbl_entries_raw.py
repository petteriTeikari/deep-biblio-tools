"""Extract raw .bbl entries showing exactly how they appear in compiled bibliography.

Output: CSV with columns:
- citation_key: The BibTeX key used
- formatted_entry: The FULL \\bibitem text as it appears in .bbl
"""

import csv
import sys
from pathlib import Path


def extract_bbl_entries(bbl_path: Path) -> list[dict]:
    """Extract each \\bibitem entry with its full formatted text."""

    with open(bbl_path, encoding="utf-8") as f:
        content = f.read()

    # Find bibliography section
    start = content.find("\\begin{thebibliography}")
    end = content.find("\\end{thebibliography}")

    if start == -1 or end == -1:
        print("ERROR: Could not find bibliography section")
        return []

    bib_section = content[start:end]

    # Split by \bibitem
    entries = []
    current_entry = ""
    current_key = None

    for line in bib_section.split("\n"):
        if line.strip().startswith("\\bibitem"):
            # Save previous entry
            if current_key and current_entry:
                entries.append(
                    {
                        "citation_key": current_key,
                        "formatted_entry": current_entry.strip(),
                    }
                )

            # Start new entry
            current_entry = line + "\n"

            # Extract citation key from \\bibitem[...]{KEY}
            # Find the {KEY} part
            brace_start = line.rfind("{")
            brace_end = line.rfind("}")
            if brace_start != -1 and brace_end != -1:
                current_key = line[brace_start + 1 : brace_end]
            else:
                current_key = "PARSE_ERROR"

        elif current_key:
            current_entry += line + "\n"

    # Don't forget last entry
    if current_key and current_entry:
        entries.append(
            {
                "citation_key": current_key,
                "formatted_entry": current_entry.strip(),
            }
        )

    return entries


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python extract_bbl_entries_raw.py <bbl_file> [output_csv]"
        )
        sys.exit(1)

    bbl_path = Path(sys.argv[1])
    output_path = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else bbl_path.parent / "bbl_entries_raw.csv"
    )

    print(f"📖 Extracting entries from {bbl_path}...")
    entries = extract_bbl_entries(bbl_path)

    print(f"💾 Writing {len(entries)} entries to {output_path}...")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["citation_key", "formatted_entry"]
        )
        writer.writeheader()
        writer.writerows(entries)

    print(f"✅ Done! Wrote {len(entries)} entries.")

    # Show first few examples
    print("\n📋 First 3 entries:")
    for i, entry in enumerate(entries[:3]):
        print(f"\n[{i + 1}] {entry['citation_key']}:")
        # Show first 200 chars of formatted entry
        preview = (
            entry["formatted_entry"][:200] + "..."
            if len(entry["formatted_entry"]) > 200
            else entry["formatted_entry"]
        )
        print(f"    {preview}")


if __name__ == "__main__":
    main()
