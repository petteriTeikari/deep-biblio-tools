"""Report generation utilities."""

from datetime import datetime

from ..models.citation import ValidationResult


def generate_report(
    results: list[ValidationResult], format: str = "markdown"
) -> str:
    """Generate validation report in specified format."""
    if format == "markdown":
        return generate_markdown_report(results)
    elif format == "json":
        import json

        return json.dumps([r.to_dict() for r in results], indent=2)
    elif format == "html":
        return generate_html_report(results)
    else:
        raise ValueError(f"Unsupported format: {format}")


def generate_markdown_report(results: list[ValidationResult]) -> str:
    """Generate markdown validation report."""
    total = len(results)
    valid = sum(1 for r in results if r.is_valid)
    invalid = total - valid

    lines = [
        "# Citation Validation Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        f"- Total citations: {total}",
        f"- Valid: {valid} ({valid / total * 100:.1f}%)",
        f"- Invalid: {invalid} ({invalid / total * 100:.1f}%)",
        "",
    ]

    # Group by validation source
    by_source = {}
    for result in results:
        if result.is_valid and result.source:
            by_source.setdefault(result.source, 0)
            by_source[result.source] += 1

    if by_source:
        lines.extend(["## Validation Sources", ""])
        for source, count in sorted(by_source.items()):
            lines.append(f"- {source}: {count} citations")
        lines.append("")

    # List invalid citations
    invalid_results = [r for r in results if not r.is_valid]
    if invalid_results:
        lines.extend(["## Invalid Citations", ""])

        for result in invalid_results:
            lines.append(f"### {result.citation.key}")
            if result.citation.line_number:
                lines.append(
                    f"- **Location:** Line {result.citation.line_number}"
                )
            lines.append(f"- **Text:** `{result.citation.text}`")

            if result.issues:
                lines.append("- **Issues:**")
                for issue in result.issues:
                    lines.append(f"  - {issue}")

            if result.suggestions:
                lines.append("- **Suggestions:**")
                for suggestion in result.suggestions:
                    lines.append(f"  - {suggestion}")

            lines.append("")

    return "\n".join(lines)


def generate_html_report(results: list[ValidationResult]) -> str:
    """Generate HTML validation report."""
    total = len(results)
    valid = sum(1 for r in results if r.is_valid)
    invalid = total - valid

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Citation Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .summary {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .valid {{ color: green; }}
        .invalid {{ color: red; }}
        .citation {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
        .issue {{ color: red; }}
        .suggestion {{ color: blue; }}
    </style>
</head>
<body>
    <h1>Citation Validation Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <ul>
            <li>Total citations: {total}</li>
            <li class="valid">Valid: {valid} ({valid / total * 100:.1f}%)</li>
            <li class="invalid">Invalid: {invalid} ({invalid / total * 100:.1f}%)</li>
        </ul>
    </div>
"""

    invalid_results = [r for r in results if not r.is_valid]
    if invalid_results:
        html += "\n    <h2>Invalid Citations</h2>\n"

        for result in invalid_results:
            html += f"""    <div class="citation">
        <h3>{result.citation.key}</h3>
        <p><strong>Text:</strong> <code>{result.citation.text}</code></p>
"""

            if result.citation.line_number:
                html += f"        <p><strong>Location:</strong> Line {result.citation.line_number}</p>\n"

            if result.issues:
                html += "        <p class='issue'><strong>Issues:</strong></p>\n        <ul>\n"
                for issue in result.issues:
                    html += f"            <li>{issue}</li>\n"
                html += "        </ul>\n"

            if result.suggestions:
                html += "        <p class='suggestion'><strong>Suggestions:</strong></p>\n        <ul>\n"
                for suggestion in result.suggestions:
                    html += f"            <li>{suggestion}</li>\n"
                html += "        </ul>\n"

            html += "    </div>\n"

    html += """</body>
</html>"""

    return html
