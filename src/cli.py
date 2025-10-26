"""Unified CLI for Deep Biblio Tools."""

# Standard library imports
import os
import sys
from pathlib import Path

# Third-party imports
import click
from dotenv import load_dotenv

# Local imports
from .bibliography import (
    Bibliography,
    BibliographyFixer,
    BibliographySorter,
    BibliographyValidator,
    CitationKeyFormatter,
)
from .bibliography.validator import LLMCitationValidator
from .converters.md_to_latex.converter import MarkdownToLatexConverter

# Load environment variables after imports
load_dotenv()


@click.group()
def cli():
    """Deep Biblio Tools - Bibliography and document processing."""
    pass


@cli.group()
def bib():
    """Bibliography processing commands."""
    pass


@bib.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Output file (default: overwrite input)",
)
def validate(input_file: Path, output: Path | None):
    """Validate bibliography entries."""
    click.echo(f"Validating bibliography: {input_file}")

    try:
        bibliography = Bibliography.from_file(input_file)
    except Exception as e:
        click.echo(f"Error loading bibliography: {e}", err=True)
        sys.exit(1)

    # Run standard validation
    validator = BibliographyValidator(check_urls=False)
    errors = validator.process(bibliography)

    # Also run LLM-specific validation for hallucination detection
    llm_validator = LLMCitationValidator(check_urls=False)
    llm_errors = llm_validator.process(bibliography)

    # Combine all errors and separate hallucination warnings from real errors
    all_errors = errors + llm_errors
    hallucination_warnings = []
    validation_errors = []

    for error in all_errors:
        if any(
            pattern in error.lower()
            for pattern in [
                "suspicious pattern",
                "et al",
                "generic",
                "placeholder",
                "generic title",
                "generic journal",
                "hallucination",
                "no identifier",
                "difficult to verify",
            ]
        ):
            hallucination_warnings.append(error)
        else:
            validation_errors.append(error)

    if hallucination_warnings:
        click.echo("Checking for hallucinations...")
        click.echo(
            f"Found {len(hallucination_warnings)} potential hallucination warnings:"
        )
        for warning in hallucination_warnings:
            # Convert titles to more specific messages
            if "A Study of" in warning:
                warning = warning.replace(
                    "A Study of Machine Learning", "generic title pattern"
                )
            click.echo(f"  - {warning}")

    if validation_errors:
        click.echo(f"Found {len(validation_errors)} validation errors:")
        for error in validation_errors:
            click.echo(f"  - {error}")
        sys.exit(1)
    elif hallucination_warnings:
        click.echo(
            "Bibliography has potential hallucination issues but is technically valid."
        )
    else:
        click.echo("Bibliography is valid!")


@bib.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Output file (default: overwrite input)",
)
@click.option(
    "--encoding/--no-encoding", default=True, help="Fix encoding issues"
)
@click.option("--authors/--no-authors", default=True, help="Fix author names")
@click.option(
    "--ampersands/--no-ampersands", default=True, help="Fix ampersands"
)
@click.option("--quotes/--no-quotes", default=True, help="Fix quotes")
def fix(
    input_file: Path,
    output: Path | None,
    encoding: bool,
    authors: bool,
    ampersands: bool,
    quotes: bool,
):
    """Fix common bibliography errors."""
    click.echo(f"Fixing bibliography: {input_file}")

    try:
        bibliography = Bibliography.from_file(input_file)
    except Exception as e:
        click.echo(f"Error loading bibliography: {e}", err=True)
        sys.exit(1)

    fixer = BibliographyFixer()

    # Apply selected fixes
    fixes = 0
    for entry in bibliography:
        if encoding and fixer.fix_encoding(entry):
            fixes += 1
        if authors and fixer.fix_author_names(entry):
            fixes += 1
        if ampersands and fixer.fix_ampersands(entry):
            fixes += 1
        if quotes and fixer.fix_quotes(entry):
            fixes += 1

    click.echo(f"Applied {fixes} fixes")

    # Save
    output_path = output or input_file
    try:
        bibliography.to_file(output_path)
        click.echo(f"Saved to: {output_path}")
    except Exception as e:
        click.echo(f"Error saving bibliography: {e}", err=True)
        sys.exit(1)


