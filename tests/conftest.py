"""Pytest configuration and shared fixtures."""

import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip tex2lyx tests in Docker/CI environments."""
    if os.environ.get("CI") or os.environ.get("CONTAINER_ENV"):
        skip_tex2lyx = pytest.mark.skip(
            reason="tex2lyx tests skipped in CI/Container environment"
        )
        for item in items:
            # Skip tex2lyx related tests
            if "tex2lyx" in item.nodeid.lower() or "lyx" in item.nodeid.lower():
                item.add_marker(skip_tex2lyx)
