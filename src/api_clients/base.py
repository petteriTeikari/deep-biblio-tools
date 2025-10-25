"""Base API client for external services."""

import time
from abc import ABC
from typing import Any

import requests


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded."""

    pass


class APIClient(ABC):
    """Base class for API clients with rate limiting and common functionality."""

    def __init__(self, delay: float = 0.5):
        """
        Initialize API client.

        Args:
            delay: Delay between requests in seconds
        """
        self.delay = delay
        self.session = requests.Session()
        self._last_request_time = 0

    def _rate_limited_request(self, request_func, *args, **kwargs):
        """Make a rate-limited request."""
        # Ensure we don't make requests too quickly
        current_time = time.time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self.delay:
            time.sleep(self.delay - time_since_last)

        self._last_request_time = time.time()
        return request_func(*args, **kwargs)

    def _make_request(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        json_response: bool = True,
        **kwargs,
    ):
        """
        Make an HTTP request with rate limiting.

        Args:
            url: URL to request
            params: Query parameters
            json_response: Whether to parse response as JSON
            **kwargs: Additional arguments for requests

        Returns:
            Response data or requests.Response object
        """
        response = self._rate_limited_request(
            self.session.get, url, params=params, timeout=10, **kwargs
        )

        if response.status_code == 200:
            if json_response:
                return response.json()
            else:
                return response

        response.raise_for_status()
