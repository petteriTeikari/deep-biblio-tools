"""MCP tool for checking link health (HTTP status)."""

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default timeout for HTTP requests
DEFAULT_TIMEOUT = 10.0


async def check_link_health(urls: list[str]) -> dict[str, Any]:
    """Check if HTTP(S) links are reachable.

    Args:
        urls: List of URLs to check

    Returns:
        Dictionary with results for each URL including:
        - url: The URL checked
        - status: HTTP status code (or 0 if unreachable)
        - reachable: Whether the link is accessible
        - error: Error message if request failed
    """
    results = []

    async with httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT, follow_redirects=True
    ) as client:
        tasks = [_check_single_url(client, url) for url in urls]
        results = await asyncio.gather(*tasks)

    return {"results": results}


async def _check_single_url(
    client: httpx.AsyncClient, url: str
) -> dict[str, Any]:
    """Check a single URL.

    Args:
        client: HTTP client instance
        url: URL to check

    Returns:
        Dictionary with check results
    """
    try:
        # Use HEAD request to avoid downloading content
        response = await client.head(url)

        return {
            "url": url,
            "status": response.status_code,
            "reachable": response.status_code < 400,
            "error": None,
        }

    except httpx.TimeoutException:
        return {
            "url": url,
            "status": 0,
            "reachable": False,
            "error": "Request timed out",
        }

    except httpx.HTTPStatusError as e:
        return {
            "url": url,
            "status": e.response.status_code,
            "reachable": False,
            "error": f"HTTP error: {e.response.status_code}",
        }

    except httpx.RequestError as e:
        return {
            "url": url,
            "status": 0,
            "reachable": False,
            "error": f"Request error: {e!s}",
        }

    except Exception as e:
        logger.exception(f"Unexpected error checking URL: {url}")
        return {
            "url": url,
            "status": 0,
            "reachable": False,
            "error": f"Unexpected error: {e!s}",
        }
