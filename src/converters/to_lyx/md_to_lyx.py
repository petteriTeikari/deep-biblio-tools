"""Markdown to LyX converter using pandoc and tex2lyx."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from src.converters.md_to_latex.converter import MarkdownToLatexConverter
from src.converters.to_lyx.tex_to_lyx import TexToLyxConverter


class MarkdownToLyxConverter:
    """Convert Markdown files to LyX format via LaTeX."""

    def __init__(self, output_dir: Path | None = None):
        """Initialize the converter.

        Args:
            output_dir: Directory for output files (defaults to temp directory)
        """
        self.output_dir = output_dir or Path(tempfile.mkdtemp())
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Check dependencies
        if not shutil.which("pandoc"):
            raise RuntimeError("pandoc not found. Please install pandoc.")
        if not shutil.which("tex2lyx"):
            raise RuntimeError("tex2lyx not found. Please install LyX.")

    def convert_simple(
        self, md_file: Path, output_file: Path | None = None
    ) -> Path:
        """Simple conversion using pandoc directly to LyX.

        Args:
            md_file: Path to the input Markdown file
            output_file: Optional output file path (defaults to same name with .lyx)

        Returns:
            Path to the generated LyX file
        """
        if not md_file.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_file}")

        # Determine output file
        if output_file is None:
            output_file = self.output_dir / f"{md_file.stem}.lyx"

        # Try direct pandoc to LyX conversion (if supported)
        cmd = [
            "pandoc",
            "-f",
            "markdown",
            "-t",
            "latex",  # Will convert to LaTeX first
            "-o",
            str(output_file.with_suffix(".tex")),
            str(md_file),
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Convert LaTeX to LyX
            tex_converter = TexToLyxConverter(self.output_dir)
            lyx_file = tex_converter.convert(
                output_file.with_suffix(".tex"), output_file
            )

            # Clean up temporary LaTeX file
            output_file.with_suffix(".tex").unlink(missing_ok=True)

            return lyx_file

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Conversion failed: {e.stderr}")

    def convert_advanced(
        self,
        md_file: Path,
        output_file: Path | None = None,
        process_citations: bool = True,
        process_concept_boxes: bool = True,
        two_column: bool = False,
        arxiv_ready: bool = False,
    ) -> Path:
        """Advanced conversion using our Markdown to LaTeX converter first.

        This preserves citations, concept boxes, and other advanced formatting.

        Args:
            md_file: Path to the input Markdown file
            output_file: Optional output file path
            process_citations: Extract and process citations
            process_concept_boxes: Convert concept boxes
            two_column: Use two-column layout
            arxiv_ready: Make arXiv-ready output

        Returns:
            Path to the generated LyX file
        """
        if not md_file.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_file}")

        # Create temporary directory for intermediate files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # First convert to LaTeX using our converter
            md_converter = MarkdownToLatexConverter(
                output_dir=temp_path,
                two_column=two_column,
                arxiv_ready=arxiv_ready,
            )

            # Convert to LaTeX
            output_tex = md_converter.convert(md_file)

            if not output_tex.exists():
                raise RuntimeError(
                    f"LaTeX conversion failed - {output_tex} not created"
                )

            # Determine output file
            if output_file is None:
                output_file = self.output_dir / f"{md_file.stem}.lyx"

            # Convert LaTeX to LyX
            tex_converter = TexToLyxConverter(self.output_dir)
            lyx_file = tex_converter.convert(output_tex, output_file)

            # Copy bibliography file if it exists
            bib_file = temp_path / "references.bib"
            if bib_file.exists():
                shutil.copy2(bib_file, self.output_dir / "references.bib")
                print(
                    f"Copied bibliography to {self.output_dir / 'references.bib'}"
                )

            return lyx_file

    def batch_convert(
        self, md_files: list[Path], simple: bool = False
    ) -> dict[Path, Path]:
        """Convert multiple Markdown files to LyX.

        Args:
            md_files: List of Markdown files to convert
            simple: Use simple conversion (faster but less features)

        Returns:
            Dictionary mapping input files to output files
        """
        results = {}

        for md_file in md_files:
            try:
                if simple:
                    lyx_file = self.convert_simple(md_file)
                else:
                    lyx_file = self.convert_advanced(md_file)
                results[md_file] = lyx_file
                print(f"Converted {md_file} -> {lyx_file}")
            except Exception as e:
                print(f"Failed to convert {md_file}: {e}")
                results[md_file] = None

        return results
