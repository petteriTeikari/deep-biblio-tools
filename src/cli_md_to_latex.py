"""CLI interface for markdown to LaTeX converter."""

import logging
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from src.converters.md_to_latex import MarkdownToLatexConverter
from src.converters.md_to_latex.concept_boxes import ConceptBoxStyle

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@click.command()
@click.argument("markdown_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for LaTeX files (default: ./latex_output)",
)
@click.option(
    "-n",
    "--output-name",
    type=str,
    default=None,
    help="Name for output files without extension (default: same as input)",
)
@click.option(
    "-a",
    "--author",
    type=str,
    default=None,
    help="Author name for the document",
)
@click.option(
    "--style",
    type=click.Choice([s.value for s in ConceptBoxStyle]),
    default=ConceptBoxStyle.PROFESSIONAL_BLUE.value,
    help="Style for concept boxes",
)
@click.option(
    "--cache-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Directory for citation cache",
)
@click.option("--no-arxiv", is_flag=True, help="Disable arXiv-ready formatting")
@click.option(
    "--single-column",
    is_flag=True,
    help="Use single-column layout instead of two-column",
)
@click.option(
    "--box-encoding",
    type=click.Choice(
        ["asterisk", "hline", "blockquote"], case_sensitive=False
    ),
    default=None,
    help="Encoding format for concept boxes (asterisk: *Title*, hline: between ---, blockquote: > Title)",
)
@click.option(
    "--prefer-arxiv",
    is_flag=True,
    help="Prefer arXiv metadata over CrossRef when both are available",
)
@click.option(
    "--zotero-api-key",
    envvar="ZOTERO_API_KEY",
    help="Zotero API key for fetching metadata (can also be set via ZOTERO_API_KEY env var)",
)
@click.option(
    "--zotero-library-id",
    envvar="ZOTERO_LIBRARY_ID",
    help="Zotero library ID for searching user's library (can also be set via ZOTERO_LIBRARY_ID env var)",
)
@click.option(
    "--bibliography-style",
    type=str,
    default="spbasic_pt",
    help="Custom bibliography style file (default: 'spbasic_pt')",
)
@click.option(
    "-v", "--verbose", is_flag=True, help="Show progress and detailed output"
)
@click.option(
    "--font-size",
    type=click.Choice(["10pt", "11pt", "12pt"], case_sensitive=False),
    default="11pt",
    help="Font size for document (10pt is common for arXiv)",
)
@click.option(
    "--enable-auto-add/--no-auto-add",
    default=True,
    help="Enable automatic addition of missing citations to Zotero (default: enabled)",
)
@click.option(
    "--auto-add-dry-run/--auto-add-real",
    default=True,
    help="Dry-run mode for auto-add (default: dry-run for safety)",
)
@click.option(
    "--allow-failures",
    is_flag=True,
    help="Allow conversion to continue when citations fail (generates temp keys)",
)
def convert_markdown_to_latex(
    markdown_file: Path,
    output_dir: Path | None,
    output_name: str | None,
    author: str | None,
    style: str,
    cache_dir: Path | None,
    no_arxiv: bool,
    single_column: bool,
    box_encoding: str | None,
    prefer_arxiv: bool,
    zotero_api_key: str | None,
    zotero_library_id: str | None,
    bibliography_style: str | None,
    verbose: bool,
    font_size: str,
    enable_auto_add: bool,
    auto_add_dry_run: bool,
    allow_failures: bool,
):
    """Convert markdown file to LaTeX format with citations and concept boxes.

    MARKDOWN_FILE: Path to the markdown file to convert

    Example usage:

        # Basic conversion
        deep-biblio-md2latex document.md

        # With custom output and author
        deep-biblio-md2latex document.md -o ./output -n paper -a "John Doe"

        # With different concept box style
        deep-biblio-md2latex document.md --style modern_gradient

        # With Zotero integration for better metadata
        deep-biblio-md2latex document.md --zotero-api-key YOUR_KEY --zotero-library-id YOUR_ID

        # Or set environment variables
        export ZOTERO_API_KEY="your_api_key"
        export ZOTERO_LIBRARY_ID="your_library_id"
        deep-biblio-md2latex document.md
    """
    try:
        # Initialize converter
        converter = MarkdownToLatexConverter(
            output_dir=output_dir,
            cache_dir=cache_dir,
            concept_box_style=ConceptBoxStyle(style),
            concept_box_encoding=box_encoding,
            arxiv_ready=not no_arxiv,
            two_column=not single_column,
            prefer_arxiv=prefer_arxiv,
            zotero_api_key=zotero_api_key,
            zotero_library_id=zotero_library_id,
            bibliography_style=bibliography_style,
            font_size=font_size,
            enable_auto_add=enable_auto_add,
            auto_add_dry_run=auto_add_dry_run,
            allow_failures=allow_failures,
        )

        # Convert the file
        output_file = converter.convert(
            markdown_file=markdown_file,
            output_name=output_name,
            author=author,
            verbose=verbose,
        )

        # Print failure report if there were any failures
        if converter.citation_manager.failed_citations:
            failure_report = (
                converter.citation_manager.generate_failure_report()
            )
            click.echo(failure_report)

        if verbose:
            click.echo("\nConversion successful!")
            click.echo(f"Output file: {output_file}")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Conversion failed: {e}", err=True)
        logger.exception("Conversion failed with exception:")
        sys.exit(1)


if __name__ == "__main__":
    convert_markdown_to_latex()
