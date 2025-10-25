"""Bibliography error correction and fixing."""

# import re  # Banned - using string methods instead

from .core import Bibliography, BibliographyEntry, BibliographyProcessor


class BibliographyFixer(BibliographyProcessor):
    """Fix common errors in bibliography entries.

    This class consolidates functionality from:
    - fix_bibliography.py
    - fix_bibliography_errors.py
    - fix_bibliography_ampersands.py
    - fix_incomplete_authors.py
    - fix_unknown_authors.py
    - fix_unknown_refs.py
    """

    def __init__(self):
        """Initialize fixer."""
        self.fixes_applied = 0

    def process(self, bibliography: Bibliography) -> int:
        """Process all entries in bibliography.

        Args:
            bibliography: Bibliography to process

        Returns:
            Number of fixes applied
        """
        self.fixes_applied = 0

        for entry in bibliography:
            self.process_entry(entry)

        return self.fixes_applied

    def process_entry(self, entry: BibliographyEntry) -> None:
        """Process a single entry.

        Args:
            entry: Entry to process
        """
        # Apply all fixes
        if self.fix_encoding(entry):
            self.fixes_applied += 1

        if self.fix_author_names(entry):
            self.fixes_applied += 1

        if self.fix_ampersands(entry):
            self.fixes_applied += 1

        if self.fix_quotes(entry):
            self.fixes_applied += 1

        if self.fix_special_characters(entry):
            self.fixes_applied += 1

        if self.fix_pages(entry):
            self.fixes_applied += 1

        if self.fix_doi_from_url(entry):
            self.fixes_applied += 1

        if self.fix_arxiv_format(entry):
            self.fixes_applied += 1

        if self.fix_duplicate_fields(entry):
            self.fixes_applied += 1

        if self.fix_title_capitalization(entry):
            self.fixes_applied += 1

    def fix_encoding(self, entry: BibliographyEntry) -> bool:
        """Fix encoding issues in entry fields.

        Args:
            entry: Bibliography entry

        Returns:
            True if fixes were applied
        """
        fixed = False

        # Common encoding fixes
        encoding_fixes = {
            "â€™": "'",
            "â€œ": '"',
            "â€": '"',
            "–": "--",  # en dash
            "—": "---",  # em dash
            "Ã¡": "á",
            "Ã©": "é",
            "Ã­": "í",
            "Ã³": "ó",
            "Ãº": "ú",
            "Ã±": "ñ",
            "Ã¼": "ü",
            "Ã¶": "ö",
        }

        for field_name, value in entry.fields.items():
            if not isinstance(value, str):
                continue

            original = value
            for bad, good in encoding_fixes.items():
                value = value.replace(bad, good)

            if value != original:
                entry.set_field(field_name, value)
                fixed = True

        return fixed

    def fix_author_names(self, entry: BibliographyEntry) -> bool:
        """Fix author name formatting.

        Args:
            entry: Bibliography entry

        Returns:
            True if fixes were applied
        """
        if not entry.has_field("author"):
            return False

        authors = entry.get_field("author")
        original = authors

        # Fix "et al." - should list all authors
        if "et al." in authors or "et al" in authors:
            # Remove et al. for now - ideally would look up full author list
            # Remove et al. without regex
            for variant in [" et al.", " et al", " et. al.", " et. al"]:
                if variant in authors:
                    authors = authors.replace(variant, "")
            authors = authors.strip()
            authors = authors.rstrip(" ,;")

        # Fix multiple "and" separators
        # Fix multiple "and" separators without regex
        while " and and " in authors:
            authors = authors.replace(" and and ", " and ")

        # Fix missing spaces after commas in author names
        # Fix missing spaces after commas without regex
        result = []
        for i, char in enumerate(authors):
            result.append(char)
            if (
                char == ","
                and i + 1 < len(authors)
                and authors[i + 1].isupper()
            ):
                result.append(" ")
        authors = "".join(result)

        # Normalize "and" separators
        # Normalize "and" separators without regex
        authors = authors.replace(" & ", " and ").replace("&", " and ")

        # Fix double spaces
        # Fix double spaces without regex
        while "  " in authors:
            authors = authors.replace("  ", " ")

        # Ensure proper spacing around "and"
        # Ensure proper spacing around "and" without regex
        authors = authors.replace(" and", " and ").replace("and ", " and ")
        while "  and  " in authors:
            authors = authors.replace("  and  ", " and ")
        authors = authors.strip()

        if authors != original:
            entry.set_field("author", authors.strip())
            return True

        return False

    def fix_ampersands(self, entry: BibliographyEntry) -> bool:
        """Fix LaTeX ampersand escaping.

        Args:
            entry: Bibliography entry

        Returns:
            True if fixes were applied
        """
        fixed = False

        # Fields that commonly need ampersand escaping
        text_fields = [
            "title",
            "booktitle",
            "journal",
            "publisher",
            "organization",
            "note",
        ]

        for field in text_fields:
            if not entry.has_field(field):
                continue

            value = entry.get_field(field)
            if not isinstance(value, str):
                continue

            # Skip if already escaped
            if "\\&" in value:
                continue

            # Check for unescaped ampersands
            if "&" in value:
                # Don't escape in author field or URL fields
                if field not in ["author", "url", "doi"]:
                    new_value = value.replace("&", "\\&")
                    entry.set_field(field, new_value)
                    fixed = True

        return fixed

    def fix_quotes(self, entry: BibliographyEntry) -> bool:
        """Fix quote formatting for LaTeX.

        Args:
            entry: Bibliography entry

        Returns:
            True if fixes were applied
        """
        fixed = False

        # Fields that commonly have quotes
        text_fields = ["title", "booktitle", "journal", "note"]

        for field in text_fields:
            if not entry.has_field(field):
                continue

            value = entry.get_field(field)
            if not isinstance(value, str):
                continue

            original = value

            # Fix straight quotes to LaTeX quotes
            # Opening quotes
            # Fix quotes without regex
            # Convert opening quotes
            new_value = []
            prev_char = " "
            for i, char in enumerate(value):
                if char == '"':
                    # Check if it's an opening quote
                    next_char = value[i + 1] if i + 1 < len(value) else " "
                    if not prev_char.isalnum() and next_char.isalnum():
                        new_value.append("``")
                    elif prev_char.isalnum() and not next_char.isalnum():
                        new_value.append("''")
                    else:
                        new_value.append(char)
                elif char == "'":
                    # Check if it's an opening quote
                    next_char = value[i + 1] if i + 1 < len(value) else " "
                    if not prev_char.isalnum() and next_char.isalnum():
                        new_value.append("`")
                    else:
                        new_value.append(char)
                else:
                    new_value.append(char)
                prev_char = char
            value = "".join(new_value)

            # Fix smart quotes that may have been copied
            value = value.replace(
                """, "``")
            value = value.replace(""",
                "''",
            )
            value = value.replace("'", "`")
            value = value.replace("'", "'")

            if value != original:
                entry.set_field(field, value)
                fixed = True

        return fixed

    def fix_special_characters(self, entry: BibliographyEntry) -> bool:
        """Fix special characters for LaTeX.

        Args:
            entry: Bibliography entry

        Returns:
            True if fixes were applied
        """
        fixed = False

        # Special character replacements
        replacements = {
            "—": "---",  # em dash
            "–": "--",  # en dash
            "…": "...",  # ellipsis
            "°": r"$^\circ$",  # degree symbol
            "±": r"$\pm$",  # plus-minus
            "×": r"$\times$",  # multiplication
            "÷": r"$\div$",  # division
            "≤": r"$\leq$",  # less than or equal
            "≥": r"$\geq$",  # greater than or equal
            "≠": r"$\neq$",  # not equal
            "∞": r"$\infty$",  # infinity
            "α": r"$\alpha$",  # alpha
            "β": r"$\beta$",  # beta
            "γ": r"$\gamma$",  # gamma
            "δ": r"$\delta$",  # delta
            "μ": r"$\mu$",  # mu
            "π": r"$\pi$",  # pi
            "σ": r"$\sigma$",  # sigma
        }

        # Apply to text fields
        text_fields = ["title", "booktitle", "journal", "abstract", "note"]

        for field in text_fields:
            if not entry.has_field(field):
                continue

            value = entry.get_field(field)
            if not isinstance(value, str):
                continue

            original = value

            for char, replacement in replacements.items():
                value = value.replace(char, replacement)

            if value != original:
                entry.set_field(field, value)
                fixed = True

        return fixed

    def fix_pages(self, entry: BibliographyEntry) -> bool:
        """Fix page number formatting.

        Args:
            entry: Bibliography entry

        Returns:
            True if fixes were applied
        """
        if not entry.has_field("pages"):
            return False

        pages = entry.get_field("pages")
        original = pages

        # Convert single dash to double dash
        # Convert single dash to double dash without regex
        if "-" in pages and "--" not in pages:
            parts = pages.split("-")
            if (
                len(parts) == 2
                and parts[0].strip().isdigit()
                and parts[1].strip().isdigit()
            ):
                pages = parts[0].strip() + "--" + parts[1].strip()

        # Remove spaces around dashes
        # Remove spaces around dashes without regex
        pages = (
            pages.replace(" -- ", "--")
            .replace(" --", "--")
            .replace("-- ", "--")
        )

        # Fix common OCR errors
        pages = pages.replace("–", "--")  # en dash to double dash

        if pages != original:
            entry.set_field("pages", pages)
            return True

        return False

    def fix_missing_fields(
        self, entry: BibliographyEntry, defaults: dict[str, str] | None = None
    ) -> bool:
        """Add missing but commonly expected fields.

        Args:
            entry: Bibliography entry
            defaults: Optional default values for missing fields

        Returns:
            True if fields were added
        """
        added = False
        defaults = defaults or {}

        # Add missing DOI/URL for arXiv entries
        if entry.has_field("eprint") and not entry.has_field("url"):
            eprint = entry.get_field("eprint")
            if (
                "arxiv" in eprint.lower()
                or entry.get_field("archiveprefix", "").lower() == "arxiv"
            ):
                arxiv_id = eprint.replace("arXiv:", "").replace("arxiv:", "")
                entry.set_field("url", f"https://arxiv.org/abs/{arxiv_id}")
                added = True

        # Apply any provided defaults
        for field, default_value in defaults.items():
            if not entry.has_field(field):
                entry.set_field(field, default_value)
                added = True

        return added

    def fix_doi_from_url(self, entry: BibliographyEntry) -> bool:
        """Extract DOI from URL field if present.

        Args:
            entry: Bibliography entry

        Returns:
            True if DOI was extracted
        """
        if not entry.has_field("url") or entry.has_field("doi"):
            return False

        url = entry.get_field("url")
        if not isinstance(url, str):
            return False

        # Extract DOI from URL
        if "doi.org/" in url:
            doi_start = url.find("doi.org/") + len("doi.org/")
            doi = url[doi_start:].strip()
            if doi:
                entry.set_field("doi", doi)
                return True

        return False

    def fix_arxiv_format(self, entry: BibliographyEntry) -> bool:
        """Fix arXiv entries to proper format.

        Args:
            entry: Bibliography entry

        Returns:
            True if arXiv format was fixed
        """
        if not entry.has_field("url"):
            return False

        url = entry.get_field("url")
        if not isinstance(url, str) or "arxiv.org/abs/" not in url:
            return False

        # Extract arXiv ID
        arxiv_start = url.find("arxiv.org/abs/") + len("arxiv.org/abs/")
        arxiv_id = url[arxiv_start:].strip()

        if arxiv_id:
            entry.set_field("eprint", arxiv_id)
            entry.set_field("archivePrefix", "arXiv")
            return True

        return False

    def fix_duplicate_fields(self, entry: BibliographyEntry) -> bool:
        """Remove duplicate information between fields.

        Args:
            entry: Bibliography entry

        Returns:
            True if duplicates were removed
        """
        fixed = False

        # Remove URL if it just points to the DOI
        if entry.has_field("doi") and entry.has_field("url"):
            doi = entry.get_field("doi")
            url = entry.get_field("url")
            if isinstance(url, str) and isinstance(doi, str):
                if f"doi.org/{doi}" in url:
                    entry.fields.pop("url", None)
                    fixed = True

        return fixed

    def fix_title_capitalization(self, entry: BibliographyEntry) -> bool:
        """Fix title capitalization for BibTeX.

        Args:
            entry: Bibliography entry

        Returns:
            True if capitalization was fixed
        """
        if not entry.has_field("title"):
            return False

        title = entry.get_field("title")
        if not isinstance(title, str):
            return False

        original = title

        # Basic capitalization: first letter should be uppercase
        if title and title[0].islower():
            title = title[0].upper() + title[1:]

        if title != original:
            entry.set_field("title", title)
            return True

        return False


