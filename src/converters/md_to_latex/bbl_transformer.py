"""Transform BibTeX .bbl files to arXiv-ready format with hyperlinked authors.

This module converts standard .bbl bibliographies into the arXiv hard-coded format
where author names are wrapped in \\href{} commands for clickable citations.

Format transformation:
    FROM: \\bibitem[Author(Year)]{key}
          Author (Year) Title. Journal
          \\urlprefix\\url{https://...}

    TO:   \\bibitem[Author(Year)]{key}
          \\href{https://...}{Author (Year)} Title. Journal

Key features:
- Extracts URLs from .bib file by citation key
- Parses .bbl file to identify author names and years
- Wraps author-year in \\href{URL}{...} for hyperlinked author names
- Removes \\urlprefix\\url{} commands from bibliography
- Preserves all other LaTeX formatting intact
"""

from pathlib import Path

import bibtexparser


class BblTransformer:
    """Transform .bbl bibliographies to arXiv format with hyperlinked authors."""

    def __init__(self, bib_path: Path, bbl_path: Path):
        """Initialize transformer with paths to .bib and .bbl files.

        Args:
            bib_path: Path to .bib file containing URL metadata
            bbl_path: Path to .bbl file to transform
        """
        self.bib_path = bib_path
        self.bbl_path = bbl_path
        self.url_map = self._extract_urls_from_bib()

    def _extract_urls_from_bib(self) -> dict[str, str]:
        """Extract URL and author metadata from .bib file.

        Returns:
            Dictionary mapping citation keys to (URL, authors, year) tuples
        """
        with open(self.bib_path) as bib_file:
            bib_database = bibtexparser.load(bib_file)

        metadata_map = {}
        for entry in bib_database.entries:
            cite_key = entry.get("ID")
            url = entry.get("url") or entry.get("doi")
            authors = entry.get("author", "")
            year = entry.get("year", "")

            if cite_key:
                # Ensure DOI URLs are properly formatted
                if url and url.startswith("10."):
                    url = f"https://doi.org/{url}"

                # Store as tuple: (url, authors, year)
                metadata_map[cite_key] = (url, authors, year)

        return metadata_map

    def transform(self) -> str:
        """Transform .bbl file to arXiv format with hyperlinked authors.

        Returns:
            Transformed bibliography content ready for embedding in main.tex
        """
        with open(self.bbl_path) as bbl_file:
            bbl_content = bbl_file.read()

        # Split into individual bibitem entries
        entries = bbl_content.split("\\bibitem")

        # Keep preamble (before first \\bibitem)
        preamble = entries[0]

        # Transform each bibitem entry
        transformed_entries = [preamble]
        for entry in entries[1:]:
            transformed_entry = self._transform_bibitem(entry)
            transformed_entries.append(transformed_entry)

        return "\\bibitem".join(transformed_entries)

    def _transform_bibitem(self, entry: str) -> str:
        """Transform a single bibitem entry to wrap authors in \\href{}.

        Args:
            entry: Raw bibitem entry text (without leading \\bibitem)

        Returns:
            Transformed entry with hyperlinked author names
        """
        # Extract citation key from: [label]{key}
        # Find the closing bracket of the label
        close_bracket = entry.find("]")
        if close_bracket == -1:
            return entry  # Malformed entry, return as-is

        # Extract the label (everything before ])
        label = entry[1:close_bracket]  # Skip opening '['

        # Find cite key after ']' - should be '{key}'
        cite_key_start = entry.find("{", close_bracket)
        if cite_key_start == -1:
            return entry  # Malformed entry

        cite_key_end = entry.find("}", cite_key_start)
        if cite_key_end == -1:
            return entry  # Malformed entry

        cite_key = entry[cite_key_start + 1 : cite_key_end].strip()

        # Get URL for this citation
        metadata = self.url_map.get(cite_key)
        if not metadata:
            # No URL available, return entry unchanged
            return entry

        url, authors, year = metadata
        if not url:
            # No URL available, return entry unchanged
            return entry

        # Find the start of the actual content (after citation key closing brace)
        # The format is: }]{key}\n
        # So we need to skip to the NEXT line after the newline
        content_start = cite_key_end + 1

        # Find first newline after the closing brace (this is empty)
        first_newline_pos = entry.find("\n", content_start)
        if first_newline_pos == -1:
            return entry  # Malformed entry

        # Start from after the first newline - this is where the actual content begins
        actual_content_start = first_newline_pos + 1

        # Find the SECOND newline (end of the author-year line)
        second_newline_pos = entry.find("\n", actual_content_start)
        if second_newline_pos == -1:
            # No second newline, take rest of entry
            second_newline_pos = len(entry)

        # Extract the first line (author-year line)
        first_line = entry[actual_content_start:second_newline_pos].strip()

        # Extract author-year portion (text before first punctuation or "et~al")
        # This is fragile but matches .bbl format: "Author T (Year) Title..."
        # We need to wrap "Author T (Year)" in \href{}

        # Find the year (YYYY) pattern - search for "(YYYY)"
        year_start = -1
        for i in range(len(first_line) - 4):
            if (
                first_line[i : i + 4].isdigit()
                and i > 0
                and first_line[i - 1] == "("
            ):
                year_start = i - 1  # Start from the opening parenthesis
                break

        if year_start == -1:
            # No year found, can't transform
            return entry

        # Find closing parenthesis after year
        year_end = first_line.find(")", year_start + 4)
        if year_end == -1:
            return entry

        # Author-year portion is everything from start to closing paren
        author_year = first_line[: year_end + 1].strip()

        # Rest of the entry (title, journal, etc.)
        rest_of_line = first_line[year_end + 1 :].strip()

        # Rest of the entry (following lines after the author-year line)
        rest_of_entry = entry[second_newline_pos:]

        # Remove any \urlprefix\url{...} commands from rest of entry
        rest_of_entry = self._remove_url_commands(rest_of_entry)

        # Construct transformed entry
        transformed = f"[{label}]{{{cite_key}}}\n"
        transformed += f"\\href{{{url}}}{{{author_year}}} {rest_of_line}"
        transformed += rest_of_entry

        return transformed

    def _remove_url_commands(self, text: str) -> str:
        """Remove \\urlprefix\\url{} commands from text.

        Args:
            text: Text potentially containing URL commands

        Returns:
            Text with URL commands removed
        """
        # Remove \urlprefix\url{...} patterns
        # This is a simple character-by-character state machine (no regex!)
        result = []
        i = 0
        while i < len(text):
            # Check for \urlprefix
            if text[i : i + 10] == "\\urlprefix":
                # Skip \urlprefix
                i += 10
                # Skip whitespace
                while i < len(text) and text[i] in " \t\n":
                    i += 1
                # Check for \url{
                if i < len(text) and text[i : i + 5] == "\\url{":
                    # Find matching closing brace
                    i += 5
                    brace_count = 1
                    while i < len(text) and brace_count > 0:
                        if text[i] == "{":
                            brace_count += 1
                        elif text[i] == "}":
                            brace_count -= 1
                        i += 1
                    continue

            # Check for standalone \url{...}
            if text[i : i + 5] == "\\url{":
                # Find matching closing brace
                i += 5
                brace_count = 1
                while i < len(text) and brace_count > 0:
                    if text[i] == "{":
                        brace_count += 1
                    elif text[i] == "}":
                        brace_count -= 1
                    i += 1
                continue

            # Normal character
            result.append(text[i])
            i += 1

        return "".join(result)


def transform_bbl_to_arxiv(
    bib_path: Path, bbl_path: Path, output_path: Path
) -> None:
    """Transform a .bbl file to arXiv format and write to output.

    Args:
        bib_path: Path to .bib file
        bbl_path: Path to .bbl file
        output_path: Path to write transformed bibliography
    """
    transformer = BblTransformer(bib_path, bbl_path)
    transformed_bbl = transformer.transform()

    with open(output_path, "w") as output_file:
        output_file.write(transformed_bbl)
