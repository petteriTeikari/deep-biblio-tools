#!/usr/bin/env python3
"""
Script to find and fix incomplete author names in bibliography entries.
Attempts to fetch complete author information from DOI/URL metadata.
"""

import argparse
import logging

# import re  # Banned - using string methods instead
import sys
from pathlib import Path

import bibtexparser
import requests
from bibtexparser.bwriter import BibTexWriter

# Add validation functionality
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.validate_llm_citations import CitationValidator

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


class AuthorFixer:
    """Fix incomplete author names in bibliography entries."""

    def __init__(self):
        self.validator = CitationValidator()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "DeepBiblioTools/1.0 (mailto:petteri.teikari@gmail.com)"
            }
        )

        # Known author completions (manually verified)
        self.known_completions = {
            "Gibson": "Gibson, James J.",
            "Kotter": "Kotter, John P.",
            "Lusht": "Lusht, Kenneth M.",
            "Narayanan": "Narayanan, Arvind",
            "Pace": "Pace, R. Kelley",
            "Rogers": "Rogers, Everett M.",
            "Rothstein": "Rothstein, Richard",
            "Stiglitz": "Stiglitz, Joseph E.",
            "Weiss": "Weiss, Gerhard",
            "Williamson": "Williamson, Oliver E.",
            "Brynjolfsson and McAfee": "Brynjolfsson, Erik and McAfee, Andrew",
            "Nonaka and Takeuchi": "Nonaka, Ikujiro and Takeuchi, Hirotaka",
            "Susskind and Susskind": "Susskind, Richard and Susskind, Daniel",
            "Wilson and Daugherty": "Wilson, H. James and Daugherty, Paul R.",
            "Alexandrov, Alexei and Neal": "Alexandrov, Alexei and Neal, Michael",
            "Neufville, de and Geltner": "de Neufville, Richard and Geltner, David",
            "Kiureghian, Der and Ditlevsen": "Der Kiureghian, Armen and Ditlevsen, Ove",
            "Mooya": "Mooya, Manya M.",
            "Kucharska-Stasiak": "Kucharska-Stasiak, Ewa",
            "Quadri": "Quadri, Salman",
        }

        # Define patterns for incomplete authors (will check manually)
        self.incomplete_checks = [
            # Single word (no comma, no first name)
            lambda s: self._is_single_word(s),
            # "LastName and LastName" (no first names)
            lambda s: self._is_lastname_and_lastname(s),
            # "LastName and others"
            lambda s: s.endswith(" and others") and " " in s[:-11],
            # Organization names that might need expansion
            lambda s: s.isupper() and s.isalpha(),  # All caps abbreviations
        ]

    def _is_single_word(self, s: str) -> bool:
        """Check if string is a single word with only letters and hyphens."""
        if not s:
            return False
        for char in s:
            if not (char.isalpha() or char == "-"):
                return False
        return True

    def _is_lastname_and_lastname(self, s: str) -> bool:
        """Check if string matches 'LastName and LastName' pattern."""
        parts = s.split(" and ")
        if len(parts) != 2:
            return False
        return self._is_single_word(parts[0]) and self._is_single_word(parts[1])

    def is_incomplete(self, author_string: str) -> bool:
        """Check if author string appears incomplete."""
        # Check against patterns
        for check_func in self.incomplete_checks:
            if check_func(author_string):
                return True

        # Check if any author part lacks comma (except organizations)
        authors = author_string.split(" and ")
        for author in authors:
            author = author.strip()
            # Skip if it looks like an organization (all caps or contains non-letter chars)
            if author.isupper():
                continue
            # Check for digits or special chars
            has_special = False
            for char in author:
                if char in "0123456789&.":
                    has_special = True
                    break
            if has_special:
                continue
            # If no comma and not a known organization, likely incomplete
            if "," not in author and len(author.split()) <= 2:
                return True

        return False

    def fix_author(self, entry: dict) -> tuple[dict, str]:
        """Attempt to fix incomplete author information."""
        original_author = entry.get("author", "")

        # Check known completions first
        if original_author in self.known_completions:
            entry["author"] = self.known_completions[original_author]
            return (
                entry,
                f"Fixed from known completion: {original_author} -> {entry['author']}",
            )

        # Try to fetch from DOI if available
        if "doi" in entry:
            try:
                metadata = self.validator.validate_via_doi(entry["doi"])
                if metadata and metadata.get("authors"):
                    # Format authors properly
                    authors = []
                    for auth in metadata["authors"]:
                        if "given" in auth and "family" in auth:
                            authors.append(f"{auth['family']}, {auth['given']}")
                        elif "name" in auth:
                            authors.append(auth["name"])

                    if authors:
                        entry["author"] = " and ".join(authors)
                        return (
                            entry,
                            f"Fixed via DOI: {original_author} -> {entry['author']}",
                        )
            except Exception as e:
                logger.debug(
                    f"DOI fetch failed for {entry.get('ID', 'unknown')}: {e}"
                )

        # Try to fetch from URL if available
        if "url" in entry and "arxiv.org" in entry["url"]:
            try:
                metadata = self.validator.validate_via_arxiv(entry["url"])
                if metadata and metadata.get("authors"):
                    entry["author"] = " and ".join(metadata["authors"])
                    return (
                        entry,
                        f"Fixed via arXiv: {original_author} -> {entry['author']}",
                    )
            except Exception as e:
                logger.debug(
                    f"arXiv fetch failed for {entry.get('ID', 'unknown')}: {e}"
                )

        # Add note if we couldn't fix it
        if "note" not in entry or "Incomplete author" not in entry.get(
            "note", ""
        ):
            note = entry.get("note", "")
            if note:
                entry["note"] = (
                    f"{note}; NEEDS MANUAL FIX - incomplete author: {original_author}"
                )
            else:
                entry["note"] = (
                    f"NEEDS MANUAL FIX - incomplete author: {original_author}"
                )

        return entry, f"Could not fix automatically: {original_author}"

    def process_bibliography(self, bib_file: Path) -> tuple[list, list]:
        """Process bibliography and fix incomplete authors."""
        with open(bib_file, encoding="utf-8") as f:
            bib_db = bibtexparser.load(f)

        fixed_entries = []
        unfixed_entries = []

        for entry in bib_db.entries:
            author = entry.get("author", "")
            if not author:
                continue

            if self.is_incomplete(author):
                fixed_entry, message = self.fix_author(entry)

                if "Fixed" in message:
                    fixed_entries.append(
                        {
                            "key": entry.get("ID", "unknown"),
                            "original": author,
                            "fixed": fixed_entry.get("author", author),
                            "message": message,
                        }
                    )
                else:
                    unfixed_entries.append(
                        {
                            "key": entry.get("ID", "unknown"),
                            "author": author,
                            "type": entry.get("ENTRYTYPE", "unknown"),
                            "title": entry.get("title", "unknown")[:60] + "...",
                            "doi": entry.get("doi", ""),
                            "url": entry.get("url", ""),
                        }
                    )

        # Write updated bibliography
        writer = BibTexWriter()
        writer.indent = "  "
        writer.order_entries_by = None
        writer.align_values = True

        with open(bib_file, "w", encoding="utf-8") as f:
            f.write(writer.write(bib_db))

        return fixed_entries, unfixed_entries


