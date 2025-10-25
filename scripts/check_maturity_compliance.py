#!/usr/bin/env python3
"""Check if changes comply with repository maturity level."""

import subprocess
import sys
from pathlib import Path

import yaml


def load_maturity_config():
    """Load repository maturity configuration."""
    config_path = (
        Path(__file__).parent.parent / ".claude" / "repo-maturity.yaml"
    )

    if not config_path.exists():
        print("Warning: No maturity configuration found")
        return None

    with open(config_path) as f:
        return yaml.safe_load(f)


def get_changed_files():
    """Get list of changed files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split("\n") if result.stdout else []
    except subprocess.CalledProcessError:
        return []


def check_documentation_requirements(config, changed_files):
    """Check if documentation requirements are met."""
    maturity = config["maturity_level"]
    mode = config["behavior_modes"][maturity]

    if mode["documentation_required"] in ["comprehensive", "exhaustive"]:
        # Check for ADR if significant changes
        significant_paths = ["src/", ".github/", "scripts/"]
        needs_adr = any(
            any(sig in file for sig in significant_paths)
            for file in changed_files
        )

        if needs_adr:
            adr_files = list(Path("docs/decisions").glob("ADR-*.md"))
            recent_adrs = [
                f
                for f in adr_files
                if f.stat().st_mtime > (Path(".").stat().st_mtime - 86400)
            ]

            if not recent_adrs:
                return (
                    False,
                    "Production repo requires ADR for significant changes",
                )

    return True, None


def check_testing_requirements(config, changed_files):
    """Check if testing requirements are met."""
    maturity = config["maturity_level"]
    mode = config["behavior_modes"][maturity]

    if mode["testing_required"]:
        # Check if Python files were changed
        py_files = [
            f for f in changed_files if f.endswith(".py") and "test" not in f
        ]

        if py_files:
            # Check if corresponding tests exist or were added
            test_files = [f for f in changed_files if "test" in f]

            if not test_files:
                return False, f"{maturity} repo requires tests for code changes"

    return True, None


def check_refactoring_scope(config, changed_files):
    """Check if refactoring scope is appropriate."""
    maturity = config["maturity_level"]
    mode = config["behavior_modes"][maturity]

    if mode["refactoring_allowed"] == "minimal" and len(changed_files) > 10:
        return (
            False,
            f"Production repo: Large refactoring ({len(changed_files)} files) requires approval",
        )

    return True, None


def main():
    """Run maturity compliance checks."""
    config = load_maturity_config()
    if not config:
        return 0

    changed_files = get_changed_files()
    if not changed_files:
        return 0

    maturity = config["maturity_level"]
    print(f"Repository maturity level: {maturity}")
    print(
        f"Expected behavior: {config['behavior_modes'][maturity]['ai_personality']}"
    )

    # Run checks
    checks = [
        ("Documentation", check_documentation_requirements),
        ("Testing", check_testing_requirements),
        ("Refactoring Scope", check_refactoring_scope),
    ]

    all_passed = True
    for check_name, check_func in checks:
        passed, message = check_func(config, changed_files)
        if passed:
            print(f"[PASS] {check_name} check passed")
        else:
            print(f"[FAIL] {check_name} check failed: {message}")
            all_passed = False

    if not all_passed:
        print(
            f"\n[WARNING] Changes don't meet {maturity} repository standards!"
        )
        return 1

    print(f"\n[PASS] All maturity checks passed for {maturity} repository!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
