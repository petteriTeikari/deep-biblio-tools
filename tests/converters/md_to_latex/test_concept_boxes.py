"""Tests for concept box converter."""

from src.converters.md_to_latex.concept_boxes import (
    ConceptBox,
    ConceptBoxConverter,
    ConceptBoxStyle,
)


class TestConceptBox:
    """Test ConceptBox class."""

    def test_basic_concept_box(self):
        """Test basic concept box creation."""
        box = ConceptBox("Test Title", "Test content")
        assert box.title == "Test Title"
        assert box.content == "Test content"
        assert box.style == ConceptBoxStyle.PROFESSIONAL_BLUE

    def test_custom_style(self):
        """Test concept box with custom style."""
        box = ConceptBox("Title", "Content", ConceptBoxStyle.MODERN_GRADIENT)
        assert box.style == ConceptBoxStyle.MODERN_GRADIENT

    def test_professional_blue_latex(self):
        """Test professional blue style LaTeX output."""
        box = ConceptBox(
            "Blue Box", "Content here", ConceptBoxStyle.PROFESSIONAL_BLUE
        )
        latex = box.to_latex()
        assert "\\begin{tcolorbox}" in latex
        # Updated to match new RGB color format (hex #dae0e8 = rgb 218,224,232)
        assert "colback={rgb,255:red,218;green,224;blue,232}" in latex
        assert "colframe={rgb,255:red,180;green,190;blue,200}" in latex
        assert "\\textbf{Blue Box}" in latex
        assert "Content here" in latex
        assert "\\end{tcolorbox}" in latex

    def test_modern_gradient_latex(self):
        """Test modern gradient style LaTeX output."""
        box = ConceptBox(
            "Gradient Box", "Content", ConceptBoxStyle.MODERN_GRADIENT
        )
        latex = box.to_latex()
        assert "enhanced" in latex
        assert "colbacktitle=blue!10!white" in latex
        assert "leftrule=3pt" in latex

    def test_clean_minimal_latex(self):
        """Test clean minimal style LaTeX output."""
        box = ConceptBox(
            "Minimal Box", "Content", ConceptBoxStyle.CLEAN_MINIMAL
        )
        latex = box.to_latex()
        assert "colback=gray!20!white" in latex
        assert "colframe=gray!50!black" in latex

    def test_academic_formal_latex(self):
        """Test academic formal style LaTeX output."""
        box = ConceptBox(
            "Formal Box", "Content", ConceptBoxStyle.ACADEMIC_FORMAL
        )
        latex = box.to_latex()
        assert "\\textsc{Formal Box}" in latex
        assert "colframe=black" in latex

    def test_technical_dark_latex(self):
        """Test technical dark style LaTeX output."""
        box = ConceptBox("Dark Box", "Content", ConceptBoxStyle.TECHNICAL_DARK)
        latex = box.to_latex()
        assert "colback=gray!10!white" in latex
        assert "colbacktitle=gray!80!black" in latex
        assert "coltitle=white" in latex


class TestConceptBoxConverter:
    """Test ConceptBoxConverter class."""

    def test_extract_single_box(self):
        """Test extraction of single concept box."""
        converter = ConceptBoxConverter()
        content = """
        Some text before.

        *Technical Concept Box: Important Concept*

        This is the content of the concept box.
        It can have multiple lines.

        Text after the box.
        """

        boxes = converter.extract_concept_boxes(content)
        assert len(boxes) == 1
        assert boxes[0].title == "Important Concept"
        assert "This is the content" in boxes[0].content
        assert "multiple lines" in boxes[0].content

    def test_extract_multiple_boxes(self):
        """Test extraction of multiple concept boxes."""
        converter = ConceptBoxConverter()
        content = """
        *Technical Concept Box: First Box*

        First box content.

        Some text between.

        *Technical Concept Box: Second Box*

        Second box content.
        """

        boxes = converter.extract_concept_boxes(content)
        assert len(boxes) == 2
        assert boxes[0].title == "First Box"
        assert boxes[1].title == "Second Box"

    def test_replace_boxes_in_text(self):
        """Test replacement of concept boxes with LaTeX."""
        converter = ConceptBoxConverter()
        content = """
        Text before.

        *Technical Concept Box: Test Box*

        Box content here.

        Text after.
        """

        # Extract boxes first
        converter.extract_concept_boxes(content)

        # Replace in text
        latex_content = converter.replace_boxes_in_text(content)
        assert "\\begin{tcolorbox}" in latex_content
        assert "\\textbf{Test Box}" in latex_content
        assert "Box content here." in latex_content
        assert "\\end{tcolorbox}" in latex_content
        assert "*Technical Concept Box:" not in latex_content

    def test_empty_content_handling(self):
        """Test handling of boxes with empty content."""
        converter = ConceptBoxConverter()
        content = """
        *Technical Concept Box: Empty Box*


        Next section.
        """

        boxes = converter.extract_concept_boxes(content)
        assert len(boxes) == 1
        assert boxes[0].title == "Empty Box"
        # The content includes "Next section." because it's not a new concept box
        assert "Next section." in boxes[0].content

    def test_required_packages(self):
        """Test getting required LaTeX packages."""
        converter = ConceptBoxConverter()
        packages = converter.get_required_packages()
        assert "\\usepackage{tcolorbox}" in packages
        assert "\\usepackage[most]{tcolorbox}" in packages
        assert "\\tcbuselibrary{skins,breakable}" in packages

    def test_set_style(self):
        """Test changing default style."""
        converter = ConceptBoxConverter()
        converter.set_style(ConceptBoxStyle.TECHNICAL_DARK)
        assert converter.default_style == ConceptBoxStyle.TECHNICAL_DARK

        # Extract a box and check it uses new style
        content = "*Technical Concept Box: Test*\nContent"
        boxes = converter.extract_concept_boxes(content)
        assert boxes[0].style == ConceptBoxStyle.TECHNICAL_DARK
