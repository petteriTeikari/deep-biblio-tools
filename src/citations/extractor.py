"""Extract citations from various text formats deterministically."""

import logging

# import re  # Banned - using string methods instead
from dataclasses import dataclass

from markdown_it import MarkdownIt


@dataclass
class RawCitation:
    """Raw citation extracted from text."""

    text: str  # Display text
    url: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    pmid: str | None = None
    title: str | None = None
    authors: str | None = None  # Raw author string
    year: str | None = None

    # Location info for replacements
    line_number: int = 0
    start_pos: int = 0
    end_pos: int = 0
    file_path: str | None = None

    # Context for better understanding
    context_before: str = ""
    context_after: str = ""
    full_line: str = ""

    # Format info
    format: str = "plain"  # markdown, latex, bibtex


class CitationExtractor:
    """Extract citations from various text formats."""

    # Academic domain patterns
    ACADEMIC_DOMAINS = {
        "doi.org",
        "arxiv.org",
        "pubmed.ncbi.nlm.nih.gov",
        "researchgate.net",
        "ieee.org",
        "acm.org",
        "springer.com",
        "sciencedirect.com",
        "wiley.com",
        "nature.com",
        "cambridge.org",
        "oxford.org",
        "oup.com",
        "tandfonline.com",
        "sagepub.com",
        "frontiersin.org",
        "mdpi.com",
        "scholar.google.com",
        "semanticscholar.org",
        "jstor.org",
        "plos.org",
        "biomedcentral.com",
        "nih.gov",
        "europepmc.org",
        "biorxiv.org",
        "medrxiv.org",
    }

    # Identifier patterns - commented out due to regex ban
    # DOI_PATTERN = re.compile(r"10\.\d{4,}/[-._;()/:\w]+", re.IGNORECASE)
    # ARXIV_PATTERN = re.compile(
    #     r"(?:arxiv:|(?:https?://)?arxiv\.org/abs/)(\d{4}\.\d{4,5})",
    #     re.IGNORECASE,
    # )
    # PMID_PATTERN = re.compile(r"(?:pmid:\s*|pubmed/)(\d+)", re.IGNORECASE)

    def __init__(self):
        """Initialize extractor."""
        self.logger = logging.getLogger(__name__)
        self.md_parser = MarkdownIt()

    def extract_from_markdown(
        self, text: str, file_path: str | None = None
    ) -> list[RawCitation]:
        """Extract citations from markdown text using AST."""
        citations = []

        # Parse markdown to AST
        env = {}
        tokens = self.md_parser.parse(text, env)

        # Process tokens to find citations
        lines = text.split("\n")
        line_starts = [0]
        for line in lines[:-1]:
            line_starts.append(line_starts[-1] + len(line) + 1)

        for token in tokens:
            if token.type == "inline" and token.children:
                line_num = token.map[0] + 1 if token.map else 0

                # Process inline tokens
                for i, child in enumerate(token.children):
                    if child.type == "link_open":
                        # Find corresponding link_close and text
                        # In markdown-it-py, attrs is a dict of attributes
                        url = ""
                        if hasattr(child, "attrs") and child.attrs:
                            # attrs can be a dict or a list of [key, value] pairs
                            if isinstance(child.attrs, dict):
                                url = child.attrs.get("href", "")
                            elif isinstance(child.attrs, list):
                                for attr in child.attrs:
                                    if len(attr) >= 2 and attr[0] == "href":
                                        url = attr[1]
                                        break

                        # Find the text token
                        text_parts = []
                        j = i + 1
                        while (
                            j < len(token.children)
                            and token.children[j].type != "link_close"
                        ):
                            if token.children[j].type == "text":
                                text_parts.append(token.children[j].content)
                            j += 1

                        citation_text = "".join(text_parts)

                        if self._is_academic_url(url):
                            # Extract context
                            line_content = (
                                lines[line_num - 1] if line_num > 0 else ""
                            )

                            # Create citation
                            raw_citation = RawCitation(
                                text=citation_text,
                                url=url,
                                line_number=line_num,
                                file_path=file_path,
                                full_line=line_content.strip(),
                                format="markdown",
                            )

                            # Extract identifiers from URL
                            self._extract_identifiers_from_url(raw_citation)

                            citations.append(raw_citation)

        return citations

    def extract_from_latex(
        self, text: str, file_path: str | None = None
    ) -> list[RawCitation]:
        """Extract citations from LaTeX text."""
        citations = []
        lines = text.split("\n")

        # Common LaTeX citation patterns

        for line_num, line in enumerate(lines, 1):
            # Extract LaTeX citations using string methods
            i = 0
            while i < len(line):
                # Look for \cite
                if line[i : i + 5] == "\\cite":
                    # Check if it's \citep or \citet
                    j = i + 5
                    if j < len(line) and line[j] in "pt":
                        j += 1

                    # Skip optional parameters [...]
                    if j < len(line) and line[j] == "[":
                        while j < len(line) and line[j] != "]":
                            j += 1
                        if j < len(line):
                            j += 1  # Skip ]

                    # Skip whitespace
                    while j < len(line) and line[j] in " \t":
                        j += 1

                    # Check for opening brace
                    if j < len(line) and line[j] == "{":
                        # Find closing brace
                        k = j + 1
                        brace_count = 1
                        while k < len(line) and brace_count > 0:
                            if line[k] == "{":
                                brace_count += 1
                            elif line[k] == "}":
                                brace_count -= 1
                            k += 1

                        if brace_count == 0:
                            # Extract citation key
                            content = line[j + 1 : k - 1]
                            raw_citation = RawCitation(
                                text=content,
                                line_number=line_num,
                                file_path=file_path,
                                full_line=line.strip(),
                                format="latex",
                            )
                            citations.append(raw_citation)

                        i = k
                        continue

                # Look for \href
                elif line[i : i + 5] == "\\href":
                    j = i + 5
                    # Skip whitespace
                    while j < len(line) and line[j] in " \t":
                        j += 1

                    if j < len(line) and line[j] == "{":
                        # Find first closing brace (URL)
                        k = j + 1
                        brace_count = 1
                        while k < len(line) and brace_count > 0:
                            if line[k] == "{":
                                brace_count += 1
                            elif line[k] == "}":
                                brace_count -= 1
                            k += 1

                        if brace_count == 0:
                            url = line[j + 1 : k - 1]

                            # Look for second brace (text)
                            if k < len(line) and line[k] == "{":
                                text_pos = k + 1
                                brace_count = 1
                                while text_pos < len(line) and brace_count > 0:
                                    if line[text_pos] == "{":
                                        brace_count += 1
                                    elif line[text_pos] == "}":
                                        brace_count -= 1
                                    text_pos += 1

                                if brace_count == 0:
                                    text = line[k + 1 : text_pos - 1]

                                    if self._is_academic_url(url):
                                        raw_citation = RawCitation(
                                            text=text,
                                            url=url,
                                            line_number=line_num,
                                            file_path=file_path,
                                            full_line=line.strip(),
                                            format="latex",
                                        )
                                        self._extract_identifiers_from_url(
                                            raw_citation
                                        )
                                        citations.append(raw_citation)

                                i = text_pos
                                continue

                        i = k
                        continue

                # Look for \url
                elif line[i : i + 4] == "\\url":
                    j = i + 4
                    # Skip whitespace
                    while j < len(line) and line[j] in " \t":
                        j += 1

                    if j < len(line) and line[j] == "{":
                        # Find closing brace
                        k = j + 1
                        brace_count = 1
                        while k < len(line) and brace_count > 0:
                            if line[k] == "{":
                                brace_count += 1
                            elif line[k] == "}":
                                brace_count -= 1
                            k += 1

                        if brace_count == 0:
                            content = line[j + 1 : k - 1]

                            if self._is_academic_url(content):
                                raw_citation = RawCitation(
                                    text=content,
                                    url=content,
                                    line_number=line_num,
                                    file_path=file_path,
                                    full_line=line.strip(),
                                    format="latex",
                                )
                                self._extract_identifiers_from_url(raw_citation)
                                citations.append(raw_citation)

                        i = k
                        continue

                i += 1

        return citations

    def extract_from_bibtex(
        self, text: str, file_path: str | None = None
    ) -> list[RawCitation]:
        """Extract citations from BibTeX entries."""
        # This would use bibtexparser but keeping it simple for now
        citations = []

        # Parse BibTeX entries using string methods
        entries = []
        i = 0
        while i < len(text):
            if text[i] == "@":
                # Find entry type
                j = i + 1
                while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                    j += 1

                if j > i + 1:
                    text[i + 1 : j]

                    # Skip whitespace
                    while j < len(text) and text[j].isspace():
                        j += 1

                    # Look for opening brace
                    if j < len(text) and text[j] == "{":
                        k = j + 1
                        brace_count = 1
                        start_pos = k

                        # Find matching closing brace
                        while k < len(text) and brace_count > 0:
                            if text[k] == "{":
                                brace_count += 1
                            elif text[k] == "}":
                                brace_count -= 1
                            k += 1

                        if brace_count == 0:
                            # Extract entry content
                            entry_content = text[start_pos : k - 1]

                            # Find first comma (separates key from fields)
                            comma_pos = entry_content.find(",")
                            if comma_pos > 0:
                                entry_key = entry_content[:comma_pos].strip()
                                fields_text = entry_content[comma_pos + 1 :]
                                entries.append((entry_key, fields_text))

                        i = k
                        continue
            i += 1

        for entry_key, fields_text in entries:
            # Extract basic fields
            fields = self._parse_bibtex_fields(fields_text)

            raw_citation = RawCitation(
                text=entry_key,
                title=fields.get("title", ""),
                authors=fields.get("author", ""),
                year=fields.get("year", ""),
                url=fields.get("url"),
                doi=fields.get("doi"),
                file_path=file_path,
                format="bibtex",
            )

            # Extract identifiers
            if "arxiv" in fields:
                raw_citation.arxiv_id = fields["arxiv"]
            elif "eprint" in fields and "archivePrefix" in fields:
                if fields["archivePrefix"].lower() == "arxiv":
                    raw_citation.arxiv_id = fields["eprint"]

            citations.append(raw_citation)

        return citations

    def extract_identifiers(self, text: str) -> dict[str, str]:
        """Extract all identifiers from a text string."""
        identifiers = {}

        # DOI - look for pattern 10.xxxx/...
        doi = self._extract_doi_from_text(text)
        if doi:
            identifiers["doi"] = doi

        # ArXiv - look for arxiv patterns
        arxiv_id = self._extract_arxiv_from_text(text)
        if arxiv_id:
            identifiers["arxiv"] = arxiv_id

        # PMID - look for pubmed IDs
        pmid = self._extract_pmid_from_text(text)
        if pmid:
            identifiers["pmid"] = pmid

        return identifiers

    def _extract_doi_from_text(self, text: str) -> str | None:
        """Extract DOI from text without regex."""
        text_lower = text.lower()

        # Look for "10." pattern
        start = text_lower.find("10.")
        if start == -1:
            return None

        # Check if followed by digits
        i = start + 3
        digit_count = 0
        while i < len(text) and text[i].isdigit():
            digit_count += 1
            i += 1

        if digit_count < 4:  # Need at least 4 digits
            return None

        # Look for slash
        if i >= len(text) or text[i] != "/":
            return None

        # Extract rest of DOI (alphanumeric, dash, underscore, semicolon, parens, colon, dot)
        j = i + 1
        while j < len(text):
            char = text[j]
            if char.isalnum() or char in "-_.;()/:":
                j += 1
            else:
                break

        if j > i + 1:  # Must have content after slash
            return text[start:j]
        return None

    def _extract_arxiv_from_text(self, text: str) -> str | None:
        """Extract arXiv ID from text without regex."""
        text_lower = text.lower()

        # Look for arxiv patterns
        for prefix in ["arxiv:", "arxiv.org/abs/"]:
            pos = text_lower.find(prefix)
            if pos != -1:
                start = pos + len(prefix)
                # Extract YYYY.NNNNN pattern
                if start + 9 <= len(text):
                    potential_id = text[start : start + 10]
                    # Validate format
                    if (
                        len(potential_id) >= 9
                        and potential_id[:4].isdigit()
                        and potential_id[4] == "."
                        and potential_id[5:9].isdigit()
                    ):
                        # May have 5th digit
                        if (
                            len(potential_id) == 10
                            and potential_id[9].isdigit()
                        ):
                            return potential_id
                        return potential_id[:9]
        return None

    def _extract_pmid_from_text(self, text: str) -> str | None:
        """Extract PMID from text without regex."""
        text_lower = text.lower()

        # Look for PMID patterns
        for prefix in ["pmid:", "pmid :", "pubmed/"]:
            pos = text_lower.find(prefix)
            if pos != -1:
                start = pos + len(prefix)
                # Skip whitespace
                while start < len(text) and text[start].isspace():
                    start += 1
                # Extract digits
                end = start
                while end < len(text) and text[end].isdigit():
                    end += 1
                if end > start:
                    return text[start:end]
        return None

    def _is_academic_url(self, url: str) -> bool:
        """Check if URL is likely academic content."""
        if not url:
            return False

        url_lower = url.lower()

        # Check for PDF files
        if url_lower.endswith(".pdf"):
            return True

        # Check academic domains
        for domain in self.ACADEMIC_DOMAINS:
            if domain in url_lower:
                return True

        # Check for .edu domains
        if ".edu" in url_lower:
            return True

        return False

    def _extract_identifiers_from_url(self, citation: RawCitation) -> None:
        """Extract identifiers from URL."""
        if not citation.url:
            return

        url = citation.url

        # DOI
        if "doi.org/" in url:
            doi_pos = url.find("doi.org/")
            if doi_pos != -1:
                doi_start = doi_pos + 8  # len("doi.org/")
                citation.doi = url[doi_start:]

        # ArXiv
        if "arxiv.org" in url:
            arxiv_id = self._extract_arxiv_from_text(url)
            if arxiv_id:
                citation.arxiv_id = arxiv_id

        # PubMed
        if "pubmed" in url or "ncbi.nlm.nih.gov" in url:
            # Look for ID at end of URL
            url_parts = url.rstrip("/").split("/")
            if url_parts and url_parts[-1].isdigit():
                citation.pmid = url_parts[-1]

    def _parse_bibtex_fields(self, fields_text: str) -> dict[str, str]:
        """Parse BibTeX fields from text."""
        fields = {}

        # Parse BibTeX fields using string methods
        i = 0
        while i < len(fields_text):
            # Look for field name
            if fields_text[i].isalpha():
                j = i
                while j < len(fields_text) and (
                    fields_text[j].isalnum() or fields_text[j] == "_"
                ):
                    j += 1

                field_name = fields_text[i:j].lower()

                # Skip whitespace
                while j < len(fields_text) and fields_text[j].isspace():
                    j += 1

                # Look for =
                if j < len(fields_text) and fields_text[j] == "=":
                    j += 1
                    # Skip whitespace
                    while j < len(fields_text) and fields_text[j].isspace():
                        j += 1

                    # Look for opening delimiter
                    if j < len(fields_text) and fields_text[j] in '"{':
                        delimiter = "}" if fields_text[j] == "{" else '"'
                        j += 1
                        value_start = j

                        # Find closing delimiter
                        while (
                            j < len(fields_text) and fields_text[j] != delimiter
                        ):
                            j += 1

                        if j < len(fields_text):
                            field_value = fields_text[value_start:j].strip()
                            fields[field_name] = field_value
                            j += 1

                i = j
            else:
                i += 1

        return fields
