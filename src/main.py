#!/usr/bin/env python3
"""
Deep Biblio Tools - CLI for bibliography validation and correction
"""

import csv
import logging
from pathlib import Path

import click

from .core.biblio_checker import BiblioChecker


@click.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory for corrected files",
)
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Show what would be done without making changes",
)
@click.option(
    "--check-links",
    is_flag=True,
    default=True,
    help="Validate that citation links are accessible",
)
@click.option(
    "--check-citations",
    is_flag=True,
    default=True,
    help="Validate citation text matches actual paper metadata",
)
@click.option(
    "--no-progress", is_flag=True, help="Disable progress bar display"
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable local cache, force fresh network requests",
)
def main(
    input_path,
    output_dir,
    log_level,
    dry_run,
    check_links,
    check_citations,
    no_progress,
    no_cache,
):
    """
    Validate and correct bibliographic entries in Markdown files.

    INPUT_PATH can be a single Markdown file or a directory containing Markdown files.
    """
    logging.basicConfig(level=getattr(logging, log_level))

    checker = BiblioChecker(use_cache=not no_cache)

    if input_path.is_file():
        files = [input_path]
    else:
        files = list(input_path.glob("**/*.md"))

    if not files:
        click.echo("No Markdown files found.")
        return

    click.echo(f"Processing {len(files)} file(s)...")

    for file_path in files:
        click.echo(f"\nProcessing: {file_path}")

        if dry_run:
            click.echo(f"  [DRY RUN] Would process {file_path}")
            # TODO: Add dry-run preview functionality
        else:
            try:
                corrected_content, results = checker.process_markdown_file(
                    str(file_path), show_progress=not no_progress
                )

                errors = [r for r in results if not r.is_valid]
                corrections = [r for r in results if r.corrected_text]

                click.echo("  Processed successfully")
                click.echo(f"    - Found {len(results)} citations")
                if corrections:
                    click.echo(f"    - Made {len(corrections)} corrections")
                if errors:
                    click.echo(f"    - Found {len(errors)} errors")

                # Show detailed results
                for result in results:
                    if not result.is_valid:
                        click.echo(
                            f"    WARNING: {result.citation.text}: {', '.join(result.errors)}",
                            err=True,
                        )
                    elif result.corrected_text:
                        click.echo(
                            f"    Corrected: {result.citation.text} -> {result.corrected_text}"
                        )

                # Always save corrected content and comparison CSV
                if corrections or errors:
                    # Create output directory
                    if output_dir:
                        final_output_dir = output_dir
                    else:
                        final_output_dir = file_path.parent / "md_output"

                    final_output_dir.mkdir(parents=True, exist_ok=True)

                    # Save corrected markdown file with suffix
                    file_stem = file_path.stem
                    output_file = (
                        final_output_dir / f"{file_stem}_citation-fix.md"
                    )
                    output_file.write_text(corrected_content)
                    click.echo(
                        f"    -> Saved corrected version to {output_file}"
                    )

                    # Create CSV comparison file
                    csv_file = (
                        final_output_dir / f"{file_stem}_citation-changes.csv"
                    )

                    with open(
                        csv_file, "w", newline="", encoding="utf-8"
                    ) as csvf:
                        writer = csv.writer(csvf)
                        writer.writerow(
                            [
                                "Status",
                                "Original_Citation",
                                "Original_URL",
                                "Corrected_Citation",
                                "Corrected_URL",
                                "Tags",
                                "Confidence",
                                "Errors",
                                "Source_File",
                                "Line_Number",
                                "Context_Before",
                                "Context_After",
                                "Full_Line",
                            ]
                        )

                        for result in results:
                            status = (
                                "CORRECTED"
                                if result.corrected_text
                                else ("ERROR" if result.errors else "NO_CHANGE")
                            )
                            writer.writerow(
                                [
                                    status,
                                    result.citation.text,
                                    result.citation.url,
                                    result.corrected_text
                                    or result.citation.text,
                                    result.corrected_url or result.citation.url,
                                    " ".join(result.tags),
                                    result.confidence,
                                    "; ".join(result.errors)
                                    if result.errors
                                    else "",
                                    result.citation.file_path,
                                    result.citation.line_number,
                                    result.citation.context_before,
                                    result.citation.context_after,
                                    result.citation.full_line,
                                ]
                            )

                    click.echo(f"    -> Saved citation changes to {csv_file}")
                    click.echo(f"    -> Output directory: {final_output_dir}")

            except Exception as e:
                click.echo(f"  ERROR: {e}", err=True)


if __name__ == "__main__":
    main()
