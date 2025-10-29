"""CLI for markdown knowledge base validation.

Usage:
    validate-markdown-kb <path>             # Validate file or directory
    validate-markdown-kb <path> --output report.txt
    validate-markdown-kb <path> --fail-on-issues

This tool validates markdown files BEFORE they enter the knowledge base.
It is independent of any conversion process - it checks source quality.
"""

import sys
from pathlib import Path
import click
from .url_validator import MarkdownKBValidator, generate_report


@click.command()
@click.argument('path', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--output',
    type=click.Path(path_type=Path),
    help='Write report to file instead of stdout'
)
@click.option(
    '--fail-on-issues/--no-fail',
    default=True,
    help='Exit with error code if issues found (default: True for CI/CD)'
)
@click.option(
    '--network-checks/--no-network',
    default=False,
    help='Enable expensive network validation (default: False for speed)'
)
@click.option(
    '-v', '--verbose',
    is_flag=True,
    help='Show detailed progress'
)
def validate(
    path: Path,
    output: Path | None,
    fail_on_issues: bool,
    network_checks: bool,
    verbose: bool
):
    """Validate markdown knowledge base quality.

    PATH can be a file or directory. If directory, all .md files are validated recursively.

    Examples:

        # Validate single file
        validate-markdown-kb /path/to/paper.md

        # Validate entire knowledge base
        validate-markdown-kb /path/to/kb/

        # Generate report file
        validate-markdown-kb /path/to/kb/ --output report.txt

        # Allow issues (don't fail CI/CD)
        validate-markdown-kb /path/to/kb/ --no-fail
    """
    validator = MarkdownKBValidator(enable_network_checks=network_checks)

    # Collect all markdown files
    if path.is_file():
        files = [path]
    else:
        files = list(path.rglob('*.md'))

    if verbose:
        click.echo(f"Validating {len(files)} markdown file(s)...")
        if network_checks:
            click.echo("⚠️  Network checks enabled (slow)")

    all_issues = []
    total_citations = 0

    for file in files:
        if verbose:
            click.echo(f"  Checking {file.name}...")

        issues = validator.validate_file(file)
        all_issues.extend(issues)

        # Count citations (approximate)
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            total_citations += len(validator._extract_citations(content))

    # Generate report
    report = generate_report(all_issues, total_citations)

    # Output report
    if output:
        output.write_text(report)
        click.echo(f"\n📄 Report written to: {output}")
        # Also show summary on stdout
        click.echo(f"\nTotal citations: {total_citations}")
        click.echo(f"Issues found: {len(all_issues)}")
    else:
        click.echo(report)

    # Exit code
    if all_issues and fail_on_issues:
        critical = sum(1 for i in all_issues if i.severity == "CRITICAL")
        click.echo(f"\n❌ Found {len(all_issues)} issues ({critical} CRITICAL)", err=True)
        click.echo("❌ Knowledge base quality check FAILED", err=True)
        click.echo("💡 Fix CRITICAL issues before committing", err=True)
        sys.exit(1)
    elif all_issues:
        click.echo(f"\n⚠️  Found {len(all_issues)} issues (not failing due to --no-fail)")
        sys.exit(0)
    else:
        click.echo(f"\n✅ Validation complete: All {total_citations} citations are valid")
        sys.exit(0)


if __name__ == '__main__':
    validate()
