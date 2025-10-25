#!/usr/bin/env python3
"""
Convert numbered citations in manual LaTeX bibliography to author-year format.

This script transforms \bibitem entries from numbered format to author-year format
while preserving hyperlinks and handling complex edge cases.

Author: Deep Biblio Tools
License: MIT
"""

import argparse
import logging

# import re  # Banned - using string methods instead
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class BibEntry:
    """Represents a bibliography entry with parsed components."""

    key: str
    original_text: str
    author_part: str
    year: str
    formatted_label: str
    confidence: float
    needs_review: bool
    review_reason: str = ""


class AuthorYearConverter:
    """Convert manual bibliography entries to author-year format."""

    def __init__(
        self, interactive: bool = False, confidence_threshold: float = 0.8
    ):
        """Initialize the converter.

        Args:
            interactive: Whether to prompt for user input on ambiguous cases
            confidence_threshold: Minimum confidence for automatic conversion
        """
        self.interactive = interactive
        self.confidence_threshold = confidence_threshold
        self.entries_processed = 0
        self.entries_converted = 0
        self.entries_failed = 0
        self.entries_needing_review = []

        # Surname prefixes that should be included with the surname
        self.surname_prefixes = [
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
            "van der",
            "von der",
            "de la",
            "de los",
            "de las",
        ]

        # Common initials
        self.initials = [
            f"{letter}." for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        ]

    def detect_width_parameter(self, content: str) -> tuple[str, int, str]:
        """Detect the width parameter and count entries.

        Args:
            content: The LaTeX content

        Returns:
            Tuple of (current_width, entry_count, suggested_width)
        """
        # Find bibliography environment
        begin_marker = "\\begin{thebibliography}{"
        start_pos = content.find(begin_marker)
        if start_pos == -1:
            return ("unknown", 0, "99")

        # Find the closing brace
        width_start = start_pos + len(begin_marker)
        width_end = content.find("}", width_start)
        if width_end == -1:
            return ("unknown", 0, "99")

        current_width = content[width_start:width_end]

        # Count bibitem entries using string methods
        entry_count = 0
        pos = 0
        while True:
            pos = content.find("\\bibitem", pos)
            if pos == -1:
                break
            # Check if it's followed by optional [...] and then {key}
            i = pos + len("\\bibitem")
            # Skip optional [...]
            if i < len(content) and content[i] == "[":
                # Find matching ]
                bracket_count = 1
                i += 1
                while i < len(content) and bracket_count > 0:
                    if content[i] == "[":
                        bracket_count += 1
                    elif content[i] == "]":
                        bracket_count -= 1
                    i += 1
            # Now should have {
            if i < len(content) and content[i] == "{":
                # Find matching }
                brace_count = 1
                i += 1
                while i < len(content) and brace_count > 0:
                    if content[i] == "{":
                        brace_count += 1
                    elif content[i] == "}":
                        brace_count -= 1
                    i += 1
                if brace_count == 0:
                    entry_count += 1
            pos += 1

        # Suggest appropriate width
        if entry_count <= 9:
            suggested_width = "9"
        elif entry_count <= 99:
            suggested_width = "99"
        elif entry_count <= 999:
            suggested_width = "999"
        else:
            suggested_width = "9999"

        return (current_width, entry_count, suggested_width)

    def extract_author_year(self, text: str) -> tuple[str, str, float]:
        """Extract author names and year from bibliography text.

        Args:
            text: The text after \\href{...}{...} or from the start if no href

        Returns:
            Tuple of (author_names, year, confidence)
        """
        confidence = 1.0

        # Remove leading/trailing whitespace
        text = text.strip()

        # Pattern 1: Look for clear author (year) pattern
        # This handles most standard cases
        # Find the last occurrence of (year) pattern
        paren_pos = text.rfind("(")
        if paren_pos != -1:
            close_paren = text.find(")", paren_pos)
            if close_paren != -1:
                potential_year = text[paren_pos + 1 : close_paren].strip()
                # Check if it's a valid year
                if potential_year.isdigit() and len(potential_year) == 4:
                    authors = text[:paren_pos].strip()
                    year = potential_year
                    return (authors, year, confidence)
                elif "-" in potential_year or "/" in potential_year:
                    # Handle year ranges
                    parts = potential_year.replace("/", "-").split("-")
                    if parts and parts[0].isdigit() and len(parts[0]) == 4:
                        authors = text[:paren_pos].strip()
                        year = parts[0]
                        return (authors, year, confidence)
                elif potential_year.lower() in ["forthcoming", "in press"]:
                    authors = text[:paren_pos].strip()
                    year = potential_year
                    confidence *= 0.9
                    return (authors, year, confidence)

        # Pattern 2: No clear parentheses, try to find year at the end
        # Look for 4-digit years
        years = []
        i = 0
        while i < len(text) - 3:
            if text[i].isdigit():
                # Check if we have 4 consecutive digits
                if i + 3 < len(text) and all(
                    text[i + j].isdigit() for j in range(4)
                ):
                    # Check word boundaries
                    if (i == 0 or not text[i - 1].isalnum()) and (
                        i + 4 >= len(text) or not text[i + 4].isalnum()
                    ):
                        years.append(text[i : i + 4])
                        i += 4
                        continue
            i += 1

        if years:
            # Take the first year found
            year = years[0]
            # Extract everything before the year as authors
            year_pos = text.find(year)
            authors = text[:year_pos].strip()
            confidence *= 0.7  # Lower confidence
            return (authors, year, confidence)

        # Pattern 3: No year found
        return (text, "", 0.3)

    def format_author_label(self, authors: str, year: str) -> str:
        """Format the author-year label for \bibitem.

        Args:
            authors: The author string
            year: The publication year

        Returns:
            Formatted label like "Smith et al.(2025)"
        """
        # Handle empty authors
        if not authors:
            return f"Anonymous({year})" if year else "Unknown"

        # Handle URL-like authors
        if authors.startswith("http"):
            # Extract domain name using string methods
            if authors.startswith("https://"):
                domain_part = authors[8:]  # Skip "https://"
            elif authors.startswith("http://"):
                domain_part = authors[7:]  # Skip "http://"
            else:
                domain_part = authors

            # Skip www. if present
            if domain_part.startswith("www."):
                domain_part = domain_part[4:]

            # Extract domain (up to first /)
            slash_pos = domain_part.find("/")
            if slash_pos != -1:
                authors = domain_part[:slash_pos]
            else:
                authors = domain_part

        # Check if already formatted with "et al."
        if " et al." in authors:
            # Just clean it up
            authors = authors.replace(" et al.", "")
            author_list = [authors.strip()]
            use_et_al = True
        else:
            # Split authors by "and" or comma
            # But be careful of organizations with "and" in the name
            if " and " in authors:
                # Check for organization patterns
                org_keywords = [
                    "Inc",
                    "Corp",
                    "Corporation",
                    "Company",
                    "Ltd",
                    "LLC",
                    "LLP",
                    "Group",
                    "Society",
                    "Foundation",
                    "Association",
                    "Institute",
                    "Department",
                    "Ministry",
                    "Agency",
                    "Board",
                    "Commission",
                    "Committee",
                    "Council",
                ]

                company_prefixes = [
                    "Procter",
                    "Johnson",
                    "Black",
                    "Young",
                    "Ernst",
                    "Deloitte",
                    "McKinsey",
                    "Boston",
                    "Bain",
                ]

                is_org = False
                authors_lower = authors.lower()

                # Check for organization keywords
                for keyword in org_keywords:
                    if keyword.lower() in authors_lower:
                        # Check word boundaries
                        pos = authors_lower.find(keyword.lower())
                        if pos != -1:
                            # Check if it's a whole word
                            if (
                                pos == 0 or not authors_lower[pos - 1].isalnum()
                            ) and (
                                pos + len(keyword) >= len(authors_lower)
                                or not authors_lower[
                                    pos + len(keyword)
                                ].isalnum()
                            ):
                                is_org = True
                                break

                # Check for company names with "and" or "&"
                if not is_org:
                    for prefix in company_prefixes:
                        if prefix.lower() in authors_lower:
                            # Check if followed by " and" or " &"
                            pos = authors_lower.find(prefix.lower())
                            if pos != -1:
                                after_prefix = authors_lower[
                                    pos + len(prefix) :
                                ]
                                if after_prefix.startswith(
                                    " and"
                                ) or after_prefix.startswith(" &"):
                                    is_org = True
                                    break

                if is_org:
                    # Treat as single organization
                    author_list = [authors]
                else:
                    # Split by "and"
                    author_list = [a.strip() for a in authors.split(" and ")]
            elif "," in authors:
                # Could be "Last, First" or multiple authors
                # Simple heuristic: if only one comma, it's probably "Last, First"
                comma_count = authors.count(",")
                if comma_count == 1:
                    author_list = [authors]
                else:
                    author_list = [a.strip() for a in authors.split(",")]
            else:
                # Single author
                author_list = [authors]

            use_et_al = len(author_list) > 2

        # Extract surnames
        formatted_authors = []
        for author in author_list[:1] if use_et_al else author_list[:2]:
            surname = self.extract_surname(author)
            formatted_authors.append(surname)

        # Format the label
        if use_et_al:
            label = f"{formatted_authors[0]} et al."
        elif len(formatted_authors) == 2:
            label = f"{formatted_authors[0]} and {formatted_authors[1]}"
        else:
            label = formatted_authors[0]

        # Add year
        return f"{label}({year})" if year else label

    def extract_surname(self, author: str) -> str:
        """Extract surname from an author name.

        Args:
            author: Full author name

        Returns:
            The surname
        """
        author = author.strip()

        # Handle special LaTeX characters
        # Replace LaTeX accents using string methods
        i = 0
        result = []
        while i < len(author):
            if i < len(author) - 3 and author[i] == "\\":
                # Check for accent commands
                if i + 1 < len(author) and author[i + 1] in "'`^~\"":
                    # Look for {letter}
                    if i + 2 < len(author) and author[i + 2] == "{":
                        end = author.find("}", i + 3)
                        if end != -1 and end == i + 4:  # Single character
                            result.append(author[i + 3])
                            i = end + 1
                            continue
                result.append(author[i])
                i += 1
            else:
                result.append(author[i])
                i += 1

        author = "".join(result)
        # Remove math mode using string methods
        i = 0
        result = []
        while i < len(author):
            if author[i] == "$":
                # Skip to next $
                end = author.find("$", i + 1)
                if end != -1:
                    i = end + 1
                else:
                    result.append(author[i])
                    i += 1
            else:
                result.append(author[i])
                i += 1

        author = "".join(result)

        # Check for comma (Last, First format)
        if "," in author:
            return author.split(",")[0].strip()

        # Split into parts
        parts = author.split()

        if len(parts) == 0:
            return author
        elif len(parts) == 1:
            return parts[0]

        # Check for initials at the beginning
        if parts[0] in self.initials:
            # E. Smith format
            return parts[-1]

        # Check for surname prefixes
        for i in range(len(parts) - 1):
            # Check two-word prefixes first
            if i < len(parts) - 2:
                two_word = f"{parts[i].lower()} {parts[i + 1].lower()}"
                if two_word in self.surname_prefixes:
                    return " ".join(parts[i:])

            # Check single-word prefixes
            if parts[i].lower() in self.surname_prefixes:
                return " ".join(parts[i:])

        # Default: last part is surname
        return parts[-1]

    def parse_bibitem(self, entry: str) -> BibEntry | None:
        """Parse a single \bibitem entry.

        Args:
            entry: The complete \bibitem entry (possibly multiline)

        Returns:
            Parsed BibEntry or None if parsing fails
        """
        # Extract the key using string methods
        bibitem_pos = entry.find("\\bibitem")
        if bibitem_pos == -1:
            logger.warning("Could not find \\bibitem in entry")
            return None

        i = bibitem_pos + len("\\bibitem")

        # Skip optional [...]
        if i < len(entry) and entry[i] == "[":
            bracket_count = 1
            i += 1
            while i < len(entry) and bracket_count > 0:
                if entry[i] == "[":
                    bracket_count += 1
                elif entry[i] == "]":
                    bracket_count -= 1
                i += 1

        # Now should have {
        if i >= len(entry) or entry[i] != "{":
            logger.warning("Could not find { after \\bibitem")
            return None

        # Find the key
        key_start = i + 1
        brace_count = 1
        i += 1
        while i < len(entry) and brace_count > 0:
            if entry[i] == "{":
                brace_count += 1
            elif entry[i] == "}":
                brace_count -= 1
            i += 1

        if brace_count != 0:
            logger.warning("Could not find matching } for key")
            return None

        key = entry[key_start : i - 1]
        key_match_end = i

        # Check if already has author-year format
        if "\\bibitem[" in entry and entry.find("\\bibitem[") < entry.find(
            "{key}"
        ):
            logger.info(f"Entry {key} already has author-year format")
            return None

        # Extract content after \bibitem{key}
        content_start = key_match_end
        content = entry[content_start:].strip()

        # Look for \href{url}{text} pattern using string methods
        href_found = False
        if content.startswith("\\href{"):
            # Find the URL part
            url_start = 6  # len("\\href{")
            brace_count = 1
            i = url_start
            while i < len(content) and brace_count > 0:
                if content[i] == "{":
                    brace_count += 1
                elif content[i] == "}":
                    brace_count -= 1
                i += 1

            if brace_count == 0 and i < len(content) and content[i] == "{":
                # Found the text part
                text_start = i + 1
                brace_count = 1
                i = text_start
                while i < len(content) and brace_count > 0:
                    if content[i] == "{":
                        brace_count += 1
                    elif content[i] == "}":
                        brace_count -= 1
                    i += 1

                if brace_count == 0:
                    href_text = content[text_start : i - 1]
                    href_found = True
                    # Try to extract author and year from href text
                    authors, year, confidence = self.extract_author_year(
                        href_text
                    )

        if not href_found:
            # No href, try to parse the whole content
            authors, year, confidence = self.extract_author_year(content)

        # Format the label
        label = self.format_author_label(authors, year)

        # Determine if needs review
        needs_review = confidence < self.confidence_threshold
        review_reason = ""

        if not year:
            needs_review = True
            review_reason = "No year found"
        elif not authors or authors == "Unknown":
            needs_review = True
            review_reason = "No authors found"
        elif confidence < self.confidence_threshold:
            needs_review = True
            review_reason = f"Low confidence ({confidence:.2f})"

        return BibEntry(
            key=key,
            original_text=entry,
            author_part=authors,
            year=year,
            formatted_label=label,
            confidence=confidence,
            needs_review=needs_review,
            review_reason=review_reason,
        )

    def convert_entry(self, entry: str) -> str:
        """Convert a single bibliography entry.

        Args:
            entry: The complete \bibitem entry

        Returns:
            Converted entry
        """
        parsed = self.parse_bibitem(entry)

        if parsed is None:
            return entry

        self.entries_processed += 1

        if parsed.needs_review:
            self.entries_needing_review.append(parsed)

            if self.interactive:
                # Prompt user
                print(f"\nEntry needs review: {parsed.key}")
                print(f"Reason: {parsed.review_reason}")
                print(f"Detected: {parsed.formatted_label}")
                response = input("Accept? (y/n/skip): ").lower()

                if response == "n":
                    new_label = input("Enter correct label: ")
                    parsed.formatted_label = new_label
                elif response == "skip":
                    self.entries_failed += 1
                    return entry

        # Replace \bibitem{key} with \bibitem[label]{key}
        # Find the exact position to replace
        search_str = f"\\bibitem{{{parsed.key}}}"
        pos = entry.find(search_str)
        if pos != -1:
            replacement = f"\\bibitem[{parsed.formatted_label}]{{{parsed.key}}}"
            converted = (
                entry[:pos] + replacement + entry[pos + len(search_str) :]
            )
        else:
            converted = entry

        # Add review comment if needed
        if parsed.needs_review and not self.interactive:
            converted = f"% NEEDS_REVIEW: {parsed.review_reason}\n{converted}"

        self.entries_converted += 1
        return converted

    def ensure_natbib_setup(self, content: str) -> str:
        """Ensure the document has proper natbib configuration.

        Args:
            content: The LaTeX document content

        Returns:
            Updated content with natbib properly configured
        """
        # Check if natbib is already loaded using string methods
        has_natbib = False
        usepackage_pos = 0
        while True:
            usepackage_pos = content.find("\\usepackage", usepackage_pos)
            if usepackage_pos == -1:
                break

            i = usepackage_pos + len("\\usepackage")

            # Skip optional [...]
            if i < len(content) and content[i] == "[":
                bracket_count = 1
                i += 1
                while i < len(content) and bracket_count > 0:
                    if content[i] == "[":
                        bracket_count += 1
                    elif content[i] == "]":
                        bracket_count -= 1
                    i += 1

            # Check for {natbib}
            if i < len(content) and content[i:].startswith("{natbib}"):
                has_natbib = True
                break

            usepackage_pos += 1

        if not has_natbib:
            # Add natbib package after documentclass using string methods
            doc_class_pos = content.find("\\documentclass")
            if doc_class_pos != -1:
                # Find the end of documentclass command
                i = doc_class_pos + len("\\documentclass")

                # Skip optional [...]
                if i < len(content) and content[i] == "[":
                    bracket_count = 1
                    i += 1
                    while i < len(content) and bracket_count > 0:
                        if content[i] == "[":
                            bracket_count += 1
                        elif content[i] == "]":
                            bracket_count -= 1
                        i += 1

                # Skip {class}
                if i < len(content) and content[i] == "{":
                    brace_count = 1
                    i += 1
                    while i < len(content) and brace_count > 0:
                        if content[i] == "{":
                            brace_count += 1
                        elif content[i] == "}":
                            brace_count -= 1
                        i += 1

                insert_pos = i
                # Insert natbib with authoryear option
                natbib_line = "\n\\usepackage[authoryear,round]{natbib}\n"
                content = (
                    content[:insert_pos] + natbib_line + content[insert_pos:]
                )
                logger.info("Added natbib package with authoryear option")
        else:
            # Check if natbib has authoryear option
            # Find the natbib usepackage line
            natbib_pos = content.find("\\usepackage")

            while natbib_pos != -1:
                # Check if this is the natbib package
                i = natbib_pos + len("\\usepackage")

                # Check for options
                options_start = -1
                options_end = -1
                if i < len(content) and content[i] == "[":
                    options_start = i + 1
                    bracket_count = 1
                    i += 1
                    while i < len(content) and bracket_count > 0:
                        if content[i] == "[":
                            bracket_count += 1
                        elif content[i] == "]":
                            bracket_count -= 1
                        i += 1
                    options_end = i - 1

                # Check if this is natbib
                if i < len(content) and content[i:].startswith("{natbib}"):
                    if options_start != -1:
                        # Has options
                        options = content[options_start:options_end]
                        if "authoryear" not in options:
                            # Add authoryear option
                            if options.strip():
                                new_options = f"authoryear,round,{options}"
                            else:
                                new_options = "authoryear,round"

                            # Replace the whole usepackage line
                            old_line = content[
                                natbib_pos : i + 8
                            ]  # 8 = len("{natbib}")
                            new_line = f"\\usepackage[{new_options}]{{natbib}}"
                            content = (
                                content[:natbib_pos]
                                + new_line
                                + content[i + 8 :]
                            )
                            logger.info(
                                "Updated natbib options to include authoryear"
                            )
                    else:
                        # No options, add them
                        old_line = "\\usepackage{natbib}"
                        new_line = "\\usepackage[authoryear,round]{natbib}"
                        content = (
                            content[:natbib_pos]
                            + new_line
                            + content[natbib_pos + len(old_line) :]
                        )
                        logger.info("Added authoryear option to natbib")
                    break

                natbib_pos = content.find("\\usepackage", natbib_pos + 1)

        # Also check for conflicting packages using string methods
        cite_pos = 0
        while True:
            cite_pos = content.find("\\usepackage", cite_pos)
            if cite_pos == -1:
                break

            i = cite_pos + len("\\usepackage")

            # Skip optional [...]
            if i < len(content) and content[i] == "[":
                bracket_count = 1
                i += 1
                while i < len(content) and bracket_count > 0:
                    if content[i] == "[":
                        bracket_count += 1
                    elif content[i] == "]":
                        bracket_count -= 1
                    i += 1

            # Check for {cite}
            if i < len(content) and content[i:].startswith("{cite}"):
                logger.warning(
                    "Found 'cite' package which conflicts with natbib. Consider removing it."
                )
                break

            cite_pos += 1

        return content

    def convert_file(
        self,
        input_path: Path,
        output_path: Path | None = None,
        fix_width: bool = False,
        in_place: bool = False,
        backup: bool = True,
        ensure_natbib: bool = True,
        sort_entries: bool = True,
    ) -> None:
        """Convert a LaTeX file.

        Args:
            input_path: Path to input file
            output_path: Path to output file (if None, use stdout)
            fix_width: Whether to fix the width parameter
            in_place: Whether to modify the input file
            backup: Whether to create a backup when modifying in-place
            ensure_natbib: Whether to ensure natbib package is properly configured
            sort_entries: Whether to sort bibliography entries alphabetically
        """
        # Read input file
        try:
            content = input_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try with latin-1
            content = input_path.read_text(encoding="latin-1")

        # Detect width parameter
        current_width, entry_count, suggested_width = (
            self.detect_width_parameter(content)
        )

        if current_width != suggested_width:
            logger.warning(
                f"Width parameter mismatch: current={current_width}, "
                f"suggested={suggested_width} for {entry_count} entries"
            )

        # Fix width if requested
        if fix_width and current_width != suggested_width:
            # Find and replace width parameter using string methods
            begin_marker = "\\begin{thebibliography}{"
            start_pos = content.find(begin_marker)
            if start_pos != -1:
                width_start = start_pos + len(begin_marker)
                width_end = content.find("}", width_start)
                if width_end != -1:
                    content = (
                        content[:width_start]
                        + suggested_width
                        + content[width_end:]
                    )
                    logger.info(
                        f"Fixed width parameter: {current_width} -> {suggested_width}"
                    )

        # Find bibliography environment using string methods
        begin_bib = "\\begin{thebibliography}"
        end_bib = "\\end{thebibliography}"

        begin_pos = content.find(begin_bib)
        if begin_pos == -1:
            logger.error("No bibliography environment found")
            return

        end_pos = content.find(end_bib, begin_pos)
        if end_pos == -1:
            logger.error("No \\end{thebibliography} found")
            return

        # Include the end tag
        end_pos += len(end_bib)
        bib_content = content[begin_pos:end_pos]

        # Split into entries
        # This is tricky because entries can be multiline
        entries = []
        current_entry = []

        in_entry = False
        for line in bib_content.split("\n"):
            line_stripped = line.strip()
            if line_stripped.startswith("\\bibitem"):
                if current_entry:
                    entries.append("\n".join(current_entry))
                current_entry = [line]
                in_entry = True
            elif line_stripped.startswith(
                "\\begin{thebibliography}"
            ) or line_stripped.startswith("\\end{thebibliography}"):
                if current_entry:
                    entries.append("\n".join(current_entry))
                    current_entry = []
                entries.append(line)
                in_entry = False
            elif in_entry:
                current_entry.append(line)
            else:
                # Lines outside entries (e.g., empty lines before first \bibitem)
                if not entries and not current_entry:
                    # This handles content before the first entry
                    entries.append(line)

        # Don't forget the last entry
        if current_entry:
            entries.append("\n".join(current_entry))

        # Separate bibliography commands from entries
        bib_start = []
        bib_entries = []
        bib_end = []

        for entry in entries:
            if "\\begin{thebibliography}" in entry:
                bib_start.append(entry)
            elif "\\end{thebibliography}" in entry:
                bib_end.append(entry)
            elif "\\bibitem" in entry:
                # Parse and convert the entry
                parsed = self.parse_bibitem(entry)
                if parsed:
                    converted = self.convert_entry(entry)
                    bib_entries.append((parsed, converted))
                else:
                    bib_entries.append((None, entry))
            else:
                # Other content (empty lines, comments)
                if bib_entries:
                    # Attach to last entry
                    parsed, converted = bib_entries[-1]
                    bib_entries[-1] = (parsed, converted + "\n" + entry)

        # Sort entries alphabetically by author surname if requested
        if sort_entries:

            def get_sort_key(entry_tuple):
                parsed, converted = entry_tuple
                if parsed and parsed.formatted_label:
                    # Extract the first author surname from the formatted label
                    # Format is "Surname(Year)" or "Surname and Other(Year)" or "Surname et al.(Year)"
                    label = parsed.formatted_label

                    # Remove the year part
                    if "(" in label:
                        label = label[: label.rfind("(")]

                    # Get the first author
                    if " and " in label:
                        first_author = label.split(" and ")[0]
                    elif " et al." in label:
                        first_author = label.replace(" et al.", "")
                    else:
                        first_author = label

                    # For sorting, use the surname (which is already extracted in the label)
                    return first_author.strip().lower()
                else:
                    # Fallback to the entry text
                    return converted.lower()

            bib_entries.sort(key=get_sort_key)
            logger.info("Sorted bibliography entries alphabetically")

        # Reconstruct bibliography
        converted_entries = []
        converted_entries.extend(bib_start)
        for parsed, converted in bib_entries:
            converted_entries.append(converted)
        converted_entries.extend(bib_end)

        new_bib = "\n".join(converted_entries)

        # Replace in content
        new_content = content.replace(bib_content, new_bib)

        # Ensure natbib is properly configured if requested
        if ensure_natbib:
            new_content = self.ensure_natbib_setup(new_content)

        # Handle output
        if in_place:
            if backup:
                backup_path = input_path.with_suffix(input_path.suffix + ".bak")
                shutil.copy2(input_path, backup_path)
                logger.info(f"Created backup: {backup_path}")

            input_path.write_text(new_content, encoding="utf-8")
            logger.info(f"Updated file in-place: {input_path}")
        elif output_path:
            output_path.write_text(new_content, encoding="utf-8")
            logger.info(f"Wrote converted file: {output_path}")
        else:
            # Output to stdout
            print(new_content)

        # Report statistics
        logger.info(
            f"Conversion complete: {self.entries_processed} processed, "
            f"{self.entries_converted} converted, {self.entries_failed} failed"
        )

        if self.entries_needing_review and not self.interactive:
            logger.warning(
                f"{len(self.entries_needing_review)} entries need manual review"
            )
            for entry in self.entries_needing_review:
                logger.warning(f"  {entry.key}: {entry.review_reason}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert manual LaTeX bibliography to author-year format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.tex -o output.tex
  %(prog)s input.tex --fix-width --in-place --backup
  %(prog)s input.tex --interactive --confidence-threshold 0.8
  %(prog)s input.tex --analyze-only
        """,
    )

    parser.add_argument(
        "input", type=Path, help="Input LaTeX file with manual bibliography"
    )

    parser.add_argument(
        "-o", "--output", type=Path, help="Output file (default: stdout)"
    )

    parser.add_argument(
        "--fix-width",
        action="store_true",
        help="Fix the width parameter of \\begin{thebibliography}",
    )

    parser.add_argument(
        "--in-place", action="store_true", help="Modify the input file in-place"
    )

    parser.add_argument(
        "--backup",
        action="store_true",
        default=True,
        help="Create backup when using --in-place (default: True)",
    )

    parser.add_argument(
        "--no-backup",
        action="store_false",
        dest="backup",
        help="Don't create backup when using --in-place",
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode for ambiguous entries",
    )

    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.8,
        help="Minimum confidence for automatic conversion (default: 0.8)",
    )

    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze, don't convert",
    )

    parser.add_argument(
        "--ensure-natbib",
        action="store_true",
        default=True,
        help="Ensure natbib package is configured for authoryear citations (default: True)",
    )

    parser.add_argument(
        "--no-ensure-natbib",
        action="store_false",
        dest="ensure_natbib",
        help="Don't modify natbib configuration",
    )

    parser.add_argument(
        "--sort-entries",
        action="store_true",
        default=True,
        help="Sort bibliography entries alphabetically by author surname (default: True)",
    )

    parser.add_argument(
        "--no-sort-entries",
        action="store_false",
        dest="sort_entries",
        help="Keep original bibliography entry order",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)

    if args.in_place and args.output:
        logger.error("Cannot use both --in-place and --output")
        sys.exit(1)

    if args.analyze_only:
        # Just analyze the file
        converter = AuthorYearConverter()
        content = args.input.read_text(encoding="utf-8")
        width_info = converter.detect_width_parameter(content)

        print(f"Width parameter analysis for {args.input}:")
        print(f"  Current width: {width_info[0]}")
        print(f"  Entry count: {width_info[1]}")
        print(f"  Suggested width: {width_info[2]}")

        if width_info[0] != width_info[2]:
            print(f"  WARNING: Width parameter should be {width_info[2]}")
    else:
        # Convert the file
        converter = AuthorYearConverter(
            interactive=args.interactive,
            confidence_threshold=args.confidence_threshold,
        )

        converter.convert_file(
            args.input,
            args.output,
            fix_width=args.fix_width,
            in_place=args.in_place,
            backup=args.backup,
            ensure_natbib=args.ensure_natbib,
            sort_entries=args.sort_entries,
        )


if __name__ == "__main__":
    main()
