"""Enhanced PDF paper extractor with multiple backend support."""

import re
from pathlib import Path
from typing import Any

import pdfplumber
import PyPDF2

from ..models.paper import Paper, Reference, Section
from .base import BaseExtractor

# Import advanced PDF processing libraries
try:
    import pymupdf4llm

    PYMUPDF4LLM_AVAILABLE = True
except ImportError:
    PYMUPDF4LLM_AVAILABLE = False

try:
    from marker.convert import convert_single_pdf
    from marker.models import load_all_models

    MARKER_AVAILABLE = True
except ImportError:
    convert_single_pdf = None
    load_all_models = None
    MARKER_AVAILABLE = False


class PDFExtractor(BaseExtractor):
    """Extract content from PDF papers."""

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.use_advanced = (
            config.get("pdf", {}).get("use_advanced", True) if config else True
        )
        self.use_marker = (
            config.get("pdf", {}).get("use_marker", True) if config else True
        )

    def extract(self, file_path: Path) -> Paper:
        """Extract paper content from PDF file."""
        # Try advanced methods first if available
        if self.use_advanced:
            if self.use_marker and MARKER_AVAILABLE:
                try:
                    return self._extract_with_marker(file_path)
                except Exception as e:
                    print(f"Marker extraction failed: {e}")

            if PYMUPDF4LLM_AVAILABLE:
                try:
                    return self._extract_with_pymupdf4llm(file_path)
                except Exception as e:
                    print(f"PyMuPDF4LLM extraction failed: {e}")

        # Fallback to basic extraction
        return self._extract_basic(file_path)

    def _extract_with_marker(self, file_path: Path) -> Paper:
        """Extract using Marker for high accuracy."""
        # Convert PDF to markdown using Marker
        model_lst = load_all_models()
        full_text, images, out_meta = convert_single_pdf(
            str(file_path), model_lst
        )

        # Parse the markdown content
        return self._parse_markdown_content(
            full_text, file_path, "marker", out_meta
        )

    def _extract_with_pymupdf4llm(self, file_path: Path) -> Paper:
        """Extract using PyMuPDF4LLM for fast markdown conversion."""
        # Convert PDF to markdown
        md_text = pymupdf4llm.to_markdown(str(file_path))

        return self._parse_markdown_content(md_text, file_path, "pymupdf4llm")

    def _extract_basic(self, file_path: Path) -> Paper:
        """Basic PDF extraction using pdfplumber and PyPDF2."""
        paper = Paper(source_path=str(file_path))

        # Try pdfplumber first for better text extraction
        try:
            with pdfplumber.open(file_path) as pdf:
                # Extract text from all pages
                full_text = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text.append(text)

                combined_text = "\n".join(full_text)

                # Extract metadata from PDF info
                if pdf.metadata:
                    paper.title = pdf.metadata.get("Title", "")
                    paper.metadata["pdf_metadata"] = dict(pdf.metadata)

                # Parse content
                self._parse_pdf_content(combined_text, paper)

        except Exception:
            # Fallback to PyPDF2
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)

                # Extract metadata
                if pdf_reader.metadata:
                    paper.title = pdf_reader.metadata.get("/Title", "")
                    paper.metadata["pdf_metadata"] = {
                        k: v for k, v in pdf_reader.metadata.items()
                    }

                # Extract text
                full_text = []
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        full_text.append(text)

                combined_text = "\n".join(full_text)
                self._parse_pdf_content(combined_text, paper)

        return paper

    def _parse_markdown_content(
        self, md_text: str, file_path: Path, method: str, metadata: dict = None
    ) -> Paper:
        """Parse markdown content from advanced PDF extractors."""
        # Initialize paper object
        paper = Paper(source_path=str(file_path))
        paper.metadata = {"extraction_method": method}
        if metadata:
            paper.metadata.update(metadata)

        lines = md_text.split("\n")

        # Extract title (usually the first # heading)
        title_found = False
        for line in lines[:20]:  # Check first 20 lines
            if line.startswith("# ") and not title_found:
                paper.title = line[2:].strip()
                title_found = True
                break

        # Extract sections from markdown
        sections = []
        current_section = None
        current_content = []
        in_abstract = False
        abstract_content = []

        for line in lines:
            line = line.strip()

            # Check for headings
            if line.startswith("# "):
                # Main title, skip if already processed
                continue
            elif line.startswith("## "):
                # Save previous section
                if current_section and current_content:
                    current_section.content = "\n".join(current_content).strip()
                    sections.append(current_section)

                # Start new section
                section_title = line[3:].strip()
                current_section = Section(title=section_title, content="")
                current_content = []

                # Check if this is abstract
                if "abstract" in section_title.lower():
                    in_abstract = True
                else:
                    in_abstract = False
            elif line.startswith("### "):
                # Subsection - add to current content for now
                # Could be enhanced to create proper subsections
                if current_section:
                    if current_content:
                        current_content.append("")  # Add spacing
                    current_content.append(f"**{line[4:].strip()}**")
            else:
                # Regular content
                if in_abstract:
                    if line:  # Non-empty line
                        abstract_content.append(line)
                elif current_section:
                    if line:  # Non-empty line
                        current_content.append(line)

        # Save last section
        if current_section and current_content:
            current_section.content = "\n".join(current_content).strip()
            sections.append(current_section)

        # Set abstract
        if abstract_content:
            paper.abstract = " ".join(abstract_content)

        paper.sections = sections

        # Extract references from markdown
        references = []
        ref_pattern = r"^\[(\d+)\]\s*(.*)"
        ref_counter = 1

        for line in lines:
            match = re.match(ref_pattern, line.strip())
            if match:
                ref_key = match.group(1)
                ref_text = match.group(2)
                references.append(Reference(key=f"ref{ref_key}", text=ref_text))
            elif line.strip().startswith("- ") and any(
                "doi" in line.lower() or "http" in line.lower()
                for line in [line]
            ):
                # Handle bullet point references
                ref_text = line.strip()[2:]  # Remove '- '
                references.append(
                    Reference(key=f"ref{ref_counter}", text=ref_text)
                )
                ref_counter += 1

        paper.references = references
        return paper

    def _parse_pdf_content(self, text: str, paper: Paper):
        """Parse content from extracted PDF text."""
        lines = text.split("\n")

        # Try to identify title (usually one of the first non-empty lines)
        if not paper.title:
            for line in lines[:20]:  # Check first 20 lines
                line = line.strip()
                if (
                    len(line) > 10 and len(line) < 200
                ):  # Reasonable title length
                    # Heuristic: titles often don't end with period
                    if not line.endswith("."):
                        paper.title = line
                        break

        # Extract abstract
        abstract_start = -1
        abstract_end = -1

        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            if line_lower in ["abstract", "abstract."]:
                abstract_start = i + 1
            elif abstract_start > 0 and abstract_end < 0:
                # Look for next section
                if line_lower in [
                    "introduction",
                    "keywords",
                    "1. introduction",
                    "1 introduction",
                ]:
                    abstract_end = i
                    break

        if abstract_start > 0:
            if abstract_end < 0:
                abstract_end = min(
                    abstract_start + 20, len(lines)
                )  # Max 20 lines

            abstract_lines = lines[abstract_start:abstract_end]
            paper.abstract = " ".join(
                line.strip() for line in abstract_lines if line.strip()
            )

        # Extract sections
        sections = []
        current_section = None
        current_content = []

        section_indicators = [
            "introduction",
            "methodology",
            "methods",
            "results",
            "discussion",
            "conclusion",
            "conclusions",
            "related work",
            "background",
            "literature review",
            "experiments",
        ]

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            # Check if this is a section header
            is_section = False
            for indicator in section_indicators:
                if indicator in line_lower and len(line_stripped) < 100:
                    is_section = True
                    break

            # Also check for numbered sections
            import re

            if re.match(r"^\d+\.?\s+[A-Z]", line_stripped):
                is_section = True

            if is_section:
                # Save previous section
                if current_section:
                    current_section.content = " ".join(current_content).strip()
                    sections.append(current_section)

                # Start new section
                current_section = Section(title=line_stripped, content="")
                current_content = []
            elif current_section and line_stripped:
                current_content.append(line_stripped)

        # Save last section
        if current_section:
            current_section.content = " ".join(current_content).strip()
            sections.append(current_section)

        paper.sections = sections

        # Extract references
        ref_start = -1
        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            if line_lower in ["references", "bibliography", "references."]:
                ref_start = i + 1
                break

        if ref_start > 0:
            references = []
            current_ref = []

            for line in lines[ref_start:]:
                line_stripped = line.strip()

                # Check if this starts a new reference
                if line_stripped and (
                    line_stripped[0].isdigit() or line_stripped.startswith("[")
                ):
                    if current_ref:
                        ref_text = " ".join(current_ref)
                        references.append(
                            Reference(
                                key=f"ref{len(references) + 1}", text=ref_text
                            )
                        )
                    current_ref = [line_stripped]
                elif current_ref and line_stripped:
                    current_ref.append(line_stripped)

            # Add last reference
            if current_ref:
                ref_text = " ".join(current_ref)
                references.append(
                    Reference(key=f"ref{len(references) + 1}", text=ref_text)
                )

            paper.references = references
