"""Concept box detection and conversion for markdown to LaTeX."""

import logging

# import re  # Banned - using string methods instead
from enum import Enum

logger = logging.getLogger(__name__)


class ConceptBoxStyle(Enum):
    """Available concept box styles."""

    PROFESSIONAL_BLUE = "professional_blue"
    MODERN_GRADIENT = "modern_gradient"
    CLEAN_MINIMAL = "clean_minimal"
    ACADEMIC_FORMAL = "academic_formal"
    TECHNICAL_DARK = "technical_dark"


class ConceptBox:
    """Represents a concept box."""

    def __init__(
        self,
        title: str,
        content: str,
        style: ConceptBoxStyle = ConceptBoxStyle.PROFESSIONAL_BLUE,
    ):
        self.title = title
        self.content = content
        self.style = style

    def to_latex(self) -> str:
        """Convert concept box to LaTeX."""
        if self.style == ConceptBoxStyle.PROFESSIONAL_BLUE:
            return self._professional_blue_style()
        elif self.style == ConceptBoxStyle.MODERN_GRADIENT:
            return self._modern_gradient_style()
        elif self.style == ConceptBoxStyle.CLEAN_MINIMAL:
            return self._clean_minimal_style()
        elif self.style == ConceptBoxStyle.ACADEMIC_FORMAL:
            return self._academic_formal_style()
        elif self.style == ConceptBoxStyle.TECHNICAL_DARK:
            return self._technical_dark_style()
        else:
            return self._professional_blue_style()

    def _professional_blue_style(self) -> str:
        """Professional blue style with tcolorbox."""
        # Color #dae0e8 in RGB is (218, 224, 232)
        return f"""\\begin{{tcolorbox}}[
    colback={{rgb,255:red,218;green,224;blue,232}},
    colframe={{rgb,255:red,180;green,190;blue,200}},
    title={{\\textbf{{{self.title}}}}},
    fonttitle=\\bfseries,
    boxrule=1pt,
    arc=4pt,
    outer arc=4pt,
    top=10pt,
    bottom=10pt,
    left=10pt,
    right=10pt
]
{self.content}
\\end{{tcolorbox}}"""

    def _modern_gradient_style(self) -> str:
        """Modern gradient style."""
        return f"""\\begin{{tcolorbox}}[
    enhanced,
    colback=white,
    colframe=blue!50!black,
    colbacktitle=blue!10!white,
    coltitle=blue!70!black,
    title={{\\textbf{{{self.title}}}}},
    fonttitle=\\bfseries\\sffamily,
    boxrule=0.5pt,
    arc=0pt,
    outer arc=0pt,
    leftrule=3pt,
    rightrule=0.5pt,
    toprule=0.5pt,
    bottomrule=0.5pt,
    top=10pt,
    bottom=10pt,
    left=10pt,
    right=10pt
]
{self.content}
\\end{{tcolorbox}}"""

    def _clean_minimal_style(self) -> str:
        """Clean minimal style."""
        return f"""\\begin{{tcolorbox}}[
    colback=gray!20!white,
    colframe=gray!50!black,
    title={{\\textbf{{{self.title}}}}},
    fonttitle=\\bfseries,
    boxrule=0.5pt,
    arc=2pt,
    outer arc=2pt,
    top=8pt,
    bottom=8pt,
    left=8pt,
    right=8pt
]
{self.content}
\\end{{tcolorbox}}"""

    def _academic_formal_style(self) -> str:
        """Academic formal style."""
        return f"""\\begin{{tcolorbox}}[
    colback=white,
    colframe=black,
    title={{\\textsc{{{self.title}}}}},
    fonttitle=\\bfseries,
    boxrule=1pt,
    arc=0pt,
    outer arc=0pt,
    top=10pt,
    bottom=10pt,
    left=10pt,
    right=10pt
]
{self.content}
\\end{{tcolorbox}}"""

    def _technical_dark_style(self) -> str:
        """Technical dark style."""
        return f"""\\begin{{tcolorbox}}[
    colback=gray!10!white,
    colframe=gray!80!black,
    colbacktitle=gray!80!black,
    coltitle=white,
    title={{\\textbf{{{self.title}}}}},
    fonttitle=\\bfseries\\sffamily,
    boxrule=1pt,
    arc=0pt,
    outer arc=0pt,
    top=10pt,
    bottom=10pt,
    left=10pt,
    right=10pt
]
{self.content}
\\end{{tcolorbox}}"""


