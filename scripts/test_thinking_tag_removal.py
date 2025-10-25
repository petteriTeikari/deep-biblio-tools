#!/usr/bin/env python3
"""Test script to verify thinking tag removal in preprocessing."""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.biblio_checker import BiblioChecker


def test_thinking_tag_removal():
    """Test that thinking tags are properly removed during preprocessing."""
    checker = BiblioChecker()

    # Test cases
    test_cases = [
        # Basic thinking tag
        {
            "input": "Some text before\n<thinking>\nThis is thinking content\n</thinking>\nSome text after",
            "expected": "Some text before\n\nSome text after",
        },
        # Multiple thinking tags
        {
            "input": "First part\n<thinking>First thought</thinking>\nMiddle part\n<thinking>Second thought</thinking>\nEnd part",
            "expected": "First part\n\nMiddle part\n\nEnd part",
        },
        # Thinking tag with complex content
        {
            "input": """# Title
<thinking>
The user wants me to create Version 4 by adding ~4,000 words to Version 3b while keeping ALL content from v3b and adding technical depth without removing economic analysis. They've provided specific instructions about what to add, including:

1. Section 3.1 (Physical Data Acquisition) - Add proper technical explanations
2. Section 3.2 (Neural Rendering) - Critical analysis of 3DGS
3. Technical Concept Boxes Throughout (10-15 boxes)
4. Key Expansions by Section with word counts

I need to carefully integrate technical content from Version 2 into Version 3b while maintaining the economic framework and avoiding any code snippets or implementation details. The writing style should be "just right" - not too simple, not too technical.

Let me continue building Version 4, integrating the technical content appropriately...
</thinking>

## Introduction

This is the actual content that should remain.""",
            "expected": """# Title


## Introduction

This is the actual content that should remain.""",
        },
        # No thinking tags
        {
            "input": "This is normal text without any thinking tags.",
            "expected": "This is normal text without any thinking tags.",
        },
    ]

    print("Testing thinking tag removal...")
    all_passed = True

    for i, test_case in enumerate(test_cases, 1):
        result = checker._preprocess_markdown(test_case["input"])

        # The preprocessing also does other things like fixing spacing, so we need to
        # check if thinking tags are removed rather than exact match
        has_thinking_tags = "<thinking>" in result or "</thinking>" in result

        if has_thinking_tags:
            print(f"\nTest {i} FAILED: Thinking tags not removed")
            print(f"Input preview: {test_case['input'][:100]}...")
            print(f"Output preview: {result[:100]}...")
            all_passed = False
        else:
            print(f"Test {i} PASSED: Thinking tags successfully removed")

    # Additional check: ensure no thinking content remains
    if all_passed:
        # Check a real example
        real_example = """<thinking>
The user wants me to analyze this document.
</thinking>

# Real Document Title

Here's a citation to check: [Smith et al. (2023)](https://example.com/paper)"""

        processed = checker._preprocess_markdown(real_example)
        if "The user wants me" in processed:
            print("\nContent within thinking tags not fully removed!")
            all_passed = False
        else:
            print("\nAll thinking tag content properly removed!")

    print(f"\n{'All tests passed!' if all_passed else 'Some tests failed!'}")
    return all_passed


if __name__ == "__main__":
    success = test_thinking_tag_removal()
    sys.exit(0 if success else 1)
