#!/usr/bin/env python3
"""
Fix invalid arXiv citations in markdown file.

Replaces:
1. 2025.mcp.taxonomy → 2509.24272 (Zhao et al.)
2. 2025.mcp.privilege → 2507.06250 (Li et al.)
3. 2025.mpma → 2505.11154 (Wang et al.)
"""

import sys
from pathlib import Path

REPLACEMENTS = {
    "https://arxiv.org/abs/2025.mcp.taxonomy": "https://arxiv.org/abs/2509.24272",
    "https://arxiv.org/abs/2025.mcp.privilege": "https://arxiv.org/abs/2507.06250",
    "https://arxiv.org/abs/2025.mpma": "https://arxiv.org/abs/2505.11154",
}

AUTHOR_FIXES = {
    # Update author names if needed
    "[Unknown, 2025](https://arxiv.org/abs/2025.mpma)": "[Wang et al., 2025](https://arxiv.org/abs/2505.11154)",
}


def fix_citations(md_path: Path, output_path: Path | None = None) -> None:
    """Fix invalid citations in markdown file."""
    if output_path is None:
        output_path = md_path

    with open(md_path) as f:
        content = f.read()

    original_content = content
    replacements_made = 0

    # Fix URLs
    for old_url, new_url in REPLACEMENTS.items():
        if old_url in content:
            count = content.count(old_url)
            content = content.replace(old_url, new_url)
            replacements_made += count
            print(f"Replaced {count} occurrence(s): {old_url} → {new_url}")

    # Fix author names
    for old_citation, new_citation in AUTHOR_FIXES.items():
        if old_citation in content:
            count = content.count(old_citation)
            content = content.replace(old_citation, new_citation)
            print(
                f"Fixed {count} author name(s): {old_citation} → {new_citation}"
            )

    if content != original_content:
        # Write fixed content
        with open(output_path, "w") as f:
            f.write(content)

        print(f"\nTotal replacements: {replacements_made}")
        print(f"Fixed file written to: {output_path}")
    else:
        print("No invalid citations found.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python3 fix_invalid_arxiv_citations.py <markdown_file> [output_file]"
        )
        sys.exit(1)

    md_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    fix_citations(md_path, output_path)
