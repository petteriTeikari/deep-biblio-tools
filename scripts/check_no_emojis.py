#!/usr/bin/env python3
"""
Pre-commit hook to check for emojis in files.

This ensures consistent cross-platform compatibility by preventing
emoji usage that could cause encoding issues. Emojis are only allowed
in markdown (.md) files for documentation purposes.
"""

# import re  # Banned - using string methods instead
import sys


def contains_emoji(text: str) -> bool:
    """Check if text contains any emoji characters.

    Args:
        text: Text to check for emojis

    Returns:
        True if emojis found, False otherwise
    """
    # Check each character against known emoji ranges
    for char in text:
        code = ord(char)

        # Check various emoji ranges
        if (
            0x1F600 <= code <= 0x1F64F  # emoticons
            or 0x1F300 <= code <= 0x1F5FF  # symbols & pictographs
            or 0x1F680 <= code <= 0x1F6FF  # transport & map symbols
            or 0x1F1E0 <= code <= 0x1F1FF  # flags (iOS)
            or 0x2700 <= code <= 0x27BF  # dingbats
            or 0x1F926 <= code <= 0x1F937  # supplemental symbols
            or 0x10000 <= code <= 0x10FFFF  # supplementary unicode
            or 0x2640 <= code <= 0x2642  # gender symbols
            or 0x2600 <= code <= 0x2B55  # misc symbols
            or code == 0x200D  # zero width joiner
            or code == 0x23CF  # eject symbol
            or code == 0x23E9  # fast forward
            or code == 0x231A  # watch
            or code == 0xFE0F  # variation selector
            or code == 0x3030  # wavy dash
        ):
            return True

    return False


def check_file(file_path: str) -> list[str]:
    """Check a single file for emojis.

    Args:
        file_path: Path to file to check

    Returns:
        List of error messages (empty if no emojis found)
    """
    errors = []

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            if contains_emoji(line):
                errors.append(f"{file_path}:{line_num}: Found emoji in line")

    except UnicodeDecodeError:
        errors.append(
            f"{file_path}: Unicode decode error - file may contain invalid characters"
        )
    except Exception as e:
        errors.append(f"{file_path}: Error reading file: {e}")

    return errors


def main():
    """Main entry point for pre-commit hook."""
    if len(sys.argv) < 2:
        print("Usage: check_no_emojis.py <file1> [file2] ...")
        sys.exit(1)

    all_errors = []

    for file_path in sys.argv[1:]:
        errors = check_file(file_path)
        all_errors.extend(errors)

    if all_errors:
        print("Emoji check failed:")
        for error in all_errors:
            print(f"  {error}")
        print(f"\nFound emojis in {len(all_errors)} location(s)")
        print("Please remove all emojis from your files.")
        print("Note: Emojis are only allowed in markdown (.md) files.")
        print(
            "Run 'python scripts/remove_emojis.py' to automatically clean files."
        )
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
