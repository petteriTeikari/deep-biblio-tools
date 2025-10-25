#!/usr/bin/env python3
"""
Entry point for running deep_biblio_tools as a module.

Usage: python -m deep_biblio_tools
"""

from .cli import cli

if __name__ == "__main__":
    cli()
