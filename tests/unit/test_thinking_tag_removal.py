"""Unit tests for thinking tag removal in preprocessing."""

import pytest
from src.core.biblio_checker import BiblioChecker


class TestThinkingTagRemoval:
    """Test cases for Claude thinking tag removal."""

    @pytest.fixture
    def checker(self):
        """Create a BiblioChecker instance for testing."""
        return BiblioChecker()

    def test_single_thinking_tag_removal(self, checker):
        """Test removal of a single thinking tag."""
        input_text = "Before\n<thinking>Internal thoughts</thinking>\nAfter"
        result = checker._preprocess_markdown(input_text)

        assert "<thinking>" not in result
        assert "</thinking>" not in result
        assert "Internal thoughts" not in result
        assert "Before" in result
        assert "After" in result

    def test_multiple_thinking_tags_removal(self, checker):
        """Test removal of multiple thinking tags."""
        input_text = """First section
<thinking>First thought</thinking>
Middle section
<thinking>Second thought</thinking>
Last section"""

        result = checker._preprocess_markdown(input_text)

        assert "<thinking>" not in result
        assert "</thinking>" not in result
        assert "First thought" not in result
        assert "Second thought" not in result
        assert "First section" in result
        assert "Middle section" in result
        assert "Last section" in result

    def test_nested_content_removal(self, checker):
        """Test removal of complex nested content within thinking tags."""
        input_text = """# Document
<thinking>
This is a complex thought with:
- Bullet points
- Multiple lines
- [Even links](https://example.com)

And multiple paragraphs.
</thinking>

Actual content here."""

        result = checker._preprocess_markdown(input_text)

        assert "<thinking>" not in result
        assert "</thinking>" not in result
        assert "Bullet points" not in result
        assert "Even links" not in result
        assert "# Document" in result
        assert "Actual content here." in result

    def test_no_thinking_tags(self, checker):
        """Test that content without thinking tags is unchanged (except for other preprocessing)."""
        input_text = "This is normal content without any special tags."
        result = checker._preprocess_markdown(input_text)

        # Content should be present (may have minor formatting changes from other preprocessing)
        assert "This is normal content without any special tags." in result

    def test_empty_thinking_tags(self, checker):
        """Test removal of empty thinking tags."""
        input_text = "Before\n<thinking></thinking>\nAfter"
        result = checker._preprocess_markdown(input_text)

        assert "<thinking>" not in result
        assert "</thinking>" not in result
        assert "Before" in result
        assert "After" in result

    def test_thinking_tags_with_special_characters(self, checker):
        """Test removal of thinking tags containing special regex characters."""
        input_text = """Start
<thinking>
Special chars: $.*+?{}[]()|\\ and more
</thinking>
End"""

        result = checker._preprocess_markdown(input_text)

        assert "<thinking>" not in result
        assert "</thinking>" not in result
        assert "Special chars:" not in result
        assert "$.*+?{}[]()|\\" not in result
        assert "Start" in result
        assert "End" in result
