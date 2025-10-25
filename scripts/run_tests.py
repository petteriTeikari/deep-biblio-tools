#!/usr/bin/env python3
"""Smart test runner that auto-detects environment and optimizes for available resources."""

import multiprocessing
import os
import subprocess


def get_optimal_workers():
    """Determine optimal number of test workers based on environment."""
    # Check if we're in CI environment
    if os.environ.get("CI"):
        # GitHub Actions provides 2 cores for Linux/Windows, 3 for macOS
        # Conservative approach: use 2 workers in CI
        return 2

    # Check if we're in a container
    if os.environ.get("CONTAINER_ENV") or os.path.exists("/.dockerenv"):
        # Containers might have limited resources
        return min(2, multiprocessing.cpu_count())

    # Local development: use all available cores
    cpu_count = multiprocessing.cpu_count()

    # For local development, leave one core free for system responsiveness
    if cpu_count > 2:
        return cpu_count - 1

    return cpu_count


def main():
    """Run tests with optimal parallelization."""
    workers = get_optimal_workers()

    # Build pytest command
    cmd = ["uv", "run", "pytest"]

    # Add parallel execution if beneficial
    if workers > 1:
        cmd.extend(["-n", str(workers)])
        print(f"Running tests with {workers} parallel workers")
    else:
        print("Running tests sequentially")

    # Add coverage if not in quick mode
    if "--quick" not in os.sys.argv:
        cmd.extend(["--cov", "--cov-report=term", "--cov-report=xml"])

    # Add any additional arguments passed to this script
    import sys

    additional_args = [arg for arg in sys.argv[1:] if arg != "--quick"]
    cmd.extend(additional_args)

    # Run the tests
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    return result.returncode


if __name__ == "__main__":
    exit(main())
