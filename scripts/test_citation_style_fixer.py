#!/usr/bin/env python3
"""Test the citation style fixer with real examples."""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.citation_style_fixer import CitationStyleFixer


def test_citation_style_fixer():
    """Test the citation style fixer with various examples."""

    test_cases = [
        # Case 1: The exact example from the user
        {
            "input": "The statistical and machine learning literature provides sophisticated frameworks for uncertainty quantification. Der Kiureghian and Ditlevsen ([Kiureghian and Ditlevsen (2009)](https://doi.org/10.1016/j.strusafe.2008.06.020)) formalize the aleatory/epistemic distinction and methods for propagation through complex systems.",
            "expected": "The statistical and machine learning literature provides sophisticated frameworks for uncertainty quantification. Der Kiureghian and Ditlevsen ([2009](https://doi.org/10.1016/j.strusafe.2008.06.020)) formalize the aleatory/epistemic distinction and methods for propagation through complex systems.",
            "description": "Author names repeated in citation",
        },
        # Case 2: Et al. case
        {
            "input": "Recent work by Smith et al. (Smith et al. (2023)) demonstrates this principle.",
            "expected": "Recent work by Smith et al. (2023) demonstrates this principle.",
            "description": "Et al. repetition",
        },
        # Case 3: Single author
        {
            "input": "As noted by Johnson (Johnson (2022)), the effect is significant.",
            "expected": "As noted by Johnson (2022), the effect is significant.",
            "description": "Single author repetition",
        },
        # Case 4: Should NOT be changed - different context
        {
            "input": "Smith's analysis differs from Johnson (Johnson (2022)) in several ways.",
            "expected": "Smith's analysis differs from Johnson (Johnson (2022)) in several ways.",
            "description": "Different authors - should not change",
        },
        # Case 5: Complex with markdown links
        {
            "input": "The framework proposed by Lee and Park ([Lee and Park (2021)](https://example.com)) addresses this gap.",
            "expected": "The framework proposed by Lee and Park ([2021](https://example.com)) addresses this gap.",
            "description": "Two authors with markdown link",
        },
    ]

    fixer = CitationStyleFixer()

    print("Testing Citation Style Fixer")
    print("=" * 80)

    all_passed = True

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['description']}")
        print(f"Input:    {test_case['input'][:80]}...")

        corrected_text, issues = fixer.fix_document(test_case["input"])

        if corrected_text == test_case["expected"]:
            print("PASSED")
        else:
            print("FAILED")
            print(f"Expected: {test_case['expected'][:80]}...")
            print(f"Got:      {corrected_text[:80]}...")
            all_passed = False

        if issues:
            for issue in issues:
                print(f"  - Line {issue.line_number}: {issue.explanation}")
                print(f"    Original:  '{issue.original_text}'")
                print(f"    Corrected: '{issue.corrected_text}'")

    print("\n" + "=" * 80)
    print(
        f"Summary: {'All tests passed!' if all_passed else 'Some tests failed!'}"
    )

    # Test on a real file excerpt
    print("\n\nTesting on real UADReview_v4 excerpt:")
    print("=" * 80)

    real_text = """
The statistical and machine learning literature provides sophisticated frameworks for uncertainty quantification. Der Kiureghian and Ditlevsen ([Kiureghian and Ditlevsen (2009)](https://doi.org/10.1016/j.strusafe.2008.06.020)) formalize the aleatory/epistemic distinction and methods for propagation through complex systems. For neural network models, several approaches have emerged:

Another example might be when Lundberg and Lee ([Lee (2017)](https://arxiv.org/abs/1705.07874)) developed SHAP values for model interpretation.

The work of Rudin ([Rudin (2019)](https://doi.org/10.1038/s42256-019-0048-x)) argues for inherently interpretable models.
"""

    corrected_text, issues = fixer.fix_document(real_text)

    print(f"Found {len(issues)} issues:")
    for issue in issues:
        print(f"\nLine {issue.line_number}:")
        print(f"  Original:  {issue.original_text}")
        print(f"  Corrected: {issue.corrected_text}")
        print(f"  Confidence: {issue.confidence}")

    print("\nCorrected text:")
    print("-" * 40)
    print(corrected_text)


if __name__ == "__main__":
    test_citation_style_fixer()
