"""CLI interface for quality-guardian."""

import concurrent.futures
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from .core.guardian import QualityGuardian
from .utils.config import load_config

console = Console()


@click.group()
@click.version_option()
@click.option(
    "--config", "-c", type=click.Path(), help="Path to configuration file"
)
@click.pass_context
def cli(ctx, config):
    """Ensure high-quality academic writing with automated checks."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config) if config else {}


@cli.command()
@click.argument("document", type=click.Path(exists=True))
@click.option(
    "--style",
    "-s",
    type=click.Choice(["apa", "ieee", "chicago", "mla"]),
    help="Style guide to use",
)
@click.option(
    "--output", "-o", type=click.Path(), help="Output file for fixed document"
)
@click.option("--report", "-r", type=click.Path(), help="Save detailed report")
@click.pass_context
def check(ctx, document, style, output, report):
    """Check document quality and optionally fix issues."""
    guardian = QualityGuardian(config=ctx.obj.get("config", {}))

    console.print(f"[bold blue]Checking {document}...[/bold blue]")

    # Run quality checks
    doc_path = Path(document)
    result = guardian.check_document(doc_path, style_guide=style)

    # Display summary
    _display_summary(result)

    # Apply fixes if output specified
    if output:
        fixed_content = guardian.apply_fixes(doc_path, result)
        Path(output).write_text(fixed_content, encoding="utf-8")
        console.print(f"\n[green] Fixed document saved to {output}[/green]")

    # Save report if requested
    if report:
        report_content = result.to_html()
        Path(report).write_text(report_content, encoding="utf-8")
        console.print(f"[green] Report saved to {report}[/green]")


@cli.command()
@click.argument("document", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    required=True,
    help="Output path for analysis report",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["html", "json", "markdown"]),
    default="html",
    help="Report format",
)
@click.option(
    "--focus",
    type=click.Choice(
        ["all", "grammar", "style", "readability", "consistency"]
    ),
    default="all",
    help="Analysis focus area",
)
@click.pass_context
def analyze(ctx, document, output, format, focus):
    """Perform detailed quality analysis."""
    guardian = QualityGuardian(config=ctx.obj.get("config", {}))

    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Analyzing document...", total=5)

        # Run analysis
        doc_path = Path(document)
        result = guardian.analyze_document(
            doc_path,
            focus=focus,
            progress_callback=lambda: progress.advance(task),
        )

        # Generate report
        if format == "html":
            report_content = result.to_html()
        elif format == "json":
            import json

            report_content = json.dumps(result.to_dict(), indent=2)
        else:
            report_content = result.to_markdown()

        # Save report
        Path(output).write_text(report_content, encoding="utf-8")

    console.print(f"\n[green] Analysis report saved to {output}[/green]")

    # Show summary
    _display_analysis_summary(result)


@cli.command()
@click.argument("document", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    required=True,
    help="Output path for fixed document",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Interactive mode - approve each fix",
)
@click.option(
    "--types",
    "-t",
    multiple=True,
    type=click.Choice(["grammar", "spelling", "style", "consistency"]),
    help="Types of fixes to apply",
)
@click.pass_context
def fix(ctx, document, output, interactive, types):
    """Fix quality issues in document."""
    guardian = QualityGuardian(config=ctx.obj.get("config", {}))

    console.print(f"[bold blue]Fixing issues in {document}...[/bold blue]")

    # Check document first
    doc_path = Path(document)
    result = guardian.check_document(doc_path)

    # Filter issues by type if specified
    if types:
        result = guardian.filter_issues(result, types)

    # Apply fixes
    if interactive:
        fixed_content = guardian.apply_fixes_interactive(
            doc_path, result, console
        )
    else:
        fixed_content = guardian.apply_fixes(doc_path, result)

    # Save fixed document
    Path(output).write_text(fixed_content, encoding="utf-8")

    console.print(f"\n[green] Fixed document saved to {output}[/green]")
    console.print(f"[dim]Applied {result.fixes_applied} fixes[/dim]")


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    required=True,
    help="Output directory for reports",
)
@click.option("--pattern", "-p", default="*.md", help="File pattern to match")
@click.option(
    "--parallel", "-P", is_flag=True, help="Process files in parallel"
)
@click.pass_context
def batch_check(ctx, input_dir, output_dir, pattern, parallel):
    """Check multiple documents in batch."""
    guardian = QualityGuardian(config=ctx.obj.get("config", {}))

    # Find files
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    files = list(input_path.glob(pattern))
    console.print(f"[bold]Found {len(files)} files to check[/bold]")

    def check_file(file_path):
        try:
            result = guardian.check_document(file_path)
            report_path = output_path / f"{file_path.stem}_quality.html"
            report_path.write_text(result.to_html(), encoding="utf-8")
            return file_path, True, result.overall_score
        except Exception as e:
            return file_path, False, str(e)

    # Process files
    results = []
    with Progress(console=console) as progress:
        task = progress.add_task(
            "[cyan]Checking documents...", total=len(files)
        )

        if parallel:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=4
            ) as executor:
                futures = {executor.submit(check_file, f): f for f in files}
                for future in concurrent.futures.as_completed(futures):
                    file_path, success, score_or_error = future.result()
                    results.append((file_path, success, score_or_error))
                    progress.advance(task)
        else:
            for file_path in files:
                result = check_file(file_path)
                results.append(result)
                progress.advance(task)

    # Display summary
    console.print("\n[bold]Batch Check Summary:[/bold]")
    successful = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]

    if successful:
        avg_score = sum(r[2] for r in successful) / len(successful)
        console.print(
            f"[green] Checked {len(successful)} documents successfully[/green]"
        )
        console.print(f"[dim]Average quality score: {avg_score:.1f}/100[/dim]")

    if failed:
        console.print(f"[red] Failed to check {len(failed)} documents[/red]")


@cli.command()
@click.argument("document", type=click.Path(exists=True))
@click.option(
    "--ai-powered", is_flag=True, help="Use AI for advanced suggestions"
)
@click.option(
    "--focus",
    type=click.Choice(["clarity", "conciseness", "flow", "academic-tone"]),
    help="Focus area for suggestions",
)
@click.pass_context
def suggest(ctx, document, ai_powered, focus):
    """Generate improvement suggestions."""
    guardian = QualityGuardian(config=ctx.obj.get("config", {}))

    console.print(
        f"[bold blue]Generating suggestions for {document}...[/bold blue]"
    )

    # Generate suggestions
    doc_path = Path(document)
    suggestions = guardian.generate_suggestions(
        doc_path, use_ai=ai_powered, focus=focus
    )

    # Display suggestions
    if not suggestions:
        console.print("[green] No major improvements needed![/green]")
    else:
        console.print(
            f"\n[bold]Found {len(suggestions)} improvement suggestions:[/bold]\n"
        )

        for i, suggestion in enumerate(suggestions, 1):
            console.print(f"[cyan]{i}. {suggestion['type'].upper()}[/cyan]")
            console.print(f"   Location: {suggestion['location']}")
            console.print(f"   Issue: {suggestion['issue']}")
            console.print(
                f"   Suggestion: [green]{suggestion['suggestion']}[/green]"
            )
            console.print()


def _display_summary(result):
    """Display check results summary."""
    # Create summary table
    table = Table(title="Quality Check Summary")
    table.add_column("Category", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Issues", justify="right")

    for category in ["Grammar", "Style", "Readability", "Consistency"]:
        score = result.scores.get(category.lower(), 0)
        issues = result.issue_counts.get(category.lower(), 0)

        score_style = (
            "green" if score >= 80 else "yellow" if score >= 60 else "red"
        )
        table.add_row(
            category,
            f"[{score_style}]{score:.0f}/100[/{score_style}]",
            str(issues),
        )

    console.print(table)

    # Overall score
    overall_style = (
        "green"
        if result.overall_score >= 80
        else "yellow"
        if result.overall_score >= 60
        else "red"
    )
    console.print(
        f"\n[bold]Overall Score: [{overall_style}]{result.overall_score:.0f}/100[/{overall_style}][/bold]"
    )

    # Top issues
    if result.top_issues:
        console.print("\n[bold]Top Issues:[/bold]")
        for issue in result.top_issues[:5]:
            console.print(f"  • {issue}")


def _display_analysis_summary(result):
    """Display analysis summary."""
    console.print("\n[bold]Document Analysis Summary:[/bold]")

    # Basic metrics
    console.print(f"\nWord count: {result.metrics['word_count']:,}")
    console.print(f"Sentence count: {result.metrics['sentence_count']:,}")
    console.print(
        f"Average sentence length: {result.metrics['avg_sentence_length']:.1f} words"
    )
    console.print(f"Paragraph count: {result.metrics['paragraph_count']}")

    # Readability
    console.print("\n[bold]Readability Scores:[/bold]")
    console.print(
        f"  Flesch Reading Ease: {result.metrics['flesch_reading_ease']:.1f}"
    )
    console.print(
        f"  Flesch-Kincaid Grade: {result.metrics['flesch_kincaid_grade']:.1f}"
    )

    # Style metrics
    console.print("\n[bold]Style Metrics:[/bold]")
    console.print(
        f"  Passive voice: {result.metrics['passive_voice_percentage']:.1f}%"
    )
    console.print(
        f"  Complex sentences: {result.metrics['complex_sentence_percentage']:.1f}%"
    )


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
