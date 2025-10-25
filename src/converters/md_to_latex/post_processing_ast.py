"""AST-based post-processing module for cleaning up LaTeX output.

This module uses the LaTeX AST parser to safely transform LaTeX documents
without relying on error-prone regex patterns.
"""

# Standard library imports
import logging
from pathlib import Path

# Third-party imports
from pylatexenc.latexwalker import LatexCharsNode

# Local imports
from src.parsers import LatexParser
from src.parsers.base import ParsedDocument, ParsedNode

logger = logging.getLogger(__name__)


class ASTLatexPostProcessor:
    """Clean up common issues in LaTeX files using AST-based parsing."""

    def __init__(self):
        """Initialize the post-processor."""
        self.fixes_applied = []
        self.parser = LatexParser()

    def process_file(self, latex_file: Path) -> None:
        """Process a LaTeX file and apply all cleaning routines.

        Args:
            latex_file: Path to the LaTeX file to process
        """
        logger.info(f"Post-processing LaTeX file using AST: {latex_file}")

        # Read the file
        content = latex_file.read_text(encoding="utf-8")
        original_content = content

        try:
            # Parse the LaTeX document
            doc = self.parser.parse(content)

            # Apply AST-based transformations
            self._fix_passthrough_commands_ast(doc)
            self._fix_nested_emphasis_ast(doc)
            self._fix_empty_captions_ast(doc)
            self._convert_href_citations_ast(doc)

            # Reconstruct the document
            content = self._reconstruct_document(doc)

            # Apply remaining text-based fixes that don't require AST
            content = self._clean_excessive_line_breaks(content)

        except Exception as e:
            logger.warning(f"AST parsing failed, falling back to regex: {e}")
            # Fall back to regex-based processing - import here to avoid circular imports
            from .post_processing import LatexPostProcessor

            fallback = LatexPostProcessor()
            fallback.process_file(latex_file)
            return

        # Write back if changes were made
        if content != original_content:
            latex_file.write_text(content, encoding="utf-8")
            logger.info(
                f"Applied {len(self.fixes_applied)} fixes to {latex_file}"
            )
            for fix in self.fixes_applied:
                logger.debug(f"  - {fix}")
        else:
            logger.info("No fixes needed")

    def _fix_passthrough_commands_ast(self, doc: ParsedDocument) -> None:
        """Fix pandoc's passthrough commands using AST."""
        # Process all nodes recursively
        self._fix_passthrough_in_nodes(doc.nodes)

    def _fix_passthrough_in_nodes(self, nodes: list) -> None:
        """Recursively fix passthrough commands in nodes."""
        # Track nodes to remove
        nodes_to_remove = set()

        # First, find passthrough macros and their associated group nodes
        for i, node in enumerate(nodes):
            # Process children first
            if node.children:
                self._fix_passthrough_in_nodes(node.children)
            if (
                node.type == "macro"
                and node.metadata.get("macro_name") == "passthrough"
            ):
                # Check for parsed args first
                content = None
                if (
                    "parsed_args" in node.metadata
                    and node.metadata["parsed_args"]
                ):
                    # Extract from parsed args
                    arg_text = self._extract_text_from_pylatexenc_node(
                        node.metadata["parsed_args"][0]
                    )
                    content = self._extract_lstinline_from_text(arg_text)
                elif i + 1 < len(nodes) and nodes[i + 1].type == "group":
                    # Check next node for group argument
                    group_node = nodes[i + 1]
                    if (
                        group_node.children
                        and group_node.children[0].type == "text"
                    ):
                        content = self._extract_lstinline_from_text(
                            group_node.children[0].content
                        )
                        # Mark the group node for removal since we're extracting its content
                        nodes_to_remove.add(i + 1)

                if content:
                    # Replace with texttt
                    node.metadata["original_macro"] = "passthrough"
                    node.metadata["macro_name"] = "texttt"
                    node.content = "texttt"

                    # Create parsed args for proper reconstruction
                    node.metadata["parsed_args"] = [
                        type(
                            "obj", (object,), {"chars": content, "nodelist": []}
                        )
                    ]

                    # Clear any existing children
                    node.children = []

                    self.fixes_applied.append("Fixed passthrough command")

        # Remove marked nodes (in reverse order to maintain indices)
        for idx in sorted(nodes_to_remove, reverse=True):
            if idx < len(nodes):
                nodes.pop(idx)

    def _fix_nested_emphasis_ast(self, doc: ParsedDocument) -> None:
        """Fix nested emphasis using AST."""
        for node in self._walk_nodes(doc.nodes):
            if (
                node.type == "macro"
                and node.metadata.get("macro_name") == "emph"
            ):
                # Check for nested emph
                for child in self._walk_nodes(node.children):
                    if (
                        child.type == "macro"
                        and child.metadata.get("macro_name") == "emph"
                    ):
                        # Remove the inner emph
                        child.type = "group"
                        child.metadata = {}
                        self.fixes_applied.append("Fixed nested emphasis")

    def _fix_empty_captions_ast(self, doc: ParsedDocument) -> None:
        """Remove empty captions using AST."""

        def find_and_remove_empty_captions(nodes):
            """Recursively find and fix empty captions, handling their arguments."""
            i = 0
            while i < len(nodes):
                node = nodes[i]

                if (
                    node.type == "macro"
                    and node.metadata.get("macro_name") == "caption"
                ):
                    # Check if caption is empty
                    is_empty = True

                    # Check parsed args first
                    if (
                        "parsed_args" in node.metadata
                        and node.metadata["parsed_args"]
                    ):
                        for arg in node.metadata["parsed_args"]:
                            if arg is not None:
                                arg_text = (
                                    self._extract_text_from_pylatexenc_node(arg)
                                )
                                if arg_text.strip():
                                    is_empty = False
                                    break

                    # Check if next node is an empty group (for unknown macros)
                    if (
                        is_empty
                        and i + 1 < len(nodes)
                        and nodes[i + 1].type == "group"
                    ):
                        group_node = nodes[i + 1]
                        # Check if group is empty
                        if group_node.children:
                            for child in group_node.children:
                                if (
                                    child.type == "text"
                                    and child.content.strip()
                                ):
                                    is_empty = False
                                    break

                        if is_empty:
                            # Remove the empty group node
                            nodes.pop(i + 1)

                    if is_empty:
                        # Mark node for removal
                        node.type = "comment"
                        node.content = " Empty caption removed"
                        node.metadata = {}
                        node.children = []

                        # Remove parsed args if present
                        if "parsed_args" in node.metadata:
                            del node.metadata["parsed_args"]

                        self.fixes_applied.append("Removed empty caption")

                # Recursively process children
                if node.children:
                    find_and_remove_empty_captions(node.children)

                i += 1

        # Process all nodes
        find_and_remove_empty_captions(doc.nodes)

    def _convert_href_citations_ast(self, doc: ParsedDocument) -> None:
        """Convert academic hrefs to citations using AST."""
        academic_domains = {
            "doi.org",
            "arxiv.org",
            "sciencedirect.com",
            "springer.com",
            "wiley.com",
            "nature.com",
            "science.org",
            "plos.org",
            "ieee.org",
            "acm.org",
            "jstor.org",
            "pubmed",
            "ncbi.nlm.nih.gov",
            "researchgate.net",
            "academia.edu",
            "scholar.google",
            "ssrn.com",
            "elsevier.com",
            "tandfonline.com",
            "sagepub.com",
            "oup.com",
            "cambridge.org",
        }

        # Process all nodes recursively
        self._convert_href_in_nodes(doc.nodes, academic_domains)

    def _convert_href_in_nodes(
        self, nodes: list, academic_domains: set
    ) -> None:
        """Recursively convert href nodes to citations."""
        nodes_to_remove = set()

        for i, node in enumerate(nodes):
            # Process children first
            if node.children:
                self._convert_href_in_nodes(node.children, academic_domains)

            if (
                node.type == "macro"
                and node.metadata.get("macro_name") == "href"
            ):
                # Extract URL and text from following group nodes
                url = None
                text = None

                # Check for group nodes that follow
                if i + 2 < len(nodes):
                    url_node = nodes[i + 1]
                    text_node = nodes[i + 2]

                    if url_node.type == "group" and url_node.children:
                        url = (
                            url_node.children[0].content
                            if url_node.children[0].type == "text"
                            else None
                        )

                    if text_node.type == "group" and text_node.children:
                        text = (
                            text_node.children[0].content
                            if text_node.children[0].type == "text"
                            else None
                        )

                # Check if URL is academic and text looks like citation
                if (
                    url
                    and text
                    and any(domain in url for domain in academic_domains)
                ):
                    if self._looks_like_citation(text):
                        # Convert to citep
                        citation_key = self._generate_citation_key(text)
                        node.metadata["macro_name"] = "citep"
                        node.content = "citep"
                        node.type = "citation"

                        # Add citation key to metadata
                        node.metadata["citation_keys"] = [citation_key]

                        # Create parsed args for proper reconstruction
                        node.metadata["parsed_args"] = [
                            type(
                                "obj",
                                (object,),
                                {"chars": citation_key, "nodelist": []},
                            )
                        ]

                        # Mark the argument nodes for removal
                        nodes_to_remove.add(i + 1)
                        nodes_to_remove.add(i + 2)

                        self.fixes_applied.append(
                            f"Converted href to citation: {citation_key}"
                        )

        # Remove marked nodes (in reverse order to maintain indices)
        for idx in sorted(nodes_to_remove, reverse=True):
            if idx < len(nodes):
                nodes.pop(idx)

    def _walk_nodes(self, nodes: list[ParsedNode]):
        """Recursively walk through all nodes."""
        for node in nodes:
            yield node
            yield from self._walk_nodes(node.children)

    def _extract_lstinline_from_text(self, text: str) -> str | None:
        """Extract content from lstinline!...! pattern in text."""
        if "lstinline!" in text:
            # Extract content between exclamation marks
            match = text.find("lstinline!")
            if match >= 0:
                start = match + len("lstinline!")
                end = text.find("!", start)
                if end > start:
                    return text[start:end]
        return None

    def _extract_lstinline_content(self, node: ParsedNode) -> str | None:
        """Extract content from lstinline within a passthrough."""
        # Look for lstinline pattern in children
        for child in node.children:
            if child.type == "text" and "lstinline!" in child.content:
                return self._extract_lstinline_from_text(child.content)
        return None

    def _extract_href_url(self, node: ParsedNode) -> str | None:
        """Extract URL from href node."""
        # href has two arguments: URL and text
        if node.children and len(node.children) >= 1:
            # First child should contain URL
            return (
                node.children[0].content
                if node.children[0].type == "text"
                else None
            )
        return None

    def _extract_href_text(self, node: ParsedNode) -> str | None:
        """Extract display text from href node."""
        # href has two arguments: URL and text
        if node.children and len(node.children) >= 2:
            # Second child should contain text
            return (
                node.children[1].content
                if node.children[1].type == "text"
                else None
            )
        return None

    def _looks_like_citation(self, text: str) -> bool:
        """Check if text looks like a citation (Author Year format)."""
        # Simple heuristic: contains year (1900-2099)
        # Look for 4-digit years without regex
        words = text.split()
        for word in words:
            # Remove common punctuation
            cleaned = word.strip("()[]{},.;:")
            if len(cleaned) == 4 and cleaned.isdigit():
                # Check if it's a year in reasonable range
                year = int(cleaned)
                if 1900 <= year <= 2099:
                    return True
        return False

    def _generate_citation_key(self, text: str) -> str:
        """Generate a citation key from citation text."""
        # Extract author and year
        words = text.split()
        author = ""
        year = ""

        for word in words:
            # Check if word starts with capital letter (potential author name)
            cleaned_word = word.strip("()[]{},.;:")
            if (
                cleaned_word
                and cleaned_word[0].isupper()
                and len(cleaned_word) > 1
            ):
                # Check if rest is lowercase (typical surname pattern)
                if cleaned_word[1:].islower():
                    author = cleaned_word
                    break

        # Find year (4-digit number in reasonable range)
        for word in words:
            cleaned = word.strip("()[]{},.;:")
            if len(cleaned) == 4 and cleaned.isdigit():
                year_int = int(cleaned)
                if 1900 <= year_int <= 2099:
                    year = cleaned
                    break

        return f"{author}{year}" if author and year else "unknown"

    def _reconstruct_document(self, doc: ParsedDocument) -> str:
        """Reconstruct LaTeX document from AST.

        KNOWN LIMITATION: This method only reconstructs top-level nodes.
        Modifications to nested nodes (e.g., within environments) are processed
        but not reflected in the output. This affects:
        - passthrough commands inside environments
        - nested emphasis fixes

        The recursive processing of href->citation conversion works because it
        modifies the AST structure itself, but other fixes that only modify
        metadata may not be reflected in nested contexts.

        A full fix would require recursive reconstruction that tracks modifications
        at all levels of the AST tree.
        """
        # Track which nodes we've already processed to avoid duplicates
        processed_positions = set()
        reconstructed_parts = []
        last_end_pos = 0

        for i, node in enumerate(doc.nodes):
            # Skip if we've already processed this position (e.g., as part of a macro)
            if node.start_pos in processed_positions:
                continue

            # Add any text between nodes
            if node.start_pos > last_end_pos:
                reconstructed_parts.append(
                    doc.raw_text[last_end_pos : node.start_pos]
                )

            # Reconstruct the node
            reconstructed, end_pos = self._reconstruct_node_with_args(
                node, doc, i
            )
            reconstructed_parts.append(reconstructed)

            # Mark positions as processed
            for pos in range(node.start_pos, end_pos):
                processed_positions.add(pos)

            last_end_pos = end_pos

        # Add any trailing content
        if last_end_pos < len(doc.raw_text):
            reconstructed_parts.append(doc.raw_text[last_end_pos:])

        return "".join(reconstructed_parts)

    def _reconstruct_node_with_args(
        self, node: ParsedNode, doc: ParsedDocument, node_index: int
    ) -> tuple[str, int]:
        """Reconstruct a node with its arguments, returning (reconstructed_text, end_position)."""
        if node.type == "environment":
            # Handle environment nodes specially
            env_name = node.metadata.get("environment_name", node.content)
            reconstructed = self._reconstruct_node(node, doc.raw_text)

            # Find the actual end position by searching for \end{envname}
            search_text = f"\\end{{{env_name}}}"
            end_idx = doc.raw_text.find(search_text, node.start_pos)
            if end_idx != -1:
                end_pos = end_idx + len(search_text)
            else:
                # Fallback to node end position
                end_pos = node.end_pos

            return reconstructed, end_pos

        elif (
            node.type == "macro" or node.type == "citation"
        ) and node.metadata.get("macro_name"):
            macro_name = node.metadata["macro_name"]

            # Check if this macro has parsed arguments
            if "parsed_args" in node.metadata:
                # Use the parsed arguments to reconstruct
                args = []
                for arg in node.metadata["parsed_args"]:
                    if arg is not None:
                        # Extract text from the argument
                        arg_text = self._extract_text_from_pylatexenc_node(arg)
                        # Only add non-empty arguments
                        if arg_text:
                            args.append(f"{{{arg_text}}}")

                reconstructed = f"\\{macro_name}{''.join(args)}"

                # For transformed nodes, we need to find the actual end position
                # by looking at the original text
                if (
                    node.metadata.get("original_macro")
                    or node.type == "citation"
                ):
                    # This was transformed, find the real end position
                    # Look for the end of the original macro in the raw text
                    search_start = node.start_pos
                    brace_count = 0
                    pos = search_start

                    # Skip past the macro name
                    while (
                        pos < len(doc.raw_text)
                        and doc.raw_text[pos] not in "{["
                    ):
                        pos += 1

                    # Find the end of all arguments
                    while pos < len(doc.raw_text):
                        char = doc.raw_text[pos]
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                # Found the end of an argument
                                pos += 1
                                # Check if there's another argument
                                if (
                                    pos < len(doc.raw_text)
                                    and doc.raw_text[pos] == "{"
                                ):
                                    continue
                                else:
                                    break
                        pos += 1

                    end_pos = pos
                else:
                    # Calculate end position by finding the end of all macro arguments
                    # For macros with parsed_args, we need to find where the arguments end in the original text
                    end_pos = node.end_pos  # Start with node's end position

                    # Look for arguments after the macro name
                    for arg in node.metadata["parsed_args"]:
                        if (
                            arg is not None
                            and hasattr(arg, "pos")
                            and hasattr(arg, "len")
                        ):
                            # This argument has position info, extend end_pos to cover it
                            arg_end = arg.pos + arg.len
                            if arg_end > end_pos:
                                end_pos = arg_end

                return reconstructed, end_pos
            else:
                # For macros without parsed args, check if following nodes are arguments
                args = []
                end_pos = node.end_pos
                next_index = node_index + 1

                # Look for group nodes that follow this macro
                while next_index < len(doc.nodes):
                    next_node = doc.nodes[next_index]
                    if (
                        next_node.type == "group"
                        and next_node.start_pos == end_pos
                    ):
                        # This group is an argument to the macro
                        arg_content = self._reconstruct_children(
                            next_node.children, doc.raw_text
                        )
                        args.append(f"{{{arg_content}}}")
                        end_pos = next_node.end_pos
                        next_index += 1
                    else:
                        break

                reconstructed = f"\\{macro_name}{''.join(args)}"
                return reconstructed, end_pos
        else:
            # For non-macro nodes, use the regular reconstruction
            reconstructed = self._reconstruct_node(node, doc.raw_text)
            return reconstructed, node.end_pos

    def _extract_text_from_pylatexenc_node(self, node) -> str:
        """Extract text content from a pylatexenc node."""
        if hasattr(node, "nodelist") and node.nodelist:
            # Group node with children
            text_parts = []
            for child in node.nodelist:
                if isinstance(child, LatexCharsNode):
                    text_parts.append(child.chars)
                else:
                    # Recursively extract from nested nodes
                    text_parts.append(
                        self._extract_text_from_pylatexenc_node(child)
                    )
            return "".join(text_parts)
        elif hasattr(node, "chars"):
            # Chars node
            return node.chars
        else:
            return ""

    def _reconstruct_node(self, node: ParsedNode, original_text: str) -> str:
        """Reconstruct a single node and its children."""
        if node.type == "text":
            # For text nodes, return the content directly
            return node.content

        elif node.type == "comment":
            # Preserve comment format
            return (
                f"%{node.content}\n"
                if not node.content.startswith(" ")
                else f"%{node.content}"
            )

        elif node.type == "macro":
            # Reconstruct macro with its name and arguments
            macro_name = node.metadata.get("macro_name", node.content)

            # Special handling for modified macros
            if (
                macro_name == "texttt"
                and node.metadata.get("original_macro") == "passthrough"
            ):
                # This was converted from passthrough
                if node.children:
                    content = self._reconstruct_children(
                        node.children, original_text
                    )
                    return f"\\texttt{{{content}}}"
                elif "parsed_args" in node.metadata:
                    # Use parsed args if available
                    args = []
                    for arg in node.metadata["parsed_args"]:
                        if arg is not None:
                            arg_text = self._extract_text_from_pylatexenc_node(
                                arg
                            )
                            args.append(f"{{{arg_text}}}")
                    return f"\\texttt{''.join(args)}"

            # Handle citation macros
            if node.type == "citation" or macro_name in [
                "cite",
                "citep",
                "citet",
                "textcite",
            ]:
                citation_keys = node.metadata.get("citation_keys", [])
                if citation_keys:
                    return f"\\{macro_name}{{{','.join(citation_keys)}}}"
                elif node.children:
                    # Reconstruct from children
                    content = self._reconstruct_children(
                        node.children, original_text
                    )
                    return f"\\{macro_name}{{{content}}}"
                else:
                    # Fallback for citations without keys
                    return f"\\{macro_name}{{}}"

            # Handle other macros with arguments
            if node.children:
                args = []
                current_arg = []

                # Group children into arguments (separated by groups)
                for child in node.children:
                    if child.type == "group":
                        if current_arg:
                            args.append(
                                self._reconstruct_children(
                                    current_arg, original_text
                                )
                            )
                            current_arg = []
                        args.append(
                            "{"
                            + self._reconstruct_children(
                                child.children, original_text
                            )
                            + "}"
                        )
                    else:
                        current_arg.append(child)

                # Add any remaining children as the last argument
                if current_arg:
                    content = self._reconstruct_children(
                        current_arg, original_text
                    )
                    args.append("{" + content + "}")

                return f"\\{macro_name}{''.join(args)}"
            else:
                # Macro without arguments
                return f"\\{macro_name}"

        elif node.type == "environment":
            env_name = node.metadata.get("environment_name", node.content)
            # Reconstruct environment with its content
            if node.children:
                content = self._reconstruct_children(
                    node.children, original_text
                )
                return f"\\begin{{{env_name}}}\n{content}\\end{{{env_name}}}"
            else:
                return f"\\begin{{{env_name}}}\n\\end{{{env_name}}}"

        elif node.type == "math":
            # Preserve math content as-is
            return node.content

        elif node.type == "group":
            # Reconstruct group with braces
            if node.children:
                content = self._reconstruct_children(
                    node.children, original_text
                )
                return f"{{{content}}}"
            else:
                return "{}"

        else:
            # For unknown types, try to preserve original text
            if node.start_pos is not None and node.end_pos is not None:
                return original_text[node.start_pos : node.end_pos]
            else:
                # Fallback: reconstruct children if any
                if node.children:
                    return self._reconstruct_children(
                        node.children, original_text
                    )
                else:
                    return node.content

    def _reconstruct_children(
        self, children: list[ParsedNode], original_text: str
    ) -> str:
        """Reconstruct a list of child nodes."""
        parts = []
        for child in children:
            parts.append(self._reconstruct_node(child, original_text))
        return "".join(parts)

    def _clean_excessive_line_breaks(self, content: str) -> str:
        """Clean up excessive line breaks (text-based, not AST)."""
        # Remove more than 2 consecutive blank lines to prevent 4+ consecutive newlines
        lines = content.split("\n")
        result = []
        blank_count = 0

        for line in lines:
            if not line.strip():  # Blank line
                blank_count += 1
                if blank_count <= 2:  # Allow max 2 blank lines
                    result.append(line)
            else:
                blank_count = 0
                result.append(line)

        new_content = "\n".join(result)
        if new_content != content:
            self.fixes_applied.append("Cleaned excessive line breaks")
        return new_content


def post_process_latex_file(latex_file: Path, use_ast: bool = True) -> None:
    """Process a LaTeX file to fix common issues.

    Args:
        latex_file: Path to the LaTeX file
        use_ast: Whether to use AST-based processing (default: True)
    """
    if use_ast:
        processor = ASTLatexPostProcessor()
    else:
        # Import here to avoid circular imports
        from .post_processing import LatexPostProcessor

        processor = LatexPostProcessor()

    processor.process_file(latex_file)
