"""
Enhanced AST-based validation utilities with structured error reporting.

Uses proper parsers and structured error reporting for precise error locations.
"""

from urllib.parse import urlparse

from src.core.error_reporter import ASTErrorReporter
from src.parsers import BibtexParser, LatexParser, MarkdownParser


def validate_latex_document_with_structured_errors(
    latex_text: str, file_path: str = ""
) -> ASTErrorReporter:
    """
    Validate a complete LaTeX document with structured error reporting.

    Args:
        latex_text: LaTeX text to validate
        file_path: Optional file path for error reporting

    Returns:
        ASTErrorReporter with detailed error information
    """
    reporter = ASTErrorReporter(latex_text, file_path)
    parser = LatexParser()

    try:
        doc = parser.parse(latex_text)

        # Check for parsing errors
        if "parse_error" in doc.metadata:
            # Report parsing error at document start
            reporter.report_position_error(
                f"LaTeX parsing failed: {doc.metadata['parse_error']}",
                line=1,
                column=1,
                start_pos=0,
                end_pos=len(latex_text),
                error_type="ParsingError",
                suggestion="Check LaTeX syntax for malformed commands or environments",
            )
            return reporter

        # Validate each node in the document
        for node in doc.nodes:
            _validate_latex_node(node, reporter, parser)

    except Exception as e:
        reporter.report_position_error(
            f"Critical parsing error: {str(e)}",
            line=1,
            column=1,
            start_pos=0,
            end_pos=len(latex_text),
            error_type="CriticalParsingError",
            suggestion="Document may contain severe syntax errors",
        )

    return reporter


def _validate_latex_node(node, reporter: ASTErrorReporter, parser: LatexParser):
    """Validate a single LaTeX AST node."""

    # Validate citations
    if node.type == "citation":
        _validate_citation_node(node, reporter)

    # Validate commands
    elif node.type == "command":
        _validate_command_node(node, reporter)

    # Validate environments
    elif node.type == "environment":
        _validate_environment_node(node, reporter)

    # Recursively validate children
    for child in node.children:
        _validate_latex_node(child, reporter, parser)


def _validate_citation_node(node, reporter: ASTErrorReporter):
    """Validate a citation node specifically."""
    citation_keys = node.metadata.get("citation_keys", [])
    citation_type = node.metadata.get("citation_type", "")

    # Check citation type
    valid_types = [
        "cite",
        "citep",
        "citet",
        "textcite",
        "citeauthor",
        "citeyear",
        "autocite",
    ]
    if citation_type and citation_type not in valid_types:
        reporter.report_warning(
            f"Unknown citation command: \\{citation_type}",
            node,
            suggestion=f"Use one of: {', '.join(valid_types)}",
        )

    # Check citation keys
    if not citation_keys:
        reporter.report_error(
            "Citation command has no keys",
            node,
            error_type="ValidationError",
            suggestion="Add at least one citation key inside the braces",
        )
        return

    for key in citation_keys:
        if not key.strip():
            reporter.report_error(
                "Empty citation key found",
                node,
                error_type="ValidationError",
                suggestion="Remove empty keys or add proper citation key",
            )
        elif " " in key:
            reporter.report_error(
                f"Citation key contains spaces: '{key}'",
                node,
                error_type="ValidationError",
                suggestion="Remove spaces from citation key or use underscores/hyphens",
            )
        elif (
            not key.replace("_", "")
            .replace("-", "")
            .replace(":", "")
            .replace(".", "")
            .isalnum()
        ):
            reporter.report_warning(
                f"Citation key contains unusual characters: '{key}'",
                node,
                suggestion="Consider using only letters, numbers, underscores, hyphens, and colons",
            )


