"""Tests for enhanced concept box converter with multiple encodings."""

from src.converters.md_to_latex.concept_boxes_enhanced import (
    ConceptBoxEncoding,
    ConceptBoxStyle,
    EnhancedConceptBoxConverter,
)


class TestEnhancedConceptBoxConverter:
    """Test suite for enhanced concept box converter."""

    def test_asterisk_encoding(self):
        """Test original asterisk encoding format."""
        content = """
# Test Document

Some text here.

*Technical Concept Box: Neural Networks*
Neural networks are computational models inspired by the human brain.
They consist of interconnected layers of nodes.

More text after the box.
"""

        converter = EnhancedConceptBoxConverter(
            encoding=ConceptBoxEncoding.ASTERISK
        )
        boxes = converter.extract_concept_boxes(content)

        assert len(boxes) == 1
        assert boxes[0].title == "Neural Networks"
        assert "computational models" in boxes[0].content
        assert "interconnected layers" in boxes[0].content

    def test_hline_encoding(self):
        """Test horizontal line encoding format."""
        content = """
# Test Document

Some text here.

---
*Technical Concept Box: Machine Learning*
Machine learning is a subset of artificial intelligence.
It enables systems to learn from data.
Key types include:
- Supervised learning
- Unsupervised learning
- Reinforcement learning
---

More text after the box.
"""

        converter = EnhancedConceptBoxConverter(
            encoding=ConceptBoxEncoding.HLINE
        )
        boxes = converter.extract_concept_boxes(content)

        assert len(boxes) == 1
        assert boxes[0].title == "Machine Learning"
        assert "subset of artificial intelligence" in boxes[0].content
        assert "Supervised learning" in boxes[0].content

    def test_blockquote_encoding(self):
        """Test blockquote encoding format."""
        content = """
# Test Document

Some text here.

> Technical Concept Box: Deep Learning
> Deep learning uses neural networks with multiple layers.
> It has revolutionized computer vision and NLP.
> Key architectures include CNNs and RNNs.

More text after the box.
"""

        converter = EnhancedConceptBoxConverter(
            encoding=ConceptBoxEncoding.BLOCKQUOTE
        )
        boxes = converter.extract_concept_boxes(content)

        assert len(boxes) == 1
        assert boxes[0].title == "Deep Learning"
        assert "neural networks with multiple layers" in boxes[0].content
        assert "CNNs and RNNs" in boxes[0].content

    def test_multiple_boxes_hline(self):
        """Test multiple boxes with hline encoding."""
        content = """
# Document

---
*Technical Concept Box: First Box*
Content of first box.
---

Some text between boxes.

---
*Technical Concept Box: Second Box*
Content of second box.
With multiple lines.
---
"""

        converter = EnhancedConceptBoxConverter(
            encoding=ConceptBoxEncoding.HLINE
        )
        boxes = converter.extract_concept_boxes(content)

        assert len(boxes) == 2
        assert boxes[0].title == "First Box"
        assert boxes[1].title == "Second Box"
        assert "Content of first box" in boxes[0].content
        assert "multiple lines" in boxes[1].content

    def test_replace_boxes_in_text(self):
        """Test replacing boxes with LaTeX equivalents."""
        content = """
# Test

---
*Technical Concept Box: Test Box*
This is a test.
---

End of document.
"""

        converter = EnhancedConceptBoxConverter(
            encoding=ConceptBoxEncoding.HLINE,
            default_style=ConceptBoxStyle.PROFESSIONAL_BLUE,
        )

        # Extract boxes first
        converter.extract_concept_boxes(content)

        # Replace in text
        latex_content = converter.replace_boxes_in_text(content)

        assert "\\begin{tcolorbox}" in latex_content
        assert "\\textbf{Test Box}" in latex_content
        assert "This is a test." in latex_content
        assert "\\end{tcolorbox}" in latex_content
        assert "End of document." in latex_content

    def test_style_selection(self):
        """Test different concept box styles."""
        content = """
*Technical Concept Box: Style Test*
Testing different styles.
"""

        styles = [
            ConceptBoxStyle.PROFESSIONAL_BLUE,
            ConceptBoxStyle.MODERN_GRADIENT,
            ConceptBoxStyle.CLEAN_MINIMAL,
            ConceptBoxStyle.ACADEMIC_FORMAL,
            ConceptBoxStyle.TECHNICAL_DARK,
        ]

        for style in styles:
            converter = EnhancedConceptBoxConverter(
                encoding=ConceptBoxEncoding.ASTERISK, default_style=style
            )
            boxes = converter.extract_concept_boxes(content)
            assert len(boxes) == 1

            latex = boxes[0].to_latex()
            assert "\\begin{tcolorbox}" in latex
            assert "Style Test" in latex

    def test_encoding_change(self):
        """Test changing encoding after initialization."""
        converter = EnhancedConceptBoxConverter(
            encoding=ConceptBoxEncoding.ASTERISK
        )

        # Test with asterisk first
        content1 = "*Technical Concept Box: Test 1*\nContent 1"
        boxes1 = converter.extract_concept_boxes(content1)
        assert len(boxes1) == 1

        # Change to hline
        converter.set_encoding(ConceptBoxEncoding.HLINE)

        # Test with hline
        content2 = "---\n*Technical Concept Box: Test 2*\nContent 2\n---"
        boxes2 = converter.extract_concept_boxes(content2)
        assert len(boxes2) == 1
        assert boxes2[0].title == "Test 2"

    def test_complex_hline_content(self):
        """Test hline encoding with complex content matching UADReview format."""
        content = """
---

*Technical Concept Box: Neural 3D Reconstruction Evolution*
The progression from classical to neural reconstruction methods represents a fundamental shift in how we capture and represent physical spaces:

Classical Methods (2000-2020):

- Photogrammetry: Uses multiple photos to triangulate 3D points
- Time to process: 2-8 hours for a single room
- Output: Sparse point clouds requiring manual cleanup
- Accuracy: High geometric precision but poor visual quality

Neural Methods (2020-present):

- NeRFs: Learn implicit 3D representation from images
- 3D Gaussian Splatting: Explicit primitives enabling real-time rendering
- Time to process: 5-30 minutes with modern algorithms
- Output: Photorealistic, explorable 3D models

Business Impact: The 100x speedup from NeRFs to 3DGS makes on-demand 3D capture viable for routine appraisals. However, current methods struggle with key architectural elements like walls and windows, driving research into specialized primitives.

---
"""

        converter = EnhancedConceptBoxConverter(
            encoding=ConceptBoxEncoding.HLINE,
            default_style=ConceptBoxStyle.PROFESSIONAL_BLUE,
        )

        boxes = converter.extract_concept_boxes(content)

        assert len(boxes) == 1
        assert boxes[0].title == "Neural 3D Reconstruction Evolution"
        assert "Classical Methods (2000-2020):" in boxes[0].content
        assert "Neural Methods (2020-present):" in boxes[0].content
        assert "Business Impact:" in boxes[0].content
        assert "100x speedup" in boxes[0].content

        # Test LaTeX conversion
        latex = boxes[0].to_latex()
        assert "\\begin{tcolorbox}" in latex
        assert "Neural 3D Reconstruction Evolution" in latex
        assert "Photogrammetry" in latex
        assert "3D Gaussian Splatting" in latex