class AuthorFixer(BibliographyFixer):
    """Specialized fixer for author-related issues.

    This class handles more complex author name fixing including:
    - Resolving "et al." to full author lists
    - Fixing reversed names
    - Handling special characters in names
    """

    def fix_author_names(self, entry: BibliographyEntry) -> bool:
        """Enhanced author name fixing.

        Args:
            entry: Bibliography entry

        Returns:
            True if fixes were applied
        """
        # First apply basic fixes
        fixed = super().fix_author_names(entry)

        if not entry.has_field("author"):
            return fixed

        authors = entry.get_field("author")
        original = authors

        # Split authors
        # Split authors without regex
        author_list = authors.split(" and ")
        fixed_authors = []

        for author in author_list:
            author = author.strip()

            # Fix reversed names without comma (e.g., "Smith John" -> "Smith, John")
            # Fix reversed names without regex
            parts = author.split()
            if len(parts) == 2:
                if (
                    parts[0]
                    and parts[0][0].isupper()
                    and parts[0][1:].islower()
                    and parts[1]
                    and parts[1][0].isupper()
                    and parts[1][1:].islower()
                ):
                    author = f"{parts[0]}, {parts[1]}"

            # Fix missing periods in initials
            # Fix missing periods in initials without regex
            new_author = []
            i = 0
            while i < len(author):
                if (
                    i < len(author) - 1
                    and author[i].isupper()
                    and author[i + 1] == " "
                ):
                    # Check if next char after space is also uppercase
                    j = i + 2
                    while j < len(author) and author[j] == " ":
                        j += 1
                    if j < len(author) and author[j].isupper():
                        new_author.append(author[i] + ".")
                        i += 1
                    else:
                        new_author.append(author[i])
                        i += 1
                elif (
                    i == len(author) - 1
                    and author[i].isupper()
                    and (i == 0 or author[i - 1] == " ")
                ):
                    new_author.append(author[i] + ".")
                    i += 1
                else:
                    new_author.append(author[i])
                    i += 1
            author = "".join(new_author)

            # Fix spacing around initials
            # Fix spacing around initials without regex
            new_author = []
            for i, char in enumerate(author):
                new_author.append(char)
                if (
                    i < len(author) - 2
                    and char == "."
                    and author[i + 1].isupper()
                    and author[i - 1].isupper()
                ):
                    new_author.append(" ")
            author = "".join(new_author)

            fixed_authors.append(author)

        # Rejoin authors
        new_authors = " and ".join(fixed_authors)

        if new_authors != original:
            entry.set_field("author", new_authors)
            return True

        return fixed
