#!/usr/bin/env python3
"""
Hardcode LaTeX bibliography with custom formatting including hyperlinked author names and years.

This script converts .tex files with .bib and .bst files into hardcoded .bbl with custom formatting
that includes hyperlinked author names and years for better digital accessibility.

Key features:
- Hyperlinks author names and publication years
- Handles DOI papers, arXiv papers, and non-academic references differently
- Validates and warns about missing URLs and malformed entries
- Preserves title case and special formatting
"""

import argparse
import html
import logging

# import re  # Banned - using string methods instead
import sys
from dataclasses import dataclass
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class BibEntry:
    """Represents a bibliography entry with all necessary fields."""

    key: str
    authors: str
    year: str
    title: str
    journal: str | None = None
    volume: str | None = None
    number: str | None = None
    pages: str | None = None
    doi: str | None = None
    url: str | None = None
    arxiv: str | None = None
    urldate: str | None = None
    entry_type: str = "article"
    note: str | None = None
    publisher: str | None = None
    series: str | None = None
    booktitle: str | None = None


class BibliographyHardcoder:
    """Converts bibliography entries to hardcoded format with hyperlinked authors and years."""

    def __init__(self, validate_urls: bool = True):
        """Initialize the hardcoder.

        Args:
            validate_urls: Whether to validate and warn about missing URLs
        """
        self.validate_urls = validate_urls
        self.missing_urls: list[str] = []
        self.malformed_entries: list[str] = []

        # HTML entities commonly found in bibliographies
        self.html_entities_map = {
            "&amp;": "&",
            "&lt;": "<",
            "&gt;": ">",
            "&quot;": '"',
            "&apos;": "'",
            "&#39;": "'",
            "&nbsp;": " ",
            "&ndash;": "--",
            "&mdash;": "---",
        }

    def parse_bib_file(
        self, bib_path: Path
    ) -> tuple[dict[str, BibEntry], list[str]]:
        """Parse a .bib file and extract entries while preserving order.

        Args:
            bib_path: Path to the .bib file

        Returns:
            Tuple of:
            - Dictionary mapping citation keys to BibEntry objects
            - List of citation keys in order they appear in the file
        """
        logger.info(f"Parsing bibliography file: {bib_path}")

        with open(bib_path, encoding="utf-8") as bibfile:
            parser = BibTexParser()
            parser.customization = convert_to_unicode
            bib_database = bibtexparser.load(bibfile, parser=parser)

        entries = {}
        ordered_keys = []

        for entry in bib_database.entries:
            bib_entry = self._convert_to_bib_entry(entry)
            entries[bib_entry.key] = bib_entry
            ordered_keys.append(bib_entry.key)

            # Validate entry
            if self.validate_urls:
                self._validate_entry(bib_entry)

        return entries, ordered_keys

    def _clean_html_entities(self, text: str) -> str:
        """Clean HTML entities from text.

        Args:
            text: Text potentially containing HTML entities

        Returns:
            Text with HTML entities converted to their proper characters
        """
        if not text:
            return text

        # First use html.unescape for standard entities
        text = html.unescape(text)

        # Then handle any specific mappings we want to ensure
        for entity, replacement in self.html_entities_map.items():
            text = text.replace(entity, replacement)

        return text

    def _convert_to_bib_entry(self, entry: dict) -> BibEntry:
        """Convert a bibtexparser entry to our BibEntry format.

        Args:
            entry: Dictionary from bibtexparser

        Returns:
            BibEntry object
        """
        # Extract authors
        authors = entry.get("author", "")
        if not authors:
            authors = entry.get("editor", "Unknown")

        # Clean up author names
        authors = self._format_authors(authors)

        # Extract arXiv ID if present
        arxiv = None
        if "eprint" in entry:
            arxiv = entry["eprint"]
        elif "arxiv" in entry:
            arxiv = entry["arxiv"]
        elif "journal" in entry and "arxiv" in entry["journal"].lower():
            # Extract from journal field like "arXiv preprint arXiv:2502.06722"
            journal_lower = entry["journal"].lower()
            arxiv_pos = journal_lower.find("arxiv:")
            if arxiv_pos != -1:
                # Extract the ID
                start = arxiv_pos + 6
                end = start
                while end < len(entry["journal"]) and (
                    entry["journal"][end].isdigit()
                    or entry["journal"][end] == "."
                ):
                    end += 1
                if end > start:
                    arxiv = entry["journal"][start:end]

        # Also check URL for arXiv papers
        if not arxiv and "url" in entry and "arxiv.org" in entry.get("url", ""):
            url = entry["url"]
            abs_pos = url.find("arxiv.org/abs/")
            if abs_pos != -1:
                start = abs_pos + 14
                end = start
                while end < len(url) and (
                    url[end].isdigit() or url[end] == "."
                ):
                    end += 1
                if end > start:
                    arxiv = url[start:end]

        # Handle URL
        url = entry.get("url", "")
        if not url and "doi" in entry:
            url = f"https://doi.org/{entry['doi']}"
        elif not url and arxiv:
            url = f"https://arxiv.org/abs/{arxiv}"

        # Extract year from either 'year' or 'date' field (BibLaTeX uses 'date')
        year = entry.get("year", "")
        if not year and "date" in entry:
            # Extract year from date field (format: YYYY-MM-DD or YYYY)
            date = entry["date"]
            if len(date) >= 4 and date[:4].isdigit():
                year = date[:4]

        return BibEntry(
            key=entry.get("ID", ""),
            authors=self._clean_html_entities(authors),
            year=year,
            title=self._clean_html_entities(entry.get("title", "")),
            journal=self._clean_html_entities(
                entry.get("journaltitle", entry.get("journal", ""))
            ),
            volume=entry.get("volume", ""),
            number=entry.get("number", ""),
            pages=entry.get("pages", ""),
            doi=entry.get("doi", ""),
            url=url,
            arxiv=arxiv,
            urldate=entry.get("urldate", ""),
            entry_type=entry.get("ENTRYTYPE", "article"),
            note=self._clean_html_entities(entry.get("note", "")),
            publisher=self._clean_html_entities(entry.get("publisher", "")),
            series=self._clean_html_entities(entry.get("series", "")),
            booktitle=self._clean_html_entities(entry.get("booktitle", "")),
        )

    def _format_authors(self, authors: str) -> str:
        """Format author names, handling 'and' separators and cleaning up.

        Args:
            authors: Raw author string

        Returns:
            Formatted author string
        """
        # Handle "et al." and "others"
        if "others" in authors:
            authors = authors.replace("and others", "et al.")

        # Split by 'and' and clean up
        author_list = [a.strip() for a in authors.split(" and ")]

        # Format each author
        formatted = []
        for author in author_list:
            # Handle reversed names (Last, First)
            if "," in author:
                parts = author.split(",", 1)
                author = f"{parts[1].strip()} {parts[0].strip()}"
            formatted.append(author)

        # Join with commas
        if len(formatted) > 2:
            return ", ".join(formatted[:-1]) + ", " + formatted[-1]
        elif len(formatted) == 2:
            return " and ".join(formatted)
        else:
            return formatted[0] if formatted else "Unknown"

    def _get_sort_key(self, entry: BibEntry) -> str:
        """Extract sort key from entry (author surname + year + title).

        Args:
            entry: BibEntry to extract sort key from

        Returns:
            Sort key string for alphabetical ordering
        """
        # Extract first author's surname
        authors = entry.authors

        # Handle special cases
        if not authors or authors == "Unknown":
            # Use title as fallback
            return entry.title.lower()

        # Handle URL-like authors (e.g., "https://rerun.io/")
        if authors.startswith("http"):
            # Use the domain name or title
            return entry.title.lower()

        # Handle "et al." entries - use the actual first author name
        if " et al." in authors:
            authors = authors.replace(" et al.", "").strip()
            # If nothing left after removing et al., use title
            if not authors:
                return entry.title.lower()

        # Extract first author
        if " and " in authors:
            first_author = authors.split(" and ")[0].strip()
        else:
            first_author = authors.strip()

        # Extract surname based on format
        if "," in first_author:
            # Format: "Surname, First"
            surname = first_author.split(",")[0].strip()
        else:
            # Format: "First Surname" or just "Surname"
            parts = first_author.split()
            if len(parts) == 0:
                surname = first_author
            elif len(parts) == 1:
                # Single name (e.g., "Dronecode")
                surname = parts[0]
            else:
                # Multiple parts - need to handle special cases
                # Check for lowercase prefixes that might be part of surname
                # e.g., "da Silva", "von Neumann", "de la Cruz"
                surname_prefixes = [
                    "da",
                    "de",
                    "del",
                    "della",
                    "di",
                    "do",
                    "dos",
                    "du",
                    "la",
                    "le",
                    "van",
                    "von",
                    "der",
                    "den",
                    "ten",
                ]

                # Check if second-to-last word is a surname prefix
                if len(parts) >= 2 and parts[-2].lower() in surname_prefixes:
                    # Include prefix in surname (e.g., "da Silva")
                    surname = " ".join(parts[-2:])
                else:
                    # Check if all parts except the last one are initials
                    all_initials = True
                    for i, part in enumerate(parts[:-1]):
                        # Check if it's an initial: single uppercase letter with or without period
                        # or two uppercase letters with period (e.g., "Ph.")
                        if not (
                            (
                                len(part) == 1 and part.isupper()
                            )  # Single letter like "A"
                            or (
                                len(part) == 2
                                and part[1] == "."
                                and part[0].isupper()
                            )  # Like "A."
                            or (
                                len(part) == 3
                                and part[1:] == ".."
                                and part[0].isupper()
                            )  # Like "A.."
                            or (
                                len(part) <= 3
                                and part.endswith(".")
                                and all(c.isupper() for c in part[:-1])
                            )  # Like "Ph."
                        ):
                            all_initials = False
                            break

                    if all_initials and len(parts) >= 2:
                        # All parts before last are initials, so last is surname
                        surname = parts[-1]
                    else:
                        # Not all initials or single name, use default (last part)
                        surname = parts[-1]

        # Create sort key: surname + year + title
        # This ensures consistent ordering for same author
        sort_key = f"{surname.lower()}_{entry.year}_{entry.title.lower()}"
        return sort_key

    def _validate_entry(self, entry: BibEntry) -> None:
        """Validate a bibliography entry and record issues.

        Args:
            entry: BibEntry to validate
        """
        # Check for missing URLs in entries that should have them
        if not entry.url and not entry.doi and not entry.arxiv:
            if entry.entry_type in ["misc", "online", "webpage"]:
                self.missing_urls.append(
                    f"{entry.key}: {entry.title} (type: {entry.entry_type})"
                )
            elif entry.journal and any(
                term in entry.journal.lower()
                for term in ["online", "web", "internet", "website"]
            ):
                self.missing_urls.append(
                    f"{entry.key}: {entry.title} (journal: {entry.journal})"
                )

        # Check for malformed author names
        if "al, Author et" in entry.authors or entry.authors == "et al.":
            self.malformed_entries.append(
                f"{entry.key}: Malformed authors - '{entry.authors}'"
            )
        elif "others" in entry.authors and "and others" not in entry.authors:
            # Check for improperly formatted "others"
            self.malformed_entries.append(
                f"{entry.key}: Possibly malformed authors - '{entry.authors}'"
            )

        # Check for missing essential fields
        if not entry.year:
            self.malformed_entries.append(f"{entry.key}: Missing year")
        if not entry.title:
            self.malformed_entries.append(f"{entry.key}: Missing title")
        if not entry.authors or entry.authors == "Unknown":
            self.malformed_entries.append(
                f"{entry.key}: Missing or unknown authors"
            )

    def format_entry(self, entry: BibEntry) -> str:
        """Format a single bibliography entry with hyperlinked authors and year.

        Args:
            entry: BibEntry to format

        Returns:
            Formatted LaTeX bibliography entry
        """
        # Determine the URL for hyperlinking
        link_url = entry.url or (
            f"https://doi.org/{entry.doi}" if entry.doi else ""
        )

        # Format author-year hyperlink
        if link_url:
            author_year = (
                f"\\href{{{link_url}}}{{{entry.authors} ({entry.year})}}"
            )
        else:
            author_year = f"{entry.authors} ({entry.year})"

        # Start building the entry
        parts = [f"\\bibitem{{{entry.key}}}", author_year]

        # Add title
        parts.append(entry.title)

        # Determine if this is a non-academic reference (no DOI, no arXiv)
        is_non_academic = not entry.doi and not entry.arxiv

        # Handle different entry types
        if entry.arxiv:
            # arXiv paper - format with italics and ID
            parts.append(f"{{\\em arXiv:{entry.arxiv}}}")
        elif entry.series and entry.entry_type in [
            "inproceedings",
            "conference",
        ]:
            # Conference proceedings - use series field in emphasis
            series_text = f"{{\\em {entry.series}}}"
            if entry.pages:
                # Convert single dash to double dash for page ranges
                pages = entry.pages.replace("-", "--")
                series_text += f":{pages}"
            parts.append(series_text)
        elif entry.journal:
            # Academic journal article
            # Format journal name and volume in italics
            journal_text = f"{{\\em {entry.journal}"
            if entry.volume:
                journal_text += f" {entry.volume}}}"
                if entry.number:
                    journal_text += f"({entry.number})"
            else:
                journal_text += "}"
            if entry.pages:
                # Convert single dash to double dash for page ranges
                pages = entry.pages.replace("-", "--")
                journal_text += f":{pages}"
            parts.append(journal_text)
        elif entry.booktitle:
            # Conference or book chapter without series - use booktitle in emphasis
            booktitle_text = f"{{\\em {entry.booktitle}}}"
            if entry.pages:
                # Convert single dash to double dash for page ranges
                pages = entry.pages.replace("-", "--")
                booktitle_text += f":{pages}"
            parts.append(booktitle_text)
        elif is_non_academic:
            # Non-academic reference (no DOI, no arXiv)
            if entry.journal:
                parts.append(entry.journal)
            elif entry.series:
                parts.append(entry.series)
            elif entry.booktitle:
                parts.append(entry.booktitle)
            # Add access date for non-academic references
            if entry.urldate:
                parts.append(f"(accessed {entry.urldate})")

        # Join all parts
        formatted = " ".join(parts)

        # Ensure entry ends with period
        if not formatted.rstrip().endswith("."):
            formatted += "."

        return formatted

    def generate_hardcoded_bibliography(
        self,
        entries: dict[str, BibEntry],
        citation_order: list[str] | None = None,
        preserve_bib_order: bool = True,
    ) -> str:
        """Generate the complete hardcoded bibliography.

        Args:
            entries: Dictionary of bibliography entries
            citation_order: Optional list of citation keys in desired order
            preserve_bib_order: If True and citation_order provided, use that order

        Returns:
            Complete LaTeX bibliography environment
        """
        # Use the provided order if available, otherwise sort alphabetically
        if preserve_bib_order and citation_order:
            ordered_keys = [key for key in citation_order if key in entries]
        else:
            # Fallback to alphabetical order by author surname
            sorted_entries = sorted(
                entries.items(), key=lambda x: self._get_sort_key(x[1])
            )
            ordered_keys = [key for key, _ in sorted_entries]

        # Generate bibliography
        lines = ["\\begin{thebibliography}{99}", ""]

        for key in ordered_keys:
            if key in entries:
                formatted_entry = self.format_entry(entries[key])
                lines.append(formatted_entry)
                lines.append("")  # Empty line between entries

        lines.append("\\end{thebibliography}")

        return "\n".join(lines)

    def process_tex_file(
        self, tex_path: Path, bib_path: Path, output_path: Path | None = None
    ) -> None:
        """Process a .tex file and replace bibliography with hardcoded version.

        Args:
            tex_path: Path to input .tex file
            bib_path: Path to .bib file
            output_path: Optional output path (defaults to input with _hardcoded suffix)
        """
        logger.info(f"Processing {tex_path}")

        # Parse bibliography and get ordered keys
        entries, bib_ordered_keys = self.parse_bib_file(bib_path)

        # Read tex file
        tex_content = tex_path.read_text(encoding="utf-8")

        # Generate hardcoded bibliography using the bib file order
        hardcoded_bib = self.generate_hardcoded_bibliography(
            entries, bib_ordered_keys, preserve_bib_order=True
        )

        # Also save the bibliography as a separate .bbl file
        bbl_path = tex_path.parent / f"{tex_path.stem}_hardcoded.bbl"
        bbl_path.write_text(hardcoded_bib, encoding="utf-8")
        logger.info(f"Written hardcoded bibliography to {bbl_path}")

        # Replace bibliography commands with hardcoded version
        # Remove \bibliography{...}
        while True:
            pos = tex_content.find("\\bibliography{")
            if pos == -1:
                break
            # Find matching closing brace
            brace_count = 1
            j = pos + 14
            while j < len(tex_content) and brace_count > 0:
                if tex_content[j] == "{":
                    brace_count += 1
                elif tex_content[j] == "}":
                    brace_count -= 1
                j += 1
            if brace_count == 0:
                tex_content = tex_content[:pos] + tex_content[j:]
            else:
                break

        # Remove \bibliographystyle{...}
        while True:
            pos = tex_content.find("\\bibliographystyle{")
            if pos == -1:
                break
            # Find matching closing brace
            brace_count = 1
            j = pos + 19
            while j < len(tex_content) and brace_count > 0:
                if tex_content[j] == "{":
                    brace_count += 1
                elif tex_content[j] == "}":
                    brace_count -= 1
                j += 1
            if brace_count == 0:
                tex_content = tex_content[:pos] + tex_content[j:]
            else:
                break

        # Also remove any existing thebibliography environment
        begin_pos = tex_content.find("\\begin{thebibliography}")
        if begin_pos != -1:
            # Find the matching \end{thebibliography}
            end_pos = tex_content.find("\\end{thebibliography}", begin_pos)
            if end_pos != -1:
                # Remove everything from begin to end of the end command
                tex_content = (
                    tex_content[:begin_pos] + tex_content[end_pos + 21 :]
                )

        # Find where to insert bibliography (before \end{document})
        end_doc_pos = tex_content.find("\\end{document}")
        if end_doc_pos != -1:
            tex_content = (
                tex_content[:end_doc_pos]
                + "\n\n"
                + hardcoded_bib
                + "\n\n"
                + tex_content[end_doc_pos:]
            )

        # Write output
        if output_path is None:
            output_path = (
                tex_path.parent / f"{tex_path.stem}_hardcoded{tex_path.suffix}"
            )

        output_path.write_text(tex_content, encoding="utf-8")
        logger.info(
            f"Written complete document with hardcoded bibliography to {output_path}"
        )

        # Report issues
        if self.missing_urls:
            logger.warning("Entries missing URLs:")
            for entry in self.missing_urls:
                logger.warning(f"  - {entry}")

        if self.malformed_entries:
            logger.warning("Malformed entries:")
            for entry in self.malformed_entries:
                logger.warning(f"  - {entry}")

    def _extract_citation_order(self, tex_content: str) -> list[str]:
        """Extract the order of citations from the tex file.

        Args:
            tex_content: Content of the .tex file

        Returns:
            List of citation keys in order of appearance
        """
        # Find all \cite{...} commands
        citations = []
        i = 0
        while i < len(tex_content):
            if tex_content[i : i + 6] == "\\cite{":
                # Find closing brace
                j = i + 6
                brace_count = 1
                while j < len(tex_content) and brace_count > 0:
                    if tex_content[j] == "{":
                        brace_count += 1
                    elif tex_content[j] == "}":
                        brace_count -= 1
                    j += 1
                if brace_count == 0:
                    # Extract and split citations
                    cite_str = tex_content[i + 6 : j - 1]
                    keys = [k.strip() for k in cite_str.split(",")]
                    for key in keys:
                        if key and key not in citations:
                            citations.append(key)
                    i = j
                    continue
            i += 1

        return citations


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Hardcode LaTeX bibliography with hyperlinked authors and years"
    )
    parser.add_argument("tex_file", type=Path, help="Input .tex file")
    parser.add_argument("bib_file", type=Path, help="Input .bib file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output .tex file (default: input_hardcoded.tex)",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Disable URL validation warnings",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.tex_file.exists():
        logger.error(f"TeX file not found: {args.tex_file}")
        sys.exit(1)

    if not args.bib_file.exists():
        logger.error(f"Bibliography file not found: {args.bib_file}")
        sys.exit(1)

    # Process the files
    hardcoder = BibliographyHardcoder(validate_urls=not args.no_validate)
    hardcoder.process_tex_file(args.tex_file, args.bib_file, args.output)


if __name__ == "__main__":
    main()
