#!/usr/bin/env python3
"""Main script for fixing bibliography entries.

This consolidated script combines all bibliography fixing functionality:
- Author name formatting (LastName, FirstName)
- "et al" catastrophe fixes
- DOI metadata enhancement
- URL validation and fixing
- Entry type detection
- Validation notes and failure tracking

IMPORTANT: Designed to fix bibliographies from LLM-generated content
where author names may be hallucinated or incomplete.
"""

import argparse

# import re  # Banned - using string methods instead
import sys
import time
from pathlib import Path

import bibtexparser
import requests
from bibtexparser.bwriter import BibTexWriter

# Add validation functionality
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.validate_llm_citations import CitationValidator


class BibliographyFixer:
    """Comprehensive bibliography fixing with multiple strategies."""

    def __init__(self, validate: bool = False, add_notes: bool = True):
        self.validate = validate
        self.add_notes = add_notes
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "DeepBiblioTools/1.0 (mailto:petteri.teikari@gmail.com)"
            }
        )

        if validate:
            self.validator = CitationValidator()

        self.stats = {
            "total": 0,
            "author_fixed": 0,
            "et_al_fixed": 0,
            "doi_enhanced": 0,
            "url_fixed": 0,
            "type_fixed": 0,
            "validated": 0,
            "notes_added": 0,
        }

    def fix_et_al_catastrophe(
        self, author_string: str
    ) -> tuple[str, list[str]]:
        """Fix entries where 'et al' was parsed as a name."""
        fixes = []

        # Pattern 1: "al, FirstAuthor et"
        if author_string.startswith("al, ") and " et" in author_string:
            # Extract the name between "al, " and " et"
            start_idx = 4  # len("al, ")
            end_idx = author_string.find(" et", start_idx)
            if end_idx != -1:
                actual_author = author_string[start_idx:end_idx]
                if actual_author and actual_author.isalpha():
                    fixes.append("et_al_catastrophe_fixed")
                    return actual_author, fixes

        # Pattern 2: Just "al" or variations
        if author_string.lower() in ["al", "al.", "et al", "et al."]:
            fixes.append("et_al_removed")
            return "", fixes

        return author_string, fixes

    def fix_author_format(self, author_string: str) -> tuple[str, list[str]]:
        """Fix author formatting to LastName, FirstName."""
        if not author_string:
            return author_string, []

        fixes = []
        authors = []

        # Split by 'and' or '&'
        author_string = author_string.replace(" & ", " and ")
        author_parts = author_string.split(" and ")

        for author in author_parts:
            author = author.strip()
            if not author:
                continue

            # Check for et al catastrophe first
            fixed_author, et_al_fixes = self.fix_et_al_catastrophe(author)
            if et_al_fixes:
                fixes.extend(et_al_fixes)
                if fixed_author:
                    author = fixed_author
                else:
                    continue

            # Check if already in correct format (has comma)
            if "," in author:
                authors.append(author)
            else:
                # Split into parts
                parts = author.split()
                if len(parts) == 1:
                    # Single name only - needs completion
                    authors.append(parts[0])
                    fixes.append("incomplete_name")
                elif len(parts) == 2:
                    # Assume FirstName LastName format
                    authors.append(f"{parts[1]}, {parts[0]}")
                    fixes.append("name_reordered")
                else:
                    # Multiple parts - assume last is surname
                    last_name = parts[-1]
                    first_names = " ".join(parts[:-1])
                    authors.append(f"{last_name}, {first_names}")
                    fixes.append("name_reordered")

        return " and ".join(authors), fixes

    def extract_doi_from_url(self, url: str) -> str | None:
        """Extract DOI from various academic URLs."""
        # Extract DOI from various patterns
        url_lower = url.lower()

        # Standard DOI URLs
        if "doi.org/" in url_lower:
            start_idx = url.find("doi.org/") + 8
            end_idx = url.find(" ", start_idx)
            if end_idx == -1:
                end_idx = len(url)
            return url[start_idx:end_idx].strip("/")

        if "dx.doi.org/" in url_lower:
            start_idx = url.find("dx.doi.org/") + 12
            end_idx = url.find(" ", start_idx)
            if end_idx == -1:
                end_idx = len(url)
            return url[start_idx:end_idx].strip("/")

        # Publisher-specific patterns
        if "link.springer.com/" in url_lower:
            if "/article/" in url_lower:
                start_idx = url.find("/article/") + 9
            elif "/chapter/" in url_lower:
                start_idx = url.find("/chapter/") + 9
            else:
                return None
            end_idx = url.find(" ", start_idx)
            if end_idx == -1:
                end_idx = len(url)
            return url[start_idx:end_idx].strip("/")

        if "nature.com/articles/" in url_lower:
            start_idx = url.find("/articles/") + 10
            end_idx = url.find(" ", start_idx)
            if end_idx == -1:
                end_idx = len(url)
            return url[start_idx:end_idx].strip("/")

        if "onlinelibrary.wiley.com/doi/" in url_lower:
            start_idx = url.find("/doi/") + 5
            # Skip optional abs/ or full/
            if url[start_idx:].startswith("abs/"):
                start_idx += 4
            elif url[start_idx:].startswith("full/"):
                start_idx += 5
            end_idx = url.find(" ", start_idx)
            if end_idx == -1:
                end_idx = len(url)
            return url[start_idx:end_idx].strip("/")

        return None

    def fix_arxiv_url(self, url: str) -> tuple[str, bool]:
        """Convert arXiv HTML URLs to abstract URLs."""
        if "arxiv.org/html/" in url:
            # Extract ID and convert to abstract URL
            start_idx = url.find("arxiv.org/html/") + 15
            # Look for pattern like XXXX.XXXXX
            if start_idx > 14:  # Found the pattern
                remaining = url[start_idx:]
                # Find the arxiv ID (digits.digits)
                id_parts = []
                for i, char in enumerate(remaining):
                    if char.isdigit() or char == ".":
                        id_parts.append(char)
                    else:
                        break
                arxiv_id = "".join(id_parts)
                if "." in arxiv_id and len(arxiv_id) >= 10:
                    return f"https://arxiv.org/abs/{arxiv_id}", True
        return url, False

    def fetch_doi_metadata(self, doi: str) -> tuple[bool, dict]:
        """Fetch metadata from CrossRef."""
        url = f"https://api.crossref.org/works/{doi}"

        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                message = data.get("message", {})

                # Extract authors
                authors = []
                if "author" in message:
                    for author in message["author"]:
                        family = author.get("family", "")
                        given = author.get("given", "")
                        if family and given:
                            authors.append(f"{family}, {given}")
                        elif family:
                            authors.append(family)

                metadata = {
                    "authors": authors,
                    "title": message.get("title", [""])[0]
                    if isinstance(message.get("title"), list)
                    else message.get("title", ""),
                    "journal": message.get("container-title", [""])[0]
                    if isinstance(message.get("container-title"), list)
                    else message.get("container-title", ""),
                    "year": str(
                        message.get("published-print", {}).get(
                            "date-parts", [[]]
                        )[0][0]
                    )
                    if message.get("published-print")
                    else "",
                    "volume": str(message.get("volume", ""))
                    if message.get("volume")
                    else "",
                    "pages": message.get("page", ""),
                }

                return True, metadata

        except Exception:
            pass

        return False, {}

    def determine_entry_type(self, entry: dict) -> str:
        """Determine proper BibTeX entry type."""
        # Check for conference indicators
        if any(field in entry for field in ["booktitle", "conference"]):
            return "inproceedings"

        # Check for book indicators
        if "publisher" in entry and "journal" not in entry:
            if "chapter" in entry:
                return "incollection"
            return "book"

        # Check for thesis
        if "school" in entry:
            return "phdthesis"

        # Check for technical report
        if "institution" in entry and "journal" not in entry:
            return "techreport"

        # Default to article if has journal
        if "journal" in entry:
            return "article"

        # Otherwise misc
        return "misc"

    def parse_github_info(self, url: str) -> dict | None:
        """Parse GitHub URL and fetch repository information."""
        # Extract owner and repo from GitHub URL
        owner = None
        repo = None

        if "github.com/" in url:
            start_idx = url.find("github.com/") + 11
            remaining = url[start_idx:]
            parts = remaining.split("/")
            if len(parts) >= 2:
                owner = parts[0]
                repo = parts[1].rstrip("/")
        elif "github.io/" in url:
            start_idx = url.find("github.io/") + 10
            remaining = url[start_idx:]
            parts = remaining.split("/")
            if len(parts) >= 2:
                owner = parts[0]
                repo = parts[1].rstrip("/")

        if owner and repo:
            # Try to fetch repo info from GitHub API
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            try:
                response = self.session.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "owner": owner,
                        "repo": repo,
                        "description": data.get("description", ""),
                        "topics": data.get("topics", []),
                    }
            except Exception:
                pass

            # Return basic info even if API fails
            return {"owner": owner, "repo": repo}

        return None

    def fix_entry(self, entry: dict) -> tuple[dict, list[str]]:
        """Fix a single bibliography entry."""
        fixes = []
        notes = []

        # Fix authors
        if "author" in entry:
            original_authors = entry["author"]
            fixed_authors, author_fixes = self.fix_author_format(
                original_authors
            )
            if author_fixes:
                entry["author"] = fixed_authors
                fixes.extend(author_fixes)
                self.stats["author_fixed"] += 1

                if "et_al" in " ".join(author_fixes):
                    self.stats["et_al_fixed"] += 1
                    notes.append("Fixed 'et al' parsing error")

                if "incomplete_name" in author_fixes:
                    notes.append(
                        "Incomplete author names - needs manual verification"
                    )

        # Extract DOI from URL if not present
        if "url" in entry and "doi" not in entry:
            doi = self.extract_doi_from_url(entry["url"])
            if doi:
                entry["doi"] = doi
                fixes.append("doi_extracted")

        # Fix arXiv URLs
        if "url" in entry:
            fixed_url, was_fixed = self.fix_arxiv_url(entry["url"])
            if was_fixed:
                entry["url"] = fixed_url
                fixes.append("arxiv_url_fixed")
                self.stats["url_fixed"] += 1

            # Handle GitHub URLs
            if "github.com" in entry["url"] or "github.io" in entry["url"]:
                github_info = self.parse_github_info(entry["url"])
                if github_info:
                    # Improve title if needed
                    if (
                        not entry.get("title")
                        or entry["title"] == f"{github_info['owner']} et al"
                    ):
                        if github_info.get("description"):
                            entry["title"] = github_info["description"]
                            fixes.append("github_title_added")
                        else:
                            entry["title"] = (
                                f"{github_info['repo']} - GitHub Repository"
                            )
                            fixes.append("github_title_generated")

                    # Fix author if it looks wrong
                    if entry.get("author", "").startswith(
                        "al, "
                    ) or " et al" in entry.get("author", ""):
                        # Use GitHub owner as author
                        entry["author"] = github_info["owner"]
                        fixes.append("github_author_fixed")
                        notes.append("GitHub repository - author is repo owner")

        # Enhance with DOI metadata if available
        if "doi" in entry and (
            "incomplete_name" in fixes or not entry.get("title")
        ):
            time.sleep(0.3)  # Rate limiting
            success, metadata = self.fetch_doi_metadata(entry["doi"])

            if success:
                # Update authors if we have better data
                if metadata["authors"] and len(metadata["authors"]) > len(
                    entry.get("author", "").split(" and ")
                ):
                    entry["author"] = " and ".join(metadata["authors"])
                    fixes.append("authors_from_doi")
                    self.stats["doi_enhanced"] += 1

                # Update other fields
                for field in ["title", "journal", "year", "volume", "pages"]:
                    if metadata.get(field) and not entry.get(field):
                        entry[field] = metadata[field]
                        fixes.append(f"{field}_from_doi")
            else:
                notes.append("DOI metadata fetch failed")

        # Validate if requested
        if self.validate and hasattr(self, "validator"):
            url = entry.get("url", "")
            if not url and entry.get("doi"):
                url = f"https://doi.org/{entry['doi']}"

            if url:
                # Parse current authors
                authors = [
                    a.strip() for a in entry.get("author", "").split(" and ")
                ]
                result = self.validator.validate_citation(
                    citation_text=entry.get("ID", ""),
                    url=url,
                    original_authors=authors,
                )

                if result.validation_status == "validated":
                    self.stats["validated"] += 1
                    if result.validated_authors:
                        entry["author"] = " and ".join(result.validated_authors)
                        fixes.append("authors_validated")

                        # Update BibTeX key to match first author
                        first_author_lastname = (
                            result.validated_authors[0].split(",")[0].lower()
                        )
                        new_id = (
                            f"{first_author_lastname}{entry.get('year', '')}"
                        )
                        if new_id != entry.get("ID", ""):
                            entry["ID"] = new_id
                            fixes.append(f"id_updated_to_{new_id}")

                        # Update other metadata from validation
                        if result.metadata.get("title") and not entry.get(
                            "title"
                        ):
                            entry["title"] = result.metadata["title"]
                            fixes.append("title_from_validation")
                elif result.validation_status == "failed":
                    # Even if validation "failed", if we have better authors, use them
                    if (
                        result.validated_authors
                        and result.confidence_score < 0.5
                    ):
                        # This is a hallucinated entry - replace with correct data
                        entry["author"] = " and ".join(result.validated_authors)
                        fixes.append("hallucinated_authors_replaced")
                        notes.append(
                            "Authors were hallucinated - replaced with validated authors"
                        )

                        # Update title if available
                        if result.metadata.get("title"):
                            entry["title"] = result.metadata["title"]
                            fixes.append("title_from_validation")
                    else:
                        notes.append(
                            "VALIDATION FAILED - authors may be incorrect!"
                        )
                elif result.validation_status == "partial":
                    if result.validated_authors:
                        entry["author"] = " and ".join(result.validated_authors)
                        fixes.append("partial_authors_replaced")
                    notes.append(
                        f"Partial validation - confidence: {result.confidence_score:.2f}"
                    )

        # Fix entry type
        current_type = entry.get("ENTRYTYPE", "misc")
        correct_type = self.determine_entry_type(entry)
        if current_type != correct_type:
            entry["ENTRYTYPE"] = correct_type
            fixes.append(f"type_changed_{current_type}_to_{correct_type}")
            self.stats["type_fixed"] += 1

        # Add notes if requested
        if self.add_notes and notes:
            existing_note = entry.get("note", "")
            if existing_note:
                entry["note"] = existing_note + "; " + "; ".join(notes)
            else:
                entry["note"] = "; ".join(notes)
            self.stats["notes_added"] += 1

        return entry, fixes

    def fix_bibliography_file(
        self, input_file: Path, output_file: Path | None = None
    ) -> Path:
        """Fix all entries in a bibliography file."""
        print(f"Fixing bibliography: {input_file}")

        with open(input_file, encoding="utf-8") as f:
            bib_database = bibtexparser.load(f)

        self.stats["total"] = len(bib_database.entries)
        print(f"Total entries: {self.stats['total']}")

        # Process each entry
        all_fixes = []
        for i, entry in enumerate(bib_database.entries):
            if (i + 1) % 50 == 0:
                print(f"  Processing {i + 1}/{self.stats['total']}...")

            entry, fixes = self.fix_entry(entry)
            if fixes:
                all_fixes.append((entry.get("ID", f"entry_{i}"), fixes))

        # Write output
        if output_file is None:
            output_file = input_file.parent / f"{input_file.stem}_fixed.bib"

        writer = BibTexWriter()
        writer.indent = "  "
        writer.order_entries_by = "ID"
        writer.align_values = True

        with open(output_file, "w", encoding="utf-8") as f:
            bibtexparser.dump(bib_database, f, writer)

        # Print summary
        print(f"\nFixed bibliography written to: {output_file}")
        print("\nFix Summary:")
        print(f"  Total entries:        {self.stats['total']}")
        print(f"  Authors fixed:        {self.stats['author_fixed']}")
        print(f"  Et al catastrophes:   {self.stats['et_al_fixed']}")
        print(f"  DOI enhanced:         {self.stats['doi_enhanced']}")
        print(f"  URLs fixed:           {self.stats['url_fixed']}")
        print(f"  Types corrected:      {self.stats['type_fixed']}")
        if self.validate:
            print(f"  Validated:            {self.stats['validated']}")
        if self.add_notes:
            print(f"  Notes added:          {self.stats['notes_added']}")

        # Show example fixes
        if all_fixes:
            print("\nExample fixes:")
            for entry_id, fixes in all_fixes[:5]:
                print(f"  {entry_id}: {', '.join(fixes)}")

        return output_file


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Fix bibliography entries with comprehensive enhancements",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script fixes common bibliography issues:
- Author name formatting (LastName, FirstName)
- "et al" parsing catastrophes
- Missing DOI extraction from URLs
- arXiv HTML to abstract URL conversion
- GitHub repository parsing and enhancement
- Entry type detection
- Metadata enhancement from CrossRef
- Citation validation (for LLM content)
- Auto-correction of hallucinated entries

Examples:
  # Basic fixing
  %(prog)s references.bib

  # Fix with validation
  %(prog)s references.bib --validate

  # Fix without adding notes
  %(prog)s references.bib --no-notes -o fixed.bib
""",
    )

    parser.add_argument("input", type=Path, help="Input bibliography file")
    parser.add_argument("-o", "--output", type=Path, help="Output file")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate citations against real sources",
    )
    parser.add_argument(
        "--no-notes",
        action="store_true",
        help="Do not add explanatory notes to entries",
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}")
        return 1

    try:
        fixer = BibliographyFixer(
            validate=args.validate, add_notes=not args.no_notes
        )

        output_file = fixer.fix_bibliography_file(args.input, args.output)
        print(f"\nSuccess! Fixed bibliography: {output_file}")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