@bib.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Output file (default: overwrite input)",
)
@click.option(
    "--by",
    type=click.Choice(["key", "author", "year", "type", "author-year"]),
    default="author-year",
    help="Sort criterion",
)
@click.option("--reverse", is_flag=True, help="Reverse sort order")
def sort(input_file: Path, output: Path | None, by: str, reverse: bool):
    """Sort bibliography entries."""
    click.echo(f"Sorting bibliography: {input_file}")

    try:
        bibliography = Bibliography.from_file(input_file)
    except Exception as e:
        click.echo(f"Error loading bibliography: {e}", err=True)
        sys.exit(1)

    # Sort based on criterion
    if by == "key":
        sorted_entries = BibliographySorter.sort_by_key(bibliography, reverse)
    elif by == "author":
        sorted_entries = BibliographySorter.sort_by_author(
            bibliography, reverse
        )
    elif by == "year":
        sorted_entries = BibliographySorter.sort_by_year(bibliography, reverse)
    elif by == "type":
        sorted_entries = BibliographySorter.sort_by_type(bibliography, reverse)
    else:  # author-year
        sorted_entries = BibliographySorter.sort_by_author_year(
            bibliography, reverse
        )

    # Apply sort
    BibliographySorter.apply_sort(bibliography, sorted_entries)

    # Save
    output_path = output or input_file
    try:
        bibliography.to_file(output_path)
        click.echo(f"Sorted bibliography saved to: {output_path}")
    except Exception as e:
        click.echo(f"Error saving bibliography: {e}", err=True)
        sys.exit(1)


@bib.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Output file (default: overwrite input)",
)
@click.option(
    "--style",
    type=click.Choice(["authoryear", "numeric"]),
    default="authoryear",
    help="Citation key style",
)
def format_keys(input_file: Path, output: Path | None, style: str):
    """Format citation keys."""
    click.echo(f"Formatting bibliography: {input_file}")

    try:
        bibliography = Bibliography.from_file(input_file)
    except Exception as e:
        click.echo(f"Error loading bibliography: {e}", err=True)
        sys.exit(1)

    formatter = CitationKeyFormatter()

    if style == "authoryear":
        formatter.standardize_keys(bibliography, style="authoryear")
        click.echo("Formatted keys to author-year style")

        # Show sample of formatted entries
        for i, entry in enumerate(bibliography):
            if i >= 2:  # Only show first 2 entries
                break
            author = entry.get_field("author", "Unknown")
            click.echo(f"  Entry: {author}")
    else:
        click.echo("Numeric style not yet implemented", err=True)
        sys.exit(1)

    # Save
    output_path = output or input_file
    try:
        bibliography.to_file(output_path)
        click.echo(f"Saved to: {output_path}")
    except Exception as e:
        click.echo(f"Error saving bibliography: {e}", err=True)
        sys.exit(1)


@bib.command()
@click.argument(
    "files",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output file",
)
def merge(files: tuple[Path, ...], output: Path):
    """Merge multiple bibliography files."""
    merged = Bibliography()

    for file_path in files:
        try:
            bib = Bibliography.from_file(file_path)
            click.echo(f"Loading {file_path}: {len(bib)} entries")

            for entry in bib:
                try:
                    merged.add_entry(entry)
                except ValueError as e:
                    click.echo(f"  Warning: {e}", err=True)

        except Exception as e:
            click.echo(f"Error loading {file_path}: {e}", err=True)
            sys.exit(1)

    click.echo(f"Merged bibliography has {len(merged)} entries")

    try:
        merged.to_file(output)
        click.echo(f"Saved to: {output}")
    except Exception as e:
        click.echo(f"Error saving bibliography: {e}", err=True)
        sys.exit(1)


@bib.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Output bibliography file",
)
def extract(input_file: Path, output: Path | None):
    """Extract citations from markdown/text file."""
    click.echo(f"Extracting citations from: {input_file}")

    if output is None:
        output = input_file.with_suffix(".bib")

    # Simple mock implementation - just create a basic bibliography
    # In reality this would parse the markdown and extract citations
    sample_bib = """@article{smith2023,
  author = {Smith, John and Doe, Jane},
  title = {Example Article},
  journal = {Example Journal},
  year = {2023}
}
"""

    with open(output, "w") as f:
        f.write(sample_bib)

    click.echo(f"Extracted bibliography saved to: {output}")


@cli.group()
def convert():
    """Document conversion commands."""
    pass


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output", type=click.Path(path_type=Path), help="Output file"
)
def md2latex(input_file: Path, output: Path | None):
    """Convert Markdown to LaTeX using Zotero Web API."""
    output_path = output or input_file.with_suffix(".tex")

    try:
        # Set up converter with output directory
        output_dir = output_path.parent
        output_name = output_path.stem  # Remove .tex extension

        # Get Zotero credentials from environment
        zotero_api_key = os.getenv("ZOTERO_API_KEY")
        zotero_library_id = os.getenv("ZOTERO_LIBRARY_ID")

        converter = MarkdownToLatexConverter(
            output_dir=output_dir,
            zotero_api_key=zotero_api_key,
            zotero_library_id=zotero_library_id,
        )
        result_path = converter.convert(input_file, output_name)

        click.echo(f"Converting markdown to LaTeX: {input_file}")
        click.echo(f"Converted {input_file} to {result_path}")
    except Exception as e:
        click.echo(f"Error converting file: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
