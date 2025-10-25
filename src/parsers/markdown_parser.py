"""Markdown parser using markdown-it-py."""

import logging
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from .base import ParsedDocument, ParsedNode, StructuredParser

logger = logging.getLogger(__name__)


class MarkdownParser(StructuredParser):
    """Parser for Markdown documents using markdown-it-py."""

    def __init__(self):
        """Initialize Markdown parser."""
        self.md = MarkdownIt("commonmark", {"breaks": True, "html": True})
        # Enable additional features
        self.md.enable(["table", "strikethrough"])

    def parse(self, text: str) -> ParsedDocument:
        """Parse Markdown text into structured document."""
        try:
            tokens = self.md.parse(text)
        except Exception as e:
            logger.error(f"Markdown parsing error: {e}")
            return ParsedDocument(
                raw_text=text, nodes=[], metadata={"parse_error": str(e)}
            )

        # Convert tokens to ParsedNodes recursively
        nodes = self._process_tokens(tokens, text)

        # Extract metadata
        metadata = {
            "num_tokens": len(tokens),
            "has_headings": any(
                n.type == "heading" for n in self._flatten_nodes(nodes)
            ),
            "has_links": any(
                n.type == "link" for n in self._flatten_nodes(nodes)
            ),
            "has_images": any(
                n.type == "image" for n in self._flatten_nodes(nodes)
            ),
            "has_code": any(
                n.type in ["code_inline", "code_block"]
                for n in self._flatten_nodes(nodes)
            ),
        }

        return ParsedDocument(raw_text=text, nodes=nodes, metadata=metadata)

    def _process_tokens(
        self, tokens: list[Token], text: str
    ) -> list[ParsedNode]:
        """Process a list of tokens into ParsedNodes."""
        nodes = []
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.nesting == 1:  # Opening tag
                # Find corresponding closing tag
                closing_idx = self._find_closing_token(tokens, i)
                if closing_idx is not None:
                    # Process block with children
                    node = self._create_block_node(
                        token, tokens[i + 1 : closing_idx], text
                    )
                    if node:
                        nodes.append(node)
                    i = closing_idx + 1
                else:
                    # No closing tag found, treat as self-closing
                    node = self._token_to_node(token, text)
                    if node:
                        nodes.append(node)
                    i += 1
            elif token.nesting == 0:  # Self-closing or inline
                # Special handling for inline tokens with children
                if (
                    token.type == "inline"
                    and hasattr(token, "children")
                    and token.children
                ):
                    # Process inline children specially to detect images
                    inline_nodes = self._process_inline_tokens(
                        token.children, text
                    )
                    nodes.extend(inline_nodes)
                else:
                    node = self._token_to_node(token, text)
                    if node:
                        nodes.append(node)
                i += 1
            else:  # Closing tag (-1), skip
                i += 1

        return nodes

    def _process_inline_tokens(
        self, tokens: list[Token], text: str
    ) -> list[ParsedNode]:
        """Process inline tokens, detecting images and links."""
        nodes = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            # Check for image pattern: text with "!" followed by link_open
            if (
                i + 1 < len(tokens)
                and token.type == "text"
                and token.content == "!"
                and tokens[i + 1].type == "link_open"
            ):
                # This is an image
                link_token = tokens[i + 1]
                attrs_dict = dict(link_token.attrs) if link_token.attrs else {}

                # Find the alt text
                alt_text = ""
                j = i + 2
                while j < len(tokens) and tokens[j].type != "link_close":
                    if tokens[j].type == "text":
                        alt_text += tokens[j].content
                    j += 1

                # Create image node
                image_node = ParsedNode(
                    type="image",
                    content=alt_text,
                    start_pos=0,  # Will be set later
                    end_pos=0,
                    line_no=1,
                    col_no=0,
                    metadata={
                        "src": attrs_dict.get("href", ""),
                        "alt": alt_text,
                        "title": attrs_dict.get("title", ""),
                    },
                    children=[],
                )
                nodes.append(image_node)

                # Skip to after link_close
                i = j + 1
            elif token.type == "link_open":
                # This is a regular link
                attrs_dict = dict(token.attrs) if token.attrs else {}

                # Find the link text
                link_text = ""
                link_children = []
                j = i + 1
                while j < len(tokens) and tokens[j].type != "link_close":
                    if tokens[j].type == "text":
                        link_text += tokens[j].content
                    # Process child node for link content
                    child_node = self._token_to_node(tokens[j], text)
                    if child_node:
                        link_children.append(child_node)
                    j += 1

                # Create link node
                link_node = ParsedNode(
                    type="link",
                    content=link_text,
                    start_pos=0,  # Will be set later
                    end_pos=0,
                    line_no=1,
                    col_no=0,
                    metadata={
                        "href": attrs_dict.get("href", ""),
                        "title": attrs_dict.get("title", ""),
                    },
                    children=link_children,
                )
                nodes.append(link_node)

                # Skip to after link_close
                i = j + 1
            else:
                # Regular token processing
                node = self._token_to_node(token, text)
                if node:
                    nodes.append(node)
                i += 1

        return nodes

    def _find_closing_token(
        self, tokens: list[Token], start_idx: int
    ) -> int | None:
        """Find the closing token for an opening token."""
        opening_token = tokens[start_idx]
        target_type = opening_token.type.replace("_open", "_close")
        nesting_level = 1

        for i in range(start_idx + 1, len(tokens)):
            if tokens[i].type == opening_token.type:
                nesting_level += 1
            elif tokens[i].type == target_type:
                nesting_level -= 1
                if nesting_level == 0:
                    return i

        return None

    def _create_block_node(
        self, opening_token: Token, inner_tokens: list[Token], text: str
    ) -> ParsedNode | None:
        """Create a block node with children."""
        node = self._token_to_node(opening_token, text)
        if node:
            # Process inner tokens as children
            node.children = self._process_tokens(inner_tokens, text)

            # Special case for inline tokens inside blocks
            if len(inner_tokens) == 1 and inner_tokens[0].type == "inline":
                inline_token = inner_tokens[0]
                if hasattr(inline_token, "children") and inline_token.children:
                    # Replace with processed inline children
                    node.children = self._process_inline_tokens(
                        inline_token.children, text
                    )
        return node

    def _flatten_nodes(self, nodes: list[ParsedNode]) -> list[ParsedNode]:
        """Flatten nested nodes for easier searching."""
        result = []
        for node in nodes:
            result.append(node)
            result.extend(self._flatten_nodes(node.children))
        return result

    def _token_to_node(self, token: Token, text: str) -> ParsedNode | None:
        """Convert markdown-it token to ParsedNode."""
        # Skip closing tokens (handled by nesting logic)
        if token.nesting == -1:
            return ParsedNode(
                type=token.type,
                content="",
                start_pos=0,
                end_pos=0,
                line_no=0,
                col_no=0,
                metadata={},
                children=[],
            )

        # Map token types to our types
        type_mapping = {
            "heading_open": "heading",
            "paragraph_open": "paragraph",
            "link_open": "link",
            "image": "image",
            "code_inline": "code_inline",
            "fence": "code_block",
            "code_block": "code_block",
            "blockquote_open": "blockquote",
            "list_item_open": "list_item",
            "bullet_list_open": "bullet_list",
            "ordered_list_open": "ordered_list",
            "text": "text",
            "inline": "inline",
            "softbreak": "softbreak",
            "hardbreak": "hardbreak",
        }

        # DEBUG: Log token info for debugging
        logger.debug(
            f"Token type: {token.type}, nesting: {token.nesting}, content: {token.content[:50] if token.content else 'None'}"
        )

        node_type = type_mapping.get(token.type, token.type)

        # Extract content and metadata based on type
        content = token.content or ""
        metadata = {}

        if token.type == "heading_open":
            metadata["level"] = (
                int(token.tag[1]) if token.tag and len(token.tag) > 1 else 1
            )  # h1 -> 1, h2 -> 2, etc.
        elif token.type == "link_open":
            if token.attrs:
                attrs_dict = dict(token.attrs)
                metadata["href"] = attrs_dict.get("href", "")
                metadata["title"] = attrs_dict.get("title", "")
        elif token.type == "image":
            if token.attrs:
                attrs_dict = dict(token.attrs)
                metadata["src"] = attrs_dict.get("src", "")
                metadata["alt"] = attrs_dict.get("alt", "")
            # For images, extract alt text from content
            if token.content:
                metadata["alt"] = token.content
        elif token.type == "fence":
            metadata["language"] = token.info or ""
        elif token.type == "ordered_list_open":
            if token.attrs:
                attrs_dict = dict(token.attrs)
                metadata["start"] = attrs_dict.get("start", "1")

        # Calculate position
        if hasattr(token, "map") and token.map:
            line_start, line_end = token.map
            line_no = line_start + 1
            # Find actual position in text
            lines = text.split("\n")
            start_pos = sum(len(line) + 1 for line in lines[:line_start])
            end_pos = sum(len(line) + 1 for line in lines[:line_end])
            col_no = 0
        else:
            # Approximate position
            start_pos = 0
            end_pos = len(content)
            line_no = 1
            col_no = 0

        # Handle children for inline content
        children = []
        if hasattr(token, "children") and token.children:
            for child_token in token.children:
                child_node = self._token_to_node(child_token, text)
                if child_node:
                    children.append(child_node)

        return ParsedNode(
            type=node_type,
            content=content,
            start_pos=start_pos,
            end_pos=end_pos,
            line_no=line_no,
            col_no=col_no,
            metadata=metadata,
            children=children,
        )

    def validate(self, text: str) -> list[str]:
        """Validate Markdown text and return errors."""
        errors = []

        try:
            doc = self.parse(text)

            # Check for parse errors
            if "parse_error" in doc.metadata:
                errors.append(f"Parse error: {doc.metadata['parse_error']}")
                return errors

            # Check for common issues
            # Check unclosed links
            open_brackets = text.count("[")
            close_brackets = text.count("]")
            if open_brackets != close_brackets:
                errors.append(
                    f"Unmatched brackets: {open_brackets} [ vs {close_brackets} ]"
                )

            # Check for broken reference links
            # TODO: Implement reference link validation
            # This would check that [ref]: definitions match [text][ref] usage

            # Check heading hierarchy
            headings = [
                n for n in self._flatten_nodes(doc.nodes) if n.type == "heading"
            ]
            prev_level = 0
            for heading in headings:
                level = heading.metadata.get("level", 1)
                if level > prev_level + 1:
                    errors.append(
                        f"Heading level skip at line {heading.line_no}: h{prev_level} -> h{level}"
                    )
                prev_level = level

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return errors

    def extract_links(self, text: str) -> list[dict[str, Any]]:
        """Extract all links from Markdown text."""
        doc = self.parse(text)
        links = []

        for node in self._flatten_nodes(doc.nodes):
            if node.type == "link":
                # Get link text from children
                link_text = self._get_text_content(node)

                link_info = {
                    "text": link_text.strip(),
                    "href": node.metadata.get("href", ""),
                    "title": node.metadata.get("title", ""),
                    "position": (node.start_pos, node.end_pos),
                    "line": node.line_no,
                    "column": node.col_no,
                }
                links.append(link_info)

        return links

    def extract_headings(self, text: str) -> list[dict[str, Any]]:
        """Extract all headings from Markdown text."""
        doc = self.parse(text)
        headings = []

        for node in self._flatten_nodes(doc.nodes):
            if node.type == "heading":
                # Get heading text from children
                heading_text = self._get_text_content(node)

                heading_info = {
                    "level": node.metadata.get("level", 1),
                    "text": heading_text.strip(),
                    "position": (node.start_pos, node.end_pos),
                    "line": node.line_no,
                    "column": node.col_no,
                }
                headings.append(heading_info)

        return headings

    def _get_text_content(self, node: ParsedNode) -> str:
        """Recursively extract text content from a node and its children."""
        text = ""
        if node.type == "text":
            text = node.content
        elif node.type == "code_inline":
            text = node.content

        for child in node.children:
            text += self._get_text_content(child)

        return text

    def extract_code_blocks(self, text: str) -> list[dict[str, Any]]:
        """Extract all code blocks from Markdown text."""
        doc = self.parse(text)
        code_blocks = []

        for node in self._flatten_nodes(doc.nodes):
            if node.type == "code_block":
                code_info = {
                    "language": node.metadata.get("language", ""),
                    "content": node.content,
                    "position": (node.start_pos, node.end_pos),
                    "line": node.line_no,
                    "column": node.col_no,
                }
                code_blocks.append(code_info)

        return code_blocks

    def extract_images(self, text: str) -> list[dict[str, Any]]:
        """Extract all images from Markdown text."""
        doc = self.parse(text)
        images = []

        for node in self._flatten_nodes(doc.nodes):
            if node.type == "image":
                image_info = {
                    "src": node.metadata.get("src", ""),
                    "alt": node.metadata.get("alt", ""),
                    "position": (node.start_pos, node.end_pos),
                    "line": node.line_no,
                    "column": node.col_no,
                }
                images.append(image_info)

        return images
