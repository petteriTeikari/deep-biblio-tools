"""LaTeX compilation log parsing helpers for end-to-end tests.

This module provides utilities for parsing LaTeX .log files to detect
compilation errors and warnings. All parsing uses string methods (NO REGEX)
per project policy (.claude/CLAUDE.md).

The goal is to fail tests EARLY if LaTeX compilation has issues, rather than
waiting to discover problems in the PDF output.
"""

from pathlib import Path

# ---------- Critical Error Detection ----------


def assert_no_critical_latex_errors(log_path: Path) -> None:
    """Fail fast if LaTeX log contains critical errors.

    Checks for patterns that indicate compilation failure or broken output:
    - "LaTeX Error" - Fatal compilation error
    - "Undefined citation" - Missing BibTeX entries (→ (?) in PDF)
    - "No file references.bbl" - BibTeX didn't run or failed
    - "Undefined control sequence" - Missing package or typo

    Args:
        log_path: Path to LaTeX .log file

    Raises:
        AssertionError: If any critical error pattern found

    Example:
        >>> assert_no_critical_latex_errors(Path("output/paper.log"))
        # Raises if compilation had errors
    """
    if not log_path.exists():
        raise AssertionError(f"LaTeX log file not found: {log_path}")

    log_text = log_path.read_text(encoding="utf-8", errors="ignore")

    # Define critical error patterns (NO REGEX - string matching)
    critical_patterns = [
        "LaTeX Error",
        "Undefined citation",
        "No file references.bbl",
        "Undefined control sequence",
        "! Emergency stop",
        "Fatal error occurred",
    ]

    found_errors = []

    for pattern in critical_patterns:
        # Use case-insensitive string search (NO REGEX)
        if pattern.lower() in log_text.lower():
            # Extract context around error for better diagnostics
            context = _extract_error_context(log_text, pattern)
            found_errors.append({"pattern": pattern, "context": context})

    if found_errors:
        error_summary = "\n\n".join(
            [
                f"Pattern '{err['pattern']}':\n{err['context']}"
                for err in found_errors
            ]
        )
        raise AssertionError(
            f"LaTeX log contains {len(found_errors)} critical error(s):\n\n{error_summary}"
        )


def _extract_error_context(
    log_text: str, pattern: str, context_lines: int = 3
) -> str:
    """Extract lines around error pattern for diagnostics.

    Args:
        log_text: Full LaTeX log content
        pattern: Error pattern to find
        context_lines: Number of lines to show before/after error

    Returns:
        Context snippet showing error location
    """
    lines = log_text.split("\n")
    pattern_lower = pattern.lower()

    # Find first occurrence of pattern
    for i, line in enumerate(lines):
        if pattern_lower in line.lower():
            # Extract context window
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            context_lines_list = lines[start:end]

            # Add line numbers for reference
            numbered = [
                f"  {j+1}: {line}"
                for j, line in enumerate(context_lines_list, start=start)
            ]
            return "\n".join(numbered)

    # Pattern found in log_text but not in individual lines
    # (e.g., spans multiple lines) - return first 200 chars after match
    idx = log_text.lower().find(pattern_lower)
    if idx != -1:
        return log_text[idx : idx + 200]

    return "(context not found)"


# ---------- Warning Categorization ----------


def extract_log_warnings(log_path: Path) -> dict[str, list[str]]:
    """Categorize warnings from LaTeX log.

    Args:
        log_path: Path to LaTeX .log file

    Returns:
        Dict mapping warning category → list of warning messages

    Example:
        >>> warnings = extract_log_warnings(Path("output/paper.log"))
        >>> if warnings['overfull_hbox']:
        ...     print(f"Found {len(warnings['overfull_hbox'])} overfull boxes")
    """
    if not log_path.exists():
        return {}

    log_text = log_path.read_text(encoding="utf-8", errors="ignore")

    warnings = {
        "overfull_hbox": [],
        "underfull_hbox": [],
        "overfull_vbox": [],
        "underfull_vbox": [],
        "missing_references": [],
        "multiply_defined_labels": [],
        "other": [],
    }

    lines = log_text.split("\n")

    for line in lines:
        line_lower = line.lower()

        if "overfull \\hbox" in line_lower:
            warnings["overfull_hbox"].append(line.strip())
        elif "underfull \\hbox" in line_lower:
            warnings["underfull_hbox"].append(line.strip())
        elif "overfull \\vbox" in line_lower:
            warnings["overfull_vbox"].append(line.strip())
        elif "underfull \\vbox" in line_lower:
            warnings["underfull_vbox"].append(line.strip())
        elif "reference" in line_lower and (
            "undefined" in line_lower or "missing" in line_lower
        ):
            warnings["missing_references"].append(line.strip())
        elif "multiply" in line_lower and "defined" in line_lower:
            warnings["multiply_defined_labels"].append(line.strip())
        elif "warning" in line_lower:
            warnings["other"].append(line.strip())

    return warnings


