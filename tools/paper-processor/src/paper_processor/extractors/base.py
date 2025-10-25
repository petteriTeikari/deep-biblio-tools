"""Base extractor class."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..models.paper import Paper


class BaseExtractor(ABC):
    """Abstract base class for paper extractors."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    @abstractmethod
    def extract(self, file_path: Path) -> Paper:
        """Extract paper content from file."""
        pass
