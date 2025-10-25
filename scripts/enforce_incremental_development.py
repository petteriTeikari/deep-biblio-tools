#!/usr/bin/env python3
"""Enforce incremental development practices based on repo maturity."""

import sys
from datetime import datetime
from pathlib import Path

import yaml


class IncrementalEnforcer:
    """Enforces incremental development based on maturity level."""

    def __init__(self):
        self.config = self._load_configs()
        self.session_file = Path(".claude_session")
        self.current_session = self._load_session()

    def _load_configs(self):
        """Load maturity and incremental configs."""
        base_path = Path(__file__).parent.parent / ".claude"

        with open(base_path / "repo-maturity.yaml") as f:
            maturity = yaml.safe_load(f)

        with open(base_path / "incremental-development.yaml") as f:
            incremental = yaml.safe_load(f)

        return {
            "maturity_level": maturity["maturity_level"],
            "limits": incremental["step_limits"][maturity["maturity_level"]],
            "template": incremental["response_templates"][
                maturity["maturity_level"]
            ],
            "pauses": incremental["mandatory_pauses"][
                maturity["maturity_level"]
            ],
        }

    def _load_session(self):
        """Load current session state."""
        if self.session_file.exists():
            with open(self.session_file) as f:
                return yaml.safe_load(f) or {}
        return {
            "files_changed": 0,
            "lines_changed": 0,
            "start_time": datetime.now().isoformat(),
        }

    def _save_session(self):
        """Save session state."""
        with open(self.session_file, "w") as f:
            yaml.dump(self.current_session, f)

    def check_file_limit(self, num_files):
        """Check if file change limit exceeded."""
        max_files = self.config["limits"]["max_files_per_response"]

        if num_files > max_files:
            return (
                False,
                f"Too many files ({num_files}). Limit is {max_files} for {self.config['maturity_level']} repos.",
            )

        self.current_session["files_changed"] += num_files
        self._save_session()
        return True, None

    def check_line_limit(self, num_lines):
        """Check if line change limit exceeded."""
        max_lines = self.config["limits"]["max_lines_per_change"]

        if num_lines > max_lines:
            return (
                False,
                f"Too many lines ({num_lines}). Limit is {max_lines} for {self.config['maturity_level']} repos.",
            )

        self.current_session["lines_changed"] += num_lines
        self._save_session()
        return True, None

    def get_checklist(self):
        """Get pre-action checklist."""
        return self.config["limits"]["checklist_before_action"]

    def get_template(self):
        """Get response template."""
        return self.config["template"]

    def should_pause(self):
        """Check if mandatory pause required."""
        if self.config["pauses"]["after_each_file"]:
            return True, self.config["pauses"]["message"]
        return False, None


def print_enforcement_summary():
    """Print current enforcement rules."""
    enforcer = IncrementalEnforcer()

    print(f"Repository: {enforcer.config['maturity_level']} mode")
    print("Limits:")
    print(
        f"   - Max files per response: {enforcer.config['limits']['max_files_per_response']}"
    )
    print(
        f"   - Max lines per change: {enforcer.config['limits']['max_lines_per_change']}"
    )

    if enforcer.config["limits"]["require_explanation_first"]:
        print("   - [WARNING] Must explain before implementing")

    if enforcer.config["limits"]["require_linting_after_each_file"]:
        print("   - [REQUIRED] Must lint after each file")

    checklist = enforcer.get_checklist()
    if checklist:
        print("\nRequired checks before changes:")
        for item in checklist:
            print(f"    {item}")

    should_pause, message = enforcer.should_pause()
    if should_pause:
        print(f"\n[PAUSE] Mandatory pauses: {message}")

    print(f"\nUse this template:\n{enforcer.get_template()}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--check-files", type=int, help="Check file limit")
    parser.add_argument("--check-lines", type=int, help="Check line limit")
    parser.add_argument(
        "--summary", action="store_true", help="Show enforcement summary"
    )

    args = parser.parse_args()

    if args.summary or (not args.check_files and not args.check_lines):
        print_enforcement_summary()
    else:
        enforcer = IncrementalEnforcer()

        if args.check_files:
            ok, msg = enforcer.check_file_limit(args.check_files)
            if not ok:
                print(f"[FAIL] {msg}")
                sys.exit(1)

        if args.check_lines:
            ok, msg = enforcer.check_line_limit(args.check_lines)
            if not ok:
                print(f"[FAIL] {msg}")
                sys.exit(1)

        print("[PASS] Within limits")
