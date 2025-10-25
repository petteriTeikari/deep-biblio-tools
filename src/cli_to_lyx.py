"""CLI for converting files to LyX format."""

from pathlib import Path

import click

from src.converters.to_lyx import MarkdownToLyxConverter, TexToLyxConverter


@click.group()
def cli():
    """Convert various formats to LyX."""
    pass


@cli.command()
@click.argument("tex_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Output LyX file (defaults to same name with .lyx extension)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    help="Output directory for generated files",
)
@click.option(
    "--roundtrip",
    is_flag=True,
    help="Use roundtrip algorithm (preserves more TeX constructs)",
)
@click.option(
    "--noweb", is_flag=True, help="Import as noweb (literate programming) file"
)
def from_tex(
    tex_file: Path,
    output: Path | None,
    output_dir: Path | None,
    roundtrip: bool,
    noweb: bool,
):
    """Convert TeX/LaTeX file to LyX format."""
    try:
        converter = TexToLyxConverter(output_dir=output_dir)

        if roundtrip or noweb:
            lyx_file = converter.convert_with_options(
                tex_file=tex_file,
                output_file=output,
                roundtrip=roundtrip,
                noweb=noweb,
            )
        else:
            lyx_file = converter.convert(tex_file, output)

        click.echo(f"Successfully converted to: {lyx_file}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("md_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Output LyX file (defaults to same name with .lyx extension)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    help="Output directory for generated files",
)
@click.option(
    "--simple",
    is_flag=True,
    help="Use simple conversion (faster but less features)",
)
@click.option("--no-citations", is_flag=True, help="Skip citation processing")
@click.option(
    "--no-concept-boxes", is_flag=True, help="Skip concept box processing"
)
@click.option(
    "--single-column",
    is_flag=True,
    help="Use single-column layout instead of two-column",
)
def from_markdown(
    md_file: Path,
    output: Path | None,
    output_dir: Path | None,
    simple: bool,
    no_citations: bool,
    no_concept_boxes: bool,
    single_column: bool,
):
    """Convert Markdown file to LyX format."""
    try:
        converter = MarkdownToLyxConverter(output_dir=output_dir)

        if simple:
            lyx_file = converter.convert_simple(md_file, output)
        else:
            lyx_file = converter.convert_advanced(
                md_file=md_file,
                output_file=output,
                process_citations=not no_citations,
                process_concept_boxes=not no_concept_boxes,
                two_column=not single_column,
            )

        click.echo(f"Successfully converted to: {lyx_file}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument(
    "files",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    help="Output directory for generated files",
)
@click.option(
    "--simple", is_flag=True, help="Use simple conversion for Markdown files"
)
def batch(files: tuple[Path, ...], output_dir: Path | None, simple: bool):
    """Convert multiple files to LyX format."""
    tex_files = []
    md_files = []

    # Sort files by type
    for file in files:
        if file.suffix.lower() in [".tex", ".latex"]:
            tex_files.append(file)
        elif file.suffix.lower() in [".md", ".markdown"]:
            md_files.append(file)
        else:
            click.echo(f"Warning: Skipping unsupported file: {file}", err=True)

    # Convert TeX files
    if tex_files:
        tex_converter = TexToLyxConverter(output_dir=output_dir)
        click.echo(f"\nConverting {len(tex_files)} TeX files...")
        for tex_file in tex_files:
            try:
                lyx_file = tex_converter.convert(tex_file)
                click.echo(f"  [OK] {tex_file} -> {lyx_file}")
            except Exception as e:
                click.echo(f"  [FAIL] {tex_file}: {e}", err=True)

    # Convert Markdown files
    if md_files:
        md_converter = MarkdownToLyxConverter(output_dir=output_dir)
        click.echo(f"\nConverting {len(md_files)} Markdown files...")
        results = md_converter.batch_convert(md_files, simple=simple)
        for md_file, lyx_file in results.items():
            if lyx_file:
                click.echo(f"  [OK] {md_file} -> {lyx_file}")
            else:
                click.echo(f"  [FAIL] {md_file}: Conversion failed", err=True)


if __name__ == "__main__":
    cli()
