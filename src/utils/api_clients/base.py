"""Base API client with rate limiting and caching."""

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ...utils.cache import get_cache_path, load_from_cache, save_to_cache


class APIClient(ABC):
    """Base class for API clients with rate limiting and caching.

    This class provides common functionality for all API clients including:
    - Rate limiting to respect API quotas
    - Response caching to reduce API calls
    - Error handling and retries
    """

    def __init__(
        self,
        rate_limit: float = 1.0,
        cache_enabled: bool = True,
        cache_dir: Path | None = None,
    ):
        """Initialize API client.

        Args:
            rate_limit: Minimum seconds between API calls
            cache_enabled: Whether to enable response caching
            cache_dir: Directory for cache files (uses default if None)
        """
        self.rate_limit = rate_limit
        self.cache_enabled = cache_enabled
        self.cache_dir = cache_dir or get_cache_path()
        self._last_request = 0.0

    def _rate_limit_wait(self) -> None:
        """Wait if necessary to respect rate limit."""
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    def _get_cache_key(self, endpoint: str, params: dict[str, Any]) -> str:
        """Generate cache key for request.

        Args:
            endpoint: API endpoint
            params: Request parameters

        Returns:
            Cache key string
        """
        # Create a deterministic string from endpoint and params
        param_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{self.__class__.__name__}_{endpoint}_{param_str}"

    def _get_cached_response(self, cache_key: str) -> dict[str, Any] | None:
        """Get cached response if available.

        Args:
            cache_key: Cache key for the request

        Returns:
            Cached response data or None
        """
        if not self.cache_enabled:
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            return load_from_cache(cache_file)
        return None

    def _cache_response(self, cache_key: str, response: dict[str, Any]) -> None:
        """Cache response data.

        Args:
            cache_key: Cache key for the request
            response: Response data to cache
        """
        if not self.cache_enabled:
            return

        cache_file = self.cache_dir / f"{cache_key}.json"
        save_to_cache(response, cache_file)

    @abstractmethod
    def _make_request(
        self, endpoint: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Make actual API request.

        Args:
            endpoint: API endpoint
            params: Request parameters

        Returns:
            Response data

        Raises:
            APIError: If request fails
        """
        pass

    def request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Make API request with rate limiting and caching.

        Args:
            endpoint: API endpoint
            params: Request parameters
            use_cache: Whether to use cache for this request

        Returns:
            Response data

        Raises:
            APIError: If request fails
        """
        params = params or {}

        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(endpoint, params)
            cached = self._get_cached_response(cache_key)
            if cached is not None:
                return cached

        # Rate limit
        self._rate_limit_wait()

        # Make request
        response = self._make_request(endpoint, params)

        # Cache response
        if use_cache:
            self._cache_response(cache_key, response)

        return response