# ---------- BibTeX Validation ----------


def assert_bibtex_ran_successfully(bbl_path: Path) -> None:
    """Verify BibTeX ran and generated .bbl file.

    Args:
        bbl_path: Path to .bbl file (usually same dir as .tex)

    Raises:
        AssertionError: If .bbl missing or empty

    Example:
        >>> assert_bibtex_ran_successfully(Path("output/references.bbl"))
    """
    if not bbl_path.exists():
        raise AssertionError(
            f"BibTeX output file not found: {bbl_path}\n"
            "This means BibTeX didn't run or failed silently."
        )

    content = bbl_path.read_text(encoding="utf-8", errors="ignore")

    if len(content.strip()) < 10:
        raise AssertionError(
            f"BibTeX output file is empty or too small: {bbl_path}\n"
            "Expected bibliography entries but found none."
        )

    # Check for BibTeX error markers
    if "error" in content.lower() or "fatal" in content.lower():
        raise AssertionError(
            f"BibTeX output contains error markers: {bbl_path}"
        )


# ---------- Template Validation ----------


def check_template_packages(
    tex_path: Path, required_packages: list[str]
) -> list[str]:
    """Check if LaTeX file includes required packages.

    Args:
        tex_path: Path to .tex file
        required_packages: List of package names (e.g., ['natbib', 'hyperref'])

    Returns:
        List of missing packages (empty if all present)

    Example:
        >>> missing = check_template_packages(
        ...     Path("output/paper.tex"),
        ...     ['natbib', 'hyperref', 'inputenc']
        ... )
        >>> assert not missing, f"Missing packages: {missing}"
    """
    if not tex_path.exists():
        return required_packages  # All missing if file doesn't exist

    content = tex_path.read_text(encoding="utf-8", errors="ignore")
    missing = []

    for package in required_packages:
        # Check for \usepackage{package} or \usepackage[options]{package}
        # Using string methods (NO REGEX)
        if (
            f"\\usepackage{{{package}}}" not in content
            and "\\usepackage[" not in content
        ):
            # More careful check for package with options
            found = False
            # Look for \usepackage[ ... ]{package}
            usepackage_starts = []
            idx = 0
            while True:
                idx = content.find("\\usepackage[", idx)
                if idx == -1:
                    break
                usepackage_starts.append(idx)
                idx += 12  # len("\\usepackage[")

            for start_idx in usepackage_starts:
                # Find closing ] and then {package}
                close_bracket = content.find("]", start_idx)
                if close_bracket == -1:
                    continue
                open_brace = content.find("{", close_bracket)
                if open_brace == -1:
                    continue
                close_brace = content.find("}", open_brace)
                if close_brace == -1:
                    continue

                pkg_name = content[open_brace + 1 : close_brace].strip()
                if pkg_name == package:
                    found = True
                    break

            if not found and f"\\usepackage{{{package}}}" not in content:
                missing.append(package)
        elif f"\\usepackage{{{package}}}" in content:
            continue  # Found without options

    return missing


def check_bibliography_style(
    tex_path: Path, expected_style: str = "spbasic_pt"
) -> bool:
    """Check if LaTeX file uses expected bibliography style.

    Args:
        tex_path: Path to .tex file
        expected_style: Expected bibliography style name

    Returns:
        True if correct style found, False otherwise

    Example:
        >>> assert check_bibliography_style(
        ...     Path("output/paper.tex"),
        ...     "spbasic_pt"
        ... ), "Wrong bibliography style"
    """
    if not tex_path.exists():
        return False

    content = tex_path.read_text(encoding="utf-8", errors="ignore")

    # Check for \bibliographystyle{expected_style}
    return f"\\bibliographystyle{{{expected_style}}}" in content
