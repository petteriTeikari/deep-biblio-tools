#!/usr/bin/env python3
"""Test complete pipeline from MD to PDF with all fixes."""

import subprocess
import sys
from pathlib import Path


def run_pipeline():
    """Run the complete conversion pipeline."""
    base_dir = Path(
        "/home/petteri/Dropbox/LABs/github-personal/github/deep-biblio-tools"
    )

    # Input and output paths
    input_md = base_dir / "drone_data" / "DronePosition.md"
    output_dir = base_dir / "drone_data" / "DronePosition_complete"

    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True)

    print(f"Starting conversion of {input_md}")
    print(f"Output directory: {output_dir}")

    # Run the conversion script
    cmd = [
        sys.executable,
        str(base_dir / "scripts" / "convert_markdown_to_latex.py"),
        str(input_md),
        "--output",
        str(output_dir),
        "--debug",
    ]

    print(f"Running command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("Conversion successful!")
        print(result.stdout)

        # Check if PDF was created
        pdf_file = output_dir / "DronePosition.tex.pdf"
        if pdf_file.exists():
            print(f"\n PDF created successfully: {pdf_file}")
            print(f"  Size: {pdf_file.stat().st_size / 1024:.1f} KB")
        else:
            print("\n PDF not found")

        # Check for bibliography
        bib_file = output_dir / "references.bib"
        if bib_file.exists():
            # Count entries
            with open(bib_file) as f:
                entries = sum(1 for line in f if line.strip().startswith("@"))
            print(f"\n Bibliography created with {entries} entries")

        # Check for placeholder entries
        if bib_file.exists():
            print("\nChecking for placeholder entries...")
            with open(bib_file) as f:
                content = f.read()
                placeholders = []
                for line in content.split("\n"):
                    if "author" in line.lower() and any(
                        bad in line
                        for bad in ["Unknown", "TODO", "PLACEHOLDER", ", ."]
                    ):
                        placeholders.append(line.strip())

                if placeholders:
                    print(
                        f"\nFound {len(placeholders)} entries that may need manual fixing:"
                    )
                    for p in placeholders[:10]:  # Show first 10
                        print(f"  - {p}")
                    if len(placeholders) > 10:
                        print(f"  ... and {len(placeholders) - 10} more")
                else:
                    print("No obvious placeholder entries found.")

    except subprocess.CalledProcessError as e:
        print(f"Conversion failed with error: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run_pipeline())
