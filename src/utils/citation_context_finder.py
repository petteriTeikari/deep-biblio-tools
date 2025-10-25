"""
Find context for citations in markdown files.

This module helps locate where specific URLs are cited in markdown documents,
providing the surrounding context to help understand what citation is needed.
"""

import logging

# import re  # Banned - using string methods instead
from pathlib import Path

logger = logging.getLogger(__name__)


class CitationContext:
    """Represents the context where a citation appears."""

    def __init__(
        self,
        file_path: str,
        line_number: int,
        text_before: str,
        citation_text: str,
        text_after: str,
        full_line: str,
    ):
        self.file_path = file_path
        self.line_number = line_number
        self.text_before = text_before
        self.citation_text = citation_text
        self.text_after = text_after
        self.full_line = full_line

    def __repr__(self):
        return f"CitationContext(file={Path(self.file_path).name}, line={self.line_number}, citation='{self.citation_text}')"


class CitationContextFinder:
    """Find where citations are used in markdown files."""

    def __init__(self, search_dirs: list[str] = None):
        """
        Initialize the context finder.

        Args:
            search_dirs: List of directories to search for markdown files.
                        Defaults to ['data/', 'docs/']
        """
        if search_dirs is None:
            search_dirs = ["data/", "docs/"]

        self.search_dirs = [Path(d) for d in search_dirs if Path(d).exists()]

    def find_markdown_files(self) -> list[Path]:
        """Find all markdown files in search directories."""
        md_files = []

        for search_dir in self.search_dirs:
            if search_dir.is_dir():
                # Find all .md files recursively
                md_files.extend(search_dir.rglob("*.md"))

        # Also check current directory
        md_files.extend(Path(".").glob("*.md"))

        # Remove duplicates and sort
        md_files = sorted(set(md_files))

        logger.info(f"Found {len(md_files)} markdown files to search")
        return md_files

    def find_citation_contexts(
        self, target_url: str, context_chars: int = 100
    ) -> list[CitationContext]:
        """
        Find all contexts where a URL is cited.

        Args:
            target_url: The URL to search for
            context_chars: Number of characters to include before/after citation

        Returns:
            List of CitationContext objects
        """
        contexts = []
        md_files = self.find_markdown_files()

        # Normalize the target URL for comparison
        normalized_target = self._normalize_url(target_url)

        for md_file in md_files:
            try:
                with open(md_file, encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                # Find markdown links: [text](url) using string methods
                for line_num, line in enumerate(lines, 1):
                    # Find all markdown links in the line
                    i = 0
                    while i < len(line):
                        # Look for opening [
                        bracket_start = line.find("[", i)
                        if bracket_start == -1:
                            break

                        # Find closing ]
                        bracket_end = line.find("]", bracket_start + 1)
                        if bracket_end == -1:
                            i = bracket_start + 1
                            continue

                        # Check if followed by (
                        if (
                            bracket_end + 1 < len(line)
                            and line[bracket_end + 1] == "("
                        ):
                            # Find closing )
                            paren_end = line.find(")", bracket_end + 2)
                            if paren_end == -1:
                                i = bracket_end + 1
                                continue

                            # Extract text and URL
                            citation_text = line[
                                bracket_start + 1 : bracket_end
                            ]
                            url = line[bracket_end + 2 : paren_end]

                            # Check if this URL matches our target
                            if self._normalize_url(url) == normalized_target:
                                # Extract context
                                start_pos = max(
                                    0, bracket_start - context_chars
                                )
                                end_pos = min(
                                    len(line), paren_end + 1 + context_chars
                                )

                                text_before = line[start_pos:bracket_start]
                                text_after = line[paren_end + 1 : end_pos]

                                # Clean up context
                                if start_pos > 0:
                                    text_before = "..." + text_before.lstrip()
                                if end_pos < len(line):
                                    text_after = text_after.rstrip() + "..."

                                context = CitationContext(
                                    file_path=str(md_file),
                                    line_number=line_num,
                                    text_before=text_before,
                                    citation_text=citation_text,
                                    text_after=text_after,
                                    full_line=line.strip(),
                                )
                                contexts.append(context)

                            # Move past this link
                            i = paren_end + 1
                        else:
                            i = bracket_end + 1

            except Exception as e:
                logger.error(f"Error reading {md_file}: {e}")

        return contexts

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        # Remove trailing slashes
        url = url.rstrip("/")

        # Handle escaped characters
        url = url.replace("\\(", "(").replace("\\)", ")")

        # Lowercase for comparison
        return url.lower()

    def find_all_citation_contexts(
        self, urls: list[str]
    ) -> dict[str, list[CitationContext]]:
        """
        Find contexts for multiple URLs.

        Args:
            urls: List of URLs to search for

        Returns:
            Dictionary mapping URL to list of contexts
        """
        results = {}

        for url in urls:
            contexts = self.find_citation_contexts(url)
            if contexts:
                results[url] = contexts
                logger.info(f"Found {len(contexts)} context(s) for {url}")
            else:
                results[url] = []
                logger.warning(f"No contexts found for {url}")

        return results

    def format_context_display(self, context: CitationContext) -> str:
        """Format a context for display."""
        return (
            f"File: {Path(context.file_path).name} (line {context.line_number})\n"
            f"Context: {context.text_before}[{context.citation_text}]({context.text_after})"
        )
