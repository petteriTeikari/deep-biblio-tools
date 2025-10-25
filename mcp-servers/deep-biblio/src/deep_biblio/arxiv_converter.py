"""Manuscript to arXiv converter with Zotero citation management."""

import json
import re
from pathlib import Path
from typing import Any

from loguru import logger


class ZoteroCitationMatcher:
    """Match inline citations to Zotero library and generate BibTeX."""

    def __init__(self, zotero_json_path: str | Path):
        """Initialize with Zotero CSL JSON export."""
        self.zotero_json_path = Path(zotero_json_path)
        self.entries = self._load_zotero_json()
        self._build_lookup_indices()

    def _load_zotero_json(self) -> list[dict[str, Any]]:
        """Load Zotero CSL JSON file."""
        with open(self.zotero_json_path, encoding="utf-8") as f:
            entries = json.load(f)
        logger.info(f"Loaded {len(entries)} entries from Zotero")
        return entries

    def _build_lookup_indices(self) -> None:
        """Build lookup indices for fast citation matching."""
        self.title_index = {}
        self.author_index = {}
        self.doi_index = {}
        self.arxiv_index = {}
        self.url_index = {}

        for entry in self.entries:
            # Index by title (normalized)
            title = entry.get("title", "").lower().strip()
            if title:
                self.title_index[title] = entry

            # Index by first author + year
            authors = entry.get("author", [])
            year = self._extract_year(entry)
            if authors and year:
                first_author = authors[0].get("family", "").lower()
                key = f"{first_author}{year}"
                self.author_index[key] = entry

            # Index by DOI
            doi = entry.get("DOI", "")
            if doi:
                self.doi_index[doi.lower()] = entry

            # Index by arXiv ID
            arxiv_id = self._extract_arxiv_id(entry)
            if arxiv_id:
                self.arxiv_index[arxiv_id] = entry

            # Index by URL
            url = entry.get("URL", "")
            if url:
                self.url_index[url] = entry

    def _extract_year(self, entry: dict) -> str | None:
        """Extract year from CSL JSON entry."""
        issued = entry.get("issued", {})
        date_parts = issued.get("date-parts", [])
        if date_parts and date_parts[0]:
            return str(date_parts[0][0])
        return None

    def _extract_arxiv_id(self, entry: dict) -> str | None:
        """Extract arXiv ID from entry."""
        # Check DOI field
        doi = entry.get("DOI", "")
        if "arxiv" in doi.lower():
            match = re.search(r"(\d{4}\.\d{4,5})", doi)
            if match:
                return match.group(1)

        # Check note field
        note = entry.get("note", "")
        if "arxiv" in note.lower():
            match = re.search(r"(\d{4}\.\d{4,5})", note)
            if match:
                return match.group(1)

        # Check URL
        url = entry.get("URL", "")
        if "arxiv.org" in url:
            match = re.search(r"(\d{4}\.\d{4,5})", url)
            if match:
                return match.group(1)

        return None

    def extract_citations_from_markdown(self, markdown_path: str | Path) -> list[dict]:
        """Extract all inline citations from markdown file.

        Returns list of dicts with: author, year, url, line_number
        """
        markdown_path = Path(markdown_path)
        content = markdown_path.read_text(encoding="utf-8")

        citations = []
        # Pattern: [Author, Year](URL) or [Author et al., Year](URL)
        pattern = r"\[([^\]]+?),\s*(\d{4})\]\(([^\)]+)\)"

        for line_no, line in enumerate(content.split("\n"), 1):
            for match in re.finditer(pattern, line):
                author_part = match.group(1).strip()
                year = match.group(2)
                url = match.group(3)

                citations.append(
                    {
                        "author": author_part,
                        "year": year,
                        "url": url,
                        "line_number": line_no,
                        "original": match.group(0),
                    }
                )

        logger.info(f"Extracted {len(citations)} citations from {markdown_path.name}")
        return citations

    def match_citation(self, citation: dict) -> dict | None:
        """Match a citation to Zotero entry.

        Returns Zotero entry dict or None if not found.
        """
        url = citation["url"]
        year = citation["year"]
        author = citation["author"].lower().replace(" et al.", "")

        # Try DOI matching
        if "doi.org" in url:
            doi = url.split("doi.org/")[-1]
            if doi.lower() in self.doi_index:
                return self.doi_index[doi.lower()]

        # Try arXiv matching
        if "arxiv.org" in url:
            match = re.search(r"(\d{4}\.\d{4,5})", url)
            if match:
                arxiv_id = match.group(1)
                if arxiv_id in self.arxiv_index:
                    return self.arxiv_index[arxiv_id]

        # Try URL matching
        if url in self.url_index:
            return self.url_index[url]

        # Try author + year matching
        author_key = f"{author}{year}"
        if author_key in self.author_index:
            return self.author_index[author_key]

        return None

    def generate_bibtex_entry(self, entry: dict, cite_key: str) -> str:
        """Generate BibTeX entry from CSL JSON with permalink URLs."""
        entry_type = entry.get("type", "misc")

        # Map CSL types to BibTeX types
        type_mapping = {
            "article-journal": "article",
            "article": "article",
            "paper-conference": "inproceedings",
            "chapter": "inchapter",
            "book": "book",
            "thesis": "phdthesis",
            "webpage": "misc",
        }
        bibtex_type = type_mapping.get(entry_type, "misc")

        # Start BibTeX entry
        lines = [f"@{bibtex_type}{{{cite_key},"]

        # Title
        title = entry.get("title", "")
        if title:
            lines.append(f"  title = {{{title}}},")

        # Authors
        authors = entry.get("author", [])
        if authors:
            author_str = " and ".join(
                f"{a.get('family', '')}, {a.get('given', '')}" for a in authors
            )
            lines.append(f"  author = {{{author_str}}},")

        # Year
        year = self._extract_year(entry)
        if year:
            lines.append(f"  year = {{{year}}},")

        # Journal/venue
        container = entry.get("container-title", "")
        if container:
            if bibtex_type == "article":
                lines.append(f"  journal = {{{container}}},")
            elif bibtex_type == "inproceedings":
                lines.append(f"  booktitle = {{{container}}},")

        # Volume, issue, pages
        volume = entry.get("volume", "")
        if volume:
            lines.append(f"  volume = {{{volume}}},")

        issue = entry.get("issue", "")
        if issue:
            lines.append(f"  number = {{{issue}}},")

        pages = entry.get("page", "")
        if pages:
            lines.append(f"  pages = {{{pages}}},")

        # Publisher
        publisher = entry.get("publisher", "")
        if publisher:
            lines.append(f"  publisher = {{{publisher}}},")

        # DOI or arXiv as permalink (PRIORITY: DOI > arXiv > URL)
        doi = entry.get("DOI", "")
        arxiv_id = self._extract_arxiv_id(entry)

        if doi:
            lines.append(f"  doi = {{{doi}}},")
            lines.append(f"  url = {{https://doi.org/{doi}}},")
        elif arxiv_id:
            lines.append(f"  eprint = {{{arxiv_id}}},")
            lines.append("  archivePrefix = {arXiv},")
            lines.append(f"  url = {{https://arxiv.org/abs/{arxiv_id}}},")
        else:
            # Fallback to URL (but warn - should be permalink)
            url = entry.get("URL", "")
            if url:
                lines.append(f"  url = {{{url}}},")
                logger.warning(f"No DOI or arXiv for {cite_key}, using URL: {url}")

        lines.append("}")
        return "\n".join(lines)

    def generate_cite_key(self, entry: dict) -> str:
        """Generate BibTeX citation key from entry."""
        authors = entry.get("author", [])
        year = self._extract_year(entry) or "XXXX"

        if authors:
            first_author = authors[0].get("family", "Unknown")
        else:
            first_author = "Unknown"

        # Clean author name
        first_author = re.sub(r"[^a-zA-Z]", "", first_author)

        return f"{first_author}{year}"