class ConceptBoxConverter:
    """Converts concept boxes from markdown to LaTeX."""

    def __init__(
        self, default_style: ConceptBoxStyle = ConceptBoxStyle.PROFESSIONAL_BLUE
    ):
        self.default_style = default_style
        self.boxes: list[ConceptBox] = []

    def extract_concept_boxes(self, content: str) -> list[ConceptBox]:
        """Extract all concept boxes from markdown content."""
        # Pattern for both *Technical Concept Box: Title* and **Technical Concept Box: Title**
        # We need to handle multi-line content

        boxes_found = []

        # Find concept boxes without regex
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check for concept box pattern
            if line.startswith("*") and "Technical Concept Box:" in line:
                # Extract title
                if line.startswith("**"):
                    prefix = "**Technical Concept Box:"
                    suffix = "**"
                else:
                    prefix = "*Technical Concept Box:"
                    suffix = "*"

                title_start = line.find(prefix) + len(prefix)
                title_end = line.rfind(suffix)

                if title_end > title_start:
                    title = line[title_start:title_end].strip()

                    # Extract content (lines until next concept box or paragraph break with non-box content)
                    content_lines = []
                    j = i + 1

                    while j < len(lines):
                        # Check if we've hit another concept box
                        if (
                            lines[j].strip().startswith("*")
                            and "Technical Concept Box:" in lines[j]
                        ):
                            break

                        # Check for paragraph break (empty line followed by non-box content)
                        if not lines[j].strip():
                            # Look ahead to see if there's another concept box after empty lines
                            k = j + 1
                            while k < len(lines) and not lines[k].strip():
                                k += 1
                            if k < len(lines):
                                next_line = lines[k].strip()
                                if (
                                    next_line.startswith("*")
                                    and "Technical Concept Box:" in next_line
                                ):
                                    # Next content is another concept box, so end here
                                    break
                                # Check if this looks like a new section/paragraph that's not part of the box
                                elif next_line.startswith("#") or (
                                    next_line
                                    and not next_line.startswith(" ")
                                    and j - i > 2
                                ):  # Only break if we have some content already
                                    # This looks like a new section, end the box before the empty lines
                                    break

                        content_lines.append(lines[j])
                        j += 1

                    # Clean up the content
                    # Remove leading/trailing empty lines
                    while content_lines and not content_lines[0].strip():
                        content_lines.pop(0)
                    while content_lines and not content_lines[-1].strip():
                        content_lines.pop()

                    clean_content = "\n".join(content_lines)

                    box = ConceptBox(title, clean_content, self.default_style)
                    boxes_found.append(box)
                    self.boxes.append(box)

                    # Skip processed lines
                    i = j - 1

            i += 1

        logger.info(f"Extracted {len(boxes_found)} concept boxes from content")
        return boxes_found

    def replace_boxes_in_text(self, content: str) -> str:
        """Replace markdown concept boxes with LaTeX equivalents."""
        # Pattern for both *Technical Concept Box: Title* and **Technical Concept Box: Title**

        def replace_box(match):
            title = match.group(1).strip()
            box_content = match.group(2).strip()

            # Find the corresponding box
            for box in self.boxes:
                if box.title == title:
                    return box.to_latex()

            # Fallback: create a new box
            box = ConceptBox(title, box_content, self.default_style)
            return box.to_latex()

        # Replace concept boxes without regex
        lines = content.split("\n")
        result_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check for concept box pattern
            if (
                line.strip().startswith("*")
                and "Technical Concept Box:" in line.strip()
            ):
                # Found a concept box, extract it
                stripped = line.strip()

                # Extract title
                if stripped.startswith("**"):
                    prefix = "**Technical Concept Box:"
                    suffix = "**"
                else:
                    prefix = "*Technical Concept Box:"
                    suffix = "*"

                title_start = stripped.find(prefix) + len(prefix)
                title_end = stripped.rfind(suffix)

                if title_end > title_start:
                    title = stripped[title_start:title_end].strip()

                    # Extract content lines
                    content_lines = []
                    j = i + 1
                    while j < len(lines):
                        # Check if we've hit another concept box
                        if (
                            lines[j].strip().startswith("*")
                            and "Technical Concept Box:" in lines[j]
                        ):
                            break
                        # Check for paragraph break
                        if j + 1 < len(lines) and not lines[j].strip():
                            k = j + 1
                            while k < len(lines) and not lines[k].strip():
                                k += 1
                            if k < len(lines) and not (
                                lines[k].strip().startswith("*")
                                and "Technical Concept Box:" in lines[k]
                            ):
                                break
                        content_lines.append(lines[j])
                        j += 1

                    # Clean up content
                    while content_lines and not content_lines[0].strip():
                        content_lines.pop(0)
                    while content_lines and not content_lines[-1].strip():
                        content_lines.pop()

                    box_content = "\n".join(content_lines)

                    # Create match object for replace_box
                    class FakeMatch:
                        def __init__(self, title, content):
                            self._title = title
                            self._content = content

                        def group(self, n):
                            if n == 1:
                                return self._title
                            elif n == 2:
                                return self._content
                            return ""

                    fake_match = FakeMatch(title, box_content)
                    replacement = replace_box(fake_match)
                    result_lines.append(replacement)

                    # Skip processed lines
                    i = j
                    continue

            result_lines.append(line)
            i += 1

        return "\n".join(result_lines)

    def get_required_packages(self) -> list[str]:
        """Get LaTeX packages required for concept boxes."""
        packages = [
            "\\usepackage{tcolorbox}",
            "\\usepackage[most]{tcolorbox}",
            "\\tcbuselibrary{skins,breakable}",
        ]
        return packages

    def set_style(self, style: ConceptBoxStyle) -> None:
        """Set the default style for concept boxes."""
        self.default_style = style
        # Update existing boxes
        for box in self.boxes:
            box.style = style
