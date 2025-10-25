"""
PDF parsing utilities for extracting bibliographic information.

Handles PDF metadata extraction, text parsing, and author/date detection
from various PDF formats including research papers and reports.
"""

import io
import logging

# import re  # Banned - using string methods instead
import pdfplumber
import requests
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)


class PDFParser:
    """Parser for extracting bibliographic information from PDFs."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def extract_pdf_info(self, url: str) -> dict | None:
        """
        Extract bibliographic information from a PDF URL.

        Args:
            url: URL pointing to a PDF file

        Returns:
            Dictionary with extracted information or None if failed
        """
        try:
            logger.debug(f"Downloading PDF from: {url}")
            response = requests.get(
                url, headers=self.headers, timeout=self.timeout
            )
            response.raise_for_status()

            # Check if it's actually a PDF
            content_type = response.headers.get("content-type", "").lower()
            if "pdf" not in content_type and not url.lower().endswith(".pdf"):
                logger.warning(f"URL does not appear to be a PDF: {url}")
                return None

            pdf_content = io.BytesIO(response.content)

            # Try multiple extraction methods
            info = (
                self._extract_with_pdfplumber(pdf_content)
                or self._extract_with_pypdf2(pdf_content)
                or self._extract_from_url_patterns(url)
            )

            if info:
                info["source_url"] = url
                logger.info(
                    f"Successfully extracted PDF info: {info.get('title', 'Unknown title')[:50]}..."
                )

            return info

        except requests.RequestException as e:
            logger.warning(f"Failed to download PDF from {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing PDF from {url}: {e}")
            return None

    def _extract_with_pdfplumber(self, pdf_content: io.BytesIO) -> dict | None:
        """Extract info using pdfplumber."""
        try:
            pdf_content.seek(0)
            with pdfplumber.open(pdf_content) as pdf:
                if not pdf.pages:
                    return None

                # Extract text from first few pages
                text = ""
                for i, page in enumerate(pdf.pages[:3]):  # First 3 pages
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

                if text.strip():
                    return self._parse_text_for_info(text)

        except Exception as e:
            logger.debug(f"PDFPlumber extraction failed: {e}")

        return None

    def _extract_with_pypdf2(self, pdf_content: io.BytesIO) -> dict | None:
        """Extract info using PyPDF2."""
        try:
            pdf_content.seek(0)
            reader = PdfReader(pdf_content)

            # Try metadata first
            metadata = reader.metadata
            if metadata:
                info = {}
                if metadata.title:
                    info["title"] = metadata.title
                if metadata.author:
                    info["authors"] = [metadata.author]
                if metadata.creation_date:
                    info["year"] = str(metadata.creation_date.year)

                if info:
                    return info

            # Extract text from first few pages
            text = ""
            for i, page in enumerate(reader.pages[:3]):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception:
                    continue

            if text.strip():
                return self._parse_text_for_info(text)

        except Exception as e:
            logger.debug(f"PyPDF2 extraction failed: {e}")

        return None

    def _extract_from_url_patterns(self, url: str) -> dict | None:
        """Extract basic info from URL patterns using string methods."""
        try:
            # Urban Institute pattern
            if "urban.org" in url:
                # Extract date from URL path - look for /YYYY-MM/ pattern
                parts = url.split("/")
                for part in parts:
                    if "-" in part and len(part) == 7:  # YYYY-MM format
                        year_part = part[:4]
                        if (
                            year_part.isdigit()
                            and 1900 <= int(year_part) <= 2100
                        ):
                            return {
                                "year": year_part,
                                "publisher": "Urban Institute",
                            }

            # Generic date extraction from URL - look for /YYYY/ or /YYYY-
            parts = url.split("/")
            for part in parts:
                # Check for 4-digit year
                if len(part) >= 4:
                    year_candidate = part[:4]
                    if year_candidate.isdigit():
                        year = int(year_candidate)
                        if 1900 <= year <= 2100:
                            # Check if followed by separator
                            if len(part) == 4 or (
                                len(part) > 4 and part[4] in ["-", "_"]
                            ):
                                return {"year": str(year)}

        except Exception as e:
            logger.debug(f"URL pattern extraction failed: {e}")

        return None

    def _parse_text_for_info(self, text: str) -> dict | None:
        """Parse PDF text to extract bibliographic information."""
        info = {}

        # Extract title (usually first large line)
        title = self._extract_title(text)
        if title:
            info["title"] = title

        # Extract authors
        authors = self._extract_authors(text)
        if authors:
            info["authors"] = authors

        # Extract year/date
        year = self._extract_year(text)
        if year:
            info["year"] = year

        # Extract publisher/institution
        publisher = self._extract_publisher(text)
        if publisher:
            info["publisher"] = publisher

        return info if info else None

    def _extract_title(self, text: str) -> str | None:
        """Extract title from PDF text."""
        lines = text.split("\n")

        # Look for title patterns
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            line = line.strip()
            if not line:
                continue

            # Skip headers, footers, page numbers
            if line.isdigit():  # Just a number
                continue
            if len(line) < 10:  # Too short
                continue
            if line.isupper() and len(line) > 50:  # All caps, likely title
                return line.title()
            if (
                len(line) > 20 and not line.endswith(".") and i < 5
            ):  # Likely title
                return line

        return None

    def _extract_authors(self, text: str) -> list[str] | None:
        """Extract authors from PDF text using string methods."""
        # Look in first 500 characters for author info
        search_text = text[:500]

        # Try different author indicators
        author_indicators = ["By ", "Author:", "Authors:", "Written by", "by "]

        for indicator in author_indicators:
            pos = search_text.find(indicator)
            if pos != -1:
                # Extract text after indicator
                start = pos + len(indicator)
                # Find end (newline or period)
                end = len(search_text)
                for end_char in ["\n", ".", "(", "["]:
                    end_pos = search_text.find(end_char, start)
                    if end_pos != -1 and end_pos < end:
                        end = end_pos

                author_text = search_text[start:end].strip()
                authors = self._parse_author_string(author_text)
                if authors and len(authors) <= 10:
                    return authors

        # Try to find author patterns (capitalized names)
        lines = search_text.split("\n")
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if self._looks_like_author_line(line):
                authors = self._parse_author_string(line)
                if authors and 1 <= len(authors) <= 10:
                    return authors

        # Special handling for Urban Institute format
        if "urban.org" in text.lower() or "urban institute" in text.lower():
            # Look for names in first few lines
            for line in lines[:5]:
                line = line.strip()
                if self._is_name_format(line):
                    authors = self._parse_author_string(line)
                    if authors and 2 <= len(authors) <= 6:
                        return authors

        return None

    def _looks_like_author_line(self, line: str) -> bool:
        """Check if a line looks like it contains author names."""
        if len(line) < 5 or len(line) > 200:
            return False

        # Check if line contains email addresses (common in papers)
        if "@" in line and "." in line:
            return True

        # Check if line contains "and" between capitalized words
        if " and " in line:
            parts = line.split(" and ")
            if all(self._is_name_format(part.strip()) for part in parts):
                return True

        # Check if line is mostly capitalized words
        words = line.split()
        capitalized_count = sum(
            1 for word in words if word and word[0].isupper()
        )
        if len(words) >= 2 and capitalized_count >= len(words) * 0.6:
            return True

        return False

    def _is_name_format(self, text: str) -> bool:
        """Check if text follows name format (First Last)."""
        words = text.split()
        if len(words) < 2:
            return False

        # Check if words are capitalized
        for word in words:
            if word and not word[0].isupper():
                # Allow some lowercase words like "van", "de", etc.
                if word not in ["van", "de", "der", "von", "la", "di"]:
                    return False

        return True

    def _parse_author_string(self, author_string: str) -> list[str]:
        """Parse a string containing multiple authors."""
        # Clean up the string
        author_string = " ".join(author_string.split())  # Normalize whitespace

        authors = []

        # Split by "and" or comma
        if " and " in author_string:
            # Split by comma first, then by "and"
            parts = []
            for segment in author_string.split(","):
                if " and " in segment:
                    parts.extend(segment.split(" and "))
                else:
                    parts.append(segment)
        else:
            parts = author_string.split(",")

        for part in parts:
            part = part.strip()
            if self._is_valid_author_name(part):
                authors.append(part)

        return authors

    def _is_valid_author_name(self, name: str) -> bool:
        """Check if a string is a valid author name."""
        if not name or len(name) < 3:
            return False

        # Remove email if present
        if "@" in name:
            name = name[: name.find("@")].strip()

        words = name.split()
        if len(words) < 2:
            return False

        # Check if at least first and last words are capitalized
        if (
            words[0]
            and words[0][0].isupper()
            and words[-1]
            and words[-1][0].isupper()
        ):
            return True

        return False

    def _extract_year(self, text: str) -> str | None:
        """Extract publication year from PDF text using string methods."""
        # Look for year patterns in first 300 characters
        search_text = text[:300]

        # Try different year indicators
        year_indicators = ["Published:", "Date:", "Copyright", "©"]

        for indicator in year_indicators:
            pos = search_text.find(indicator)
            if pos != -1:
                # Look for 4-digit year after indicator
                year = self._find_year_after_position(search_text, pos)
                if year:
                    return year

        # Also look for month names followed by year
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]

        for month in months:
            pos = search_text.lower().find(month.lower())
            if pos != -1:
                year = self._find_year_after_position(
                    search_text, pos + len(month)
                )
                if year:
                    return year

        # Last resort: find any 4-digit year
        year = self._find_any_year(search_text)
        if year:
            return year

        return None

    def _find_year_after_position(
        self, text: str, start_pos: int
    ) -> str | None:
        """Find a 4-digit year after given position."""
        # Look for next 50 characters
        search_area = text[start_pos : start_pos + 50]

        i = 0
        while i < len(search_area) - 3:
            if search_area[i : i + 4].isdigit():
                year = int(search_area[i : i + 4])
                if 1990 <= year <= 2030:
                    return str(year)
            i += 1

        return None

    def _find_any_year(self, text: str) -> str | None:
        """Find any 4-digit year in text."""
        words = text.split()
        for word in words:
            # Clean punctuation
            clean_word = "".join(c for c in word if c.isdigit())
            if len(clean_word) == 4:
                year = int(clean_word)
                if 1990 <= year <= 2030:
                    return str(year)

        return None

    def _extract_publisher(self, text: str) -> str | None:
        """Extract publisher from PDF text."""
        # Known publisher patterns
        publishers = {
            "urban institute": "Urban Institute",
            "brookings": "Brookings Institution",
            "harvard business review": "Harvard Business Review",
            "mckinsey": "McKinsey & Company",
            "deloitte": "Deloitte",
            "pwc": "PwC",
            "government accountability office": "U.S. Government Accountability Office",
            "congressional budget office": "Congressional Budget Office",
        }

        search_text = text[:500].lower()

        for keyword, publisher in publishers.items():
            if keyword in search_text:
                return publisher

        return None


def is_pdf_url(url: str) -> bool:
    """Check if URL points to a PDF file."""
    return url.lower().endswith(".pdf") or "filetype:pdf" in url.lower()


def extract_pdf_metadata(url: str) -> dict | None:
    """
    Convenience function to extract PDF metadata.

    Args:
        url: URL to PDF file

    Returns:
        Dictionary with extracted metadata or None
    """
    if not is_pdf_url(url):
        return None

    parser = PDFParser()
    return parser.extract_pdf_info(url)