def _validate_command_node(node, reporter: ASTErrorReporter):
    """Validate a LaTeX command node."""
    command_name = node.metadata.get("command_name", "")

    # Check for common problematic commands
    problematic_commands = {
        "href": "Consider using proper citation commands instead of raw URLs",
        "url": "Consider using proper citation commands instead of raw URLs",
        "textbf": "Excessive bold formatting can reduce readability",
        "textit": "Excessive italic formatting can reduce readability",
    }

    if command_name in problematic_commands:
        reporter.report_warning(
            f"Usage of \\{command_name} command",
            node,
            suggestion=problematic_commands[command_name],
        )


def _validate_environment_node(node, reporter: ASTErrorReporter):
    """Validate a LaTeX environment node."""
    env_name = node.metadata.get("environment_name", "")

    # Check for common environment issues
    if env_name == "figure" or env_name == "table":
        # Check if has caption
        has_caption = any(
            child.type == "command"
            and child.metadata.get("command_name") == "caption"
            for child in node.children
        )
        if not has_caption:
            reporter.report_warning(
                f"{env_name.capitalize()} environment without caption",
                node,
                suggestion=f"Add \\caption{{}} command inside the {env_name} environment",
            )


def validate_bibtex_with_structured_errors(
    bibtex_text: str, file_path: str = ""
) -> ASTErrorReporter:
    """
    Validate BibTeX entries with structured error reporting.

    Args:
        bibtex_text: BibTeX text to validate
        file_path: Optional file path for error reporting

    Returns:
        ASTErrorReporter with detailed error information
    """
    reporter = ASTErrorReporter(bibtex_text, file_path)
    parser = BibtexParser()

    try:
        doc = parser.parse(bibtex_text)

        if not doc.nodes:
            reporter.report_error(
                "No valid BibTeX entries found",
                # Create a dummy node for document-level error
                type(
                    "Node",
                    (),
                    {
                        "type": "document",
                        "line_no": 1,
                        "col_no": 1,
                        "start_pos": 0,
                        "end_pos": len(bibtex_text),
                        "children": [],
                    },
                )(),
                error_type="ValidationError",
                suggestion="Check BibTeX syntax - entries should start with @type{key,",
            )
            return reporter

        for entry_node in doc.nodes:
            if entry_node.type == "entry":
                _validate_bibtex_entry_node(entry_node, reporter)

    except Exception as e:
        reporter.report_position_error(
            f"BibTeX parsing error: {str(e)}",
            line=1,
            column=1,
            start_pos=0,
            end_pos=len(bibtex_text),
            error_type="ParsingError",
            suggestion="Check BibTeX syntax for malformed entries",
        )

    return reporter


def _validate_bibtex_entry_node(node, reporter: ASTErrorReporter):
    """Validate a single BibTeX entry node."""
    metadata = node.metadata
    entry_type = metadata.get("entry_type", "").lower()
    fields = metadata.get("fields", {})

    # Define required fields per entry type
    required_fields = {
        "article": ["author", "title", "journal", "year"],
        "book": ["author", "title", "publisher", "year"],
        "inproceedings": ["author", "title", "booktitle", "year"],
        "incollection": ["author", "title", "booktitle", "publisher", "year"],
        "phdthesis": ["author", "title", "school", "year"],
        "mastersthesis": ["author", "title", "school", "year"],
        "techreport": ["author", "title", "institution", "year"],
        "misc": ["title"],  # Minimal requirement for misc
    }

    if entry_type in required_fields:
        for field in required_fields[entry_type]:
            if field not in fields or not fields[field].strip():
                reporter.report_error(
                    f"Missing required field: {field}",
                    node,
                    error_type="MissingFieldError",
                    suggestion=f"Add {field} = {{...}} to the entry",
                )
    else:
        reporter.report_warning(
            f"Unknown entry type: @{entry_type}",
            node,
            suggestion="Check if this is a standard BibTeX entry type",
        )

    # Validate year field specifically
    if "year" in fields:
        year_value = fields["year"].strip()
        try:
            year_int = int(year_value)
            if year_int < 1900 or year_int > 2100:
                reporter.report_warning(
                    f"Suspicious year value: {year_value}",
                    node,
                    suggestion="Verify the publication year is correct",
                )
        except ValueError:
            reporter.report_error(
                f"Invalid year format: {year_value}",
                node,
                error_type="InvalidFieldError",
                suggestion="Year should be a 4-digit number",
            )


