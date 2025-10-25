#!/usr/bin/env python3
"""
Context Server for Claude Code Guardrails

Manages context budget and provides optimized context for Claude interactions.
"""

import argparse
import os
import subprocess
from pathlib import Path
from typing import Any

import yaml


class ContextServer:
    def __init__(
        self, config_path: str = ".claude/context/context-budget.yaml"
    ):
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.project_root = Path.cwd()

    def load_config(self) -> dict[str, Any]:
        """Load context budget configuration."""
        if not self.config_path.exists():
            return {}

        with open(self.config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        return len(text) // 4

    def get_priority_contexts(self) -> list[dict[str, Any]]:
        """Get contexts in priority order."""
        contexts = []

        for item in self.config.get("priority_contexts", []):
            if "file" in item:
                file_path = Path(item["file"])
                if file_path.exists():
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                    contexts.append(
                        {
                            "path": str(file_path),
                            "content": content,
                            "tokens": self.estimate_tokens(content),
                            "priority": item["priority"],
                            "description": item.get("description", ""),
                        }
                    )
            elif "pattern" in item:
                # Handle glob patterns
                pattern_files = list(self.project_root.glob(item["pattern"]))
                max_files = item.get("max_files", 999)

                for file_path in sorted(pattern_files)[:max_files]:
                    if file_path.is_file():
                        try:
                            with open(file_path, encoding="utf-8") as f:
                                content = f.read()
                            contexts.append(
                                {
                                    "path": str(file_path),
                                    "content": content,
                                    "tokens": self.estimate_tokens(content),
                                    "priority": item["priority"],
                                    "description": item.get("description", ""),
                                }
                            )
                        except (UnicodeDecodeError, PermissionError):
                            continue

        return sorted(contexts, key=lambda x: x["priority"])

    def build_optimized_context(self, max_tokens: int = None) -> str:
        """Build optimized context within token budget."""
        if max_tokens is None:
            max_tokens = self.config.get("target_context_tokens", 150000)

        contexts = self.get_priority_contexts()
        selected_contexts = []
        total_tokens = 0

        for ctx in contexts:
            if total_tokens + ctx["tokens"] <= max_tokens:
                selected_contexts.append(ctx)
                total_tokens += ctx["tokens"]
            else:
                # Try to include truncated version
                if self.config.get("auto_truncate", False):
                    remaining_tokens = max_tokens - total_tokens
                    if remaining_tokens > 100:  # Minimum useful content
                        truncated_content = ctx["content"][
                            : remaining_tokens * 4
                        ]
                        selected_contexts.append(
                            {
                                **ctx,
                                "content": truncated_content
                                + "\n\n[TRUNCATED]",
                                "tokens": remaining_tokens,
                            }
                        )
                        total_tokens = max_tokens
                break

        # Build final context
        context_parts = [
            "# Claude Code Guardrails - Optimized Context",
            f"# Total tokens: ~{total_tokens}",
            f"# Files included: {len(selected_contexts)}",
            "",
        ]

        for ctx in selected_contexts:
            context_parts.extend(
                [
                    f"## {ctx['path']} ({ctx['description']})",
                    "```",
                    ctx["content"],
                    "```",
                    "",
                ]
            )

        return "\n".join(context_parts)

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy text to clipboard using system tools."""
        try:
            if os.name == "nt":  # Windows
                subprocess.run(["clip"], input=text, text=True, check=True)
            elif os.name == "posix":  # macOS/Linux
                try:
                    subprocess.run(
                        ["pbcopy"], input=text, text=True, check=True
                    )
                except FileNotFoundError:
                    subprocess.run(
                        ["xclip", "-selection", "clipboard"],
                        input=text,
                        text=True,
                        check=True,
                    )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False


def main():
    parser = argparse.ArgumentParser(description="Claude Context Server")
    parser.add_argument(
        "--copy", action="store_true", help="Copy context to clipboard"
    )
    parser.add_argument("--max-tokens", type=int, help="Maximum token budget")
    parser.add_argument("--output", type=str, help="Output file path")

    args = parser.parse_args()

    server = ContextServer()
    context = server.build_optimized_context(args.max_tokens)

    if args.copy:
        if server.copy_to_clipboard(context):
            print("Context copied to clipboard!")
        else:
            print("Failed to copy to clipboard")
            print(context)
    elif args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(context)
        print(f"Context saved to {args.output}")
    else:
        print(context)


if __name__ == "__main__":
    main()
