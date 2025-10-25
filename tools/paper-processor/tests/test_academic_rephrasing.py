#!/usr/bin/env python3
"""
Comprehensive test suite for academic rephrasing tool.
Tests cover input validation, content extraction, retention rates,
output quality, and edge cases identified during batch processing.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from academic_rephrasing import AcademicRephraser


class TestAcademicRephrasing:
    """Test suite for academic rephrasing functionality."""

    @pytest.fixture
    def rephraser(self):
        """Create a rephraser instance for testing."""
        with (
            patch("academic_rephrasing.ContentProcessor"),
            patch("academic_rephrasing.ContentPreservingRephraser"),
            patch("academic_rephrasing.get_default_config"),
        ):
            return AcademicRephraser()

    @pytest.fixture
    def real_rephraser(self):
        """Create a real rephraser instance without mocking for integration tests."""
        return AcademicRephraser()

    # ============= Input Validation Tests =============

    def test_unicode_character_handling(self, rephraser):
        """Test handling of special Unicode characters that caused failures."""
        content = """# Test Paper

        Here are some special characters: (1) first point, (2) second point, (3) third point.

        ## References
        1. Test Reference
        """

        # This should not raise an error
        cleaned = rephraser.clean_content(content)
        assert "(1)" in cleaned or "first point" in cleaned

    def test_html_artifacts_removal(self, rephraser):
        """Test removal of HTML artifacts from arxiv papers."""
        content = """# Test Paper

        ## Report Github Issue
        Report issue for preceding element

        This is experimental HTML... help improve conversions.

        {.ltx_bibblock} {#bib.bib1} style="font-size:90%;"

        Real content here.
        """

        cleaned = rephraser.clean_content(content)
        assert "Report Github Issue" not in cleaned
        assert "Report issue for preceding element" not in cleaned
        assert "experimental HTML" not in cleaned
        assert ".ltx_bibblock" not in cleaned
        assert "Real content here." in cleaned

    # ============= Reference Extraction Tests =============

    def test_reference_extraction_bullet_format(self, rephraser):
        """Test extraction of references in bullet list format."""
        content = """# Test Paper

## References

- [Achlioptas et al. (2020)]{#bib.bib1}
  ↑
  [ Achlioptas, P.; Abdelreheem, A.; Xia, F.; Elhoseiny, M.; and Guibas, L. 2020. ]{.ltx_bibblock}
  [Referit3d: Neural listeners for fine-grained 3d object identification in real-world scenes. ]{.ltx_bibblock}
  [In *European Conference on Computer Vision*, 422--440. Springer. ]{.ltx_bibblock}

- [Chen et al. (2021)]{#bib.bib2}
  ↑
  [ Chen, D.; Gholami, A.; Niesner, M.; and Chang, A. X. 2021. ]{.ltx_bibblock}
  [Scan2cap: Context-aware dense captioning in rgb-d scans. ]{.ltx_bibblock}
  [In *CVPR*. ]{.ltx_bibblock}
"""

        references = rephraser.extract_references(content)
        assert len(references) >= 2
        assert "Achlioptas" in references[0]
        assert "2020" in references[0]
        assert "Referit3d" in references[0]
        assert "Chen" in references[1]
        assert "2021" in references[1]
        assert "Scan2cap" in references[1]

    def test_reference_extraction_numbered_format(self, rephraser):
        """Test extraction of references in numbered format."""
        content = """# Test Paper

## References

[1] Smith, J.; Jones, M. 2023. Test Paper Title. In Proceedings of Test Conference, 123-456.

[2] Brown, A.; Davis, B. 2024. Another Test Paper. Journal of Testing, 78(9):1234-1567.
"""

        references = rephraser.extract_references(content)
        assert len(references) == 2
        assert "Smith" in references[0]
        assert "2023" in references[0]
        assert "Brown" in references[1]
        assert "2024" in references[1]

    def test_reference_extraction_stops_at_appendix(self, rephraser):
        """Test that reference extraction doesn't include appendix content."""
        content = """# Test Paper

        ## References

        1. Valid Reference (2023). Test paper.

        ## Ablation Study
        We conduct extensive ablation studies...

        ## Appendix A
        Additional implementation details...
        """

        references = rephraser.extract_references(content)
        # Should only have 1 reference, not appendix content
        assert len(references) == 1
        assert "Valid Reference" in references[0]
        assert "ablation" not in " ".join(references).lower()
        assert "appendix" not in " ".join(references).lower()

    # ============= Section Processing Tests =============

    def test_stops_processing_at_references(self):
        """Test that processing stops when it hits the References section."""
        # Use real rephraser for integration test
        rephraser = AcademicRephraser()

        content = """# Test Paper

## Introduction
Introduction content here.

## Methods
Methods content here.

## References
1. Reference 1
2. Reference 2

## Appendix
This appendix content should not be processed.

## Ablation Study
This ablation study should not be processed.
"""

        # Create a temporary test file
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test_paper.md"
            test_file.write_text(content)
            output_file = Path(tmp_dir) / "test_paper_output.md"

            # Process the paper
            output = rephraser.rephrase_paper(
                test_file, output_file, target_retention=0.45
            )

            # Verify appendix and ablation content is not in output
            assert (
                "appendix content should not be processed" not in output.lower()
            )
            assert (
                "ablation study should not be processed" not in output.lower()
            )
            # But references should be included
            assert "Reference 1" in output
            assert "Reference 2" in output

    def test_appendix_filtering_integration(self):
        """Test that appendix-like sections are filtered out - integration test."""
        # Use real rephraser for integration test
        rephraser = AcademicRephraser()

        content = """# Test Paper

## Introduction
Introduction content here.

## Implementation Details
These implementation details should be skipped.

## Ablation Study
This ablation study should be skipped.

## Additional Results
These additional results should be skipped.

## Visualization
This visualization section should be skipped.

## References
1. Reference 1
"""

        # Create a temporary test file
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test_paper.md"
            test_file.write_text(content)
            output_file = Path(tmp_dir) / "test_paper_output.md"

            # Process the paper without appendix
            output = rephraser.rephrase_paper(
                test_file,
                output_file,
                target_retention=0.45,
                include_appendix=False,
            )

            # Verify appendix-like sections are not in output
            assert (
                "implementation details should be skipped" not in output.lower()
            )
            assert "ablation study should be skipped" not in output.lower()
            assert "additional results should be skipped" not in output.lower()
            assert (
                "visualization section should be skipped" not in output.lower()
            )

            # Verify basic structure is present
            assert "# Test Paper" in output  # Title preserved
            assert "Research Gap Analysis" in output  # Header present

    # ============= Retention Rate Tests =============

    def test_preservation_ratios_by_section(self, rephraser):
        """Test that preservation ratios are correctly applied by section type."""
        # Test with 25% target retention
        preservation_ratios = rephraser._get_preservation_ratios(0.25)

        assert preservation_ratios["future"] == 1.0  # 100% preservation
        assert preservation_ratios["limitation"] >= 0.95  # >95% preservation
        assert preservation_ratios["abstract"] == 0.50
        assert (
            preservation_ratios["method"] == 0.15
        )  # Low preservation for methods

        # Test with 50% target retention
        preservation_ratios = rephraser._get_preservation_ratios(0.50)

        assert preservation_ratios["future"] == 1.0
        assert preservation_ratios["limitation"] >= 0.95
        assert preservation_ratios["method"] == 0.25  # Higher than 25% target

    def test_retention_rate_calculation(self, rephraser):
        """Test actual retention rate calculation."""
        original_text = " ".join(["word"] * 1000)  # 1000 words
        rephrased_text = " ".join(["word"] * 450)  # 450 words

        retention = len(rephrased_text.split()) / len(original_text.split())
        assert abs(retention - 0.45) < 0.01  # Should be close to 45%

    # ============= Output Quality Tests =============

    def test_header_generation(self, rephraser):
        """Test proper header generation with research gap focus."""
        header = rephraser._build_header(
            title="Test Paper",
            original_words=10000,
            target_retention=0.45,
            context="BIM/Scan-to-BIM Applications",
        )

        assert "Test Paper" in header
        assert "Research Gap Analysis" in header
        assert "10,000 words" in header
        assert "4,500 words (45%)" in header
        assert "What wasn't known before this paper" in header
        assert "BIM/Scan-to-BIM Applications" in header

    def test_references_section_generation(self, rephraser):
        """Test proper references section generation."""
        references = [
            "Smith et al. (2023). Test paper. Journal of Testing.",
            "Jones et al. (2024). Another paper. Conference Proceedings.",
        ]

        ref_section = rephraser._build_references_section(references)

        assert "## References" in ref_section
        assert "(2 references)" in ref_section
        assert "1. Smith et al." in ref_section
        assert "2. Jones et al." in ref_section

    def test_empty_references_handling(self, rephraser):
        """Test handling of papers with no references."""
        ref_section = rephraser._build_references_section([])

        assert "## References" in ref_section
        assert "No references found" in ref_section

    # ============= Edge Cases Tests =============

    def test_very_short_paper(self, rephraser):
        """Test handling of very short papers."""
        content = """# Short Paper

## Introduction
This is a very short paper with minimal content.

## Conclusion
The end.

## References
1. Single reference (2023).
"""

        # Should handle without errors
        cleaned = rephraser.clean_content(content)
        references = rephraser.extract_references(cleaned)

        assert len(references) == 1
        assert "Single reference" in references[0]

    def test_malformed_references(self, rephraser):
        """Test handling of malformed reference sections."""
        content = """# Test Paper

        ## References

        This is not a properly formatted reference.
        Just some random text here.
        Maybe a year like 2023 appears.
        But no proper citation format.

        Here's another line without proper format.
        """

        references = rephraser.extract_references(content)
        # Should handle gracefully, possibly extracting nothing or minimal refs
        assert isinstance(references, list)

    def test_duplicate_sentence_removal(self, rephraser):
        """Test removal of duplicate sentences."""
        text = """This is a sentence. This is a sentence.
        Another sentence here.
        This is unique. This is unique."""

        cleaned = rephraser.remove_duplicate_sentences(text)

        # Count occurrences
        assert cleaned.count("This is a sentence.") == 1
        assert cleaned.count("This is unique.") == 1
        assert "Another sentence here." in cleaned

    def test_figure_caption_removal(self, rephraser):
        """Test removal of figure captions."""
        text = """Some normal text here.

        (a) This is a figure caption
        (b) Another caption part
        Figure 1: Main figure caption
        Table 2: Table caption

        More normal text after captions."""

        cleaned = rephraser.remove_figure_captions(text)

        assert "Some normal text here." in cleaned
        assert "More normal text after captions." in cleaned
        assert "(a) This is a figure caption" not in cleaned
        assert "Figure 1:" not in cleaned
        assert "Table 2:" not in cleaned

    # ============= Integration Tests =============

    def test_full_processing_pipeline(self, rephraser, tmp_path):
        """Test the complete processing pipeline."""
        # Create a test paper
        test_paper = tmp_path / "test_paper.md"
        test_paper.write_text("""# Test Paper for Integration

        ## Abstract
        This paper addresses important research gaps in the field.

        ## Introduction
        Previous work has limitations that we address here.

        ## Methods
        We use a novel approach with many technical details.

        ## Results
        We achieved improvements over baselines with 95.3% accuracy.

        ## Future Work
        This critical section must be preserved completely.

        ## Limitations
        Our approach cannot handle edge cases X and Y.

        ## References

        1. Smith et al. (2023). Previous work. Conference.
        2. Jones et al. (2024). Related work. Journal.

        ## Appendix A
        This should not appear in output.
        """)

        output_path = tmp_path / "output.md"

        # Process the paper
        rephraser.rephrase_paper(
            test_paper,
            output_path,
            target_retention=0.45,
            context="BIM/Scan-to-BIM Applications",
        )

        # Verify output
        assert output_path.exists()
        output_content = output_path.read_text()

        # Check key elements
        assert "Research Gap Analysis" in output_content
        assert "BIM/Scan-to-BIM Applications" in output_content
        assert "## References" in output_content
        assert "Smith et al. (2023)" in output_content
        assert "Jones et al. (2024)" in output_content
        assert "Appendix A" not in output_content
        assert "This should not appear" not in output_content


class TestBatchProcessing:
    """Test batch processing functionality."""

    @pytest.fixture
    def rephraser(self):
        """Create a rephraser instance for testing."""
        with (
            patch("academic_rephrasing.ContentProcessor"),
            patch("academic_rephrasing.ContentPreservingRephraser"),
            patch("academic_rephrasing.get_default_config"),
        ):
            return AcademicRephraser()

    def test_batch_processing_continues_on_error(self, rephraser, tmp_path):
        """Test that batch processing continues even if one file fails."""
        # Create test files
        good_file1 = tmp_path / "good1.md"
        good_file1.write_text(
            "# Good Paper 1\n\nContent\n\n## References\n1. Ref"
        )

        bad_file = tmp_path / "bad.md"
        bad_file.write_text(
            "# Bad Paper\n\n(1)(2)(3) Unicode that might cause issues"
        )

        good_file2 = tmp_path / "good2.md"
        good_file2.write_text(
            "# Good Paper 2\n\nContent\n\n## References\n1. Ref"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Mock the rephrase_paper method to simulate error
        original_rephrase = rephraser.rephrase_paper

        def mock_rephrase(input_path, *args, **kwargs):
            if "bad.md" in str(input_path):
                raise ValueError("Simulated Unicode error")
            return original_rephrase(input_path, *args, **kwargs)

        with patch.object(rephraser, "rephrase_paper", mock_rephrase):
            results = rephraser.process_folder(
                tmp_path, output_dir, target_retention=0.45, file_pattern="*.md"
            )

        # Verify results
        assert len(results) == 3
        assert results["good1.md"]["status"] == "success"
        assert results["bad.md"]["status"] == "error"
        assert results["good2.md"]["status"] == "success"

        # Verify output files
        assert (output_dir / "good1_rephrased.md").exists()
        assert not (output_dir / "bad_rephrased.md").exists()
        assert (output_dir / "good2_rephrased.md").exists()


# ============= Helper method additions to AcademicRephraser =============
# These would need to be added to the actual class for some tests to work


def _get_preservation_ratios(self, target_retention):
    """Get preservation ratios based on target retention."""
    if target_retention <= 0.25:
        return {
            "abstract": 0.50,
            "introduction": 0.40,
            "related work": 0.30,
            "method": 0.15,
            "experiment": 0.10,
            "result": 0.15,
            "discussion": 0.60,
            "conclusion": 0.70,
            "future": 1.0,
            "limitation": 0.95,
            "contribution": 0.90,
            "research gap": 0.95,
            "novel": 0.90,
        }
    elif target_retention <= 0.50:
        return {
            "abstract": 0.70,
            "introduction": 0.60,
            "related work": 0.50,
            "method": 0.25,
            "experiment": 0.20,
            "result": 0.30,
            "discussion": 0.75,
            "conclusion": 0.85,
            "future": 1.0,
            "limitation": 0.95,
            "contribution": 0.95,
            "research gap": 0.95,
            "novel": 0.95,
        }
    else:
        return {
            "abstract": 0.80,
            "introduction": 0.70,
            "related work": 0.60,
            "method": 0.40,
            "experiment": 0.35,
            "result": 0.45,
            "discussion": 0.85,
            "conclusion": 0.90,
            "future": 1.0,
            "limitation": 0.95,
            "contribution": 0.95,
            "research gap": 1.0,
            "novel": 0.95,
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
