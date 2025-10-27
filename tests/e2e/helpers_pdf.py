"""PDF inspection and comparison helpers for end-to-end tests.

This module provides utilities for validating PDF output from the MD→LaTeX→PDF
pipeline. All functions use AST-based parsing or string methods (NO REGEX) per
project policy (.claude/CLAUDE.md).

Dependencies:
    - PyMuPDF (fitz): Link extraction, text extraction
    - pikepdf: Font embedding, metadata inspection
    - PyPDF2: Already in project dependencies
"""

from pathlib import Path

import fitz  # PyMuPDF
import pikepdf

# ---------- Link / Annotation Extraction ----------


def extract_links(pdf_path: Path) -> list[tuple[int, str, str]]:
    """Extract all hyperlinks from a PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of (page_number, target_url, link_type) tuples
        where link_type is one of: 'uri', 'file', 'xref'

    Example:
        >>> links = extract_links(Path("paper.pdf"))
        >>> doi_links = [url for _, url, kind in links if 'doi.org' in url]
        >>> assert len(doi_links) > 0, "No DOI links found"
    """
    links = []
    doc = fitz.open(str(pdf_path))

    for i, page in enumerate(doc):
        for link in page.get_links():
            # Extract target URL or reference
            target = link.get("uri") or link.get("file") or link.get("xref")

            # Determine link type
            if link.get("uri"):
                kind = "uri"
            elif link.get("file"):
                kind = "file"
            else:
                kind = "xref"

            if target:
                links.append((i + 1, str(target), kind))

    return links


# ---------- Font Embedding (arXiv Compliance) ----------


def get_font_info(pdf_path: Path) -> dict[int, list[dict]]:
    """Extract font information from PDF to verify embedding.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dict mapping page_number → list of font info dicts
        Each font dict contains: name, subtype, basefont, embedded (bool)

    Example:
        >>> fonts = get_font_info(Path("paper.pdf"))
        >>> unembedded = [f for page_fonts in fonts.values()
        ...               for f in page_fonts if not f['embedded']]
        >>> assert not unembedded, f"arXiv violation: {unembedded}"
    """
    fonts = {}

    with pikepdf.Pdf.open(pdf_path) as pdf:
        for page_i, page in enumerate(pdf.pages):
            resources = page.get("/Resources")
            if not resources or "/Font" not in resources:
                continue

            fonts_obj = resources["/Font"]
            for name, font_ref in fonts_obj.items():
                # In newer pikepdf, font_ref is already the object
                # Try .get_object() for backwards compatibility
                try:
                    fdict = font_ref.get_object()
                except AttributeError:
                    fdict = font_ref

                # Check if font is embedded
                # Method 1: Check for /FontFile* entries
                embedded = any(
                    k in fdict
                    for k in ["/FontFile", "/FontFile2", "/FontFile3"]
                )

                # Method 2: Check for + prefix in /BaseFont name (standard indicator)
                if not embedded:
                    basefont = str(fdict.get("/BaseFont", ""))
                    # Format: /XXXXXX+FontName where XXXXXX is subset prefix
                    embedded = "+" in basefont

                fonts.setdefault(page_i, []).append(
                    {
                        "name": str(name),
                        "subtype": str(fdict.get("/Subtype", "Unknown")),
                        "basefont": str(fdict.get("/BaseFont", "Unknown")),
                        "embedded": embedded,
                    }
                )

    return fonts


# ---------- PDF Metadata ----------


def get_metadata(pdf_path: Path) -> dict[str, str]:
    """Extract PDF metadata (Title, Author, Producer, etc.).

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dict of metadata fields (keys may include / prefix like '/Title')

    Example:
        >>> meta = get_metadata(Path("paper.pdf"))
        >>> assert meta.get('/Title'), "PDF missing Title metadata"
        >>> assert meta.get('/Producer'), "PDF missing Producer metadata"
    """
    with pikepdf.Pdf.open(pdf_path) as pdf:
        return dict(pdf.docinfo)


# ---------- Text Normalization (Deterministic Comparison) ----------