def main():
    parser = argparse.ArgumentParser(
        description="Find and fix incomplete author names in bibliography"
    )
    parser.add_argument(
        "bib_file", type=Path, help="Bibliography file to process"
    )
    parser.add_argument(
        "--report", type=Path, help="Save detailed report to file"
    )

    args = parser.parse_args()

    if not args.bib_file.exists():
        logger.error(f"File not found: {args.bib_file}")
        return 1

    logger.info(f"Processing {args.bib_file}...")

    fixer = AuthorFixer()
    fixed, unfixed = fixer.process_bibliography(args.bib_file)

    # Report results
    logger.info(f"\n{'=' * 60}")
    logger.info("Author Name Fix Report")
    logger.info(f"{'=' * 60}\n")

    if fixed:
        logger.info(f"Successfully fixed {len(fixed)} entries:")
        for entry in fixed[:10]:  # Show first 10
            logger.info(
                f"  {entry['key']}: {entry['original']} → {entry['fixed']}"
            )
        if len(fixed) > 10:
            logger.info(f"  ... and {len(fixed) - 10} more")

    if unfixed:
        logger.info(f"\nCould not automatically fix {len(unfixed)} entries:")
        logger.info("\nThese entries need manual attention:")

        # Group by type
        by_type = {}
        for entry in unfixed:
            entry_type = entry["type"]
            if entry_type not in by_type:
                by_type[entry_type] = []
            by_type[entry_type].append(entry)

        for entry_type, entries in sorted(by_type.items()):
            logger.info(f"\n{entry_type.upper()} entries ({len(entries)}):")
            for entry in entries[:5]:  # Show first 5 of each type
                logger.info(f"  - {entry['key']}: {entry['author']}")
                logger.info(f"    Title: {entry['title']}")
                if entry["doi"]:
                    logger.info(f"    DOI: {entry['doi']}")
                elif entry["url"]:
                    logger.info(f"    URL: {entry['url']}")
            if len(entries) > 5:
                logger.info(
                    f"  ... and {len(entries) - 5} more {entry_type} entries"
                )

    # Save detailed report if requested
    if args.report:
        report = ["# Incomplete Author Names Report\n"]
        report.append(f"File: {args.bib_file}")
        report.append(f"Fixed: {len(fixed)}")
        report.append(f"Unfixed: {len(unfixed)}\n")

        if fixed:
            report.append("## Successfully Fixed\n")
            for entry in fixed:
                report.append(
                    f"- **{entry['key']}**: `{entry['original']}` → `{entry['fixed']}`"
                )
            report.append("")

        if unfixed:
            report.append("## Needs Manual Fix\n")
            for entry_type, entries in sorted(by_type.items()):
                report.append(f"### {entry_type.upper()} ({len(entries)})\n")
                for entry in entries:
                    report.append(f"**{entry['key']}**")
                    report.append(f"- Author: `{entry['author']}`")
                    report.append(f"- Title: {entry['title']}")
                    if entry["doi"]:
                        report.append(f"- DOI: {entry['doi']}")
                    if entry["url"]:
                        report.append(f"- URL: {entry['url']}")
                    report.append("")

        args.report.write_text("\n".join(report))
        logger.info(f"\nDetailed report saved to: {args.report}")

    return 0


if __name__ == "__main__":
    exit(main())
