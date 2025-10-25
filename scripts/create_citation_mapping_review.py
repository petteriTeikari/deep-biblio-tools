#!/usr/bin/env python3
"""
Create a detailed review document for citation mappings with context.
"""

# import re  # Banned - using string methods instead
import sys
from collections import defaultdict
from pathlib import Path

import bibtexparser


class CitationMappingReviewer:
    def __init__(self, tex_file: Path, bib_file: Path, report_file: Path):
        self.tex_file = tex_file
        self.bib_file = bib_file
        self.report_file = report_file
        self.bib_entries = {}
        self.citation_contexts = defaultdict(list)

    def load_bibliography(self):
        """Load bibliography entries."""
        with open(self.bib_file, encoding="utf-8") as f:
            bib_database = bibtexparser.load(f)

        for entry in bib_database.entries:
            key = entry.get("ID", "")
            if key:
                self.bib_entries[key] = entry

    def extract_citation_contexts(self):
        """Extract context around each citation in the LaTeX file."""
        content = self.tex_file.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Find all citations with their line numbers
        for line_num, line in enumerate(lines):
            # Find all \cite commands using string methods
            pos = 0
            while pos < len(line):
                cite_pos = line.find("\\cite", pos)
                if cite_pos == -1:
                    break

                # Check for optional letters after \cite
                j = cite_pos + 5  # len("\\cite")
                while j < len(line) and line[j].islower():
                    j += 1

                # Check for optional *
                if j < len(line) and line[j] == "*":
                    j += 1

                # Look for opening brace
                if j < len(line) and line[j] == "{":
                    # Find matching closing brace
                    brace_count = 1
                    k = j + 1
                    while k < len(line) and brace_count > 0:
                        if line[k] == "{":
                            brace_count += 1
                        elif line[k] == "}":
                            brace_count -= 1
                        k += 1

                    if brace_count == 0:
                        # Extract citation keys
                        citation_content = line[j + 1 : k - 1]
                        keys = citation_content.split(",")
                        for key in keys:
                            key = key.strip()
                            if key:
                                # Get context: 2 lines before and after
                                start = max(0, line_num - 2)
                                end = min(len(lines), line_num + 3)
                                context = "\n".join(
                                    f"{ii + 1:4d}: {lines[ii]}"
                                    for ii in range(start, end)
                                )
                                # Highlight the citation line
                                context = context.replace(
                                    f"{line_num + 1:4d}:",
                                    f"→{line_num + 1:3d}:",
                                )
                                self.citation_contexts[key].append(
                                    {"line": line_num + 1, "context": context}
                                )

                pos = cite_pos + 1

    def parse_report(self):
        """Parse the existing mismatch report to get mappings."""
        report_content = self.report_file.read_text(encoding="utf-8")

        mappings = {}
        current_missing_key = None

        for line in report_content.split("\n"):
            # Find missing citation headers
            if line.startswith("### `") and line.endswith("`"):
                current_missing_key = line[5:-1]
                mappings[current_missing_key] = []

            # Find suggested mappings
            elif (
                current_missing_key
                and line.strip().startswith("- `")
                and " (score:" in line
            ):
                # Parse mapping line using string methods
                line = line.strip()
                if line.startswith("- `") and "` (score:" in line:
                    # Extract key
                    key_start = 3  # len("- `")
                    key_end = line.find("`", key_start)
                    if key_end != -1:
                        suggested_key = line[key_start:key_end]

                        # Extract score
                        score_start = line.find("(score: ", key_end)
                        if score_start != -1:
                            score_start += 8  # len("(score: ")
                            score_end = line.find(",", score_start)
                            if score_end != -1:
                                try:
                                    score = float(line[score_start:score_end])

                                    # Extract reason
                                    reason_start = score_end + 2  # skip ", "
                                    reason_end = line.find(")", reason_start)
                                    if reason_end != -1:
                                        reason = line[reason_start:reason_end]
                                        mappings[current_missing_key].append(
                                            {
                                                "key": suggested_key,
                                                "score": score,
                                                "reason": reason,
                                            }
                                        )
                                except ValueError:
                                    pass  # Invalid score format

        return mappings

    def generate_review_document(self):
        """Generate a detailed review document."""
        self.load_bibliography()
        self.extract_citation_contexts()
        mappings = self.parse_report()

        review = []
        review.append("# Citation Mapping Review Document")
        review.append(
            "\nThis document provides detailed context for reviewing citation mappings."
        )
        review.append("For each missing citation, you'll see:")
        review.append("- Where it appears in the LaTeX document")
        review.append("- The context around the citation")
        review.append("- Suggested bibliography entries with full details")

        # Group by confidence level
        high_confidence = []
        medium_confidence = []
        low_confidence = []
        no_match = []

        for missing_key, suggestions in mappings.items():
            if not suggestions:
                no_match.append(missing_key)
            elif suggestions[0]["score"] >= 0.9:
                high_confidence.append((missing_key, suggestions))
            elif suggestions[0]["score"] >= 0.7:
                medium_confidence.append((missing_key, suggestions))
            else:
                low_confidence.append((missing_key, suggestions))

        # High confidence mappings
        review.append("\n## HIGH CONFIDENCE MAPPINGS (≥90% match)")
        review.append("These mappings are very likely correct:\n")

        for missing_key, suggestions in high_confidence:
            review.append(f"### {missing_key} → {suggestions[0]['key']}")
            review.append(
                f"**Confidence:** {suggestions[0]['score']:.0%} ({suggestions[0]['reason']})"
            )

            # Show bibliography entry
            if suggestions[0]["key"] in self.bib_entries:
                entry = self.bib_entries[suggestions[0]["key"]]
                review.append("\n**Bibliography entry:**")
                review.append(f"- Type: {entry.get('ENTRYTYPE', 'unknown')}")
                review.append(f"- Authors: {entry.get('author', 'Unknown')}")
                review.append(f"- Title: {entry.get('title', 'Unknown')}")
                review.append(f"- Year: {entry.get('year', 'Unknown')}")
                if "doi" in entry:
                    review.append(f"- DOI: {entry['doi']}")
                if "url" in entry:
                    review.append(f"- URL: {entry['url']}")

            review.append("")

        # Quick fix for high confidence
        if high_confidence:
            review.append("\n### Quick fix for high-confidence mappings:")
            review.append("```bash")
            for missing_key, suggestions in high_confidence:
                review.append(
                    f"sed -i 's/{missing_key}/{suggestions[0]['key']}/g' {self.tex_file}"
                )
            review.append("```")

        # Medium confidence mappings
        review.append("\n## MEDIUM CONFIDENCE MAPPINGS (70-89% match)")
        review.append("These mappings should be manually verified:\n")

        for missing_key, suggestions in medium_confidence:
            review.append(f"### {missing_key}")

            # Show context
            if missing_key in self.citation_contexts:
                review.append("\n**Usage context in LaTeX:**")
                for ctx in self.citation_contexts[missing_key][
                    :2
                ]:  # Show first 2 occurrences
                    review.append("```latex")
                    review.append(ctx["context"])
                    review.append("```")

            review.append("\n**Suggested mappings:**")
            for i, suggestion in enumerate(
                suggestions[:3]
            ):  # Top 3 suggestions
                review.append(
                    f"\n{i + 1}. `{suggestion['key']}` ({suggestion['score']:.0%}, {suggestion['reason']})"
                )

                if suggestion["key"] in self.bib_entries:
                    entry = self.bib_entries[suggestion["key"]]
                    review.append(
                        f"   - {entry.get('author', 'Unknown')} ({entry.get('year', '')})"
                    )
                    title = entry.get("title", "Unknown")
                    if len(title) > 80:
                        title = title[:77] + "..."
                    review.append(f'   - "{title}"')

            review.append("")

        # Low confidence mappings
        review.append("\n## LOW CONFIDENCE MAPPINGS (<70% match)")
        review.append("These need careful manual review:\n")

        for missing_key, suggestions in low_confidence:
            review.append(f"### {missing_key}")

            # Show context
            if missing_key in self.citation_contexts:
                review.append("\n**Usage context:**")
                ctx = self.citation_contexts[missing_key][0]
                review.append("```latex")
                review.append(ctx["context"])
                review.append("```")

            review.append(
                f"\n**Best guess:** `{suggestions[0]['key']}` ({suggestions[0]['score']:.0%})"
            )
            review.append(
                "This mapping is uncertain and likely needs a different entry or new bibliography entry."
            )
            review.append("")

        # No matches
        if no_match:
            review.append("\n## NO MATCHES FOUND")
            review.append(
                "These citations have no suggested matches and likely need new bibliography entries:\n"
            )

            for missing_key in no_match:
                review.append(f"### {missing_key}")
                if missing_key in self.citation_contexts:
                    ctx = self.citation_contexts[missing_key][0]
                    review.append("**Context:**")
                    review.append("```latex")
                    review.append(ctx["context"])
                    review.append("```")
                review.append("")

        # Summary and recommendations
        review.append("\n## SUMMARY & RECOMMENDATIONS")
        review.append(
            f"\n1. **High confidence ({len(high_confidence)} citations):** Can be automatically fixed"
        )
        review.append(
            f"2. **Medium confidence ({len(medium_confidence)} citations):** Review the context and verify mappings"
        )
        review.append(
            f"3. **Low confidence ({len(low_confidence)} citations):** Likely need different entries"
        )
        review.append(
            f"4. **No matches ({len(no_match)} citations):** Need new bibliography entries"
        )

        review.append("\n## SUSPICIOUS MAPPINGS TO REVIEW")
        review.append("\nThe following mappings seem questionable:")

        # Check for suspicious patterns
        jaro_mappings = [
            (k, s)
            for k, s in mappings.items()
            if s and s[0]["key"] == "jaro2025"
        ]
        if jaro_mappings:
            review.append(
                f"\n- **{len(jaro_mappings)} citations mapped to 'jaro2025'** (a blog post)"
            )
            review.append("  These likely need different entries:")
            for key, _ in jaro_mappings:
                review.append(f"  - {key}")

        return "\n".join(review)


def main():
    # File paths
    tex_file = Path("uadReview/main.tex")
    bib_file = Path("uadReview/references.bib")
    report_file = Path("uadReview/citation_mismatch_report.md")

    # Check files exist
    for f in [tex_file, bib_file, report_file]:
        if not f.exists():
            print(f"Error: File not found: {f}")
            sys.exit(1)

    # Generate review
    reviewer = CitationMappingReviewer(tex_file, bib_file, report_file)
    review_content = reviewer.generate_review_document()

    # Save review
    review_file = tex_file.parent / "citation_mapping_review.md"
    review_file.write_text(review_content, encoding="utf-8")

    print(f"Review document saved to: {review_file}")
    print("\nOpen this file to review the mappings in detail.")


if __name__ == "__main__":
    main()
