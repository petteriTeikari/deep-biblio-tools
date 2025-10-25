#!/usr/bin/env python3
"""
Pattern Learning and Management System for Claude Code Guardrails

Captures, validates, and suggests patterns for effective Claude collaboration.
"""

import argparse
import json
from pathlib import Path


class PatternManager:
    def __init__(self):
        self.patterns_dir = Path(".claude/learned-patterns")
        self.patterns_dir.mkdir(parents=True, exist_ok=True)
        self.patterns_file = self.patterns_dir / "patterns.json"
        self._init_pattern_storage()

    def _init_pattern_storage(self):
        """Initialize pattern storage files."""
        if not self.patterns_file.exists():
            initial_patterns = {
                "debugging": [
                    {
                        "id": "debug_001",
                        "context": "Claude encounters error messages",
                        "approach": "Provide full error stack trace and relevant code context",
                        "outcome": "Faster and more accurate problem diagnosis",
                        "confidence": 0.9,
                    }
                ]
            }

            with open(self.patterns_file, "w", encoding="utf-8") as f:
                json.dump(initial_patterns, f, indent=2)

    def list_patterns(self):
        """List all learned patterns."""
        with open(self.patterns_file, encoding="utf-8") as f:
            patterns = json.load(f)

        print("\n[EMOJI] Learned Patterns")
        print("=" * 60)

        for category, cat_patterns in patterns.items():
            category_title = f"[EMOJI] {category.title()}:"
            print("\n" + category_title)
            for pattern in cat_patterns:
                print(f"  {pattern['id']}: {pattern['context']}")


def main():
    parser = argparse.ArgumentParser(
        description="Pattern Learning and Management System"
    )
    parser.add_argument("--list", action="store_true", help="List all patterns")

    args = parser.parse_args()
    manager = PatternManager()

    if args.list:
        manager.list_patterns()


if __name__ == "__main__":
    main()
