#!/usr/bin/env python3
"""
Bibliography Integrity Test Suite

This test suite validates bibliography integrity during conversion processes,
ensuring that:
1. All cited references exist in the bibliography file
2. No references are lost during conversion
3. Bibliography backup and restoration works correctly
4. Citation format consistency is maintained

Usage:
    python -m pytest tests/test_bibliography_integrity.py -v
    python tests/test_bibliography_integrity.py  # Run directly
"""

# No regex - using string methods instead
import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class BibliographyReport:
    """Comprehensive bibliography integrity report."""

    timestamp: str
    tex_file: str
    bib_file: str
    total_citations: int
    unique_citations: int
    available_entries: int
    missing_citations: list[str]
    orphaned_entries: list[str]
    citation_patterns: dict[str, int]
    warnings: list[str]
    errors: list[str]
    is_valid: bool


class BibliographyIntegrityValidator:
    """Main validator class for bibliography integrity."""

    def __init__(self, tex_file: str, bib_file: str):
        self.tex_file = Path(tex_file)
        self.bib_file = Path(bib_file)
        self.backup_dir = Path(tex_file).parent / ".bib_backups"

        # Citation pattern matching
        self.citation_patterns = [
            r"\\cite\{([^}]+)\}",
            r"\\citep\{([^}]+)\}",
            r"\\citet\{([^}]+)\}",
            r"\\citeauthor\{([^}]+)\}",
            r"\\citeyear\{([^}]+)\}",
            r"\\citealt\{([^}]+)\}",
            r"\\citealp\{([^}]+)\}",
            r"\\nocite\{([^}]+)\}",
        ]

        # Bibliography entry pattern
        self.bib_entry_pattern = r"@\w+\{([^,\s]+),"

    def extract_citations_from_tex(self) -> set[str]:
        """Extract all citation keys from LaTeX file."""
        if not self.tex_file.exists():
            raise FileNotFoundError(f"LaTeX file not found: {self.tex_file}")

        with open(self.tex_file, encoding="utf-8") as f:
            content = f.read()

        citations = set()

        # Find all citation commands using string methods
        i = 0
        while i < len(content):
            # Look for \cite commands (including \nocite)
            if (
                content[i : i + 5] == "\\cite"
                or content[i : i + 7] == "\\nocite"
            ):
                # Determine command length
                if content[i : i + 7] == "\\nocite":
                    j = i + 7
                else:
                    j = i + 5

                # Check if it's \citep, \citet, \citeauthor, \citeyear
                while j < len(content) and content[j].isalpha():
                    j += 1

                # Skip whitespace
                while j < len(content) and content[j] in " \t\n":
                    j += 1

                # Check for opening brace
                if j < len(content) and content[j] == "{":
                    # Find closing brace
                    k = j + 1
                    brace_count = 1
                    while k < len(content) and brace_count > 0:
                        if content[k] == "{":
                            brace_count += 1
                        elif content[k] == "}":
                            brace_count -= 1
                        k += 1

                    if brace_count == 0:
                        # Extract citation keys
                        cite_text = content[j + 1 : k - 1]
                        # Split by comma and semicolon
                        cite_text = cite_text.replace(";", ",")
                        cite_keys = cite_text.split(",")
                        for key in cite_keys:
                            key = key.strip()
                            if key:
                                citations.add(key)

                        i = k
                        continue

            i += 1

        return citations

    def extract_bibliography_keys(self) -> set[str]:
        """Extract all available bibliography entry keys."""
        if not self.bib_file.exists():
            return set()

        with open(self.bib_file, encoding="utf-8") as f:
            content = f.read()

        keys = set()
        # Find all @type{key entries
        i = 0
        while i < len(content):
            if content[i] == "@":
                # Find entry type
                j = i + 1
                while j < len(content) and content[j].isalnum():
                    j += 1

                # Skip whitespace
                while j < len(content) and content[j] in " \t\n":
                    j += 1

                # Check for opening brace
                if j < len(content) and content[j] == "{":
                    # Find key end (comma or whitespace or newline)
                    k = j + 1
                    while k < len(content) and content[k] not in ",\n\t ":
                        k += 1

                    if k > j + 1:
                        key = content[j + 1 : k].strip()
                        if key:
                            keys.add(key)

                    i = k
                    continue

            i += 1

        return keys

    def analyze_citation_patterns(self, tex_content: str) -> dict[str, int]:
        """Analyze which citation commands are used and how frequently."""
        pattern_counts = {
            "\\cite": 0,
            "\\citep": 0,
            "\\citet": 0,
            "\\citeauthor": 0,
            "\\citeyear": 0,
            "\\nocite": 0,
        }

        # Count citation commands using string methods
        i = 0
        while i < len(tex_content):
            # Check for \nocite first (longer pattern)
            if tex_content[i : i + 7] == "\\nocite":
                pattern_counts["\\nocite"] += 1
                i += 7
                continue
            elif tex_content[i : i + 5] == "\\cite":
                # Determine which cite command it is
                j = i + 5
                command = "\\cite"

                # Check for extensions (p, t, author, year)
                if j < len(tex_content):
                    if tex_content[j : j + 6] == "author":
                        command = "\\citeauthor"
                        j += 6
                    elif tex_content[j : j + 4] == "year":
                        command = "\\citeyear"
                        j += 4
                    elif tex_content[j] == "p":
                        command = "\\citep"
                        j += 1
                    elif tex_content[j] == "t":
                        command = "\\citet"
                        j += 1

                if command in pattern_counts:
                    pattern_counts[command] += 1

                i = j
                continue

            i += 1

        return pattern_counts

    def create_backup(self) -> str:
        """Create timestamped backup of bibliography file."""
        if not self.bib_file.exists():
            return ""

        self.backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.bib_file.stem}_{timestamp}.bib"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(self.bib_file, backup_path)
        return str(backup_path)

    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore bibliography from backup."""
        backup = Path(backup_path)
        if not backup.exists():
            return False

        shutil.copy2(backup, self.bib_file)
        return True

    def validate_integrity(self) -> BibliographyReport:
        """Run complete bibliography integrity validation."""
        timestamp = datetime.now().isoformat()
        warnings = []
        errors = []

        try:
            # Extract citations and bibliography entries
            citations = self.extract_citations_from_tex()
            bib_entries = self.extract_bibliography_keys()

            # Find missing and orphaned entries
            missing_citations = sorted(citations - bib_entries)
            orphaned_entries = sorted(bib_entries - citations)

            # Analyze citation patterns
            with open(self.tex_file, encoding="utf-8") as f:
                tex_content = f.read()
            citation_patterns = self.analyze_citation_patterns(tex_content)

            # Generate warnings
            if missing_citations:
                warnings.append(
                    f"Found {len(missing_citations)} missing bibliography entries"
                )
            if orphaned_entries:
                warnings.append(
                    f"Found {len(orphaned_entries)} unused bibliography entries"
                )
            if len(citations) == 0:
                warnings.append("No citations found in LaTeX file")
            if len(bib_entries) == 0:
                errors.append(
                    "Bibliography file is empty or contains no valid entries"
                )

            # Determine validity
            is_valid = len(missing_citations) == 0 and len(errors) == 0

            return BibliographyReport(
                timestamp=timestamp,
                tex_file=str(self.tex_file),
                bib_file=str(self.bib_file),
                total_citations=sum(citation_patterns.values()),
                unique_citations=len(citations),
                available_entries=len(bib_entries),
                missing_citations=missing_citations,
                orphaned_entries=orphaned_entries,
                citation_patterns=citation_patterns,
                warnings=warnings,
                errors=errors,
                is_valid=is_valid,
            )

        except Exception as e:
            errors.append(f"Validation failed: {str(e)}")
            return BibliographyReport(
                timestamp=timestamp,
                tex_file=str(self.tex_file),
                bib_file=str(self.bib_file),
                total_citations=0,
                unique_citations=0,
                available_entries=0,
                missing_citations=[],
                orphaned_entries=[],
                citation_patterns={},
                warnings=warnings,
                errors=errors,
                is_valid=False,
            )

    def save_report(
        self, report: BibliographyReport, output_path: str = None
    ) -> str:
        """Save bibliography report to JSON file."""
        if output_path is None:
            output_path = (
                self.tex_file.parent
                / f"bibliography_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)

        return str(output_path)

    def print_report(self, report: BibliographyReport):
        """Print human-readable bibliography report."""
        print(f"\n{'=' * 60}")
        print("BIBLIOGRAPHY INTEGRITY REPORT")
        print(f"{'=' * 60}")
        print(f"Generated: {report.timestamp}")
        print(f"LaTeX file: {report.tex_file}")
        print(f"Bibliography file: {report.bib_file}")
        print(f"Status: {' VALID' if report.is_valid else ' INVALID'}")

        print(f"\n{'Statistics:':<20}")
        print(f"  Total citations: {report.total_citations}")
        print(f"  Unique citations: {report.unique_citations}")
        print(f"  Available entries: {report.available_entries}")
        print(f"  Missing entries: {len(report.missing_citations)}")
        print(f"  Orphaned entries: {len(report.orphaned_entries)}")

        if report.citation_patterns:
            print(f"\n{'Citation Commands:':<20}")
            for cmd, count in report.citation_patterns.items():
                if count > 0:
                    print(f"  {cmd}: {count}")

        if report.missing_citations:
            print(f"\n{'Missing Citations:':<20}")
            for i, citation in enumerate(report.missing_citations[:10], 1):
                print(f"  {i:2d}. {citation}")
            if len(report.missing_citations) > 10:
                print(f"  ... and {len(report.missing_citations) - 10} more")

        if report.orphaned_entries:
            print(f"\n{'Orphaned Entries:':<20}")
            for i, entry in enumerate(report.orphaned_entries[:5], 1):
                print(f"  {i:2d}. {entry}")
            if len(report.orphaned_entries) > 5:
                print(f"  ... and {len(report.orphaned_entries) - 5} more")

        if report.warnings:
            print(f"\n{'Warnings:':<20}")
            for warning in report.warnings:
                print(f"   {warning}")

        if report.errors:
            print(f"\n{'Errors:':<20}")
            for error in report.errors:
                print(f"   {error}")

        print(f"{'=' * 60}\n")


# Test Classes
class TestBibliographyIntegrity:
    """Pytest test cases for bibliography integrity."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.tex_file = self.test_dir / "test.tex"
        self.bib_file = self.test_dir / "test.bib"

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_test_tex(self, content: str):
        """Create test LaTeX file."""
        with open(self.tex_file, "w") as f:
            f.write(content)

    def create_test_bib(self, content: str):
        """Create test bibliography file."""
        with open(self.bib_file, "w") as f:
            f.write(content)

    def test_valid_bibliography(self):
        """Test case where all citations have corresponding bibliography entries."""
        tex_content = r"""
        This is a test document with citations \cite{smith2023} and \citep{jones2024}.
        """

        bib_content = """
        @article{smith2023,
          title={Test Article},
          author={Smith, John},
          year={2023}
        }

        @book{jones2024,
          title={Test Book},
          author={Jones, Jane},
          year={2024}
        }
        """

        self.create_test_tex(tex_content)
        self.create_test_bib(bib_content)

        validator = BibliographyIntegrityValidator(
            str(self.tex_file), str(self.bib_file)
        )
        report = validator.validate_integrity()

        assert report.is_valid
        assert len(report.missing_citations) == 0
        assert report.unique_citations == 2
        assert report.available_entries == 2

    def test_missing_citations(self):
        """Test case where some citations are missing from bibliography."""
        tex_content = r"""
        This document cites \cite{missing1}, \citep{available1}, and \cite{missing2}.
        """

        bib_content = """
        @article{available1,
          title={Available Article},
          author={Smith, John},
          year={2023}
        }
        """

        self.create_test_tex(tex_content)
        self.create_test_bib(bib_content)

        validator = BibliographyIntegrityValidator(
            str(self.tex_file), str(self.bib_file)
        )
        report = validator.validate_integrity()

        assert not report.is_valid
        assert len(report.missing_citations) == 2
        assert "missing1" in report.missing_citations
        assert "missing2" in report.missing_citations
        assert report.unique_citations == 3
        assert report.available_entries == 1

    def test_orphaned_entries(self):
        """Test case where bibliography has entries not cited in text."""
        tex_content = r"""
        This document only cites \cite{used1}.
        """

        bib_content = """
        @article{used1,
          title={Used Article},
          author={Smith, John},
          year={2023}
        }

        @article{orphaned1,
          title={Orphaned Article},
          author={Jones, Jane},
          year={2024}
        }

        @book{orphaned2,
          title={Orphaned Book},
          author={Brown, Bob},
          year={2025}
        }
        """

        self.create_test_tex(tex_content)
        self.create_test_bib(bib_content)

        validator = BibliographyIntegrityValidator(
            str(self.tex_file), str(self.bib_file)
        )
        report = validator.validate_integrity()

        assert report.is_valid  # Orphaned entries don't make it invalid
        assert len(report.orphaned_entries) == 2
        assert "orphaned1" in report.orphaned_entries
        assert "orphaned2" in report.orphaned_entries
        assert len(report.warnings) >= 1

    def test_backup_restore(self):
        """Test bibliography backup and restore functionality."""
        original_content = """
        @article{original1,
          title={Original Article},
          author={Smith, John},
          year={2023}
        }
        """

        modified_content = """
        @article{modified1,
          title={Modified Article},
          author={Jones, Jane},
          year={2024}
        }
        """

        self.create_test_bib(original_content)
        validator = BibliographyIntegrityValidator(
            str(self.tex_file), str(self.bib_file)
        )

        # Create backup
        backup_path = validator.create_backup()
        assert Path(backup_path).exists()

        # Modify file
        self.create_test_bib(modified_content)

        # Verify modification
        with open(self.bib_file) as f:
            assert "modified1" in f.read()

        # Restore from backup
        assert validator.restore_from_backup(backup_path)

        # Verify restoration
        with open(self.bib_file) as f:
            content = f.read()
            assert "original1" in content
            assert "modified1" not in content

    def test_multiple_citation_formats(self):
        """Test detection of various citation command formats."""
        tex_content = r"""
        Various citation formats:
        \cite{ref1}
        \citep{ref2}
        \citet{ref3}
        \citeauthor{ref4}
        \citeyear{ref5}
        \nocite{ref6}
        Multiple in one: \cite{ref7,ref8,ref9}
        """

        bib_content = """
        @article{ref1, title={Test 1}, author={A}, year={2023}}
        @article{ref2, title={Test 2}, author={B}, year={2023}}
        @article{ref3, title={Test 3}, author={C}, year={2023}}
        @article{ref4, title={Test 4}, author={D}, year={2023}}
        @article{ref5, title={Test 5}, author={E}, year={2023}}
        @article{ref6, title={Test 6}, author={F}, year={2023}}
        @article{ref7, title={Test 7}, author={G}, year={2023}}
        @article{ref8, title={Test 8}, author={H}, year={2023}}
        @article{ref9, title={Test 9}, author={I}, year={2023}}
        """

        self.create_test_tex(tex_content)
        self.create_test_bib(bib_content)

        validator = BibliographyIntegrityValidator(
            str(self.tex_file), str(self.bib_file)
        )
        report = validator.validate_integrity()

        assert report.is_valid
        assert report.unique_citations == 9
        assert len(report.missing_citations) == 0


