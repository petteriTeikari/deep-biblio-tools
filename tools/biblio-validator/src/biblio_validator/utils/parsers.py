"""Parsing utilities for documents and bibliographies."""

import re
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser

from ..models.bibliography import BibEntry
from ..models.citation import Citation


def parse_document_citations(
    document_path: Path, format: str | None = None
) -> list[Citation]:
    """Parse citations from a document."""
    if format is None:
        # Detect format from extension
        ext = document_path.suffix.lower()
        format_map = {".md": "markdown", ".tex": "latex", ".txt": "text"}
        format = format_map.get(ext, "text")

    content = document_path.read_text(encoding="utf-8")

    if format == "markdown":
        return parse_markdown_citations(content, str(document_path))
    elif format == "latex":
        return parse_latex_citations(content, str(document_path))
    else:
        return parse_text_citations(content, str(document_path))


def parse_markdown_citations(
    content: str, document_path: str
) -> list[Citation]:
    """Parse citations from markdown content."""
    citations = []

    # Pattern for markdown citations like [@Smith2020] or [@Smith2020; @Jones2021]
    pattern = r"\[@([^\]]+)\]"

    for line_num, line in enumerate(content.splitlines(), 1):
        matches = re.finditer(pattern, line)
        for match in matches:
            citation_group = match.group(1)
            # Split multiple citations
            for cite_key in citation_group.split(";"):
                cite_key = cite_key.strip().lstrip("@")
                if cite_key:
                    citation = Citation(
                        key=cite_key,
                        text=match.group(0),
                        document_path=document_path,
                        line_number=line_num,
                        context=line.strip(),
                    )
                    citations.append(citation)

    return citations


def parse_latex_citations(content: str, document_path: str) -> list[Citation]:
    """Parse citations from LaTeX content."""
    citations = []

    # Patterns for LaTeX citations
    patterns = [
        r"\\cite\{([^}]+)\}",
        r"\\citep\{([^}]+)\}",
        r"\\citet\{([^}]+)\}",
        r"\\parencite\{([^}]+)\}",
        r"\\textcite\{([^}]+)\}",
    ]

    for line_num, line in enumerate(content.splitlines(), 1):
        for pattern in patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                citation_keys = match.group(1)
                # Split multiple citations
                for cite_key in citation_keys.split(","):
                    cite_key = cite_key.strip()
                    if cite_key:
                        citation = Citation(
                            key=cite_key,
                            text=match.group(0),
                            document_path=document_path,
                            line_number=line_num,
                            context=line.strip(),
                        )
                        citations.append(citation)

    return citations


def parse_text_citations(content: str, document_path: str) -> list[Citation]:
    """Parse citations from plain text using common patterns."""
    citations = []

    # Pattern for author-year citations like (Smith, 2020) or Smith et al. (2020)
    patterns = [
        r"\(([A-Z][a-z]+(?:\s+et\s+al\.)?),?\s+(19|20)\d{2}\)",
        r"([A-Z][a-z]+(?:\s+et\s+al\.)?)\s+\((19|20)\d{2}\)",
        r"\[([A-Z][a-z]+(?:\s+et\s+al\.)?),?\s+(19|20)\d{2}\]",
    ]

    for line_num, line in enumerate(content.splitlines(), 1):
        for pattern in patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                # Create citation key from author and year
                if len(match.groups()) == 2:
                    author = (
                        match.group(1)
                        .replace(" et al.", "EtAl")
                        .replace(" ", "")
                    )
                    year = match.group(2)
                    cite_key = f"{author}{year}"

                    citation = Citation(
                        key=cite_key,
                        text=match.group(0),
                        document_path=document_path,
                        line_number=line_num,
                        context=line.strip(),
                    )
                    citations.append(citation)

    return citations


def parse_bibtex_file(bibfile_path: Path) -> list[BibEntry]:
    """Parse a BibTeX file and return list of entries."""
    content = bibfile_path.read_text(encoding="utf-8")

    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    parser.homogenize_fields = False

    try:
        bib_database = bibtexparser.loads(content, parser=parser)
    except Exception:
        # Return empty list on parse error
        return []

    entries = []
    for entry in bib_database.entries:
        bib_entry = BibEntry(
            key=entry.get("ID", ""),
            entry_type=entry.get("ENTRYTYPE", "misc"),
            fields={
                k.lower(): v
                for k, v in entry.items()
                if k not in ["ID", "ENTRYTYPE"]
            },
            raw_text=entry.get("raw", ""),
        )
        entries.append(bib_entry)

    return entries
