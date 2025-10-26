#!/usr/bin/env python3
"""
Deterministic test suite for MCP conversion workflow.

Validates that .md  .tex  .pdf conversion meets strict criteria.

Checks:
1. Zero "Unknown authors" in BibTeX
2. Zero internal refs treated as citations
3. PDF successfully generated (>200 KB)
4. Zero LaTeX errors
5. Zero BibTeX warnings

Outputs:
- conversion_results.json (detailed, machine-readable summary)
- conversion_history.json (persistent regression log)
- Exits with code 0 on success, 1 otherwise
"""

import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser

# === CONFIG ===
OUTPUT_DIR = Path(
    "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review"
)
PROJECT_ROOT = Path("/Users/petteri/Dropbox/github-personal/deep-biblio-tools")
INPUT_FILE = OUTPUT_DIR / "mcp-draft-refined-v3.md"
PDF_PATH = OUTPUT_DIR / "mcp-draft-refined-v3.pdf"
LOG_PATH = OUTPUT_DIR / "mcp-draft-refined-v3.log"
BIB_PATH = OUTPUT_DIR / "references.bib"
HISTORY_PATH = PROJECT_ROOT / "conversion_history.json"
RESULTS_PATH = PROJECT_ROOT / "conversion_results.json"

# === HELPERS ===


def parse_bib_file(bib_path):
    """Parse BibTeX file and return entries."""
    if not bib_path.exists():
        return []
    with open(bib_path, encoding="utf-8") as f:
        parser = BibTexParser(common_strings=True)
        bib_database = bibtexparser.load(f, parser=parser)
    return bib_database.entries


def count_unknown_authors(bib_path):
    """Return count and offending entries with Unknown or missing authors."""
    if not bib_path.exists():
        return -1, []
    entries = parse_bib_file(bib_path)
    offenders = []
    for entry in entries:
        author = entry.get("author", "").strip()
        if not author or "unknown" in author.lower():
            url = entry.get("url", "no URL")
            offenders.append({"key": entry.get("ID", "unknown"), "url": url})
    return len(offenders), offenders


def count_internal_ref_citations(bib_path):
    """Return count and offending entries with URLs starting with '#' (internal cross-refs)."""
    if not bib_path.exists():
        return -1, []
    entries = parse_bib_file(bib_path)
    offenders = []
    for entry in entries:
        url = entry.get("url", "")
        if url.startswith("#"):
            offenders.append({"key": entry.get("ID", "unknown"), "url": url})
    return len(offenders), offenders


def check_pdf_generated(pdf_path):
    if not pdf_path.exists():
        return False, 0
    size = pdf_path.stat().st_size
    return size > 200 * 1024, size  # >200KB


