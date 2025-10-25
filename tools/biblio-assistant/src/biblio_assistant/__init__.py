"""
biblio-assistant: Web-based interface for bibliography management.

This package provides a web UI for all Deep Biblio Tools functionality.
"""

__version__ = "1.0.0"

from .core.app import create_app
from .core.server import BiblioServer

__all__ = [
    "create_app",
    "BiblioServer",
]