def main():
    """Main function for direct script execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Bibliography Integrity Validator"
    )
    parser.add_argument("tex_file", help="Path to LaTeX file")
    parser.add_argument("bib_file", help="Path to bibliography file")
    parser.add_argument(
        "--backup", action="store_true", help="Create backup before validation"
    )
    parser.add_argument(
        "--save-report", metavar="PATH", help="Save report to JSON file"
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix bibliography errors when found",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output for fixing",
    )

    args = parser.parse_args()

    validator = BibliographyIntegrityValidator(args.tex_file, args.bib_file)

    # Create backup if requested
    if args.backup:
        backup_path = validator.create_backup()
        if not args.quiet:
            print(f"Backup created: {backup_path}")

    # Run validation
    report = validator.validate_integrity()

    # If --fix flag is provided and there are validation issues, attempt to fix them
    if args.fix and not report.is_valid:
        print(
            "Warning: The --fix option is no longer supported in this script."
        )
        print("Please use the 'deep-biblio bib fix' command instead.")

    # Save report if requested
    if args.save_report:
        report_path = validator.save_report(report, args.save_report)
        if not args.quiet:
            print(f"Report saved: {report_path}")

    # Print report unless quiet
    if not args.quiet:
        validator.print_report(report)

    # Exit with error code if invalid
    exit(0 if report.is_valid else 1)


if __name__ == "__main__":
    main()
