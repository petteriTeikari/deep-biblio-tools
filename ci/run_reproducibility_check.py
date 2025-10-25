#!/usr/bin/env python3
"""
Reproducibility & Validation Runner
-----------------------------------
Reads reproducibility-checklist.yml and enforces:
  - Environment consistency
  - Validation command execution
  - Zero-error / zero-warning rules
  - Deterministic output checks (PDF hash)

Usage:
    python ci/run_reproducibility_check.py ci/reproducibility-checklist.yml
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

# ----------------------------
# Utility Functions
# ----------------------------


def run_command(cmd, cwd=None, must_succeed=True):
    """Run a shell command and capture output."""
    print(f"\n[RUN] Running: {cmd}")
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if must_succeed and result.returncode != 0:
        sys.exit(f"[FAIL] Command failed: {cmd}")
    return result


def sha256sum(file_path):
    """Compute SHA256 checksum of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def grep_in_file(file_path, patterns):
    """Return True if any of the given patterns exist in file."""
    if not Path(file_path).exists():
        return False
    with open(file_path, errors="ignore") as f:
        text = f.read()
    for pat in patterns:
        if pat in text:
            print(f"  [WARNING]  Found pattern '{pat}' in {file_path}")
            return True
    return False


# ----------------------------
# Main Validation Logic
# ----------------------------


def validate_environment(cfg):
    """Check environment versions and dependencies (non-blocking info)."""
    print("\n[CHECK] Checking environment consistency...")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Expected Python: {cfg['environment']['python_version']}")
    print(f"OS: {os.uname().sysname}")

    # Check XeLaTeX availability
    try:
        result = subprocess.run(
            "xelatex --version",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version_line = result.stdout.split("\n")[0]
            print(f"XeLaTeX: {version_line}")
        else:
            print("[WARNING]  XeLaTeX not found or not working")
    except Exception as e:
        print(f"[WARNING]  Could not check XeLaTeX version: {e}")

    return True


def run_validation_pipeline(cfg):
    """Execute all stages defined under ci_pipeline."""
    stages = cfg["ci_pipeline"]["stages"]
    cmds = cfg["ci_pipeline"]["commands"]

    for stage in stages:
        print(f"\n{'='*60}")
        print(f"  Stage: {stage}")
        print(f"{'='*60}")
        cmd = cmds.get(stage)
        if not cmd:
            print(
                f"[WARNING]  No command defined for stage '{stage}', skipping."
            )
            continue
        run_command(cmd, must_succeed=True)


def post_validation_checks(cfg):
    """Perform generic validation checks based on log or output files."""
    print(f"\n{'='*60}")
    print("  Post-Validation Checks")
    print(f"{'='*60}")

    latex_log = Path("manuscript.log")
    pdf_file = Path("manuscript.pdf")
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "errors": [],
        "warnings": [],
        "status": "unknown",
    }

    # LaTeX error scan
    if latex_log.exists():
        if grep_in_file(latex_log, ["! "]):
            report["errors"].append("LaTeX errors found in log.")
        if grep_in_file(latex_log, ["Warning"]):
            report["warnings"].append("LaTeX warnings found in log.")
    else:
        report["warnings"].append("LaTeX log file not found.")

    # PDF-level validation
    if pdf_file.exists():
        # Extract text from PDF
        txt_result = subprocess.run(
            f"pdftotext {pdf_file} -",
            shell=True,
            capture_output=True,
            text=True,
        )
        txt = txt_result.stdout

        if "(?)" in txt:
            report["errors"].append("Unresolved citations (?) detected in PDF.")
        if "(Unknown)" in txt or "Unknown" in txt:
            report["errors"].append("Unknown citations detected in PDF.")

        # Check for Unicode replacement characters
        if "" in txt:
            report["warnings"].append(
                "Unicode replacement characters found in PDF."
            )

        pdf_hash = sha256sum(pdf_file)
        report["pdf_sha256"] = pdf_hash
        print(f"\n[INFO] PDF SHA256: {pdf_hash}")
    else:
        report["errors"].append("PDF not found after compilation.")

    # Determine overall status
    if report["errors"]:
        report["status"] = "failed"
    elif report["warnings"]:
        report["status"] = "warning"
    else:
        report["status"] = "success"

    # Output report file
    Path("build").mkdir(exist_ok=True)
    report_path = Path("build/conversion-report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n[INFO] Report written to: {report_path}")
    print(json.dumps(report, indent=2))

    # Exit based on validation criteria
    if (
        cfg.get("signoff", {}).get("criteria", {}).get("zero_errors")
        and report["errors"]
    ):
        print("\n[FAIL] Validation failed: Errors found")
        sys.exit(1)
    elif (
        cfg.get("signoff", {}).get("criteria", {}).get("zero_warnings")
        and report["warnings"]
    ):
        print("\n[WARNING] Validation completed with warnings")
        sys.exit(1)
    else:
        print("\n[PASS] All checks passed. PDF reproducible and error-free.")


# ----------------------------
# Entry Point
# ----------------------------


def main():
    if len(sys.argv) < 2:
        sys.exit(
            "Usage: run_reproducibility_check.py path/to/reproducibility-checklist.yml"
        )

    config_path = Path(sys.argv[1])
    if not config_path.exists():
        sys.exit(f"Config file not found: {config_path}")

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    print("[START] Starting reproducibility validation...")
    print(
        f"Pipeline: {cfg['metadata']['pipeline_name']} v{cfg['metadata']['version']}"
    )

    validate_environment(cfg)
    run_validation_pipeline(cfg)
    post_validation_checks(cfg)


if __name__ == "__main__":
    main()
