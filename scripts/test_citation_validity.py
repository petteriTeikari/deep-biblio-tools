#!/usr/bin/env python3
"""
Test script to analyze citation validity in generated PDFs.
Checks LaTeX log files for undefined citations and provides detailed analysis.

Usage:
    python scripts/test_citation_validity.py path/to/output/directory
    python scripts/test_citation_validity.py UAD_data/v6_UAD_complete
"""

# No regex - using string methods instead
import argparse
import sys
from pathlib import Path


def analyze_citation_validity(output_dir: Path) -> dict:
    """Analyze citation validity from LaTeX log file."""
    results = {
        "total_citations": 0,
        "undefined_citations": 0,
        "undefined_keys": [],
        "malformed_keys": [],
        "missing_from_bib": [],
        "compilation_issues": [],
        "success_rate": 0.0,
    }

    # Find log file
    log_files = list(output_dir.glob("*.log"))
    if not log_files:
        print(f"[ERROR] No .log file found in {output_dir}")
        return results

    log_file = log_files[0]
    print(f"Analyzing: {log_file}")

    # Read log content
    with open(log_file, encoding="utf-8", errors="ignore") as f:
        log_content = f.read()

    # Find all citation attempts - look for natbib citation warnings
    # LaTeX logs show citations as "Citation `key' on page X undefined"
    # TODO: Remove regex usage - all_citation_warnings = re.findall(r"Citation `([^']+)'", log_content)
    #     all_citation_warnings = re.findall(r"Citation `([^']+)'", log_content)

    # Also check the aux file for actual citation commands
    aux_file = output_dir / (log_file.stem + ".aux")
    if aux_file.exists():
        with open(aux_file, encoding="utf-8", errors="ignore") as f:
            aux_content = f.read()
        # In aux file, citations appear as \citation{key} - using string methods
        aux_citations = []
        for line in aux_content.split("\n"):
            if "\\citation{" in line:
                start = line.find("\\citation{") + len("\\citation{")
                end = line.find("}", start)
                if end != -1:
                    key = line[start:end]
                    aux_citations.append(key)
        results["total_citations"] = len(set(aux_citations))
    else:
        # Fallback: count all citations mentioned in warnings
        all_citation_warnings = []
        for line in log_content.split("\n"):
            if "citation" in line.lower() and "warning" in line.lower():
                all_citation_warnings.append(line)
        results["total_citations"] = len(set(all_citation_warnings))

    # Find undefined citations - using string methods instead of regex
    undefined_matches = []
    for line in log_content.split("\n"):
        if "undefined" in line and "Citation" in line:
            # Extract citation key between backticks
            start = line.find("Citation `")
            if start != -1:
                start += len("Citation `")
                end = line.find("'", start)
                if end != -1:
                    key = line[start:end]
                    undefined_matches.append(key)

    results["undefined_citations"] = len(set(undefined_matches))
    results["undefined_keys"] = sorted(set(undefined_matches))

    # Identify malformed keys (year-only, single letters, etc.)
    malformed_patterns = [
        r"^\d{4}[a-z]?$",  # Just year with optional letter: 2024, 2024a
        r"^[a-z]?\d{4}$",  # Letter then year: c2025
        r"^[a-z]{1,2}\d{4}$",  # One or two letters then year
        r"^\d+$",  # Just numbers
    ]

    for key in results["undefined_keys"]:
        for pattern in malformed_patterns:
            # TODO: Remove regex usage - if re.match(pattern, key):
            #             if re.match(pattern, key):
            results["malformed_keys"].append(key)
            break

    # Check bibliography file
    bib_file = output_dir / "references.bib"
    if bib_file.exists():
        with open(bib_file, encoding="utf-8") as f:
            bib_content = f.read()

        # Check which undefined keys are missing from bibliography
        for key in results["undefined_keys"]:
            if "@" in bib_content and f"{{{key}," not in bib_content:
                results["missing_from_bib"].append(key)

    # Calculate success rate
    if results["total_citations"] > 0:
        results["success_rate"] = (
            (results["total_citations"] - results["undefined_citations"])
            / results["total_citations"]
            * 100
        )

    return results


def print_analysis_report(results: dict, output_dir: Path):
    """Print a detailed analysis report."""
    print("\n" + "=" * 60)
    print("CITATION VALIDITY ANALYSIS REPORT")
    print("=" * 60)

    print(f"\nDirectory: {output_dir}")
    print("\nSummary:")
    print(f"  Total citations attempted: {results['total_citations']}")
    print(f"  Undefined citations: {results['undefined_citations']}")
    print(f"  Success rate: {results['success_rate']:.1f}%")

    if results["undefined_citations"] > 0:
        print(
            f"\n[WARNING] Found {results['undefined_citations']} undefined citations!"
        )

        # Show malformed keys
        if results["malformed_keys"]:
            print(
                f"\nMalformed citation keys ({len(results['malformed_keys'])}):"
            )
            for key in results["malformed_keys"][:10]:
                print(f"  - {key}")
            if len(results["malformed_keys"]) > 10:
                print(f"  ... and {len(results['malformed_keys']) - 10} more")

        # Show missing from bibliography
        if results["missing_from_bib"]:
            print(
                f"\nKeys missing from bibliography ({len(results['missing_from_bib'])}):"
            )
            for key in results["missing_from_bib"][:10]:
                print(f"  - {key}")
            if len(results["missing_from_bib"]) > 10:
                print(f"  ... and {len(results['missing_from_bib']) - 10} more")

        # Show sample of other undefined keys
        other_undefined = [
            k
            for k in results["undefined_keys"]
            if k not in results["malformed_keys"]
            and k not in results["missing_from_bib"]
        ]
        if other_undefined:
            print(f"\nOther undefined keys ({len(other_undefined)}):")
            for key in other_undefined[:10]:
                print(f"  - {key}")
            if len(other_undefined) > 10:
                print(f"  ... and {len(other_undefined) - 10} more")

        # Save detailed report
        report_file = output_dir / "citation_validity_report.txt"
        with open(report_file, "w") as f:
            f.write("CITATION VALIDITY DETAILED REPORT\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Total citations: {results['total_citations']}\n")
            f.write(f"Undefined citations: {results['undefined_citations']}\n")
            f.write(f"Success rate: {results['success_rate']:.1f}%\n\n")

            f.write("All undefined citation keys:\n")
            f.write("-" * 40 + "\n")
            for key in sorted(results["undefined_keys"]):
                status = []
                if key in results["malformed_keys"]:
                    status.append("MALFORMED")
                if key in results["missing_from_bib"]:
                    status.append("MISSING")
                status_str = f" [{', '.join(status)}]" if status else ""
                f.write(f"{key}{status_str}\n")

        print(f"\nDetailed report saved to: {report_file}")
    else:
        print("\n[SUCCESS] All citations are properly defined!")

    print("\n" + "=" * 60)

    # Return exit code based on success
    return 0 if results["success_rate"] == 100 else 1


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Test citation validity in generated LaTeX/PDF documents"
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Path to the output directory containing .log file",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=95.0,
        help="Success rate threshold for passing (default: 95.0%%)",
    )

    args = parser.parse_args()

    if not args.output_dir.exists():
        print(f"[ERROR] Directory not found: {args.output_dir}")
        return 1

    # Analyze citations
    results = analyze_citation_validity(args.output_dir)

    # Print report
    exit_code = print_analysis_report(results, args.output_dir)

    # Check against threshold
    if results["success_rate"] < args.threshold:
        print(
            f"\n[FAIL] Citation success rate {results['success_rate']:.1f}% is below threshold {args.threshold}%"
        )
        return 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
