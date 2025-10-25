#!/usr/bin/env python3
"""
Test runner for academic rephrasing tests.
Run from the tests directory or paper-processor directory.
"""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run the test suite with coverage reporting."""

    # Find the test directory
    test_dir = Path(__file__).parent

    # Check if pytest is installed
    try:
        __import__("pytest")
    except ImportError:
        print("pytest not found. Installing pytest and coverage...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pytest", "pytest-cov"]
        )

    # Run tests with coverage
    print("Running academic rephrasing tests...")
    print("=" * 60)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(test_dir / "test_academic_rephrasing.py"),
        "-v",  # verbose
        "--tb=short",  # shorter traceback format
        "-x",  # stop on first failure
        "--cov=academic_rephrasing",  # coverage for the main module
        "--cov-report=term-missing",  # show missing lines
    ]

    result = subprocess.run(cmd)

    return result.returncode


if __name__ == "__main__":
    exit_code = run_tests()
