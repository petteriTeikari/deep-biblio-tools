"""Enhanced concept box detection with multiple encoding support."""

import logging

# import re  # Banned - using string methods instead
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class ConceptBoxStyle(Enum):
    """Available concept box styles."""

    PROFESSIONAL_BLUE = "professional_blue"
    MODERN_GRADIENT = "modern_gradient"
    CLEAN_MINIMAL = "clean_minimal"
    ACADEMIC_FORMAL = "academic_formal"
    TECHNICAL_DARK = "technical_dark"


class ConceptBoxEncoding(Enum):
    """Available concept box encoding formats."""

    ASTERISK = "asterisk"  # Original: *Technical Concept Box: Title*
    HLINE = "hline"  # New: content between --- markers
    BLOCKQUOTE = "blockquote"  # > Technical Concept Box: Title
    HTML = "html"  # <div class="concept-box">
    CUSTOM = "custom"  # User-defined pattern


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
        style_methods = {
            ConceptBoxStyle.PROFESSIONAL_BLUE: self._professional_blue_style,
            ConceptBoxStyle.MODERN_GRADIENT: self._modern_gradient_style,
            ConceptBoxStyle.CLEAN_MINIMAL: self._clean_minimal_style,
            ConceptBoxStyle.ACADEMIC_FORMAL: self._academic_formal_style,
            ConceptBoxStyle.TECHNICAL_DARK: self._technical_dark_style,
        }

        method = style_methods.get(self.style, self._professional_blue_style)
        return method()

    def _professional_blue_style(self) -> str:
        """Professional blue style with tcolorbox."""
        return f"""\\begin{{tcolorbox}}[
    colback=blue!5!white,
    colframe=blue!75!black,
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
    colback=gray!5!white,
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


class BoxDetector(ABC):
    """Abstract base class for concept box detectors."""

    @abstractmethod
    def extract_boxes(self, content: str) -> list[tuple[str, str, int, int]]:
        """Extract boxes from content.

        Returns:
            List of (title, content, start_pos, end_pos) tuples
        """
        pass

    @abstractmethod
    def get_pattern(self) -> str:
        """Get the regex pattern for this detector."""
        pass


class AsteriskBoxDetector(BoxDetector):
    """Detector for *Technical Concept Box: Title* format."""

    def extract_boxes(self, content: str) -> list[tuple[str, str, int, int]]:
        """Extract boxes using asterisk format."""
        boxes = []
        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("*Technical Concept Box:") and line.endswith(
                "*"
            ):
                # Extract title
                title_start = line.find("*Technical Concept Box:") + len(
                    "*Technical Concept Box:"
                )
                title_end = line.rfind("*")
                if title_end > title_start:
                    title = line[title_start:title_end].strip()

                    # Extract content until next concept box or double empty line
                    content_lines = []
                    j = i + 1
                    empty_line_count = 0

                    while j < len(lines):
                        # Check if we've hit another concept box
                        if lines[j].strip().startswith(
                            "*Technical Concept Box:"
                        ) and lines[j].strip().endswith("*"):
                            break

                        # Count consecutive empty lines
                        if not lines[j].strip():
                            empty_line_count += 1
                            if empty_line_count >= 2:
                                break
                        else:
                            empty_line_count = 0

                        content_lines.append(lines[j])
                        j += 1

                    # Clean up content
                    while content_lines and not content_lines[0].strip():
                        content_lines.pop(0)
                    while content_lines and not content_lines[-1].strip():
                        content_lines.pop()

                    box_content = "\n".join(content_lines)
                    start_pos = i
                    end_pos = j
                    boxes.append((title, box_content, start_pos, end_pos))
                    i = j - 1
            i += 1

        return boxes

    def get_pattern(self) -> str:
        return r"^\s*\*Technical Concept Box:\s*([^*]+)\*\s*\n((?:(?!^\s*\*Technical Concept Box:).*\n)*)"


class HLineBoxDetector(BoxDetector):
    """Detector for content between --- markers with title in first line."""

    def extract_boxes(self, content: str) -> list[tuple[str, str, int, int]]:
        """Extract boxes using horizontal line format."""
        boxes = []
        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            if line == "---":
                # Look for the title line after the opening ---
                j = i + 1

                # Skip any empty lines after the opening ---
                while j < len(lines) and not lines[j].strip():
                    j += 1

                # Check if we have a title line
                if j < len(lines):
                    title_line = lines[j].strip()
                    if title_line.startswith(
                        "*Technical Concept Box:"
                    ) and title_line.endswith("*"):
                        # Extract title
                        title_start = title_line.find(
                            "*Technical Concept Box:"
                        ) + len("*Technical Concept Box:")
                        title_end = title_line.rfind("*")
                        if title_end > title_start:
                            title = title_line[title_start:title_end].strip()

                            # Extract content until closing ---
                            content_lines = []
                            k = j + 1

                            while k < len(lines):
                                if lines[k].strip() == "---":
                                    # Found closing ---
                                    # Clean up content
                                    while (
                                        content_lines
                                        and not content_lines[0].strip()
                                    ):
                                        content_lines.pop(0)
                                    while (
                                        content_lines
                                        and not content_lines[-1].strip()
                                    ):
                                        content_lines.pop()

                                    box_content = "\n".join(content_lines)
                                    start_pos = i
                                    end_pos = k
                                    boxes.append(
                                        (title, box_content, start_pos, end_pos)
                                    )
                                    i = k
                                    break
                                else:
                                    content_lines.append(lines[k])
                                k += 1
            i += 1

        return boxes

    def get_pattern(self) -> str:
        return r"^---\s*\n\s*\n?\s*\*Technical Concept Box:\s*([^*]+)\*\s*(.*?)\n---\s*$"


class BlockquoteBoxDetector(BoxDetector):
    """Detector for > Technical Concept Box: Title format."""

    def extract_boxes(self, content: str) -> list[tuple[str, str, int, int]]:
        """Extract boxes using blockquote format."""
        boxes = []
        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("> Technical Concept Box:"):
                # Extract title
                title_start = line.find("> Technical Concept Box:") + len(
                    "> Technical Concept Box:"
                )
                title = line[title_start:].strip()

                # Extract content (following blockquote lines)
                content_lines = []
                j = i + 1

                while j < len(lines):
                    if lines[j].startswith(">"):
                        # Remove > prefix and collect content
                        content_line = lines[j][1:].lstrip()
                        content_lines.append(content_line)
                    elif not lines[j].strip():
                        # Empty line - check if next non-empty line is still blockquote
                        k = j + 1
                        while k < len(lines) and not lines[k].strip():
                            k += 1
                        if k < len(lines) and lines[k].startswith(">"):
                            # Continue with blockquote
                            content_lines.append("")
                        else:
                            # End of blockquote
                            break
                    else:
                        # Non-blockquote line - end of box
                        break
                    j += 1

                # Clean up content
                while content_lines and not content_lines[0].strip():
                    content_lines.pop(0)
                while content_lines and not content_lines[-1].strip():
                    content_lines.pop()

                box_content = "\n".join(content_lines)
                start_pos = i
                end_pos = j
                boxes.append((title, box_content, start_pos, end_pos))
                i = j - 1

            i += 1

        return boxes

    def get_pattern(self) -> str:
        return r"^>\s*Technical Concept Box:\s*(.+?)\s*\n((?:>.*\n)*)"


class EnhancedConceptBoxConverter:
    """Enhanced converter supporting multiple encoding formats."""

    def __init__(
        self,
        encoding: ConceptBoxEncoding = ConceptBoxEncoding.ASTERISK,
        default_style: ConceptBoxStyle = ConceptBoxStyle.PROFESSIONAL_BLUE,
        custom_pattern: str | None = None,
    ):
        self.encoding = encoding
        self.default_style = default_style
        self.custom_pattern = custom_pattern
        self.boxes: list[ConceptBox] = []

        # Initialize detector based on encoding
        self.detector = self._get_detector()

    def _get_detector(self) -> BoxDetector:
        """Get the appropriate detector for the encoding."""
        detectors = {
            ConceptBoxEncoding.ASTERISK: AsteriskBoxDetector(),
            ConceptBoxEncoding.HLINE: HLineBoxDetector(),
            ConceptBoxEncoding.BLOCKQUOTE: BlockquoteBoxDetector(),
        }

        detector = detectors.get(self.encoding)
        if detector is None:
            raise ValueError(f"Unsupported encoding: {self.encoding}")

        return detector

    def extract_concept_boxes(self, content: str) -> list[ConceptBox]:
        """Extract all concept boxes from markdown content."""
        boxes_data = self.detector.extract_boxes(content)
        boxes_found = []

        for title, box_content, _, _ in boxes_data:
            # Clean up the content
            lines = box_content.split("\n")
            while lines and not lines[0].strip():
                lines.pop(0)
            while lines and not lines[-1].strip():
                lines.pop()

            clean_content = "\n".join(lines)

            box = ConceptBox(title, clean_content, self.default_style)
            boxes_found.append(box)
            self.boxes.append(box)

        logger.info(
            f"Extracted {len(boxes_found)} concept boxes using {self.encoding.value} encoding"
        )
        return boxes_found

    def replace_boxes_in_text(self, content: str) -> str:
        """Replace markdown concept boxes with LaTeX equivalents."""
        # Get all boxes with positions
        boxes_data = self.detector.extract_boxes(content)

        # Sort by position (reverse order for replacement)
        boxes_data.sort(key=lambda x: x[2], reverse=True)

        # Replace each box
        modified_content = content
        for title, box_content, start_pos, end_pos in boxes_data:
            # Find the corresponding box object
            box = None
            for b in self.boxes:
                if b.title == title:
                    box = b
                    break

            # If not found, create a new one
            if box is None:
                box = ConceptBox(title, box_content, self.default_style)

            # Replace in content
            latex_box = box.to_latex()
            modified_content = (
                modified_content[:start_pos]
                + latex_box
                + modified_content[end_pos:]
            )

        return modified_content

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

    def set_encoding(self, encoding: ConceptBoxEncoding) -> None:
        """Change the encoding format."""
        self.encoding = encoding
        self.detector = self._get_detector()
        # Clear existing boxes as they might not match new encoding
        self.boxes = []
