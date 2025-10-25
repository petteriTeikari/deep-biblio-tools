"""Structured error reporting using AST position information."""

import logging
from dataclasses import dataclass

from src.core.exceptions import DeepBiblioError
from src.parsers.base import ParsedNode

logger = logging.getLogger(__name__)


@dataclass
class SourceLocation:
    """Represents a location in source code with precise positioning."""

    line: int
    column: int
    start_pos: int
    end_pos: int
    file_path: str | None = None


@dataclass
class StructuredError:
    """Represents a structured error with precise location information."""

    message: str
    error_type: str
    location: SourceLocation
    severity: str = "error"  # error, warning, info
    context: str = ""
    node_type: str = ""
    suggestion: str = ""


class ASTErrorReporter:
    """Error reporter that leverages AST position information for precise error reporting."""

    def __init__(self, source_text: str = "", file_path: str = ""):
        self.source_text = source_text
        self.file_path = file_path
        self.errors: list[StructuredError] = []
        self.warnings: list[StructuredError] = []

    def report_error(
        self,
        message: str,
        node: ParsedNode,
        error_type: str = "ValidationError",
        suggestion: str = "",
        context_lines: int = 2,
    ) -> StructuredError:
        """Report an error at a specific AST node location."""
        location = SourceLocation(
            line=node.line_no,
            column=node.col_no,
            start_pos=node.start_pos,
            end_pos=node.end_pos,
            file_path=self.file_path,
        )

        # Extract context around the error
        context = self._extract_context(location, context_lines)

        error = StructuredError(
            message=message,
            error_type=error_type,
            location=location,
            severity="error",
            context=context,
            node_type=node.type,
            suggestion=suggestion,
        )

        self.errors.append(error)
        return error

    def report_warning(
        self,
        message: str,
        node: ParsedNode,
        suggestion: str = "",
        context_lines: int = 1,
    ) -> StructuredError:
        """Report a warning at a specific AST node location."""
        location = SourceLocation(
            line=node.line_no,
            column=node.col_no,
            start_pos=node.start_pos,
            end_pos=node.end_pos,
            file_path=self.file_path,
        )

        context = self._extract_context(location, context_lines)

        warning = StructuredError(
            message=message,
            error_type="Warning",
            location=location,
            severity="warning",
            context=context,
            node_type=node.type,
            suggestion=suggestion,
        )

        self.warnings.append(warning)
        return warning

    def report_position_error(
        self,
        message: str,
        line: int,
        column: int,
        start_pos: int,
        end_pos: int,
        error_type: str = "ParsingError",
        suggestion: str = "",
    ) -> StructuredError:
        """Report an error at a specific position (when no AST node is available)."""
        location = SourceLocation(
            line=line,
            column=column,
            start_pos=start_pos,
            end_pos=end_pos,
            file_path=self.file_path,
        )

        context = self._extract_context(location, 2)

        error = StructuredError(
            message=message,
            error_type=error_type,
            location=location,
            context=context,
            suggestion=suggestion,
        )

        self.errors.append(error)
        return error

    def _extract_context(
        self, location: SourceLocation, context_lines: int
    ) -> str:
        """Extract context lines around the error location."""
        if not self.source_text:
            return ""

        lines = self.source_text.split("\n")
        error_line_idx = location.line - 1  # Convert to 0-based indexing

        # Ensure we don't go out of bounds
        start_line = max(0, error_line_idx - context_lines)
        end_line = min(len(lines), error_line_idx + context_lines + 1)

        context_lines_list = []
        for i in range(start_line, end_line):
            line_num = i + 1
            line_content = lines[i] if i < len(lines) else ""

            if i == error_line_idx:
                # Mark the error line
                marker = ">" if line_content.strip() else ""
                context_lines_list.append(
                    f"{marker:>2} {line_num:4}: {line_content}"
                )

                # Add a pointer to the exact column if available
                if location.column > 0:
                    pointer = " " * (7 + location.column) + "^"
                    context_lines_list.append(pointer)
            else:
                context_lines_list.append(f"  {line_num:4}: {line_content}")

        return "\n".join(context_lines_list)

    def format_error(self, error: StructuredError) -> str:
        """Format a structured error for display."""
        location_str = (
            f"{error.location.file_path}:" if error.location.file_path else ""
        )
        location_str += f"{error.location.line}:{error.location.column}"

        lines = [
            f"{error.severity.upper()}: {error.message}",
            f"  --> {location_str}",
        ]

        if error.node_type:
            lines.append(f"  Node type: {error.node_type}")

        if error.context:
            lines.append("")
            for line in error.context.split("\n"):
                lines.append(f"     {line}")

        if error.suggestion:
            lines.append("")
            lines.append(f"  Suggestion: {error.suggestion}")

        return "\n".join(lines)

    def format_all_errors(self) -> str:
        """Format all errors and warnings for display."""
        output = []

        if self.errors:
            output.append("ERRORS:")
            output.append("=" * 50)
            for error in self.errors:
                output.append(self.format_error(error))
                output.append("")

        if self.warnings:
            output.append("WARNINGS:")
            output.append("=" * 50)
            for warning in self.warnings:
                output.append(self.format_error(warning))
                output.append("")

        return "\n".join(output)

    def has_errors(self) -> bool:
        """Check if any errors were reported."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if any warnings were reported."""
        return len(self.warnings) > 0

    def clear(self):
        """Clear all errors and warnings."""
        self.errors.clear()
        self.warnings.clear()

    def log_all(self):
        """Log all errors and warnings using the logger."""
        for error in self.errors:
            logger.error(self.format_error(error))

        for warning in self.warnings:
            logger.warning(self.format_error(warning))


def create_validation_error_from_node(
    node: ParsedNode, message: str, source_text: str = "", file_path: str = ""
) -> DeepBiblioError:
    """Create a validation error with structured location information."""
    reporter = ASTErrorReporter(source_text, file_path)
    structured_error = reporter.report_error(message, node, "ValidationError")

    # Create a detailed error message
    detailed_message = f"{message} at line {node.line_no}, column {node.col_no}"
    if node.type:
        detailed_message += f" (in {node.type} node)"

    # Create the exception with enhanced information
    error = DeepBiblioError(detailed_message)
    error.structured_error = structured_error  # Attach structured info
    return error


def create_parsing_error_from_position(
    line: int,
    column: int,
    start_pos: int,
    end_pos: int,
    message: str,
    source_text: str = "",
    file_path: str = "",
) -> DeepBiblioError:
    """Create a parsing error with position information."""
    reporter = ASTErrorReporter(source_text, file_path)
    structured_error = reporter.report_position_error(
        message, line, column, start_pos, end_pos, "ParsingError"
    )

    detailed_message = f"{message} at line {line}, column {column}"
    error = DeepBiblioError(detailed_message)
    error.structured_error = structured_error
    return error
