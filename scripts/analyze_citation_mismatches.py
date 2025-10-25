#!/usr/bin/env python3
"""
Analyze citation mismatches between LaTeX document and BibTeX file.
Particularly useful for identifying Better BibTeX key format changes.
"""

# import re  # Banned - using string methods instead
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import bibtexparser


class CitationMismatchAnalyzer:
    def __init__(self, tex_file: Path, bib_file: Path):
        self.tex_file = tex_file
        self.bib_file = bib_file
        self.tex_citations: set[str] = set()
        self.bib_keys: set[str] = set()
        self.bib_entries: dict[str, dict] = {}

    def extract_tex_citations(self) -> set[str]:
        """Extract all citation keys from LaTeX file."""
        print(f"Extracting citations from {self.tex_file}...")

        # Read the LaTeX file
        content = self.tex_file.read_text(encoding="utf-8")

        # Find all \cite commands and their variants
        # Handles: \cite{key}, \citep{key}, \citet{key}, \citealp{key}, etc.
        # Also handles multiple citations: \cite{key1,key2,key3}
        cite_commands = [
            "\\cite{",
            "\\citep{",
            "\\citet{",
            "\\citeauthor{",
            "\\citeyear{",
            "\\citealp{",
            "\\citealt{",
            # With optional star
            "\\cite*{",
            "\\citep*{",
            "\\citet*{",
            "\\citeauthor*{",
            "\\citeyear*{",
            "\\citealp*{",
            "\\citealt*{",
        ]

        all_citations = []
        for cmd in cite_commands:
            pos = 0
            while True:
                pos = content.find(cmd, pos)
                if pos == -1:
                    break

                # Find the closing brace
                start = pos + len(cmd)
                end = content.find("}", start)
                if end == -1:
                    pos += 1
                    continue

                # Extract citation keys
                cite_content = content[start:end]
                # Split by comma to handle multiple citations
                keys = cite_content.split(",")
                for key in keys:
                    key = key.strip()
                    if key:
                        all_citations.append(key)
                        self.tex_citations.add(key)

                pos = end + 1

        print(f"Found {len(self.tex_citations)} unique citations in LaTeX")
        return self.tex_citations

    def extract_bib_keys(self) -> set[str]:
        """Extract all entry keys from BibTeX file."""
        print(f"Extracting bibliography keys from {self.bib_file}...")

        # Parse BibTeX file
        with open(self.bib_file, encoding="utf-8") as f:
            bib_database = bibtexparser.load(f)

        for entry in bib_database.entries:
            key = entry.get("ID", "")
            if key:
                self.bib_keys.add(key)
                self.bib_entries[key] = entry

        print(f"Found {len(self.bib_keys)} entries in bibliography")
        return self.bib_keys

    def find_missing_citations(self) -> list[str]:
        """Find citations used in LaTeX but not in bibliography."""
        missing = sorted(list(self.tex_citations - self.bib_keys))
        return missing

    def find_unused_entries(self) -> list[str]:
        """Find bibliography entries not cited in LaTeX."""
        unused = sorted(list(self.bib_keys - self.tex_citations))
        return unused

    def suggest_key_mappings(
        self, missing_citations: list[str]
    ) -> dict[str, list[tuple[str, float, str]]]:
        """Suggest possible mappings from old keys to new Better BibTeX keys."""
        mappings = {}

        for missing_key in missing_citations:
            suggestions = []

            # Extract components from the missing key
            # Common patterns: author2023, authorYear, author_year
            missing_lower = missing_key.lower()

            # Try to extract year from missing key
            missing_year = None
            for i in range(len(missing_key) - 3):
                if missing_key[i : i + 4].isdigit() and missing_key[
                    i : i + 4
                ].startswith(("19", "20")):
                    missing_year = missing_key[i : i + 4]
                    break

            # Try to extract author from missing key
            author_part = missing_key
            if missing_year:
                year_pos = missing_key.find(missing_year)
                if year_pos > 0:
                    author_part = missing_key[:year_pos]
            author_part = author_part.strip("_-")

            for bib_key in self.bib_keys:
                score = 0
                reasons = []

                # Check if same year
                if missing_year and missing_year in bib_key:
                    score += 0.3
                    reasons.append(f"same year {missing_year}")

                # Check author similarity
                if author_part:
                    # Check if author part is in the bib key
                    if author_part.lower() in bib_key.lower():
                        score += 0.4
                        reasons.append(f"contains '{author_part}'")

                    # Get actual author from bib entry
                    entry = self.bib_entries.get(bib_key, {})
                    authors = entry.get("author", "").lower()
                    if author_part.lower() in authors:
                        score += 0.3
                        reasons.append("author match")

                # Use sequence matching for overall similarity
                seq_score = SequenceMatcher(
                    None, missing_lower, bib_key.lower()
                ).ratio()
                if seq_score > 0.5:
                    score = max(score, seq_score)
                    if seq_score > 0.7:
                        reasons.append(f"high similarity ({seq_score:.2f})")

                # Add title check for Better BibTeX keys
                entry = self.bib_entries.get(bib_key, {})
                title = entry.get("title", "").lower()
                # Extract first 3 words from title
                title_words = []
                word = ""
                for char in title + " ":
                    if char.isalnum():
                        word += char
                    elif word:
                        title_words.append(word)
                        word = ""
                        if len(title_words) >= 3:
                            break

                if any(
                    word in bib_key.lower()
                    for word in title_words
                    if len(word) > 3
                ):
                    score += 0.2
                    reasons.append("title words in key")

                if score > 0.4 and reasons:
                    reason_str = ", ".join(reasons)
                    suggestions.append((bib_key, score, reason_str))

            # Sort by score
            suggestions.sort(key=lambda x: x[1], reverse=True)
            if suggestions:
                mappings[missing_key] = suggestions[:5]  # Top 5 suggestions

        return mappings

    def generate_report(self):
        """Generate comprehensive mismatch report."""
        # Extract citations and keys
        self.extract_tex_citations()
        self.extract_bib_keys()

        # Find mismatches
        missing_citations = self.find_missing_citations()
        unused_entries = self.find_unused_entries()

        # Generate report
        report = []
        report.append("# Citation Mismatch Analysis Report")
        report.append(f"\nLaTeX file: {self.tex_file}")
        report.append(f"Bibliography file: {self.bib_file}")
        report.append(f"\nTotal citations in LaTeX: {len(self.tex_citations)}")
        report.append(f"Total entries in bibliography: {len(self.bib_keys)}")

        # Missing citations section
        report.append(
            f"\n## Missing Citations ({len(missing_citations)} found)"
        )
        report.append(
            "These citation keys are used in the LaTeX document but not found in the bibliography:\n"
        )

        if missing_citations:
            # Get mapping suggestions
            mappings = self.suggest_key_mappings(missing_citations)

            for missing_key in missing_citations:
                report.append(f"### `{missing_key}`")

                if missing_key in mappings and mappings[missing_key]:
                    report.append("Possible matches:")
                    for suggested_key, score, reason in mappings[missing_key]:
                        entry = self.bib_entries[suggested_key]
                        author = entry.get("author", "Unknown")
                        # Truncate long author lists
                        if len(author) > 50:
                            author = author[:47] + "..."
                        title = entry.get("title", "Unknown")
                        if len(title) > 60:
                            title = title[:57] + "..."
                        year = entry.get("year", "")

                        report.append(
                            f"  - `{suggested_key}` (score: {score:.2f}, {reason})"
                        )
                        report.append(f"    {author} ({year})")
                        report.append(f'    "{title}"')
                else:
                    report.append("  No good matches found")

                report.append("")
        else:
            report.append(
                "All citations in the LaTeX document exist in the bibliography!"
            )

        # Quick fix commands section
        if missing_citations and any(
            mappings.get(k) for k in missing_citations
        ):
            report.append("\n## Quick Fix Commands")
            report.append(
                "Here are sed commands to update the most likely matches in your LaTeX file:\n"
            )
            report.append("```bash")

            for missing_key in missing_citations:
                if missing_key in mappings and mappings[missing_key]:
                    best_match = mappings[missing_key][0][0]
                    report.append(f"# Replace {missing_key} with {best_match}")
                    report.append(
                        f"sed -i 's/\\\\cite{{[^}}]*{missing_key}[^}}]*}}/\\\\cite{{{best_match}}}/g' {self.tex_file}"
                    )
                    report.append("")

            report.append("```")

        # Unused entries section
        report.append(
            f"\n## Unused Bibliography Entries ({len(unused_entries)} found)"
        )
        if unused_entries:
            report.append(
                "These entries exist in the bibliography but are not cited in the LaTeX document:\n"
            )

            # Group by year
            by_year = defaultdict(list)
            for key in unused_entries:
                entry = self.bib_entries[key]
                year = entry.get("year", "Unknown")
                by_year[year].append((key, entry))

            for year in sorted(by_year.keys(), reverse=True):
                report.append(f"### {year}")
                for key, entry in by_year[year]:
                    author = entry.get("author", "Unknown")
                    if len(author) > 50:
                        author = author[:47] + "..."
                    title = entry.get("title", "Unknown")
                    if len(title) > 70:
                        title = title[:67] + "..."
                    report.append(f"- `{key}`: {author}")
                    report.append(f'  "{title}"')
                report.append("")
        else:
            report.append("All bibliography entries are used!")

        # Summary
        report.append("\n## Summary")
        if missing_citations:
            report.append(
                f"- **Action needed**: {len(missing_citations)} citations need to be updated in the LaTeX file"
            )
            report.append(
                "- Most likely cause: Better BibTeX key format changes"
            )
            report.append(
                "- Use the suggested mappings above to update your citations"
            )
        else:
            report.append("- All citations are properly matched!")

        if unused_entries:
            report.append(
                f"- **Optional**: {len(unused_entries)} bibliography entries could be removed if not needed"
            )

        return "\n".join(report)


def main():
    # Default paths
    tex_file = Path("uadReview/main.tex")
    bib_file = Path("uadReview/references.bib")

    # Allow command line override
    if len(sys.argv) > 1:
        tex_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        bib_file = Path(sys.argv[2])

    # Check files exist
    if not tex_file.exists():
        print(f"Error: LaTeX file not found: {tex_file}")
        sys.exit(1)
    if not bib_file.exists():
        print(f"Error: Bibliography file not found: {bib_file}")
        sys.exit(1)

    # Analyze
    analyzer = CitationMismatchAnalyzer(tex_file, bib_file)
    report = analyzer.generate_report()

    # Save report
    report_file = tex_file.parent / "citation_mismatch_report.md"
    report_file.write_text(report, encoding="utf-8")

    print(f"\nReport saved to: {report_file}")
    print("\nQuick summary:")

    missing = analyzer.find_missing_citations()
    if missing:
        print(f"Found {len(missing)} missing citations that need to be fixed")
    else:
        print("All citations match!")

    unused = analyzer.find_unused_entries()
    if unused:
        print(f"Found {len(unused)} unused bibliography entries")


if __name__ == "__main__":
    main()