def validate_markdown_with_structured_errors(
    markdown_text: str, file_path: str = ""
) -> ASTErrorReporter:
    """
    Validate Markdown document with structured error reporting.

    Args:
        markdown_text: Markdown text to validate
        file_path: Optional file path for error reporting

    Returns:
        ASTErrorReporter with detailed error information
    """
    reporter = ASTErrorReporter(markdown_text, file_path)
    parser = MarkdownParser()

    try:
        doc = parser.parse(markdown_text)

        # Check for parsing errors
        if "parse_error" in doc.metadata:
            reporter.report_position_error(
                f"Markdown parsing failed: {doc.metadata['parse_error']}",
                line=1,
                column=1,
                start_pos=0,
                end_pos=len(markdown_text),
                error_type="ParsingError",
            )
            return reporter

        # Validate document structure
        _validate_markdown_structure(doc, reporter)

        # Validate individual nodes
        for node in doc.nodes:
            _validate_markdown_node(node, reporter)

    except Exception as e:
        reporter.report_position_error(
            f"Critical Markdown parsing error: {str(e)}",
            line=1,
            column=1,
            start_pos=0,
            end_pos=len(markdown_text),
            error_type="CriticalParsingError",
        )

    return reporter


def _validate_markdown_structure(doc, reporter: ASTErrorReporter):
    """Validate overall Markdown document structure."""
    # Check heading hierarchy
    headings = []
    _collect_headings(doc.nodes, headings)

    prev_level = 0
    for heading_node in headings:
        level = heading_node.metadata.get("level", 1)
        if level > prev_level + 1:
            reporter.report_warning(
                f"Heading level skip: h{prev_level} → h{level}",
                heading_node,
                suggestion="Use sequential heading levels (h1, h2, h3, ...) for better document structure",
            )
        prev_level = level


def _collect_headings(nodes, headings):
    """Recursively collect heading nodes."""
    for node in nodes:
        if node.type == "heading":
            headings.append(node)
        _collect_headings(node.children, headings)


def _validate_markdown_node(node, reporter: ASTErrorReporter):
    """Validate a single Markdown AST node."""

    if node.type == "link":
        _validate_link_node(node, reporter)
    elif node.type == "image":
        _validate_image_node(node, reporter)

    # Recursively validate children
    for child in node.children:
        _validate_markdown_node(child, reporter)


def _validate_link_node(node, reporter: ASTErrorReporter):
    """Validate a Markdown link node."""
    href = node.metadata.get("href", "")
    link_text = node.content

    # Validate URL
    if href and not _is_valid_url(href):
        reporter.report_error(
            f"Invalid URL: {href}",
            node,
            error_type="ValidationError",
            suggestion="Check URL format and ensure it includes protocol (http/https)",
        )

    # Check for non-descriptive link text
    non_descriptive = ["click here", "link", "url", "reference", "here", "this"]
    if link_text.strip().lower() in non_descriptive:
        reporter.report_warning(
            f"Non-descriptive link text: '{link_text}'",
            node,
            suggestion="Use descriptive link text that explains the destination",
        )


def _validate_image_node(node, reporter: ASTErrorReporter):
    """Validate a Markdown image node."""
    src = node.metadata.get("src", "")
    alt_text = node.metadata.get("alt", "")

    if not alt_text.strip():
        reporter.report_warning(
            "Image without alt text",
            node,
            suggestion="Add descriptive alt text for accessibility",
        )

    if (
        src
        and not _is_valid_url(src)
        and not src.startswith("/")
        and not src.startswith("./")
    ):
        reporter.report_warning(
            f"Potentially invalid image path: {src}",
            node,
            suggestion="Verify image path is correct and accessible",
        )


def _is_valid_url(url: str) -> bool:
    """Simple URL validation."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False
