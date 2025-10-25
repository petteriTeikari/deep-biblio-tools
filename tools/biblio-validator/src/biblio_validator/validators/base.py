"""Base validator class."""

from abc import ABC, abstractmethod
from typing import Any

import requests

from ..models.citation import Citation, ValidationResult


class BaseValidator(ABC):
    """Abstract base class for citation validators."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}
        self.timeout = self.config.get("validation", {}).get("timeout", 30)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "biblio-validator/1.0 (https://github.com/deep-biblio-tools)"
            }
        )

    @abstractmethod
    def validate(self, citation: Citation) -> ValidationResult:
        """Validate a citation against this source."""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of this validation source."""
        pass

    def _make_request(
        self, url: str, params: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Make HTTP request with error handling."""
        try:
            response = self.session.get(
                url, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
        except ValueError as e:
            raise Exception(f"Invalid JSON response: {str(e)}")
