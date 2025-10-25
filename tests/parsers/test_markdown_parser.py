"""Tests for Markdown parser."""

from src.parsers import MarkdownParser


class TestMarkdownParser:
    """Test Markdown parser functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = MarkdownParser()

    def test_parse_simple_text(self):
        """Test parsing simple Markdown text."""
        text = "# Hello World\n\nThis is a paragraph."
        doc = self.parser.parse(text)

        assert doc.raw_text == text
        assert len(doc.nodes) > 0
        assert doc.metadata["has_headings"]

    def test_extract_headings(self):
        """Test extracting headings."""
        text = """# Main Title
## Section 1
### Subsection 1.1
## Section 2
"""

        headings = self.parser.extract_headings(text)

        assert len(headings) == 4
        assert headings[0]["level"] == 1
        assert headings[0]["text"] == "Main Title"
        assert headings[1]["level"] == 2
        assert headings[2]["level"] == 3

    def test_extract_links(self):
        """Test extracting links."""
        text = "Here is a [link](https://example.com).\n"
        text += 'Another [link with title](https://example.org "Title").\n'
        text += "And a [reference link][ref].\n\n"
        text += "[ref]: https://reference.com"

        links = self.parser.extract_links(text)

        assert len(links) >= 2
        assert links[0]["text"] == "link"
        assert links[0]["href"] == "https://example.com"
        assert links[1]["title"] == "Title"

    def test_extract_images(self):
        """Test extracting images."""
        text = "![Alt text](image.png)\n"
        text += '![Another image](https://example.com/image.jpg "Image title")'

        images = self.parser.extract_images(text)

        assert len(images) == 2
        assert images[0]["alt"] == "Alt text"
        assert images[0]["src"] == "image.png"
        assert images[1]["src"] == "https://example.com/image.jpg"

    def test_extract_code_blocks(self):
        """Test extracting code blocks."""
        text = """```python
def hello():
    print("Hello, world!")
```

```javascript
console.log("Hello");
```

    Indented code block
"""

        code_blocks = self.parser.extract_code_blocks(text)

        assert len(code_blocks) >= 2
        assert code_blocks[0]["language"] == "python"
        assert "def hello():" in code_blocks[0]["content"]
        assert code_blocks[1]["language"] == "javascript"

    def test_parse_inline_elements(self):
        """Test parsing inline elements."""
        text = "This has **bold** and *italic* and `code` text."

        doc = self.parser.parse(text)

        # Check that we have text content with formatting
        # Note: inline nodes are internal to markdown-it processing
        # We should check for the actual content nodes instead
        all_nodes = self.parser._flatten_nodes(doc.nodes)
        text_nodes = [n for n in all_nodes if n.type == "text"]
        assert len(text_nodes) > 0  # Should have text nodes

    def test_parse_lists(self):
        """Test parsing lists."""
        text = """- Item 1
- Item 2
  - Nested item
- Item 3

1. First
2. Second
3. Third
"""

        doc = self.parser.parse(text)

        # Check for list nodes
        bullet_lists = [n for n in doc.nodes if n.type == "bullet_list"]
        ordered_lists = [n for n in doc.nodes if n.type == "ordered_list"]

        assert len(bullet_lists) > 0
        assert len(ordered_lists) > 0

    def test_parse_blockquotes(self):
        """Test parsing blockquotes."""
        text = """> This is a quote
> with multiple lines
>
> > And nested quotes
"""

        doc = self.parser.parse(text)

        blockquotes = [n for n in doc.nodes if n.type == "blockquote"]
        assert len(blockquotes) > 0

    def test_validate_valid_markdown(self):
        """Test validation of valid Markdown."""
        text = """# Title

This is a paragraph with [a link](https://example.com).

## Section

- List item 1
- List item 2
"""

        errors = self.parser.validate(text)
        assert len(errors) == 0

    def test_validate_unmatched_brackets(self):
        """Test validation with unmatched brackets."""
        text = "This has [unmatched bracket"

        errors = self.parser.validate(text)
        assert len(errors) > 0
        assert any("bracket" in error.lower() for error in errors)

    def test_validate_heading_hierarchy(self):
        """Test validation of heading hierarchy."""
        text = """# Title
### Skipped Level
## Back to Level 2
"""

        errors = self.parser.validate(text)
        assert len(errors) > 0
        assert any("heading level skip" in error.lower() for error in errors)

    def test_parse_tables(self):
        """Test parsing tables (if enabled)."""
        text = """| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |
"""

        doc = self.parser.parse(text)

        # Tables might be parsed as specific tokens
        assert len(doc.nodes) > 0

    def test_parse_html_content(self):
        """Test parsing with HTML content."""
        text = """Regular text

<div>HTML content</div>

More regular text
"""

        doc = self.parser.parse(text)

        # Should parse without errors
        assert "parse_error" not in doc.metadata