def normalize_pdf_text(text: str) -> str:
    """Normalize PDF text for robust comparison.

    Handles LaTeX quirks like ligatures, Unicode dashes, and whitespace
    variations. Uses string methods only (NO REGEX per project policy).

    Args:
        text: Raw text extracted from PDF

    Returns:
        Normalized text (collapsed whitespace, standardized characters)

    Example:
        >>> text1 = "Smith et al.\\u2013\\u20142020"  # en-dash, em-dash
        >>> text2 = "Smith et al.--2020"
        >>> normalize_pdf_text(text1) == normalize_pdf_text(text2)
        True
    """
    # Unicode normalization
    text = text.replace("\u2013", "-")  # en-dash → hyphen
    text = text.replace("\u2014", "-")  # em-dash → hyphen
    text = text.replace("\u00a0", " ")  # non-breaking space → space
    text = text.replace("\ufb01", "fi")  # ligature ﬁ → fi
    text = text.replace("\ufb02", "fl")  # ligature ﬂ → fl

    # Whitespace normalization (NO REGEX - use loop)
    while "  " in text:
        text = text.replace("  ", " ")

    # Remove leading/trailing whitespace
    return text.strip()


# ---------- Text Extraction ----------


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from PDF using PyMuPDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Concatenated text from all pages

    Example:
        >>> text = extract_text_from_pdf(Path("paper.pdf"))
        >>> assert "(?)" not in text, "Unresolved citation found"
        >>> assert "(Unknown)" not in text, "Unknown author found"
    """
    doc = fitz.open(str(pdf_path))
    text_parts = []

    for page in doc:
        text_parts.append(page.get_text())

    return "\n".join(text_parts)


# ---------- Structural Validation ----------


def get_page_count(pdf_path: Path) -> int:
    """Get number of pages in PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Number of pages

    Example:
        >>> count = get_page_count(Path("paper.pdf"))
        >>> assert count > 0, "Empty PDF"
    """
    doc = fitz.open(str(pdf_path))
    return len(doc)


def extract_section_headers(pdf_text: str) -> list[str]:
    """Extract section headers from PDF text.

    Uses heuristics: lines in ALL CAPS or numbered sections (1., 2., etc.).
    NO REGEX - uses string methods.

    Args:
        pdf_text: Text extracted from PDF

    Returns:
        List of likely section headers

    Example:
        >>> text = extract_text_from_pdf(Path("paper.pdf"))
        >>> headers = extract_section_headers(text)
        >>> assert "INTRODUCTION" in headers or "Introduction" in headers
    """
    headers = []
    lines = pdf_text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Heuristic 1: ALL CAPS (at least 3 words)
        words = line.split()
        if len(words) >= 2 and line.isupper():
            headers.append(line)
            continue

        # Heuristic 2: Numbered sections (1. Introduction, 2. Methods)
        # Check if line starts with digit followed by period
        if line and line[0].isdigit():
            # Find first space after number
            space_idx = line.find(" ")
            if space_idx > 0:
                prefix = line[:space_idx]
                # Check if format is "N." or "N.M."
                if "." in prefix:
                    headers.append(line)

    return headers


def count_citations_in_text(pdf_text: str) -> int:
    """Count citation markers in PDF text.

    Counts patterns like: (Smith, 2020), (Smith et al., 2020)
    Uses string methods (NO REGEX per project policy).

    Args:
        pdf_text: Text extracted from PDF

    Returns:
        Number of citation markers found

    Example:
        >>> text = extract_text_from_pdf(Path("paper.pdf"))
        >>> count = count_citations_in_text(text)
        >>> assert count > 0, "No citations found in PDF"
    """
    count = 0
    # Simple heuristic: count occurrences of (Author, Year) patterns
    # Look for patterns like "(<text>, <year>)" where year is 4 digits

    i = 0
    while i < len(pdf_text):
        # Find opening parenthesis
        open_paren = pdf_text.find("(", i)
        if open_paren == -1:
            break

        # Find closing parenthesis
        close_paren = pdf_text.find(")", open_paren)
        if close_paren == -1:
            break

        # Extract content between parentheses
        content = pdf_text[open_paren + 1 : close_paren]

        # Check if looks like citation: contains comma and 4-digit year
        if "," in content:
            # Check for 4-digit year
            for j in range(len(content) - 3):
                if (
                    content[j].isdigit()
                    and content[j + 1].isdigit()
                    and content[j + 2].isdigit()
                    and content[j + 3].isdigit()
                ):
                    # Found a year, likely a citation
                    count += 1
                    break

        # Move to next potential citation
        i = close_paren + 1

    return count
