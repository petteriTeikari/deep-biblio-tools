"""CLI interface for biblio-validator."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .core.matcher import CitationMatcher
from .core.validator import BibliographyValidator, CitationValidator
from .utils.config import load_config
from .utils.report import generate_report

console = Console()


@click.group()
@click.version_option()
@click.option(
    "--config", "-c", type=click.Path(), help="Path to configuration file"
)
@click.pass_context
def cli(ctx, config):
    """Professional citation validation tool for academic documents."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config) if config else {}


@cli.command()
@click.argument("document", type=click.Path(exists=True))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["md", "tex", "txt"]),
    help="Document format",
)
@click.option("--output", "-o", type=click.Path(), help="Output report path")
@click.option("--fix", is_flag=True, help="Apply automatic fixes")
@click.pass_context
def check(ctx, document, format, output, fix):
    """Validate citations in a document."""
    console.print(
        f"[bold blue]Validating citations in {document}...[/bold blue]"
    )

    validator = CitationValidator(config=ctx.obj.get("config", {}))
    results = validator.validate_document(Path(document), format=format)

    # Display results
    table = Table(title="Citation Validation Results")
    table.add_column("Citation", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Issues", style="red")

    for result in results:
        status = "" if result.is_valid else ""
        issues = ", ".join(result.issues) if result.issues else "-"
        table.add_row(result.citation.key, status, issues)

    console.print(table)

    # Generate report if requested
    if output:
        report = generate_report(results, format="markdown")
        Path(output).write_text(report)
        console.print(f"[green]Report saved to {output}[/green]")

    # Apply fixes if requested
    if fix and any(not r.is_valid for r in results):
        console.print("[yellow]Applying automatic fixes...[/yellow]")
        fixed = validator.apply_fixes(results)
        console.print(f"[green]Fixed {fixed} citations[/green]")


@cli.command()
@click.argument("bibfile", type=click.Path(exists=True))
@click.option("--check-dois", is_flag=True, help="Validate DOIs")
@click.option("--check-urls", is_flag=True, help="Validate URLs")
@click.option("--output", "-o", type=click.Path(), help="Output report path")
@click.pass_context
def check_bib(ctx, bibfile, check_dois, check_urls, output):
    """Validate a BibTeX file."""
    console.print(
        f"[bold blue]Validating bibliography {bibfile}...[/bold blue]"
    )

    validator = BibliographyValidator(config=ctx.obj.get("config", {}))
    report = validator.validate_file(
        Path(bibfile), check_dois=check_dois, check_urls=check_urls
    )

    # Display summary
    console.print(f"[bold]Total entries:[/bold] {report.total_entries}")
    console.print(
        f"[bold green]Valid entries:[/bold green] {report.valid_entries}"
    )
    console.print(
        f"[bold red]Invalid entries:[/bold red] {report.invalid_entries}"
    )

    if report.issues:
        console.print("\n[bold red]Issues found:[/bold red]")
        for issue in report.issues[:10]:  # Show first 10 issues
            console.print(f"  • {issue}")
        if len(report.issues) > 10:
            console.print(f"  ... and {len(report.issues) - 10} more")

    # Save report if requested
    if output:
        Path(output).write_text(report.to_markdown())
        console.print(f"\n[green]Detailed report saved to {output}[/green]")


@cli.command()
@click.argument("document", type=click.Path(exists=True))
@click.argument("bibfile", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output report path")
@click.pass_context
def match(ctx, document, bibfile, output):
    """Match citations in document to bibliography entries."""
    console.print(
        "[bold blue]Matching citations to bibliography...[/bold blue]"
    )

    matcher = CitationMatcher(config=ctx.obj.get("config", {}))
    results = matcher.match_document_to_bib(Path(document), Path(bibfile))

    # Display results
    unmatched_citations = results.get("unmatched_citations", [])
    unused_entries = results.get("unused_entries", [])

    if unmatched_citations:
        console.print(
            f"\n[bold red]Unmatched citations ({len(unmatched_citations)}):[/bold red]"
        )
        for cite in unmatched_citations[:10]:
            console.print(f"  • {cite}")

    if unused_entries:
        console.print(
            f"\n[bold yellow]Unused bibliography entries ({len(unused_entries)}):[/bold yellow]"
        )
        for entry in unused_entries[:10]:
            console.print(f"  • {entry}")

    if not unmatched_citations and not unused_entries:
        console.print(
            "[bold green] All citations match bibliography entries![/bold green]"
        )

    # Save detailed report
    if output:
        report = matcher.generate_report(results)
        Path(output).write_text(report)
        console.print(f"\n[green]Detailed report saved to {output}[/green]")


@cli.command()
@click.argument("document", type=click.Path(exists=True))
@click.option(
    "--sources",
    "-s",
    multiple=True,
    type=click.Choice(["crossref", "pubmed", "arxiv", "all"]),
    default=["all"],
    help="Validation sources to use",
)
@click.option("--output", "-o", type=click.Path(), help="Output report path")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "json", "html"]),
    default="markdown",
    help="Report format",
)
@click.pass_context
def report(ctx, document, sources, output, format):
    """Generate comprehensive validation report."""
    console.print("[bold blue]Generating validation report...[/bold blue]")

    # Use all sources if 'all' is specified
    if "all" in sources:
        sources = ["crossref", "pubmed", "arxiv"]

    validator = CitationValidator(
        config=ctx.obj.get("config", {}), sources=list(sources)
    )

    results = validator.validate_document(Path(document))
    report = validator.generate_comprehensive_report(results, format=format)

    if output:
        Path(output).write_text(report)
        console.print(f"[green]Report saved to {output}[/green]")
    else:
        console.print("\n" + report)


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
