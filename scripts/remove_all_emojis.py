#!/usr/bin/env python3
"""Remove all emojis from code files in the repository."""

# import re  # Banned - using string methods instead
from pathlib import Path


# Emoji ranges for detection
def is_emoji_char(char: str) -> bool:
    """Check if a character is an emoji."""
    code = ord(char)
    return (
        0x1F600 <= code <= 0x1F64F  # emoticons
        or 0x1F300 <= code <= 0x1F5FF  # symbols & pictographs
        or 0x1F680 <= code <= 0x1F6FF  # transport & map symbols
        or 0x1F1E0 <= code <= 0x1F1FF  # flags (iOS)
        or 0x2702 <= code <= 0x27B0  # dingbats
        or 0x24C2 <= code <= 0x1F251  # enclosed characters
        or 0x1F900 <= code <= 0x1F9FF  # supplemental symbols
        or 0x2600 <= code <= 0x26FF  # miscellaneous symbols
        or 0x2700 <= code <= 0x27BF  # dingbats
    )


# Common emoji replacements (using Unicode escapes to avoid having actual emojis in this file)
EMOJI_REPLACEMENTS: dict[str, str] = {
    "\u2705": "[PASS]",  # check mark
    "\u274c": "[FAIL]",  # cross mark
    "\u26a0\ufe0f": "[WARNING]",  # warning sign
    "\U0001f50d": "[CHECK]",  # magnifying glass
    "\U0001f4dd": "[INFO]",  # memo
    "\U0001f3af": "[TARGET]",  # target
    "\U0001f680": "[START]",  # rocket
    "\U0001f4a1": "[TIP]",  # light bulb
    "\U0001f6d1": "[STOP]",  # stop sign
    "\U0001f4e6": "[PACKAGE]",  # package
    "\U0001f9ea": "[TEST]",  # test tube
    "\U0001f527": "[FIX]",  # wrench
    "\u23f8\ufe0f": "[PAUSE]",  # pause button
    "\U0001f4cf": "[MEASURE]",  # ruler
    "\U0001f4cb": "[CLIPBOARD]",  # clipboard
    "\U0001f44d": "[OK]",  # thumbs up
    "\U0001f44e": "[NO]",  # thumbs down
    "\u2b50": "[STAR]",  # star
    "\U0001f525": "[HOT]",  # fire
    "\U0001f41b": "[BUG]",  # bug
    "\U0001f4da": "[DOCS]",  # books
    "\U0001f389": "[SUCCESS]",  # party
    "\U0001f4bb": "[CODE]",  # computer
    "\U0001f512": "[SECURE]",  # lock
    "\U0001f513": "[INSECURE]",  # unlock
    "\U0001f4ca": "[STATS]",  # chart
    "\U0001f4c8": "[GROWTH]",  # chart up
    "\U0001f4c9": "[DECLINE]",  # chart down
    "\U0001f5d1\ufe0f": "[DELETE]",  # trash
    "\u270b": "[PAUSE]",  # hand
    "\U0001f3c3": "[RUN]",  # runner
    "\U0001f9f9": "[CLEANUP]",  # broom
    "\U0001f4c1": "[FOLDER]",  # folder
    "\U0001f4c4": "[FILE]",  # file
    "\U0001f517": "[LINK]",  # link
    "\u26a1": "[FAST]",  # lightning
    "\U0001f40c": "[SLOW]",  # snail
    "\U0001f393": "[LEARN]",  # graduation cap
    "\U0001f916": "[AI]",  # robot
    "\U0001f464": "[USER]",  # user
    "\U0001f310": "[GLOBAL]",  # globe
    "\U0001f4cd": "[LOCATION]",  # pin
    "\U0001f4d0": "[MEASURE]",  # triangular ruler
    "\U0001f528": "[BUILD]",  # hammer
    "\U0001f6a8": "[ALERT]",  # siren
    "\U0001f4e2": "[ANNOUNCE]",  # loudspeaker
    "\U0001f514": "[NOTIFY]",  # bell
    "\U0001f515": "[MUTE]",  # bell slash
    "\U0001f4be": "[SAVE]",  # floppy disk
    "\U0001f4e4": "[UPLOAD]",  # outbox
    "\U0001f4e5": "[DOWNLOAD]",  # inbox
    "\U0001f504": "[REFRESH]",  # arrows
    "\u23ed\ufe0f": "[NEXT]",  # next track
    "\u23ee\ufe0f": "[PREV]",  # previous track
    "\u23ef\ufe0f": "[PLAY]",  # play/pause
    "\u23f9\ufe0f": "[STOP]",  # stop button
}

