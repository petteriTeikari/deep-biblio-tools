#!/usr/bin/env python3
"""
Combine all markdown files without BibTeX entries.
"""

import re
from pathlib import Path


def remove_bibtex_section(content: str) -> str:
    """Remove the BibTeX section from markdown content."""
    # Find the BibTeX section and remove everything from it to the end
    bibtex_pattern = r"## BibTeX\s*\n.*"
    cleaned_content = re.sub(bibtex_pattern, "", content, flags=re.DOTALL)

    # Clean up any trailing whitespace
    return cleaned_content.rstrip()


def combine_markdown_files(input_dir: Path, output_file: Path):
    """Combine all markdown files in the directory without BibTeX entries."""
    # Get all markdown files sorted by name
    md_files = sorted(input_dir.glob("*.md"))

    print(f"Found {len(md_files)} markdown files to combine")

    with open(output_file, "w", encoding="utf-8") as outfile:
        # Write a header for the combined document
        outfile.write(
            "# Combined Literature Review: Construction and BIM Research\n\n"
        )
        outfile.write(f"*Combined from {len(md_files)} papers*\n\n")
        outfile.write("---\n\n")

        for i, md_file in enumerate(md_files):
            print(f"Processing {i + 1}/{len(md_files)}: {md_file.name}")

            # Read the content
            with open(md_file, encoding="utf-8") as infile:
                content = infile.read()

            # Remove BibTeX section
            cleaned_content = remove_bibtex_section(content)

            # Add to combined file
            outfile.write(cleaned_content)
            outfile.write("\n\n---\n\n")  # Add separator between papers

    print(f"\nCombined markdown saved to: {output_file}")


def main():
    # Set paths
    markdown_dir = Path(
        "/home/petteri/Dropbox/LABs/github-personal/github/deep-biblio-tools/data/markdown_parse"
    )
    output_file = markdown_dir / "combined_papers.md"

    # Combine files
    combine_markdown_files(markdown_dir, output_file)


if __name__ == "__main__":
    main()
