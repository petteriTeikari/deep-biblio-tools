"""CLI interface for literature-reviewer."""

import concurrent.futures
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core.reviewer import LiteratureReviewer
from .core.summarizer import Summarizer
from .utils.config import load_config

console = Console()


@click.group()
@click.version_option()
@click.option(
    "--config", "-c", type=click.Path(), help="Path to configuration file"
)
@click.pass_context
def cli(ctx, config):
    """Generate comprehensive literature reviews with smart summarization."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config) if config else {}


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option(
    "--compression",
    "-r",
    type=float,
    default=0.25,
    help="Compression ratio (default: 0.25 for 25% summary)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "latex", "json"]),
    default="markdown",
    help="Output format",
)
@click.pass_context
def summarize(ctx, input_file, output, compression, format):
    """Create a comprehensive summary of a single paper."""
    summarizer = Summarizer(config=ctx.obj.get("config", {}))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(f"Summarizing {input_file}...", total=None)

        # Create summary
        summary = summarizer.summarize_file(
            Path(input_file), compression_ratio=compression
        )

        # Format output
        if format == "markdown":
            output_content = summary.to_markdown()
        elif format == "latex":
            output_content = summary.to_latex()
        else:
            import json

            output_content = json.dumps(summary.to_dict(), indent=2)

        # Save or print
        if output:
            Path(output).write_text(output_content, encoding="utf-8")
            console.print(f"[green] Summary saved to {output}[/green]")
        else:
            console.print(output_content)


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    required=True,
    help="Output file for literature review",
)
@click.option("--theme", "-t", help="Research theme or topic")
@click.option("--context", help="Additional context for the review")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "latex", "json"]),
    default="markdown",
    help="Output format",
)
@click.pass_context
def review(ctx, input_dir, output, theme, context, format):
    """Generate a literature review from multiple papers."""
    reviewer = LiteratureReviewer(config=ctx.obj.get("config", {}))

    # Find all markdown files
    input_path = Path(input_dir)
    paper_files = list(input_path.glob("*.md"))

    console.print(f"[bold]Found {len(paper_files)} papers to review[/bold]")

    if not theme:
        theme = click.prompt("Please provide the research theme/topic")

    if not context:
        context = click.prompt(
            "How would you like the findings contextualized?",
            default="Provide a comprehensive academic review",
        )

    with Progress(console=console) as progress:
        task = progress.add_task(
            "[cyan]Generating literature review...", total=len(paper_files)
        )

        # Create review
        review_obj = reviewer.create_review(
            paper_files,
            theme=theme,
            context=context,
            progress_callback=lambda: progress.advance(task),
        )

        # Format output
        if format == "markdown":
            output_content = review_obj.to_markdown()
        elif format == "latex":
            output_content = review_obj.to_latex()
        else:
            import json

            output_content = json.dumps(review_obj.to_dict(), indent=2)

        # Save output
        Path(output).write_text(output_content, encoding="utf-8")
        console.print(f"\n[green] Literature review saved to {output}[/green]")


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    required=True,
    help="Output directory for summaries",
)
@click.option(
    "--compression",
    "-r",
    type=float,
    default=0.25,
    help="Compression ratio (default: 0.25)",
)
@click.option("--pattern", "-p", default="*.md", help="File pattern to match")
@click.option(
    "--parallel", "-P", is_flag=True, help="Process files in parallel"
)
@click.pass_context
def batch_summarize(ctx, input_dir, output_dir, compression, pattern, parallel):
    """Create summaries for multiple papers."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Find matching files
    files = list(input_path.glob(pattern))
    console.print(f"[bold]Found {len(files)} files to summarize[/bold]")

    summarizer = Summarizer(config=ctx.obj.get("config", {}))

    def process_file(file_path):
        try:
            summary = summarizer.summarize_file(
                file_path, compression_ratio=compression
            )
            output_file = output_path / f"{file_path.stem}_summary.md"
            output_file.write_text(summary.to_markdown(), encoding="utf-8")
            return file_path, True, None
        except Exception as e:
            return file_path, False, str(e)

    with Progress(console=console) as progress:
        task = progress.add_task(
            "[cyan]Summarizing papers...", total=len(files)
        )

        if parallel:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=4
            ) as executor:
                futures = {executor.submit(process_file, f): f for f in files}
                for future in concurrent.futures.as_completed(futures):
                    file_path, success, error = future.result()
                    if success:
                        console.print(f"[green][/green] {file_path.name}")
                    else:
                        console.print(f"[red][/red] {file_path.name}: {error}")
                    progress.advance(task)
        else:
            for file_path in files:
                file_path, success, error = process_file(file_path)
                if success:
                    console.print(f"[green][/green] {file_path.name}")
                else:
                    console.print(f"[red][/red] {file_path.name}: {error}")
                progress.advance(task)

    console.print("\n[bold green]Batch summarization complete![/bold green]")


@cli.command()
@click.argument("summary_file", type=click.Path(exists=True))
@click.pass_context
def analyze(ctx, summary_file):
    """Analyze a summary or review for quality metrics."""
    summarizer = Summarizer(config=ctx.obj.get("config", {}))

    console.print(f"[bold blue]Analyzing {summary_file}...[/bold blue]\n")

    # Read content
    content = Path(summary_file).read_text(encoding="utf-8")

    # Calculate metrics
    metrics = summarizer.analyze_summary(content)

    # Display results
    console.print("[bold]Summary Analysis:[/bold]")
    console.print(f"- Word count: {metrics['word_count']:,}")
    console.print(f"- Sentence count: {metrics['sentence_count']:,}")
    console.print(
        f"- Average sentence length: {metrics['avg_sentence_length']:.1f} words"
    )
    console.print(f"- Citation count: {metrics['citation_count']}")
    console.print(f"- Reference count: {metrics['reference_count']}")
    console.print(
        f"- Compression achieved: {metrics.get('compression_ratio', 'N/A')}"
    )

    if metrics.get("key_topics"):
        console.print("\n[bold]Key Topics:[/bold]")
        for topic in metrics["key_topics"][:10]:
            console.print(f"  • {topic}")


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