# File extensions to check
CODE_EXTENSIONS: set[str] = {
    ".py",
    ".yaml",
    ".yml",
    ".sh",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
}

# Directories to skip
SKIP_DIRS: set[str] = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".tox",
    "build",
    "dist",
}


def should_process_file(filepath: Path) -> bool:
    """Check if file should be processed."""
    # Skip if in excluded directory
    for parent in filepath.parents:
        if parent.name in SKIP_DIRS:
            return False

    # Check extension
    return filepath.suffix in CODE_EXTENSIONS


def find_emojis(content: str) -> list[tuple[int, int, str]]:
    """Find all emojis in content with their positions."""
    emojis = []
    line_no = 1
    col = 0

    for i, char in enumerate(content):
        if char == "\n":
            line_no += 1
            col = 0
        else:
            col += 1

        if is_emoji_char(char):
            # Check if part of a sequence
            emoji_seq = char
            j = i + 1
            while j < len(content) and is_emoji_char(content[j]):
                emoji_seq += content[j]
                j += 1
            emojis.append((line_no, col, emoji_seq))

    return emojis


def replace_emojis(content: str) -> tuple[str, int]:
    """Replace emojis with text equivalents."""
    replacements = 0

    # First, replace known emojis with their text equivalents
    for emoji, replacement in EMOJI_REPLACEMENTS.items():
        if emoji in content:
            count = content.count(emoji)
            content = content.replace(emoji, replacement)
            replacements += count

    # Then remove any remaining emojis
    result = []
    for char in content:
        if not is_emoji_char(char):
            result.append(char)
        else:
            replacements += 1

    return "".join(result), replacements


def clean_file(filepath: Path, dry_run: bool = False) -> bool:
    """Remove emojis from a single file."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] Cannot read {filepath}: {e}")
        return False

    # Find emojis
    emojis = find_emojis(content)
    if not emojis:
        return False

    if dry_run:
        print(f"\n[FOUND] {filepath}:")
        for line_no, col, emoji in emojis:
            print(f"  Line {line_no}, col {col}: {emoji}")
        return True

    # Replace emojis
    cleaned_content, replacements = replace_emojis(content)

    # Write back
    try:
        filepath.write_text(cleaned_content, encoding="utf-8")
        print(f"[CLEANED] {filepath} - Replaced {replacements} emoji(s)")
        return True
    except Exception as e:
        print(f"[ERROR] Cannot write {filepath}: {e}")
        return False


def main():
    """Clean all code files."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Remove emojis from code files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("."),
        help="Root path to search (default: current directory)",
    )
    args = parser.parse_args()

    root_path = args.path.resolve()
    if not root_path.exists():
        print(f"[ERROR] Path does not exist: {root_path}")
        return 1

    print(f"[INFO] Scanning for emojis in code files under {root_path}")
    if args.dry_run:
        print("[INFO] Dry-run mode - no files will be modified")

    cleaned_count = 0
    checked_count = 0

    for ext in CODE_EXTENSIONS:
        pattern = f"**/*{ext}"
        for filepath in root_path.glob(pattern):
            if not should_process_file(filepath):
                continue

            checked_count += 1
            if clean_file(filepath, dry_run=args.dry_run):
                cleaned_count += 1

    print(f"\n[COMPLETE] Checked {checked_count} files")
    if args.dry_run:
        print(f"[RESULT] Would clean {cleaned_count} files")
    else:
        print(f"[RESULT] Cleaned {cleaned_count} files")

    return 0 if cleaned_count == 0 else 1


if __name__ == "__main__":
    exit(main())
