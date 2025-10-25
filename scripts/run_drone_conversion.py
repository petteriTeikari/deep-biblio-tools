#!/usr/bin/env python3
"""Direct conversion script for DronePosition.md"""

import sys
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from scripts.convert_markdown_to_latex import (  # noqa: E402
    convert_markdown_to_latex,
)


def main():
    """Run conversion with full options."""
    input_file = Path("drone_data/DronePosition.md")
    output_dir = Path("drone_data/latex_output_validated")

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return 1

    print(f"Converting {input_file} to LaTeX...")
    print(f"Output directory: {output_dir}")
    print("Using cached citation data where available")
    print("Bibliography style: spbasic_pt")
    print("\n" + "=" * 60 + "\n")

    try:
        latex_file = convert_markdown_to_latex(
            input_file=input_file,
            output_dir=output_dir,
            mode="full",
            validate=True,
            style="spbasic_pt",
            compile_pdf=True,
            debug=True,
            auto_fix_pdf=True,
            max_fix_iterations=3,
        )

        print("\nConversion complete!")
        print(f"LaTeX file: {latex_file}")

        # Check for PDF
        pdf_file = latex_file.with_suffix(".pdf")
        if pdf_file.exists():
            print(f"PDF generated: {pdf_file}")
        else:
            print("PDF compilation may have failed - check the reports")

        # Check for reports
        for report in output_dir.glob("*.md"):
            print(f"Report: {report}")

        return 0

    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
