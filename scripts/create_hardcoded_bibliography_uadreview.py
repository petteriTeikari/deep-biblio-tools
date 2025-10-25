#!/usr/bin/env python3
"""
Convert BibTeX bibliography to hardcoded LaTeX bibliography with authoryear hyperlinks.
Follows the same format as used in Drone_Position project.
"""

# import re  # Banned - using string methods instead
import sys
from dataclasses import dataclass
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode


@dataclass
class BibEntry:
    """Represents a bibliography entry."""

    key: str
    entry_type: str
    authors: str
    year: str
    title: str
    raw_entry: dict
    journal: str | None = None
    volume: str | None = None
    number: str | None = None
    pages: str | None = None
    publisher: str | None = None
    booktitle: str | None = None
    series: str | None = None
    url: str | None = None
    doi: str | None = None
    urldate: str | None = None
    note: str | None = None
    institution: str | None = None


class HardcodedBibliographyGenerator:
    """Generate hardcoded bibliography with authoryear hyperlinks."""

    def __init__(self, bib_file: Path):
        self.bib_file = bib_file
        self.entries: list[BibEntry] = []

    def load_bibliography(self):
        """Load and parse the BibTeX file."""
        print(f"Loading bibliography from: {self.bib_file}")

        parser = BibTexParser()
        parser.ignore_nonstandard_types = False
        parser.homogenize_fields = False
        parser.customization = convert_to_unicode

        with open(self.bib_file, encoding="utf-8") as f:
            bib_database = bibtexparser.load(f, parser=parser)

        print(f"Found {len(bib_database.entries)} entries")

        # Convert to our dataclass format
        for entry in bib_database.entries:
            bib_entry = self._convert_entry(entry)
            if bib_entry:
                self.entries.append(bib_entry)

        # Sort alphabetically by first author's surname
        self.entries.sort(key=lambda x: self._get_sort_key(x.authors))
        print(f"Processed {len(self.entries)} valid entries")

    def _convert_entry(self, entry: dict) -> BibEntry | None:
        """Convert raw BibTeX entry to BibEntry dataclass."""
        try:
            return BibEntry(
                key=entry.get("ID", ""),
                entry_type=entry.get("ENTRYTYPE", "").lower(),
                authors=self._clean_authors(entry.get("author", "Unknown")),
                year=self._extract_year(entry),
                title=self._clean_title(entry.get("title", "Unknown Title")),
                journal=self._escape_latex_special_chars(
                    entry.get("journaltitle") or entry.get("journal")
                ),
                volume=entry.get("volume"),
                number=entry.get("number"),
                pages=entry.get("pages"),
                publisher=self._escape_latex_special_chars(
                    entry.get("publisher")
                ),
                booktitle=self._escape_latex_special_chars(
                    entry.get("booktitle")
                ),
                series=self._escape_latex_special_chars(entry.get("series")),
                url=entry.get("url"),
                doi=entry.get("doi"),
                urldate=entry.get("urldate"),
                note=self._escape_latex_special_chars(entry.get("note")),
                institution=self._escape_latex_special_chars(
                    entry.get("institution")
                ),
                raw_entry=entry,
            )
        except Exception as e:
            print(
                f"Warning: Skipping malformed entry {entry.get('ID', 'unknown')}: {e}"
            )
            return None

    def _clean_authors(self, authors: str) -> str:
        """Clean and format author names."""
        if not authors or authors.lower() in ["unknown", ""]:
            return "Unknown"

        # Remove BibTeX formatting using string methods
        # Replace {text} with text
        result = []
        i = 0
        while i < len(authors):
            if authors[i] == "{":
                # Find matching }
                j = i + 1
                brace_count = 1
                while j < len(authors) and brace_count > 0:
                    if authors[j] == "{":
                        brace_count += 1
                    elif authors[j] == "}":
                        brace_count -= 1
                    j += 1
                if brace_count == 0:
                    # Add the content without braces
                    result.append(authors[i + 1 : j - 1])
                    i = j
                else:
                    result.append(authors[i])
                    i += 1
            else:
                result.append(authors[i])
                i += 1
        authors = "".join(result)

        # Handle special corporate authors
        if authors.startswith("{") and authors.endswith("}"):
            return authors[1:-1]

        # Simple cleanup for common issues
        authors = authors.replace(" and others", " et al.")

        # Escape ampersands for LaTeX
        authors = authors.replace("&", "\\&")

        return authors

    def _extract_year(self, entry: dict) -> str:
        """Extract year from entry."""
        # Try year field first
        if "year" in entry and entry["year"]:
            year_str = str(entry["year"])
            # Find 4 consecutive digits
            for i in range(len(year_str) - 3):
                if all(year_str[i + j].isdigit() for j in range(4)):
                    return year_str[i : i + 4]

        # Try date field
        if "date" in entry and entry["date"]:
            date_str = str(entry["date"])
            # Find 4 consecutive digits
            for i in range(len(date_str) - 3):
                if all(date_str[i + j].isdigit() for j in range(4)):
                    return date_str[i : i + 4]

        # Try urldate as last resort
        if "urldate" in entry and entry["urldate"]:
            urldate_str = str(entry["urldate"])
            # Find 4 consecutive digits
            for i in range(len(urldate_str) - 3):
                if all(urldate_str[i + j].isdigit() for j in range(4)):
                    return urldate_str[i : i + 4]

        return "2024"  # Default year

    def _clean_title(self, title: str) -> str:
        """Clean and format title."""
        # Remove excessive BibTeX formatting but keep important formatting
        # Remove double braces {{text}} -> text
        while "{{" in title and "}}" in title:
            start = title.find("{{")
            end = title.find("}}", start)
            if start != -1 and end != -1:
                title = (
                    title[:start] + title[start + 2 : end] + title[end + 2 :]
                )
            else:
                break

        # Remove any remaining double braces
        title = title.replace("{{", "").replace("}}", "")

        # Escape ampersands for LaTeX
        title = title.replace("&", "\\&")

        return title.strip()

    def _escape_latex_special_chars(self, text: str) -> str:
        """Escape special LaTeX characters in text."""
        if not text:
            return text

        # Escape ampersands (but not if already escaped)
        # Use string methods to find unescaped &
        result = []
        i = 0
        while i < len(text):
            if text[i] == "&":
                # Check if already escaped (preceded by \)
                if i > 0 and text[i - 1] == "\\":
                    result.append(text[i])
                else:
                    result.append("\\&")
            else:
                result.append(text[i])
            i += 1
        text = "".join(result)

        return text

    def _get_sort_key(self, authors: str) -> str:
        """Get sorting key from authors string."""
        # Extract first author's surname for sorting
        if not authors or authors == "Unknown":
            return "zzz"  # Sort unknowns to end

        # Handle single corporate authors in braces
        if authors.startswith("{") and authors.endswith("}"):
            return authors[1:4].lower()  # Sort by first few characters

        # Extract first author's surname (before comma or first word)
        first_author = authors.split(" and ")[0].strip()
        if "," in first_author:
            surname = first_author.split(",")[0].strip()
        else:
            # Assume last word is surname
            words = first_author.split()
            surname = words[-1] if words else "unknown"

        return surname.lower()

    def _get_primary_url(self, entry: BibEntry) -> str | None:
        """Get the primary URL for the entry (DOI preferred, then URL)."""
        if entry.doi:
            # Clean DOI and create URL
            doi = entry.doi.replace("https://doi.org/", "").replace(
                "http://doi.org/", ""
            )
            return f"https://doi.org/{doi}"
        elif entry.url:
            return entry.url
        return None

    def _get_arxiv_id(self, entry: BibEntry) -> str | None:
        """Extract arXiv ID from entry fields or URL."""
        # First check if we have arXiv ID from the raw entry parsing
        arxiv_id = None
        raw_entry = entry.raw_entry

        # Check common arXiv ID fields
        if "eprint" in raw_entry:
            arxiv_id = raw_entry["eprint"]
        elif "arxiv" in raw_entry:
            arxiv_id = raw_entry["arxiv"]

        # Check journal field for arXiv
        if not arxiv_id and entry.journal and "arxiv" in entry.journal.lower():
            # Look for arxiv: followed by digits.digits pattern
            arxiv_pos = entry.journal.lower().find("arxiv:")
            if arxiv_pos != -1:
                start = arxiv_pos + 6  # len("arxiv:")
                # Skip whitespace
                while (
                    start < len(entry.journal)
                    and entry.journal[start].isspace()
                ):
                    start += 1

                # Extract digits.digits pattern
                end = start
                has_dot = False
                while end < len(entry.journal):
                    if entry.journal[end].isdigit():
                        end += 1
                    elif entry.journal[end] == "." and not has_dot:
                        has_dot = True
                        end += 1
                    else:
                        break

                if has_dot and end > start:
                    arxiv_id = entry.journal[start:end]

        # Check URL for arXiv
        if not arxiv_id and entry.url and "arxiv.org" in entry.url:
            # Extract from URL like https://arxiv.org/abs/2403.20309
            abs_pos = entry.url.find("arxiv.org/abs/")
            if abs_pos != -1:
                start = abs_pos + 14  # len("arxiv.org/abs/")
                # Extract digits.digits pattern
                end = start
                has_dot = False
                while end < len(entry.url):
                    if entry.url[end].isdigit():
                        end += 1
                    elif entry.url[end] == "." and not has_dot:
                        has_dot = True
                        end += 1
                    else:
                        break

                if has_dot and end > start:
                    arxiv_id = entry.url[start:end]

        return arxiv_id

    def _format_venue_info(self, entry: BibEntry) -> str:
        """Format venue information (journal, conference, etc.) in italics."""
        # Check if this is an arXiv paper first
        arxiv_id = self._get_arxiv_id(entry)
        if arxiv_id:
            return f"{{\\em arXiv:{arxiv_id}}}"

        if entry.entry_type == "article":
            if entry.journal:
                venue = entry.journal
                # Add volume/number if available
                if entry.volume:
                    venue += f" {entry.volume}"
                    if entry.number:
                        venue += f"({entry.number})"
                    if entry.pages:
                        venue += f":{entry.pages}"
                elif entry.pages:
                    venue += f" {entry.pages}"
                return f"{{\\em {venue}}}"
            else:
                return "{\\em Online resource}"

        elif entry.entry_type in ["inproceedings", "incollection"]:
            if entry.booktitle:
                return f"{{\\em {entry.booktitle}}}"
            elif entry.series:
                return f"{{\\em {entry.series}}}"
            else:
                return "{\\em Conference proceedings}"

        elif entry.entry_type == "book":
            if entry.publisher:
                return f"{entry.publisher}"
            else:
                return "{\\em Book}"

        elif entry.entry_type in ["techreport", "misc"]:
            if entry.institution:
                return f"{entry.institution}"
            elif entry.url and "github.com" in entry.url:
                return "{\\em GitHub repository}"
            elif entry.url and any(
                blog in entry.url.lower() for blog in ["blog", "medium"]
            ):
                return "{\\em Blog post}"
            else:
                return "{\\em Technical report}"

        else:
            return "{\\em Publication}"

    def _format_access_info(self, entry: BibEntry) -> str:
        """Format access information for web resources."""
        if not entry.url or entry.doi:
            return ""  # No access info needed if no URL or if DOI is primary

        # Add access date for non-academic resources
        is_academic = any(
            domain in entry.url
            for domain in [
                "doi.org",
                "arxiv.org",
                "ieee.org",
                "acm.org",
                "springer.com",
                "elsevier.com",
            ]
        )

        if not is_academic and entry.urldate:
            # Parse urldate using string methods
            # Look for YYYY-MM-DD pattern
            urldate = entry.urldate
            if len(urldate) >= 10 and urldate[4] == "-" and urldate[7] == "-":
                year_str = urldate[0:4]
                month_str = urldate[5:7]
                day_str = urldate[8:10]

                # Validate they are all digits
                if (
                    year_str.isdigit()
                    and month_str.isdigit()
                    and day_str.isdigit()
                ):
                    year = year_str
                    month = int(month_str)
                    day = day_str

                    months = [
                        "",
                        "Jan",
                        "Feb",
                        "Mar",
                        "Apr",
                        "May",
                        "Jun",
                        "Jul",
                        "Aug",
                        "Sep",
                        "Oct",
                        "Nov",
                        "Dec",
                    ]
                    month_name = months[month] if month <= 12 else month_str
                    return f" (accessed {month_name} {day}, {year})"

        return ""

    def _format_natbib_label(self, entry: BibEntry) -> str:
        """Format the natbib label for authoryear citations."""
        # For authoryear citations, natbib needs the format: [AuthorList(Year)]
        # This tells natbib how to format \citep{key} and \citet{key}

        # Extract first author surname for short citations
        first_author = entry.authors.split(" and ")[0].strip()
        if "," in first_author:
            # Format: "Surname, First" -> "Surname"
            surname = first_author.split(",")[0].strip()
        else:
            # Format: "First Surname" -> "Surname" (assume last word is surname)
            words = first_author.split()
            surname = words[-1] if words else first_author

        # Format based on number of authors
        if " and " not in entry.authors:
            # Single author: "Surname(Year)"
            return f"{surname}({entry.year})"
        elif entry.authors.count(" and ") == 1:
            # Two authors: "Surname1 and Surname2(Year)"
            second_author = entry.authors.split(" and ")[1].strip()
            if "," in second_author:
                second_surname = second_author.split(",")[0].strip()
            else:
                words = second_author.split()
                second_surname = words[-1] if words else second_author
            return f"{surname} and {second_surname}({entry.year})"
        else:
            # Multiple authors: "Surname et al.(Year)"
            return f"{surname} et al.({entry.year})"

    def _format_entry(self, entry: BibEntry) -> str:
        """Format a single bibliography entry."""
        # Get primary URL for hyperlink
        link_url = self._get_primary_url(entry)

        # Format author-year with hyperlink
        if link_url:
            author_year = (
                f"\\href{{{link_url}}}{{{entry.authors} ({entry.year})}}"
            )
        else:
            author_year = f"{entry.authors} ({entry.year})"

        # Format venue information
        venue_info = self._format_venue_info(entry)

        # Format access information
        access_info = self._format_access_info(entry)

        # Combine all parts
        parts = [author_year, entry.title, venue_info]
        entry_text = " ".join(filter(None, parts))

        # Add access info at the end
        if access_info:
            entry_text += access_info

        # Ensure it ends with a period
        if not entry_text.endswith("."):
            entry_text += "."

        # Format natbib label for authoryear citations
        natbib_label = self._format_natbib_label(entry)

        return f"\\bibitem[{natbib_label}]{{{entry.key}}} {entry_text}"

    def generate_hardcoded_bibliography(self) -> str:
        """Generate the complete hardcoded bibliography."""
        if not self.entries:
            self.load_bibliography()

        print("Generating hardcoded bibliography...")

        # Generate bibliography header
        bibliography_lines = [
            "% Hardcoded bibliography with authoryear hyperlinks",
            "% Generated automatically - do not edit manually",
            "",
            "\\begin{thebibliography}{999}",
            "",
        ]

        # Add each entry
        for entry in self.entries:
            formatted_entry = self._format_entry(entry)
            bibliography_lines.append(formatted_entry)
            bibliography_lines.append("")  # Empty line between entries

        # Add bibliography footer
        bibliography_lines.extend(["\\end{thebibliography}", ""])

        print(f"Generated {len(self.entries)} bibliography entries")
        return "\n".join(bibliography_lines)

    def save_hardcoded_bibliography(self, output_file: Path):
        """Save the hardcoded bibliography to a file."""
        bibliography_content = self.generate_hardcoded_bibliography()

        # Create backup if file exists
        if output_file.exists():
            backup_file = output_file.with_suffix(".tex.backup")
            print(f"Creating backup: {backup_file}")
            backup_file.write_text(
                output_file.read_text(encoding="utf-8"), encoding="utf-8"
            )

        # Save new content
        output_file.write_text(bibliography_content, encoding="utf-8")
        print(f"Hardcoded bibliography saved to: {output_file}")

        return bibliography_content


def main():
    """Main function."""
    # Default paths
    bib_file = Path("uadReview/references.bib")
    output_file = Path("uadReview/bibliography_hardcoded.tex")

    # Allow command line override
    if len(sys.argv) > 1:
        bib_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])

    # Check input file exists
    if not bib_file.exists():
        print(f"Error: Bibliography file not found: {bib_file}")
        sys.exit(1)

    # Generate hardcoded bibliography
    generator = HardcodedBibliographyGenerator(bib_file)
    generator.save_hardcoded_bibliography(output_file)

    print("\nHardcoded bibliography with authoryear hyperlinks created!")
    print(f"Input:  {bib_file}")
    print(f"Output: {output_file}")
    print("\nTo use in your LaTeX document:")
    print("1. Remove or comment out \\bibliography{references}")
    print("2. Remove or comment out \\bibliographystyle{spbasic_pt}")
    print(
        f"3. Add \\input{{{output_file.stem}}} where you want the bibliography"
    )
    print("4. Make sure natbib package is still loaded for \\citep{} commands")


if __name__ == "__main__":
    main()
