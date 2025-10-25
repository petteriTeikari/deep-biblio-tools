"""CLI interface for paper-processor."""

import concurrent.futures
import threading
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core.processor import PaperProcessor
from .utils.config import load_config

console = Console()


def _get_files_from_pattern(input_path: Path, pattern: str) -> list[Path]:
    """Get files matching pattern, with special handling for 'all_formats'."""
    if pattern == "all_formats":
        # Find all supported formats
        all_files = []
        extensions = ["*.html", "*.htm", "*.pdf", "*.tex", "*.xml"]
        for ext in extensions:
            all_files.extend(input_path.glob(ext))
        return sorted(all_files)
    else:
        return sorted(input_path.glob(pattern))


@click.group()
@click.version_option()
@click.option(
    "--config", "-c", type=click.Path(), help="Path to configuration file"
)
@click.pass_context
def cli(ctx, config):
    """Extract and process content from academic papers."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config) if config else {}


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "json", "text"]),
    default="markdown",
    help="Output format",
)
@click.option(
    "--sections", "-s", help="Comma-separated list of sections to extract"
)
@click.pass_context
def extract(ctx, input_file, output, format, sections):
    """Extract content from a single paper."""
    processor = PaperProcessor(config=ctx.obj.get("config", {}))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(f"Processing {input_file}...", total=None)

        # Extract sections if specified
        section_list = sections.split(",") if sections else None

        # Process the paper
        paper = processor.process_file(Path(input_file), sections=section_list)

        # Format output
        if format == "markdown":
            output_content = paper.to_markdown()
        elif format == "json":
            import json

            output_content = json.dumps(paper.to_dict(), indent=2)
        else:
            output_content = paper.to_text()

        # Save or print output
        if output:
            Path(output).write_text(output_content, encoding="utf-8")
            console.print(
                f"[green] Extracted content saved to {output}[/green]"
            )
        else:
            console.print(output_content)


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    help="Output directory for processed files (default: input_dir/extracted)",
)
@click.option(
    "--pattern",
    "-p",
    default="*.html",
    help="File pattern to match (use 'all_formats' for *.{html,htm,pdf,tex,xml})",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "json", "text"]),
    default="markdown",
    help="Output format",
)
@click.option(
    "--parallel", "-P", is_flag=True, help="Process files in parallel"
)
@click.option(
    "--retry-failed",
    "-r",
    is_flag=True,
    default=True,
    help="Retry failed files with longer timeout (default: True)",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=30,
    help="Timeout per file in seconds (default: 30)",
)
@click.pass_context
def batch_extract(
    ctx, input_dir, output_dir, pattern, format, parallel, retry_failed, timeout
):
    """Extract content from multiple papers."""
    input_path = Path(input_dir)

    # If no output directory specified, create it relative to input directory
    if output_dir is None:
        output_path = input_path / "extracted"
    else:
        output_path = Path(output_dir)

    output_path.mkdir(parents=True, exist_ok=True)

    # Find all matching files
    files = _get_files_from_pattern(input_path, pattern)
    console.print(f"[bold]Found {len(files)} files to process[/bold]")

    if not files:
        console.print("[yellow]No files found matching the pattern![/yellow]")
        return

    processor = PaperProcessor(config=ctx.obj.get("config", {}))

    def process_single_file(file_path, timeout_seconds=None):
        """Process a single file with optional timeout."""

        result = [None, None, None]  # file_path, success, error

        def process():
            try:
                paper = processor.process_file(file_path)

                # Determine output filename
                output_name = file_path.stem
                if format == "markdown":
                    output_file = output_path / f"{output_name}.md"
                    content = paper.to_markdown()
                elif format == "json":
                    output_file = output_path / f"{output_name}.json"
                    import json

                    content = json.dumps(paper.to_dict(), indent=2)
                else:
                    output_file = output_path / f"{output_name}.txt"
                    content = paper.to_text()

                output_file.write_text(content, encoding="utf-8")
                result[0], result[1], result[2] = file_path, True, None
            except Exception as e:
                result[0], result[1], result[2] = file_path, False, str(e)

        if timeout_seconds:
            thread = threading.Thread(target=process)
            thread.start()
            thread.join(timeout=timeout_seconds)

            if thread.is_alive():
                # Timeout occurred
                return (
                    file_path,
                    False,
                    f"Timeout after {timeout_seconds} seconds",
                )
            else:
                return result[0], result[1], result[2]
        else:
            process()
            return result[0], result[1], result[2]

    # Process files - First pass
    failed_files = []
    success_count = 0

    with Progress(console=console) as progress:
        task = progress.add_task(
            "[cyan]Processing papers (Pass 1)...", total=len(files)
        )

        if parallel:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=4
            ) as executor:
                futures = {
                    executor.submit(process_single_file, f, timeout): f
                    for f in files
                }
                for future in concurrent.futures.as_completed(futures):
                    file_path, success, error = future.result()
                    if success:
                        console.print(f"[green][/green] {file_path.name}")
                        success_count += 1
                    else:
                        console.print(
                            f"[yellow][/yellow] {file_path.name}: {error}"
                        )
                        failed_files.append((file_path, error))
                    progress.advance(task)
        else:
            for file_path in files:
                file_path, success, error = process_single_file(
                    file_path, timeout
                )
                if success:
                    console.print(f"[green][/green] {file_path.name}")
                    success_count += 1
                else:
                    console.print(
                        f"[yellow][/yellow] {file_path.name}: {error}"
                    )
                    failed_files.append((file_path, error))
                progress.advance(task)

    # Second pass - retry failed files with longer timeout and no parallelism
    if failed_files and retry_failed:
        console.print(
            f"\n[yellow]First pass complete: {success_count}/{len(files)} succeeded[/yellow]"
        )
        console.print(
            f"[yellow]Retrying {len(failed_files)} failed files with extended timeout...[/yellow]\n"
        )

        retry_timeout = max(timeout * 4, 120)  # 4x timeout or minimum 2 minutes
        retry_success = 0

        with Progress(console=console) as progress:
            task = progress.add_task(
                "[cyan]Retrying failed files (Pass 2)...",
                total=len(failed_files),
            )

            for file_path, first_error in failed_files:
                file_path, success, error = process_single_file(
                    file_path, retry_timeout
                )
                if success:
                    console.print(
                        f"[green][/green] {file_path.name} (retry successful)"
                    )
                    retry_success += 1
                    success_count += 1
                else:
                    console.print(f"[red][/red] {file_path.name}: {error}")
                progress.advance(task)

        if retry_success > 0:
            console.print(
                f"\n[green]Retry pass recovered {retry_success} additional files[/green]"
            )

    # Final summary
    total_failed = len(files) - success_count
    if total_failed == 0:
        console.print(
            f"\n[bold green]All {len(files)} files processed successfully![/bold green]"
        )
    else:
        console.print(
            f"\n[bold yellow]Processing complete: {success_count}/{len(files)} files succeeded[/bold yellow]"
        )
        if total_failed > 0:
            console.print(
                f"[red]{total_failed} files could not be processed[/red]"
            )


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--to",
    type=click.Choice(["markdown", "latex", "text"]),
    required=True,
    help="Target format",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.pass_context
def convert(ctx, input_file, to, output):
    """Convert paper between formats."""
    processor = PaperProcessor(config=ctx.obj.get("config", {}))

    console.print(f"[bold blue]Converting {input_file} to {to}...[/bold blue]")

    # Process the paper
    paper = processor.process_file(Path(input_file))

    # Convert to target format
    if to == "markdown":
        content = paper.to_markdown()
        ext = ".md"
    elif to == "latex":
        content = paper.to_latex()
        ext = ".tex"
    else:
        content = paper.to_text()
        ext = ".txt"

    # Save output
    if output:
        output_path = Path(output)
    else:
        output_path = Path(input_file).with_suffix(ext)

    output_path.write_text(content, encoding="utf-8")
    console.print(f"[green] Converted file saved to {output_path}[/green]")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--output", "-o", type=click.Path(), help="Output file for summary"
)
@click.option(
    "--compression",
    "-r",
    type=float,
    default=0.25,
    help="Compression ratio (default: 0.25 for 25% summary)",
)
@click.pass_context
def summarize(ctx, input_file, output, compression):
    """Create a summary of a single paper."""
    processor = PaperProcessor(config=ctx.obj.get("config", {}))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(f"Creating summary for {input_file}...", total=None)

        try:
            # Extract paper content
            paper = processor.process_file(Path(input_file))

            # Create summary
            summary = processor.create_summary(
                paper, compression_ratio=compression
            )

            # Format output
            summary_content = summary.to_markdown()

            # Save or print
            if output:
                Path(output).write_text(summary_content, encoding="utf-8")
                console.print(f"[green] Summary saved to {output}[/green]")
            else:
                console.print(summary_content)

        except Exception as e:
            console.print(f"[red]Error creating summary: {str(e)}[/red]")
            raise


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    help="Output directory for summaries (default: input_dir/summaries)",
)
@click.option(
    "--pattern",
    "-p",
    default="*.html",
    help="File pattern to match (use 'all_formats' for *.{html,htm,pdf,tex,xml})",
)
@click.option(
    "--compression",
    "-r",
    type=float,
    default=0.25,
    help="Compression ratio (default: 0.25 for 25% summary)",
)
@click.option(
    "--parallel", "-P", is_flag=True, help="Process files in parallel"
)
@click.option(
    "--skip-existing",
    "-s",
    is_flag=True,
    help="Skip files that already have summaries",
)
@click.option("--debug", "-d", is_flag=True, help="Enable debug output")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be processed without actually doing it",
)
@click.option(
    "--retry-failed",
    "-r",
    is_flag=True,
    default=True,
    help="Retry failed files with longer timeout (default: True)",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=60,
    help="Timeout per file in seconds (default: 60)",
)
@click.pass_context
def summarize_folder(
    ctx,
    input_dir,
    output_dir,
    pattern,
    compression,
    parallel,
    skip_existing,
    debug,
    dry_run,
    retry_failed,
    timeout,
):
    """Create summaries for all papers in a folder."""
    input_path = Path(input_dir)

    # If no output directory specified, create it relative to input directory
    if output_dir is None:
        output_path = input_path / "summaries"
    else:
        output_path = Path(output_dir)

    output_path.mkdir(parents=True, exist_ok=True)

    # Find all matching files
    files = _get_files_from_pattern(input_path, pattern)

    if debug:
        console.print(
            f"[cyan]Debug: Found {len(files)} files matching pattern '{pattern}'[/cyan]"
        )
        for f in files[:10]:  # Show first 10 files
            console.print(f"  - {f.name} ({f.suffix})")
        if len(files) > 10:
            console.print(f"  ... and {len(files) - 10} more files")

    console.print(f"[bold]Found {len(files)} files to summarize[/bold]")

    if not files:
        console.print("[yellow]No files found matching the pattern![/yellow]")
        return

    # Filter out files that already have summaries if skip_existing is enabled
    if skip_existing:
        files_to_process = []
        skipped_count = 0

        for file_path in files:
            summary_file = output_path / f"{file_path.stem}_summary.md"
            if summary_file.exists():
                if debug:
                    console.print(
                        f"[yellow]Debug: Skipping {file_path.name} - summary exists[/yellow]"
                    )
                skipped_count += 1
            else:
                files_to_process.append(file_path)

        files = files_to_process
        if skipped_count > 0:
            console.print(
                f"[yellow]Skipped {skipped_count} files with existing summaries[/yellow]"
            )

        if not files:
            console.print(
                "[green]All files already have summaries! Nothing to process.[/green]"
            )
            return

    if dry_run:
        console.print(
            f"[blue]Dry run mode - would process {len(files)} files:[/blue]"
        )
        for file_path in files:
            summary_file = output_path / f"{file_path.stem}_summary.md"
            console.print(f"  {file_path.name} -> {summary_file.name}")
        return

    processor = PaperProcessor(config=ctx.obj.get("config", {}))

    def process_and_summarize(file_path):
        try:
            if debug:
                console.print(
                    f"[cyan]Debug: Processing {file_path.name} ({file_path.suffix})[/cyan]"
                )

            # Extract paper content
            paper = processor.process_file(file_path)

            if debug:
                console.print(
                    f"[cyan]Debug: Extracted {len(paper.sections)} sections, {paper.word_count} words[/cyan]"
                )

            # Create summary
            if debug:
                console.print(
                    f"[cyan]Debug: Creating summary with compression ratio {compression} ({compression * 100}%)[/cyan]"
                )
            summary = processor.create_summary(
                paper, compression_ratio=compression
            )

            if debug:
                summary_word_count = len(summary.summary_content.split())
                console.print(
                    f"[cyan]Debug: Created summary with {summary_word_count} words (compression: {compression * 100}%)[/cyan]"
                )

            # Save summary as markdown
            output_file = output_path / f"{file_path.stem}_summary.md"
            summary_content = summary.to_markdown()
            output_file.write_text(summary_content, encoding="utf-8")

            if debug:
                # Calculate compression ratio based on extracted content vs summary
                # Use the markdown content size as the base for comparison
                extracted_content = paper.to_markdown()
                extracted_size = len(extracted_content.encode("utf-8"))
                summary_size = len(summary_content.encode("utf-8"))
                compression_ratio = (summary_size / extracted_size) * 100

                console.print(
                    f"[cyan]Debug: Content size - Extracted: {extracted_size / 1024:.1f}KB, Summary: {summary_size / 1024:.1f}KB, Ratio: {compression_ratio:.1f}%[/cyan]"
                )

                # Also show word count compression
                summary_words = len(summary_content.split())
                word_compression = (summary_words / paper.word_count) * 100
                console.print(
                    f"[cyan]Debug: Word count - Original: {paper.word_count}, Summary: {summary_words}, Ratio: {word_compression:.1f}%[/cyan]"
                )

                # Warn if compression is too aggressive
                if compression_ratio < 10:
                    console.print(
                        f"[yellow]Warning: Compression ratio {compression_ratio:.1f}% is below target (10-25%)[/yellow]"
                    )
                elif compression_ratio > 25:
                    console.print(
                        f"[yellow]Warning: Compression ratio {compression_ratio:.1f}% is above target (10-25%)[/yellow]"
                    )

            return file_path, True, None
        except Exception as e:
            if debug:
                import traceback

                console.print(
                    f"[red]Debug: Full error for {file_path.name}:[/red]"
                )
                console.print(f"[red]{traceback.format_exc()}[/red]")
            return file_path, False, str(e)

    # Process files
    with Progress(console=console) as progress:
        task = progress.add_task(
            "[cyan]Creating summaries...", total=len(files)
        )

        if parallel:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=4
            ) as executor:
                futures = {
                    executor.submit(process_and_summarize, f): f for f in files
                }
                for future in concurrent.futures.as_completed(futures):
                    file_path, success, error = future.result()
                    if success:
                        console.print(f"[green][/green] {file_path.name}")
                    else:
                        if debug:
                            console.print(
                                f"[red][/red] {file_path.name}: {error}"
                            )
                        else:
                            console.print(
                                f"[red][/red] {file_path.name}: {str(error)[:100]}..."
                            ) if len(str(error)) > 100 else console.print(
                                f"[red][/red] {file_path.name}: {error}"
                            )
                    progress.advance(task)
        else:
            for file_path in files:
                file_path, success, error = process_and_summarize(file_path)
                if success:
                    console.print(f"[green][/green] {file_path.name}")
                else:
                    if debug:
                        console.print(f"[red][/red] {file_path.name}: {error}")
                    else:
                        console.print(
                            f"[red][/red] {file_path.name}: {str(error)[:100]}..."
                        ) if len(str(error)) > 100 else console.print(
                            f"[red][/red] {file_path.name}: {error}"
                        )
                progress.advance(task)

    console.print(
        f"\n[bold green]Summary creation complete! Summaries saved to {output_path}[/bold green]"
    )


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.pass_context
def info(ctx, input_file):
    """Show information about a paper."""
    processor = PaperProcessor(config=ctx.obj.get("config", {}))

    console.print(f"[bold blue]Analyzing {input_file}...[/bold blue]\n")

    paper = processor.process_file(Path(input_file))

    # Display paper information
    console.print(f"[bold]Title:[/bold] {paper.title or 'Not found'}")
    console.print(
        f"[bold]Authors:[/bold] {', '.join(paper.authors) if paper.authors else 'Not found'}"
    )
    console.print(
        f"[bold]Abstract:[/bold] {'Found' if paper.abstract else 'Not found'}"
    )
    console.print(f"[bold]Sections:[/bold] {len(paper.sections)}")
    console.print(f"[bold]References:[/bold] {len(paper.references)}")
    console.print(f"[bold]Word count:[/bold] {paper.word_count:,}")

    if paper.sections:
        console.print("\n[bold]Section breakdown:[/bold]")
        for section in paper.sections:
            console.print(f"  • {section.title}: {section.word_count:,} words")


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
