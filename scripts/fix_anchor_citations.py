#!/usr/bin/env python3
"""
Fix anchor-link citations that point to bibliography sections of other papers.

These citations reference #bib.bibXX anchors in arXiv HTML papers, which should
be replaced with the actual paper URLs.
"""

from pathlib import Path

# Map from anchor URLs to actual paper URLs
ANCHOR_REPLACEMENTS = {
    # From https://arxiv.org/html/2510.05566v1 bibliography
    "https://arxiv.org/html/2510.05566v1#bib.bib2": "https://arxiv.org/abs/2009.14193",  # Angelopoulos et al., 2020
    "https://arxiv.org/html/2510.05566v1#bib.bib24": "https://arxiv.org/abs/1905.03222",  # Romano et al., 2019
    "https://arxiv.org/html/2510.05566v1#bib.bib28": "https://arxiv.org/abs/1904.06019",  # Tibshirani et al., 2019
    "https://arxiv.org/html/2510.05566v1#bib.bib4": "https://arxiv.org/abs/2202.13415",  # Barber et al., 2023
    "https://arxiv.org/html/2510.05566v1#bib.bib14": "https://arxiv.org/abs/2305.18404",  # Kumar et al., 2023
    "https://arxiv.org/html/2510.05566v1#bib.bib35": "https://arxiv.org/abs/2401.12794",  # Ye et al., 2024
    "https://arxiv.org/html/2510.05566v1#bib.bib20": "https://doi.org/10.1016/j.patcog.2011.06.019",  # Moreno-Torres et al., 2012
    "https://arxiv.org/html/2510.05566v1#bib.bib23": "https://arxiv.org/abs/1902.10811",  # Recht et al., 2019
    "https://arxiv.org/html/2510.05566v1#bib.bib31": "https://doi.org/10.1007/b106715",  # Vovk et al., 2005 (Springer book)
}


def fix_anchor_citations(
    md_path: Path, output_path: Path | None = None
) -> None:
    """Fix anchor-link citations in markdown file."""
    if output_path is None:
        output_path = md_path

    with open(md_path) as f:
        content = f.read()

    original_content = content
    replacements_made = 0

    # Fix anchor URLs
    for old_url, new_url in ANCHOR_REPLACEMENTS.items():
        if old_url in content:
            count = content.count(old_url)
            content = content.replace(old_url, new_url)
            replacements_made += count
            print(f"Replaced {count} occurrence(s):")
            print(f"  {old_url}")
            print(f"  → {new_url}")

    if content != original_content:
        # Write fixed content
        with open(output_path, "w") as f:
            f.write(content)

        print(f"\nTotal replacements: {replacements_made}")
        print(f"Fixed file written to: {output_path}")
    else:
        print("No anchor citations found.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python3 fix_anchor_citations.py <markdown_file> [output_file]"
        )
        sys.exit(1)

    md_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    fix_anchor_citations(md_path, output_path)
