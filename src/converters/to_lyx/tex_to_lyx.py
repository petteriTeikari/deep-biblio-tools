"""TeX to LyX converter using tex2lyx."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class TexToLyxConverter:
    """Convert TeX/LaTeX files to LyX format."""

    def __init__(self, output_dir: Path | None = None):
        """Initialize the converter.

        Args:
            output_dir: Directory for output files (defaults to temp directory)
        """
        self.output_dir = output_dir or Path(tempfile.mkdtemp())
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Check if tex2lyx is available
        if not shutil.which("tex2lyx"):
            raise RuntimeError("tex2lyx not found. Please install LyX.")

    def convert(self, tex_file: Path, output_file: Path | None = None) -> Path:
        """Convert a TeX file to LyX format.

        Args:
            tex_file: Path to the input TeX file
            output_file: Optional output file path (defaults to same name with .lyx)

        Returns:
            Path to the generated LyX file
        """
        if not tex_file.exists():
            raise FileNotFoundError(f"TeX file not found: {tex_file}")

        # Determine output file
        if output_file is None:
            output_file = self.output_dir / f"{tex_file.stem}.lyx"

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Create temporary user directory for tex2lyx if needed
        temp_dir = None
        env = os.environ.copy()

        # Check if running in Docker or if user directory doesn't exist
        if not Path.home().exists() or os.environ.get("CONTAINER_ENV"):
            temp_dir = tempfile.mkdtemp()
            env["HOME"] = temp_dir
            # Create LyX user directory structure
            lyx_dir = Path(temp_dir) / ".lyx"
            lyx_dir.mkdir(exist_ok=True)

        # Run tex2lyx
        cmd = [
            "tex2lyx",
            "-copyfiles",  # Copy included files
            "-f",  # Force overwrite
            str(tex_file),
            str(output_file),
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, env=env
            )

            if result.stderr:
                print(f"tex2lyx warnings: {result.stderr}")

            return output_file

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"tex2lyx failed: {e.stderr}")
        finally:
            # Clean up temporary directory if created
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir)

    def convert_with_options(
        self,
        tex_file: Path,
        output_file: Path | None = None,
        noweb: bool = False,
        roundtrip: bool = False,
        syntaxfile: Path | None = None,
    ) -> Path:
        """Convert with advanced options.

        Args:
            tex_file: Path to the input TeX file
            output_file: Optional output file path
            noweb: Import as noweb (literate programming) file
            roundtrip: Use roundtrip algorithm (preserves more TeX constructs)
            syntaxfile: Path to custom syntax file

        Returns:
            Path to the generated LyX file
        """
        if not tex_file.exists():
            raise FileNotFoundError(f"TeX file not found: {tex_file}")

        # Determine output file
        if output_file is None:
            # For roundtrip mode, use a different name to avoid conflicts
            if roundtrip:
                output_file = self.output_dir / f"{tex_file.stem}_roundtrip.lyx"
            else:
                output_file = self.output_dir / f"{tex_file.stem}.lyx"

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Create temporary user directory for tex2lyx if needed
        temp_dir = None
        env = os.environ.copy()

        # Check if running in Docker or if user directory doesn't exist
        if not Path.home().exists() or os.environ.get("CONTAINER_ENV"):
            temp_dir = tempfile.mkdtemp()
            env["HOME"] = temp_dir
            # Create LyX user directory structure
            lyx_dir = Path(temp_dir) / ".lyx"
            lyx_dir.mkdir(exist_ok=True)

        # Build command
        cmd = ["tex2lyx", "-f"]

        if noweb:
            cmd.append("-n")
        if roundtrip:
            cmd.append("-roundtrip")
        if syntaxfile:
            cmd.extend(["-s", str(syntaxfile)])

        cmd.extend([str(tex_file), str(output_file)])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, env=env
            )

            if result.stderr:
                print(f"tex2lyx warnings: {result.stderr}")

            return output_file

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"tex2lyx failed: {e.stderr}")
        finally:
            # Clean up temporary directory if created
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir)
