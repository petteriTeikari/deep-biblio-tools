"""XML paper extractor for JATS and other XML formats."""

import re
from pathlib import Path
from xml.etree import ElementTree as ET

from ..models.paper import Paper, Reference, Section
from .base import BaseExtractor


class XMLExtractor(BaseExtractor):
    """Extract content from XML papers (JATS format)."""

    def extract(self, file_path: Path) -> Paper:
        """Extract paper content from XML file."""
        # Parse XML
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Extract metadata
        title = self._extract_title(root)
        authors = self._extract_authors(root)
        abstract = self._extract_abstract(root)
        doi = self._extract_doi(root)
        keywords = self._extract_keywords(root)

        # Extract sections
        sections = self._extract_sections(root)

        # Extract references
        references = self._extract_references(root)

        # Create paper object
        paper = Paper(
            title=title or "Untitled",
            authors=authors,
            abstract=abstract,
            sections=sections,
            references=references,
            metadata={
                "source": "xml",
                "format": "jats",
                "doi": doi,
                "keywords": keywords,
                "file_path": str(file_path),
            },
        )

        return paper

    def _extract_title(self, root: ET.Element) -> str | None:
        """Extract article title."""
        # Look for article-title in article-meta
        title_elem = root.find(".//article-title")
        if title_elem is not None:
            return self._clean_text(title_elem)
        return None

    def _extract_authors(self, root: ET.Element) -> list[str]:
        """Extract author names."""
        authors = []

        # Look for contrib elements with contrib-type="author"
        for contrib in root.findall(".//contrib[@contrib-type='author']"):
            name_elem = contrib.find("name")
            if name_elem is not None:
                surname = name_elem.find("surname")
                given_names = name_elem.find("given-names")

                if surname is not None and given_names is not None:
                    full_name = f"{given_names.text} {surname.text}"
                    authors.append(full_name)
                elif surname is not None:
                    authors.append(surname.text)

        return authors

    def _extract_abstract(self, root: ET.Element) -> str | None:
        """Extract abstract text."""
        abstract_elem = root.find(".//abstract")
        if abstract_elem is not None:
            # Get all text from abstract, handling nested elements
            return self._clean_text(abstract_elem)
        return None

    def _extract_doi(self, root: ET.Element) -> str | None:
        """Extract DOI."""
        doi_elem = root.find(".//article-id[@pub-id-type='doi']")
        if doi_elem is not None:
            return doi_elem.text
        return None

    def _extract_keywords(self, root: ET.Element) -> list[str]:
        """Extract keywords."""
        keywords = []

        # Look for keyword groups
        for kwd_group in root.findall(".//kwd-group"):
            for kwd in kwd_group.findall("kwd"):
                if kwd.text:
                    keywords.append(kwd.text.strip())

        return keywords

    def _extract_sections(self, root: ET.Element) -> list[Section]:
        """Extract article sections."""
        sections = []

        # Look for sections in the body
        body = root.find(".//body")
        if body is None:
            return sections

        for sec_elem in body.findall(".//sec"):
            title_elem = sec_elem.find("title")
            title = (
                self._clean_text(title_elem)
                if title_elem is not None
                else "Untitled Section"
            )

            # Extract section content (excluding subsections)
            content_parts = []
            for p in sec_elem.findall("p"):
                # Only get paragraphs that are direct children or not in subsections
                if not any(
                    p in subsec.iter() for subsec in sec_elem.findall(".//sec")
                ):
                    content_parts.append(self._clean_text(p))

            content = "\n\n".join(content_parts)

            # Extract subsections
            subsections = []
            for subsec_elem in sec_elem.findall("sec"):
                subsec_title_elem = subsec_elem.find("title")
                subsec_title = (
                    self._clean_text(subsec_title_elem)
                    if subsec_title_elem is not None
                    else "Untitled Subsection"
                )

                subsec_content_parts = []
                for p in subsec_elem.findall("p"):
                    subsec_content_parts.append(self._clean_text(p))

                subsec_content = "\n\n".join(subsec_content_parts)

                if subsec_content.strip():
                    subsections.append(
                        Section(
                            title=subsec_title, content=subsec_content, level=2
                        )
                    )

            if content.strip() or subsections:
                sections.append(
                    Section(
                        title=title, content=content, subsections=subsections
                    )
                )

        return sections

    def _extract_references(self, root: ET.Element) -> list[Reference]:
        """Extract references from back matter."""
        references = []

        # Look for references in back/ref-list
        ref_list = root.find(".//back/ref-list")
        if ref_list is not None:
            for ref_elem in ref_list.findall("ref"):
                ref_id = ref_elem.get("id", "")

                # Try to extract citation text
                citation_elem = ref_elem.find(
                    ".//mixed-citation"
                ) or ref_elem.find(".//element-citation")
                if citation_elem is not None:
                    citation_text = self._clean_text(citation_elem)

                    # Try to extract DOI from citation
                    doi_elem = citation_elem.find(
                        ".//pub-id[@pub-id-type='doi']"
                    )
                    url = (
                        f"https://doi.org/{doi_elem.text}"
                        if doi_elem is not None
                        else None
                    )

                    references.append(
                        Reference(key=ref_id, text=citation_text, url=url)
                    )

        return references

    def _clean_text(self, element: ET.Element) -> str:
        """Extract and clean text from XML element."""
        if element is None:
            return ""

        # Get all text content, including from nested elements
        text_parts = []

        def extract_text(elem):
            if elem.text:
                text_parts.append(elem.text)
            for child in elem:
                extract_text(child)
                if child.tail:
                    text_parts.append(child.tail)

        extract_text(element)
        text = "".join(text_parts)

        # Clean up the text
        text = re.sub(r"\s+", " ", text)  # Multiple spaces to single space
        text = re.sub(r"\n\s*\n", "\n\n", text)  # Clean up line breaks
        text = text.strip()

        return text
