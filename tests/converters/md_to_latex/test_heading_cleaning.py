"""Tests for markdown heading cleaning functionality."""

from src.converters.md_to_latex.utils import (
    clean_markdown_headings,
)


class TestHeadingCleaning:
    """Test the clean_markdown_headings function."""

    def test_remove_bold_formatting(self):
        """Test removal of bold markers from headings."""
        content = """# **Bold Title**
## **Bold Section**
### **Bold Subsection**

Regular paragraph text."""

        expected = """# Bold Title
## Bold Section
### Bold Subsection

Regular paragraph text."""

        assert clean_markdown_headings(content) == expected

    def test_remove_numbers_simple(self):
        """Test removal of simple section numbers."""
        content = """# 1. Introduction
## 2. Methods
### 3. Results"""

        expected = """# Introduction
## Methods
### Results"""

        assert clean_markdown_headings(content) == expected

    def test_remove_numbers_hierarchical(self):
        """Test removal of hierarchical section numbers."""
        content = """## 1.1 Background
### 2.1.3 Detailed Analysis
#### 3.2.1.4 Specific Point"""

        expected = """## Background
### Detailed Analysis
#### Specific Point"""

        assert clean_markdown_headings(content) == expected

    def test_escaped_periods(self):
        """Test handling of escaped periods in markdown."""
        content = r"""## 1\. Introduction
### 2\.1 Methods
#### 3\.2\.1 Analysis"""

        expected = """## Introduction
### Methods
#### Analysis"""

        assert clean_markdown_headings(content) == expected

    def test_combined_bold_and_numbers(self):
        """Test removal of both bold formatting and numbers."""
        content = r"""# **The Main Title**
## **1\. Introduction**
### **2\.1 Background and Context**
#### **3\.2\.1 Specific Details**"""

        expected = """# The Main Title
## Introduction
### Background and Context
#### Specific Details"""

        assert clean_markdown_headings(content) == expected

    def test_preserve_non_headings(self):
        """Test that non-heading lines are preserved."""
        content = """## **1. Section**

This paragraph has **bold text** and numbers like 1.2.3.

- Item 1. First
- Item 2. Second

### **2.1 Subsection**

More content with **emphasis**."""

        expected = """## Section

This paragraph has **bold text** and numbers like 1.2.3.

- Item 1. First
- Item 2. Second

### Subsection

More content with **emphasis**."""

        assert clean_markdown_headings(content) == expected

    def test_edge_cases(self):
        """Test edge cases."""
        # Heading with no content after number
        assert clean_markdown_headings("## 1.") == "## "

        # Heading with only bold markers
        assert clean_markdown_headings("## ****") == "## "

        # Heading with multiple spaces
        assert (
            clean_markdown_headings("##   1.  Introduction")
            == "##   Introduction"
        )

        # Empty content
        assert clean_markdown_headings("") == ""

        # No headings
        assert (
            clean_markdown_headings("Just regular text") == "Just regular text"
        )
