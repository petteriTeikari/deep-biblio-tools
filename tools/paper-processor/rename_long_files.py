#!/usr/bin/env python3
"""
Rename files with names that are too long for the file system.
"""

import hashlib
import shutil
from pathlib import Path


def shorten_filename(file_path: Path, max_length: int = 200) -> Path:
    """Shorten a filename if it's too long."""
    if len(file_path.name) <= max_length:
        return file_path

    # Keep extension
    stem = file_path.stem
    suffix = file_path.suffix

    # Calculate how much we need to shorten
    target_stem_length = max_length - len(suffix) - 10  # Leave room for hash

    if len(stem) > target_stem_length:
        # Create a hash of the full name for uniqueness
        hash_obj = hashlib.md5(stem.encode())
        hash_str = hash_obj.hexdigest()[:8]

        # Truncate and add hash
        new_stem = stem[:target_stem_length] + "_" + hash_str
        new_name = new_stem + suffix
        new_path = file_path.parent / new_name

        return new_path

    return file_path


def rename_long_files_in_directory(directory: Path):
    """Rename all files with long names in a directory."""
    renamed_files = []

    for file_path in directory.iterdir():
        if file_path.is_file():
            new_path = shorten_filename(file_path)
            if new_path != file_path:
                print(f"Renaming: {file_path.name}")
                print(f"      To: {new_path.name}")
                shutil.move(str(file_path), str(new_path))
                renamed_files.append((file_path, new_path))

    return renamed_files


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python rename_long_files.py <directory>")
        sys.exit(1)

    directory = Path(sys.argv[1])
    if not directory.exists():
        print(f"Directory not found: {directory}")
        sys.exit(1)

    print(f"Checking for long filenames in: {directory}")
    renamed = rename_long_files_in_directory(directory)

    if renamed:
        print(f"\nRenamed {len(renamed)} files")

        # Save mapping for reference
        mapping_file = directory / "renamed_files_mapping.txt"
        with open(mapping_file, "w") as f:
            for old, new in renamed:
                f.write(f"{old.name} -> {new.name}\n")
        print(f"Mapping saved to: {mapping_file}")
    else:
        print("No files needed renaming")
