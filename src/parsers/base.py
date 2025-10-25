"""Base classes for structured parsers."""

# Standard library imports
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedNode:
    """Base class for parsed nodes."""

    type: str
    content: str
    start_pos: int
    end_pos: int
    line_no: int
    col_no: int
    metadata: dict[str, Any]
    children: list["ParsedNode"]


@dataclass
class ParsedDocument:
    """Represents a parsed document."""

    raw_text: str
    nodes: list[ParsedNode]
    metadata: dict[str, Any]

    def find_nodes_by_type(self, node_type: str) -> list[ParsedNode]:
        """Find all nodes of a given type."""
        results = []

        def traverse(node: ParsedNode):
            if node.type == node_type:
                results.append(node)
            for child in node.children:
                traverse(child)

        for node in self.nodes:
            traverse(node)

        return results

    def get_text_range(self, start: int, end: int) -> str:
        """Get text between positions."""
        return self.raw_text[start:end]


class StructuredParser(ABC):
    """Abstract base class for structured text parsers."""

    @abstractmethod
    def parse(self, text: str) -> ParsedDocument:
        """Parse text into a structured document."""
        pass

    @abstractmethod
    def validate(self, text: str) -> list[str]:
        """Validate text and return list of errors."""
        pass

    def extract_metadata(self, text: str) -> dict[str, Any]:
        """Extract metadata from text."""
        doc = self.parse(text)
        return doc.metadata
