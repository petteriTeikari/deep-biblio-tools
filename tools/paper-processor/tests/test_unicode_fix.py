#!/usr/bin/env python3
"""
Specific test for the Unicode character issue found in batch processing.
This tests the fix for: "invalid literal for int() with base 10: '(1)'"
"""

import sys
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from academic_rephrasing import AcademicRephraser


def test_unicode_word_count_fix():
    """Test that Unicode characters don't break word counting."""

    # Create test content with problematic Unicode characters
    test_content = """# LRR-Bench: Vision-Language Models Still Struggle

## Abstract
Apart from qualitative results, we also observe that \u278a advanced reasoning methods,
e.g., CoT, do not consistently improve spatial understanding; \u278b preference optimization,
e.g., Mixed Preference Optimization (MPO), can negatively impact spatial understanding;
\u278c parameter scaling laws are ineffective for enhancing spatial understanding.

## Introduction
We present three key findings:
- \u278a First finding with details
- \u278b Second finding with more text
- \u278c Third finding with conclusion

Total words: approximately 100 words including Unicode.

## References
1. Test et al. (2024). Unicode handling in NLP.
"""

    # Save to temporary file
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "unicode_test_paper.md"
        test_file.write_text(test_content)

        # This should not raise "invalid literal for int()" error
        try:
            with pytest.raises(ValueError):
                # First verify the error exists without fix
                # This simulates what happens in word counting
                int("\u278a")
        except ValueError:
            pass  # Expected

        # Now test that our rephraser handles it correctly
        rephraser = AcademicRephraser()

        # The clean_content method should handle Unicode properly
        cleaned = rephraser.clean_content(test_content)

        # Verify content is preserved (Unicode chars might be kept or removed)
        assert "advanced reasoning methods" in cleaned
        assert "preference optimization" in cleaned
        assert "parameter scaling laws" in cleaned

        # Test full processing doesn't crash
        output_file = Path(tmp_dir) / "unicode_test_output.md"

        # This should complete without Unicode errors
        result = rephraser.rephrase_paper(
            test_file, output_file, target_retention=0.45
        )

        # Verify output was created
        assert output_file.exists()

        # Check word count works
        word_count = len(result.split())
        assert word_count > 0


def test_mixed_unicode_handling():
    """Test various Unicode characters that might appear in papers."""

    rephraser = AcademicRephraser()

    test_cases = [
        # Mathematical symbols
        "The sum is ∑x₁ + x₂ = ∫f(x)dx",
        # Greek letters
        "Parameters α, β, γ, δ, ε, ζ, η, θ",
        # Subscripts and superscripts
        "x₁² + x₂² = r²",
        # Arrows and special symbols
        "A → B, A ⇒ B, A ↔ B",
        # Circled numbers (like the problematic ones)
        "Steps: \u278a first \u278b second \u278c third \u278d fourth",
        # Other potential problematic characters
        "Temperature: 25°C, Angle: 90°, Currency: €100",
    ]

    for test_text in test_cases:
        # Should handle without crashing
        cleaned = rephraser.clean_content(test_text)
        assert isinstance(cleaned, str)
        assert len(cleaned) > 0


def test_unicode_in_references():
    """Test Unicode in reference sections."""

    rephraser = AcademicRephraser()

    content = """# Test Paper

## References

1. Müller, K.; García, J.; Øverland, S. (2024). Unicode authors. Journal für Wissenschaft.
2. ;  (2023). Chinese names in references. .
3. Dvořák, A.; Čech, P. (2024). Eastern European names. České Vědy.
"""

    references = rephraser.extract_references(content)

    # Should extract references with Unicode preserved
    assert len(references) >= 3
    assert any("Müller" in ref for ref in references)
    assert any("" in ref or "Chinese names" in ref for ref in references)
    assert any("Dvořák" in ref for ref in references)


if __name__ == "__main__":
    # Run the specific Unicode tests
    test_unicode_word_count_fix()
    test_mixed_unicode_handling()
    test_unicode_in_references()

    print("All Unicode tests passed!")
