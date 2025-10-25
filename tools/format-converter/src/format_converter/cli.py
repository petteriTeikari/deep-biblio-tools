"""CLI interface for format-converter."""

import concurrent.futures
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress

from .core.converter import FormatConverter
from .utils.config import load_config

console = Console()

# Supported format mappings
FORMAT_EXTENSIONS = {
    "markdown": [".md", ".markdown"],
    "latex": [".tex"],
    "bibtex": [".bib"],
    "html": [".html", ".htm"],
    "docx": [".docx"],
    "rst": [".rst"],
    "json": [".json"],
}

FORMAT_NAMES = {
    "md": "markdown",
    "tex": "latex",
    "bib": "bibtex",
    "htm": "html",
    "doc": "docx",
    "word": "docx",
}


@click.group()
@click.version_option()
@click.option(
    "--config", "-c", type=click.Path(), help="Path to configuration file"
)
@click.pass_context
def cli(ctx, config):
    """Convert between academic document formats with citation preservation."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config) if config else {}


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--to",
    "-t",
    required=True,
    help="Target format (latex, markdown, html, docx, etc.)",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--template", help="Template to use for conversion")
@click.option(
    "--citation-style",
    type=click.Choice(["author-year", "numeric", "alpha"]),
    default="author-year",
    help="Citation style",
)
@click.option(
    "--bibliography",
    "-b",
    type=click.Path(exists=True),
    help="Bibliography file to use",
)
@click.pass_context
def convert(
    ctx, input_file, to, output, template, citation_style, bibliography
):
    """Convert a single document between formats."""
    converter = FormatConverter(config=ctx.obj.get("config", {}))

    # Normalize format names
    to_format = FORMAT_NAMES.get(to.lower(), to.lower())

    input_path = Path(input_file)

    # Determine output path
    if output:
        output_path = Path(output)
    else:
        # Auto-generate output filename
        output_ext = FORMAT_EXTENSIONS.get(to_format, [f".{to_format}"])[0]
        output_path = input_path.with_suffix(output_ext)

    console.print(
        f"[bold blue]Converting {input_file} to {to_format}...[/bold blue]"
    )

    try:
        # Perform conversion
        converter.convert_file(
            input_path,
            output_path,
            to_format,
            template=template,
            citation_style=citation_style,
            bibliography=Path(bibliography) if bibliography else None,
        )

        console.print(
            f"[green] Converted successfully to {output_path}[/green]"
        )

    except Exception as e:
        console.print(f"[red] Conversion failed: {str(e)}[/red]")
        raise click.ClickException(str(e))


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--from",
    "-f",
    "from_format",
    required=True,
    help="Source format (markdown, latex, etc.)",
)
@click.option("--to", "-t", required=True, help="Target format")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    required=True,
    help="Output directory",
)
@click.option(
    "--parallel", "-P", is_flag=True, help="Process files in parallel"
)
@click.option("--template", help="Template to use for conversion")
@click.pass_context
def batch(ctx, input_dir, from_format, to, output_dir, parallel, template):
    """Convert multiple documents in batch."""
    converter = FormatConverter(config=ctx.obj.get("config", {}))

    # Normalize format names
    from_format = FORMAT_NAMES.get(from_format.lower(), from_format.lower())
    to_format = FORMAT_NAMES.get(to.lower(), to.lower())

    # Find input files
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Get extensions for source format
    source_exts = FORMAT_EXTENSIONS.get(from_format, [f".{from_format}"])
    files = []
    for ext in source_exts:
        files.extend(input_path.glob(f"*{ext}"))

    console.print(
        f"[bold]Found {len(files)} {from_format} files to convert[/bold]"
    )

    def convert_single(file_path):
        try:
            output_ext = FORMAT_EXTENSIONS.get(to_format, [f".{to_format}"])[0]
            output_file = output_path / file_path.with_suffix(output_ext).name

            converter.convert_file(
                file_path, output_file, to_format, template=template
            )
            return file_path, True, None
        except Exception as e:
            return file_path, False, str(e)

    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Converting files...", total=len(files))

        if parallel:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=4
            ) as executor:
                futures = {executor.submit(convert_single, f): f for f in files}
                for future in concurrent.futures.as_completed(futures):
                    file_path, success, error = future.result()
                    if success:
                        console.print(f"[green][/green] {file_path.name}")
                    else:
                        console.print(f"[red][/red] {file_path.name}: {error}")
                    progress.advance(task)
        else:
            for file_path in files:
                file_path, success, error = convert_single(file_path)
                if success:
                    console.print(f"[green][/green] {file_path.name}")
                else:
                    console.print(f"[red][/red] {file_path.name}: {error}")
                progress.advance(task)

    console.print("\n[bold green]Batch conversion complete![/bold green]")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--output", "-o", type=click.Path(), help="Output bibliography file"
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["bibtex", "biblatex", "json"]),
    default="bibtex",
    help="Bibliography format",
)
@click.pass_context
def extract_bib(ctx, input_file, output, format):
    """Extract bibliography from a document."""
    converter = FormatConverter(config=ctx.obj.get("config", {}))

    input_path = Path(input_file)

    if output:
        output_path = Path(output)
    else:
        ext = ".bib" if format in ["bibtex", "biblatex"] else ".json"
        output_path = input_path.with_suffix(ext)

    console.print(
        f"[bold blue]Extracting bibliography from {input_file}...[/bold blue]"
    )

    try:
        references = converter.extract_bibliography(input_path)

        if format == "json":
            import json

            output_path.write_text(
                json.dumps(references, indent=2), encoding="utf-8"
            )
        else:
            # Format as BibTeX
            bib_content = converter.format_bibliography(references, format)
            output_path.write_text(bib_content, encoding="utf-8")

        console.print(
            f"[green] Bibliography extracted to {output_path}[/green]"
        )
        console.print(f"[dim]Found {len(references)} references[/dim]")

    except Exception as e:
        console.print(f"[red] Extraction failed: {str(e)}[/red]")
        raise click.ClickException(str(e))


@cli.command()
@click.pass_context
def list_formats(ctx):
    """List supported formats and conversions."""
    console.print("[bold]Supported formats:[/bold]\n")

    formats = [
        ("Markdown", "md, markdown", "", ""),
        ("LaTeX", "tex, latex", "", ""),
        ("BibTeX", "bib, bibtex", "", ""),
        ("HTML", "html, htm", "", ""),
        ("Word", "docx", "", ""),
        ("reStructuredText", "rst", "", ""),
        ("JSON", "json", "", ""),
    ]

    # Create table
    from rich.table import Table

    table = Table(title="Format Support")
    table.add_column("Format", style="cyan")
    table.add_column("Extensions", style="green")
    table.add_column("Read", justify="center")
    table.add_column("Write", justify="center")

    for fmt, ext, read, write in formats:
        table.add_row(fmt, ext, read, write)

    console.print(table)

    console.print("\n[bold]Common conversions:[/bold]")
    console.print("• Markdown → LaTeX (preserves citations)")
    console.print("• LaTeX → Markdown (extracts structure)")
    console.print("• Any format → BibTeX (extracts references)")
    console.print("• Markdown → HTML (academic styling)")
    console.print("• LaTeX → Word (via pandoc)")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.pass_context
def info(ctx, input_file):
    """Show information about a document."""
    converter = FormatConverter(config=ctx.obj.get("config", {}))

    input_path = Path(input_file)
    console.print(f"[bold blue]Analyzing {input_file}...[/bold blue]\n")

    info = converter.analyze_document(input_path)

    console.print(f"[bold]Format:[/bold] {info.get('format', 'Unknown')}")
    console.print(f"[bold]Size:[/bold] {info.get('size', 0):,} bytes")
    console.print(f"[bold]Citations:[/bold] {info.get('citation_count', 0)}")
    console.print(f"[bold]References:[/bold] {info.get('reference_count', 0)}")

    if info.get("metadata"):
        console.print("\n[bold]Metadata:[/bold]")
        for key, value in info["metadata"].items():
            console.print(f"  {key}: {value}")

    if info.get("sections"):
        console.print(f"\n[bold]Sections:[/bold] {len(info['sections'])}")
        for section in info["sections"][:5]:
            console.print(f"  • {section}")
        if len(info["sections"]) > 5:
            console.print(f"  ... and {len(info['sections']) - 5} more")


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