def create_arxiv_package(
    markdown_path: str | Path,
    zotero_json_path: str | Path,
    output_dir: str | Path,
    author: str,
    single_column: bool = False,
) -> dict:
    """Create complete arXiv submission package.

    Returns dict with:
    - matched_count: int
    - missing_count: int
    - missing_citations: list of dicts
    - bibtex_path: Path
    - latex_path: Path (if conversion succeeds)
    - warnings: list of str
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    matcher = ZoteroCitationMatcher(zotero_json_path)
    citations = matcher.extract_citations_from_markdown(markdown_path)

    matched = []
    missing = []
    warnings = []

    # Match citations
    for cite in citations:
        entry = matcher.match_citation(cite)
        if entry:
            matched.append((cite, entry))
        else:
            missing.append(cite)
            logger.warning(f"Missing: {cite['author']}, {cite['year']} - {cite['url']}")

    # Generate BibTeX file
    bibtex_entries = {}
    for cite, entry in matched:
        cite_key = matcher.generate_cite_key(entry)
        if cite_key not in bibtex_entries:
            bibtex_entries[cite_key] = matcher.generate_bibtex_entry(entry, cite_key)

    bibtex_path = output_dir / "references.bib"
    bibtex_content = "\n\n".join(bibtex_entries.values())
    bibtex_path.write_text(bibtex_content, encoding="utf-8")

    logger.info(f"Generated BibTeX with {len(bibtex_entries)} entries at {bibtex_path}")

    # Convert markdown to LaTeX (if converter available)
    latex_path = None
    try:
        import subprocess
        import sys
        from pathlib import Path as PathLib

        # Add deep-biblio-tools to path
        deep_biblio_path = PathLib(
            "/Users/petteri/Dropbox/github-personal/deep-biblio-tools"
        )
        if str(deep_biblio_path) not in sys.path:
            sys.path.insert(0, str(deep_biblio_path))

        from src.converters.md_to_latex.converter import MarkdownToLatexConverter

        logger.info("Converting markdown to LaTeX...")

        # Get markdown file size for validation
        markdown_size = Path(markdown_path).stat().st_size

        converter = MarkdownToLatexConverter(
            output_dir=output_dir,
            arxiv_ready=True,
            two_column=not single_column,
            bibliography_style="biblio-style-compact",
        )

        latex_path = converter.convert(
            markdown_file=Path(markdown_path), author=author, verbose=False
        )

        logger.info(f"Generated LaTeX at {latex_path}")

        # Validate LaTeX output
        tex_file = Path(latex_path)
        tex_size = tex_file.stat().st_size

        # Check file size ratio (should be <5x markdown size)
        size_ratio = tex_size / markdown_size
        if size_ratio > 5.0:
            logger.warning(
                f"LaTeX file is {size_ratio:.1f}x larger than markdown - "
                f"may indicate conversion issues"
            )
            warnings.append(
                f"LaTeX file unexpectedly large ({size_ratio:.1f}x markdown size)"
            )

        # Validate PDF compilation
        logger.info("Validating PDF compilation with pdflatex...")
        compile_result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", str(tex_file)],
            cwd=tex_file.parent,
            capture_output=True,
            text=True,
            timeout=120,
        )

        pdf_path = tex_file.with_suffix(".pdf")
        if compile_result.returncode == 0 and pdf_path.exists():
            logger.success(f"[PASS] PDF validation passed: {pdf_path}")
        else:
            logger.error("PDF compilation failed - LaTeX has errors")
            warnings.append("PDF compilation failed - LaTeX contains errors")

            # Log compilation errors for debugging
            if compile_result.stderr:
                error_lines = compile_result.stderr.split("\n")
                fatal_errors = [
                    line for line in error_lines if "Error" in line or "Fatal" in line
                ]
                if fatal_errors:
                    logger.error(f"Fatal LaTeX errors: {'; '.join(fatal_errors[:5])}")

    except subprocess.TimeoutExpired:
        logger.error("PDF compilation timeout (>120s)")
        warnings.append("PDF compilation timeout")
    except FileNotFoundError as e:
        if "pdflatex" in str(e):
            logger.warning("pdflatex not found - skipping PDF validation")
            warnings.append("PDF validation skipped (pdflatex not installed)")
        else:
            raise
    except ImportError as e:
        logger.warning(f"LaTeX converter not available: {e}")
        warnings.append("LaTeX conversion skipped (converter not available)")
    except Exception as e:
        logger.error(f"LaTeX conversion failed: {e}")
        warnings.append(f"LaTeX conversion failed: {str(e)}")

    return {
        "matched_count": len(matched),
        "missing_count": len(missing),
        "missing_citations": missing,
        "bibtex_path": str(bibtex_path),
        "latex_path": str(latex_path) if latex_path else None,
        "warnings": warnings,
        "total_citations": len(citations),
    }
