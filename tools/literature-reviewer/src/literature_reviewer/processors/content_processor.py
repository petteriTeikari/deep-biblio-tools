"""Content processing utilities."""

from typing import Any


class ContentProcessor:
    """Process and extract content from papers."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def extract_metadata(self, content: str) -> dict[str, Any]:
        """Extract metadata from paper content."""
        metadata = {
            "title": "",
            "authors": [],
            "journal": "",
            "year": "",
            "doi": "",
            "keywords": [],
        }

        lines = content.split("\n")

        # Extract title (usually first heading)
        for line in lines:
            if line.strip().startswith("# ") and not metadata["title"]:
                metadata["title"] = line[2:].strip()
                break

        # Extract authors
        for i, line in enumerate(lines):
            if "Author" in line and "links" in line:
                # Check next few lines for author names
                for j in range(i + 1, min(i + 10, len(lines))):
                    if lines[j].strip() and not lines[j].startswith("#"):
                        words = lines[j].split()
                        if (
                            words
                            and sum(1 for w in words if w[0].isupper())
                            > len(words) / 2
                        ):
                            metadata["authors"].extend(
                                [w for w in words if w[0].isupper()]
                            )

        # Extract DOI
        for line in lines:
            if "doi" in line.lower() or "10." in line:
                doi_start = line.find("10.")
                if doi_start != -1:
                    doi_end = line.find(" ", doi_start)
                    if doi_end == -1:
                        doi_end = len(line)
                    metadata["doi"] = line[doi_start:doi_end].strip()

        # Extract year
        for line in lines:
            for word in line.split():
                # Check if word is a valid digit before trying to convert
                if word.isdigit():
                    try:
                        year_val = int(word)
                        if 1900 <= year_val <= 2099:
                            metadata["year"] = word
                            break
                    except ValueError:
                        # Skip if conversion fails (e.g., Unicode digits)
                        continue
            if metadata["year"]:
                break

        # Extract keywords
        for i, line in enumerate(lines):
            if "keywords" in line.lower():
                keywords_text = lines[i : i + 5]
                for kw_line in keywords_text:
                    if "•" in kw_line or ";" in kw_line or "," in kw_line:
                        for delimiter in ["•", ";", ","]:
                            if delimiter in kw_line:
                                keywords = [
                                    k.strip()
                                    for k in kw_line.split(delimiter)
                                    if k.strip()
                                ]
                                metadata["keywords"].extend(keywords)

        return metadata

    def extract_citations_and_references(
        self, content: str
    ) -> tuple[dict[str, str], list[str]]:
        """Extract citations and references with hyperlinks preserved."""
        citations = {}
        references = []

        lines = content.split("\n")
        in_references = False
        current_ref = []

        for i, line in enumerate(lines):
            # Check for reference section
            if line.strip().lower() in [
                "references",
                "bibliography",
                "## references",
                "### references",
            ]:
                in_references = True
                continue

            if in_references:
                # Each reference typically starts with a number or bullet
                if line.strip() and (
                    line.strip()[0].isdigit()
                    or line.strip().startswith("-")
                    or line.strip().startswith("•")
                    or line.strip().startswith("[")
                ):
                    if current_ref:
                        references.append(" ".join(current_ref))
                    current_ref = [line.strip()]
                elif line.strip() and current_ref:
                    current_ref.append(line.strip())
            else:
                # Look for inline citations with hyperlinks
                if "[" in line and "](" in line:
                    start = 0
                    while True:
                        bracket_start = line.find("[", start)
                        if bracket_start == -1:
                            break
                        bracket_end = line.find("]", bracket_start)
                        if bracket_end == -1:
                            break
                        paren_start = line.find("(", bracket_end)
                        if paren_start != bracket_end + 1:
                            start = bracket_end + 1
                            continue
                        paren_end = line.find(")", paren_start)
                        if paren_end == -1:
                            break

                        text = line[bracket_start + 1 : bracket_end]
                        url = line[paren_start + 1 : paren_end]

                        # Check if this is a citation (contains year)
                        if any(
                            year in text
                            for year in ["199", "200", "201", "202"]
                        ):
                            citations[text] = url

                        start = paren_end + 1

        if current_ref:
            references.append(" ".join(current_ref))

        return citations, references

    def parse_sections(self, content: str) -> list[dict[str, Any]]:
        """Parse content into sections with importance scores."""
        sections = []
        current_section = {"title": "", "content": [], "importance": 0}

        lines = content.split("\n")
        for line in lines:
            if line.startswith("#"):
                if current_section["content"]:
                    sections.append(current_section)

                # Determine section importance
                importance = 0
                lower_line = line.lower()
                if any(
                    word in lower_line
                    for word in [
                        "abstract",
                        "summary",
                        "conclusion",
                        "results",
                        "findings",
                    ]
                ):
                    importance = 10
                elif any(
                    word in lower_line
                    for word in ["introduction", "method", "approach"]
                ):
                    importance = 8
                elif any(
                    word in lower_line
                    for word in ["related", "background", "literature"]
                ):
                    importance = 6
                else:
                    importance = 4

                current_section = {
                    "title": line.strip("#").strip(),
                    "content": [],
                    "importance": importance,
                }
            else:
                if line.strip():
                    current_section["content"].append(line)

        if current_section["content"]:
            sections.append(current_section)

        # Join content lines
        for section in sections:
            section["content"] = "\n".join(section["content"])

        return sections
