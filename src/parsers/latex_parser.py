"""LaTeX parser using pylatexenc."""

import logging
from typing import Any

from pylatexenc.latexwalker import (
    LatexCharsNode,
    LatexCommentNode,
    LatexEnvironmentNode,
    LatexGroupNode,
    LatexMacroNode,
    LatexMathNode,
    LatexNode,
    LatexWalker,
    LatexWalkerError,
)

from .base import ParsedDocument, ParsedNode, StructuredParser

logger = logging.getLogger(__name__)


class LatexParser(StructuredParser):
    """Parser for LaTeX documents using pylatexenc."""

    def __init__(self):
        """Initialize LaTeX parser."""
        self.walker = None

    def parse(self, text: str) -> ParsedDocument:
        """Parse LaTeX text into structured document."""
        self.walker = LatexWalker(text)

        try:
            nodes_list, pos, total_len = self.walker.get_latex_nodes()
        except LatexWalkerError as e:
            logger.error(f"LaTeX parsing error: {e}")
            # Return empty document on parse error
            return ParsedDocument(
                raw_text=text, nodes=[], metadata={"parse_error": str(e)}
            )

        # Convert LaTeX nodes to our ParsedNode format
        parsed_nodes = [
            self._convert_node(node, text) for node in nodes_list if node
        ]

        # Extract document metadata
        metadata = {
            "total_length": total_len,
            "num_nodes": len(parsed_nodes),
            "has_math": any(n.type == "math" for n in parsed_nodes),
            "has_citations": any(n.type == "citation" for n in parsed_nodes),
        }

        return ParsedDocument(
            raw_text=text, nodes=parsed_nodes, metadata=metadata
        )

    def _convert_node(self, node: LatexNode, text: str) -> ParsedNode:
        """Convert pylatexenc node to ParsedNode."""
        # Determine node type
        if isinstance(node, LatexMacroNode):
            node_type = (
                "citation"
                if node.macroname in ["cite", "citep", "citet", "textcite"]
                else "macro"
            )
            content = node.macroname
            metadata = {"macro_name": node.macroname}

            # Extract citation keys if this is a citation
            if (
                node_type == "citation"
                and node.nodeargd
                and node.nodeargd.argnlist
            ):
                citation_keys = self._extract_citation_keys(node)
                metadata["citation_keys"] = citation_keys

            # Store the parsed arguments in metadata for reconstruction
            if node.nodeargd and node.nodeargd.argnlist:
                metadata["parsed_args"] = node.nodeargd.argnlist

        elif isinstance(node, LatexEnvironmentNode):
            node_type = "environment"
            content = node.environmentname
            metadata = {"environment_name": node.environmentname}

        elif isinstance(node, LatexMathNode):
            node_type = "math"
            content = node.latex_verbatim()
            metadata = {"display_type": node.displaytype}

        elif isinstance(node, LatexCharsNode):
            node_type = "text"
            content = node.chars
            metadata = {}

        elif isinstance(node, LatexCommentNode):
            node_type = "comment"
            content = node.comment
            metadata = {}

        elif isinstance(node, LatexGroupNode):
            node_type = "group"
            content = ""
            metadata = {}

        else:
            node_type = "unknown"
            content = str(node)
            metadata = {}

        # Get position information
        start_pos = getattr(node, "pos", 0)
        end_pos = getattr(node, "pos_end", start_pos + len(content))
        line_no = text[:start_pos].count("\n") + 1
        col_no = start_pos - text.rfind("\n", 0, start_pos) - 1

        # Handle child nodes
        children = []
        if hasattr(node, "nodelist") and node.nodelist:
            for child in node.nodelist:
                if child:
                    children.append(self._convert_node(child, text))

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

    def _extract_citation_keys(self, node: LatexMacroNode) -> list[str]:
        """Extract citation keys from a citation macro node."""
        keys = []

        if node.nodeargd and node.nodeargd.argnlist:
            for arg in node.nodeargd.argnlist:
                if arg and hasattr(arg, "nodelist"):
                    # Extract text from argument
                    text_parts = []
                    for child in arg.nodelist:
                        if isinstance(child, LatexCharsNode):
                            text_parts.append(child.chars)

                    # Split by comma for multiple citations
                    arg_text = "".join(text_parts)
                    keys.extend(
                        [k.strip() for k in arg_text.split(",") if k.strip()]
                    )

        return keys

    def validate(self, text: str) -> list[str]:
        """Validate LaTeX text and return errors."""
        errors = []

        try:
            doc = self.parse(text)

            # Check for parse errors
            if "parse_error" in doc.metadata:
                errors.append(f"Parse error: {doc.metadata['parse_error']}")

            # Check for unmatched braces
            open_braces = text.count("{")
            close_braces = text.count("}")
            if open_braces != close_braces:
                errors.append(
                    f"Unmatched braces: {open_braces} {{ vs {close_braces} }}"
                )

            # Check for unmatched math delimiters
            single_dollar = text.count("$") % 2
            if single_dollar != 0:
                errors.append("Unmatched $ math delimiter")

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return errors

    def extract_citations(self, text: str) -> list[dict[str, Any]]:
        """Extract all citations from LaTeX text."""
        doc = self.parse(text)
        citations = []

        for node in doc.find_nodes_by_type("citation"):
            citation_info = {
                "type": node.metadata.get("macro_name", "cite"),
                "keys": node.metadata.get("citation_keys", []),
                "position": (node.start_pos, node.end_pos),
                "line": node.line_no,
                "column": node.col_no,
                "raw_text": doc.get_text_range(node.start_pos, node.end_pos),
            }
            citations.append(citation_info)

        return citations

    def extract_labels(self, text: str) -> list[dict[str, Any]]:
        """Extract all labels from LaTeX text."""
        labels = []

        # Parse directly to get access to raw nodes
        walker = LatexWalker(text)
        nodes_list, _, _ = walker.get_latex_nodes()

        for node in self._traverse_nodes(nodes_list):
            if isinstance(node, LatexMacroNode) and node.macroname == "label":
                if node.nodeargd and node.nodeargd.argnlist:
                    # Extract label text from first argument
                    label_text = self._extract_text_from_nodelist(
                        node.nodeargd.argnlist[0].nodelist
                    )

                    if label_text:
                        start_pos = getattr(node, "pos", 0)
                        end_pos = getattr(
                            node, "pos_end", start_pos + len(str(node))
                        )
                        labels.append(
                            {
                                "label": label_text.strip(),
                                "position": (start_pos, end_pos),
                                "line": text[:start_pos].count("\n") + 1,
                                "column": start_pos
                                - text.rfind("\n", 0, start_pos)
                                - 1,
                            }
                        )

        return labels

    def _traverse_nodes(self, nodes):
        """Recursively traverse LaTeX nodes."""
        for node in nodes:
            if node:
                yield node
                if hasattr(node, "nodelist") and node.nodelist:
                    yield from self._traverse_nodes(node.nodelist)

    def _extract_text_from_nodelist(self, nodelist):
        """Extract text content from a node list."""
        text_parts = []
        if nodelist:
            for node in nodelist:
                if isinstance(node, LatexCharsNode):
                    text_parts.append(node.chars)
        return "".join(text_parts)

    def extract_sections(self, text: str) -> list[dict[str, Any]]:
        """Extract all section commands from LaTeX text."""
        sections = []
        section_macros = [
            "section",
            "subsection",
            "subsubsection",
            "chapter",
            "part",
        ]

        # Parse directly to get access to raw nodes
        walker = LatexWalker(text)
        try:
            nodes_list, _, _ = walker.get_latex_nodes()
        except Exception as e:
            logger.error(f"Error parsing LaTeX for sections: {e}")
            return sections

        for node in self._traverse_nodes(nodes_list):
            if (
                isinstance(node, LatexMacroNode)
                and node.macroname in section_macros
            ):
                # Try different ways to get the argument
                title = None

                # Method 1: nodeargd
                if hasattr(node, "nodeargd") and node.nodeargd:
                    if (
                        hasattr(node.nodeargd, "argnlist")
                        and node.nodeargd.argnlist
                    ):
                        if len(node.nodeargd.argnlist) > 0:
                            arg = node.nodeargd.argnlist[0]
                            if (
                                arg
                                and hasattr(arg, "nodelist")
                                and arg.nodelist
                            ):
                                title = self._extract_text_from_nodelist(
                                    arg.nodelist
                                )

                # Method 2: nodeargs (older pylatexenc versions)
                if not title and hasattr(node, "nodeargs") and node.nodeargs:
                    if len(node.nodeargs) > 0:
                        arg = node.nodeargs[0]
                        if arg and hasattr(arg, "nodelist") and arg.nodelist:
                            title = self._extract_text_from_nodelist(
                                arg.nodelist
                            )
                        elif isinstance(arg, list):
                            title = self._extract_text_from_nodelist(arg)

                if title:
                    start_pos = getattr(node, "pos", 0)
                    end_pos = getattr(
                        node, "pos_end", start_pos + len(str(node))
                    )
                    sections.append(
                        {
                            "type": node.macroname,
                            "title": title.strip(),
                            "position": (start_pos, end_pos),
                            "line": text[:start_pos].count("\n") + 1,
                            "column": start_pos
                            - text.rfind("\n", 0, start_pos)
                            - 1,
                        }
                    )

        return sections