def parse_latex_log(log_path, limit=5):
    """Parse LaTeX log for errors and warnings, return counts and first few offending lines."""
    if not log_path.exists():
        return -1, -1, [], []
    errors, warnings = [], []
    with open(log_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("!"):
                errors.append(line.strip())
            elif "Warning" in line:
                warnings.append(line.strip())
    return len(errors), len(warnings), errors[:limit], warnings[:limit]


def get_environment_info():
    def safe_cmd(cmd):
        try:
            return subprocess.getoutput(cmd).splitlines()[0]
        except Exception:
            return "unavailable"

    return {
        "python": platform.python_version(),
        "pandoc": safe_cmd("pandoc --version"),
        "pdflatex": safe_cmd("pdflatex --version"),
    }


def load_previous_history(path):
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


# === MAIN ===


def main():
    print("=" * 80)
    print("DETERMINISTIC TEST SUITE FOR MCP-DRAFT-REFINED-V3.MD CONVERSION")
    print("=" * 80)
    print()

    # Clean previous outputs
    print(" Cleaning previous outputs...")
    for f in [BIB_PATH, PDF_PATH, LOG_PATH]:
        if f.exists():
            f.unlink()
            print(f"   Removed: {f.name}")
    print()

    # Run conversion
    print("=" * 80)
    print("Running MD to LaTeX conversion...")
    print("=" * 80)
    cmd = [
        "uv",
        "run",
        "--project",
        str(PROJECT_ROOT),
        "deep-biblio",
        "md2latex",
        str(INPUT_FILE),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"\n Conversion failed with exit code {result.returncode}")
        print(f"\nStderr:\n{result.stderr}")
        sys.exit(1)

    print("\n Conversion completed")
    print()

    # Run all checks
    unknown_authors_count, unknown_authors = count_unknown_authors(BIB_PATH)
    internal_refs_count, internal_refs = count_internal_ref_citations(BIB_PATH)
    pdf_ok, pdf_size = check_pdf_generated(PDF_PATH)
    (
        latex_errors,
        latex_warnings,
        latex_err_lines,
        latex_warn_lines,
    ) = parse_latex_log(LOG_PATH)
    env = get_environment_info()

    results = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "commit_hash": subprocess.getoutput(
            f"cd {PROJECT_ROOT} && git rev-parse --short HEAD 2>/dev/null"
        ),
        "unknown_authors_count": unknown_authors_count,
        "unknown_authors": unknown_authors[
            :20
        ],  # top 20 offenders for analysis, not just 10
        "internal_ref_citations_count": internal_refs_count,
        "internal_ref_citations": internal_refs[:10],
        "pdf_generated": pdf_ok,
        "pdf_size_bytes": pdf_size,
        "latex_errors_count": latex_errors,
        "latex_warnings_count": latex_warnings,
        "latex_error_snippets": latex_err_lines,
        "latex_warning_snippets": latex_warn_lines,
        "environment": env,
    }

    save_json(results, RESULTS_PATH)
    print(f" Results written to {RESULTS_PATH}")
    print()

    # Append to regression log
    history = load_previous_history(HISTORY_PATH)
    history.append(results)
    save_json(history, HISTORY_PATH)

    # === PRINT DETAILED RESULTS ===
    print("=" * 80)
    print("DETAILED TEST RESULTS")
    print("=" * 80)
    print()

    print(f" Unknown author count: {unknown_authors_count}")
    if unknown_authors_count > 0:
        print("   Top offenders (showing first 10):")
        for i, offender in enumerate(unknown_authors[:10], 1):
            print(f"   {i}. {offender['key']}")
            print(f"      URL: {offender['url']}")
    print()

    print(f" Internal reference count: {internal_refs_count}")
    if internal_refs_count > 0:
        print("   Offenders:")
        for offender in internal_refs:
            print(f"   - {offender['key']} -> {offender['url']}")
    print()

    print(f" PDF generated: {'Yes' if pdf_ok else 'No'}")
    print(f"   Size: {pdf_size // 1024} KB")
    print()

    print(f" LaTeX errors: {latex_errors}")
    if latex_errors > 0:
        print("   Error snippets:")
        for err in latex_err_lines:
            print(f"   - {err}")
    print()

    print(f" BibTeX warnings: {latex_warnings}")
    if latex_warnings > 0:
        print("   Warning snippets:")
        for warn in latex_warn_lines:
            print(f"   - {warn}")
    print()

    # === EVALUATE ===
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    fail_conditions = [
        unknown_authors_count > 0,
        internal_refs_count > 0,
        not pdf_ok,
        latex_errors > 0,
        latex_warnings > 0,
    ]

    status_unknown = (
        " PASS"
        if unknown_authors_count == 0
        else f" FAIL ({unknown_authors_count})"
    )
    status_internal = (
        " PASS"
        if internal_refs_count == 0
        else f" FAIL ({internal_refs_count})"
    )
    status_pdf = " PASS" if pdf_ok else " FAIL"
    status_errors = (
        " PASS"
        if latex_errors == 0
        else f" FAIL ({latex_errors} errors, {latex_warnings} warnings)"
    )

    print(f"{status_unknown} | No Unknown authors (expected: 0)")
    print(f"{status_internal} | No internal refs as citations (expected: 0)")
    print(f"{status_pdf} | PDF generated (size: {pdf_size // 1024} KB)")
    print(f"{status_errors} | LaTeX compilation clean")
    print()

    if any(fail_conditions):
        print("=" * 80)
        print(" TESTS FAILED")
        print("=" * 80)
        print("\nDo not claim success until all tests pass.")
        print(f"Full results in: {RESULTS_PATH}")
        sys.exit(1)
    else:
        print("=" * 80)
        print(" ALL TESTS PASSED SUCCESSFULLY")
        print("=" * 80)
        sys.exit(0)


if __name__ == "__main__":
    main()
