#!/usr/bin/env python3
"""PDF Citation Corrector - Analyzes LaTeX compilation errors and fixes bibliography issues.

This script:
1. Compiles LaTeX to PDF and captures all errors
2. Identifies citation-related problems
3. Automatically fixes common issues
4. Re-validates the bibliography
"""

import argparse

# import re  # Banned - using string methods instead
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import bibtexparser
from bibtexparser.bwriter import BibTexWriter

# Add project to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class PDFCitationCorrector:
    """Analyzes LaTeX compilation errors and fixes bibliography issues."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.errors = defaultdict(list)
        self.warnings = defaultdict(list)

    def compile_latex(self, tex_file: Path, engine: str = "xelatex") -> dict:
        """Compile LaTeX and collect all errors and warnings."""
        print(f"Compiling {tex_file.name} with {engine}...")

        # Ensure we're in the right directory
        original_dir = Path.cwd()
        tex_dir = tex_file.parent

        results = {
            "success": False,
            "pdf_created": False,
            "errors": [],
            "warnings": [],
            "undefined_citations": [],
            "duplicate_entries": [],
            "missing_fields": [],
            "compilation_errors": [],
        }

        try:
            import os

            os.chdir(tex_dir)

            # Run LaTeX
            cmd = [
                engine,
                "-interaction=nonstopmode",
                "-halt-on-error",
                str(tex_file.name),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            # Parse output
            self._parse_latex_output(result.stdout, results)

            # Run BibTeX if needed
            aux_file = tex_file.with_suffix(".aux")
            if aux_file.exists():
                print("Running BibTeX...")
                bibtex_result = subprocess.run(
                    ["bibtex", aux_file.stem], capture_output=True, text=True
                )
                self._parse_bibtex_output(
                    bibtex_result.stdout, bibtex_result.stderr, results
                )

                # Run LaTeX again to resolve references
                print(f"Running {engine} again to resolve references...")
                result = subprocess.run(cmd, capture_output=True, text=True)
                self._parse_latex_output(result.stdout, results)

            # Check if PDF was created and validate it
            pdf_file = tex_file.with_suffix(".pdf")
            results["pdf_created"] = pdf_file.exists()

            if results["pdf_created"]:
                # Validate PDF quality
                validation = self._validate_pdf(pdf_file, tex_file)
                results["pdf_validation"] = validation
                results["success"] = (
                    validation["valid"] and len(results["errors"]) == 0
                )

                # Save error PDF if validation failed
                if not validation["valid"]:
                    error_pdf = pdf_file.parent / f"{pdf_file.stem}_error.pdf"
                    shutil.copy2(pdf_file, error_pdf)
                    print(f"Saved error PDF to: {error_pdf}")
            else:
                results["pdf_validation"] = {
                    "valid": False,
                    "reason": "PDF not created",
                }
                results["success"] = False

        finally:
            os.chdir(original_dir)

        return results

    def _validate_pdf(self, pdf_file: Path, tex_file: Path) -> dict:
        """Validate PDF quality by checking for common failure indicators."""
        validation = {
            "valid": True,
            "page_count": 0,
            "has_question_marks": False,
            "size_bytes": 0,
            "issues": [],
            "tex_word_count": 0,
            "pdf_word_count": 0,
            "pdf_body_words": 0,
            "pdf_ref_words": 0,
        }

        try:
            # Check file size
            validation["size_bytes"] = pdf_file.stat().st_size
            if (
                validation["size_bytes"] < 10000
            ):  # Less than 10KB is suspiciously small
                validation["valid"] = False
                validation["issues"].append("PDF file too small (< 10KB)")

            # Use pdfinfo to get page count
            try:
                result = subprocess.run(
                    ["pdfinfo", str(pdf_file)], capture_output=True, text=True
                )
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if "Pages:" in line:
                            page_count = int(line.split(":")[1].strip())
                            validation["page_count"] = page_count
                            break
            except Exception:
                # pdfinfo not available, try alternative method
                pass

            # Extract text to check for (?) citations
            try:
                # Try pdftotext first
                result = subprocess.run(
                    ["pdftotext", str(pdf_file), "-"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    pdf_text = result.stdout

                    # Count question marks in citation context using string methods
                    question_marks = pdf_text.count("(?)")
                    if question_marks > 5:  # More than 5 (?) is suspicious
                        validation["has_question_marks"] = True
                        validation["valid"] = False
                        validation["issues"].append(
                            f"Found {question_marks} undefined citations (?)"
                        )

                    # Check if PDF seems truncated by comparing with source
                    # Count sections in tex file using string methods
                    with open(tex_file) as f:
                        tex_content = f.read()
                        tex_sections = tex_content.count("\\section{")

                    # Count sections in PDF text using string methods
                    # Look for lines that start with digit, space, and capital letter (section headers)
                    pdf_sections = 0
                    for line in pdf_text.split("\n"):
                        line = line.strip()
                        if (
                            len(line) > 2
                            and line[0].isdigit()
                            and line[1] == " "
                            and len(line) > 2
                            and line[2].isupper()
                        ):
                            pdf_sections += 1

                    # If PDF has significantly fewer sections, it's likely truncated
                    if tex_sections > 0 and pdf_sections < tex_sections * 0.5:
                        validation["valid"] = False
                        validation["issues"].append(
                            f"PDF appears truncated: {pdf_sections} sections vs {tex_sections} in source"
                        )

            except FileNotFoundError:
                # pdftotext not available
                validation["issues"].append(
                    "Could not extract text from PDF (pdftotext not found)"
                )
            except Exception as e:
                validation["issues"].append(f"Error validating PDF: {e}")

            # Extract word counts
            try:
                # Get TeX word count (excluding LaTeX commands)
                validation["tex_word_count"] = self._count_tex_words(tex_file)

                # Get PDF word counts
                if "pdf_text" in locals():
                    counts = self._count_pdf_words(pdf_text)
                    validation["pdf_word_count"] = counts["total"]
                    validation["pdf_body_words"] = counts["body"]
                    validation["pdf_ref_words"] = counts["references"]

                    # Check if word counts are significantly different
                    if validation["tex_word_count"] > 0:
                        pdf_ratio = (
                            validation["pdf_body_words"]
                            / validation["tex_word_count"]
                        )
                        if (
                            pdf_ratio < 0.7
                        ):  # PDF has less than 70% of expected words
                            validation["valid"] = False
                            validation["issues"].append(
                                f"PDF appears truncated: {validation['pdf_body_words']} words "
                                f"vs ~{validation['tex_word_count']} expected from source"
                            )
            except Exception as e:
                validation["issues"].append(f"Error counting words: {e}")

            # Check page count heuristic
            if validation["page_count"] > 0:
                # Rough estimate: if tex file is large but PDF is small, something went wrong
                tex_size = tex_file.stat().st_size
                expected_pages = max(1, tex_size // 3000)  # Very rough estimate

                if validation["page_count"] < expected_pages * 0.3:
                    validation["valid"] = False
                    validation["issues"].append(
                        f"PDF seems too short: {validation['page_count']} pages "
                        f"(expected ~{expected_pages} based on source size)"
                    )

        except Exception as e:
            validation["valid"] = False
            validation["issues"].append(f"Error during validation: {str(e)}")

        return validation

    def _count_tex_words(self, tex_file: Path) -> int:
        """Count words in TeX file, excluding LaTeX commands."""
        try:
            with open(tex_file, encoding="utf-8") as f:
                content = f.read()

            # Remove comments
            lines = content.split("\n")
            cleaned_lines = []
            for line in lines:
                # Find first % that's not escaped
                i = 0
                while i < len(line):
                    if line[i] == "%" and (i == 0 or line[i - 1] != "\\"):
                        # Found comment start, take only part before it
                        cleaned_lines.append(line[:i])
                        break
                    i += 1
                else:
                    # No comment found
                    cleaned_lines.append(line)
            content = "\n".join(cleaned_lines)

            # Remove common LaTeX commands and environments
            # Remove inline math $...$
            result = ""
            i = 0
            in_math = False
            while i < len(content):
                if content[i] == "$" and (i == 0 or content[i - 1] != "\\"):
                    in_math = not in_math
                    result += " "
                elif not in_math:
                    result += content[i]
                else:
                    result += " "
                i += 1
            content = result

            # Remove display math \[...\]
            while True:
                start = content.find("\\[")
                if start == -1:
                    break
                end = content.find("\\]", start)
                if end == -1:
                    break
                content = content[:start] + " " + content[end + 2 :]

            # Remove \begin{...}...\end{...} environments
            while True:
                begin_pos = content.find("\\begin{")
                if begin_pos == -1:
                    break
                # Find environment name
                env_start = begin_pos + 7
                env_end = content.find("}", env_start)
                if env_end == -1:
                    break
                env_name = content[env_start:env_end]
                # Find matching \end{env_name}
                end_pattern = f"\\end{{{env_name}}}"
                end_pos = content.find(end_pattern, env_end)
                if end_pos == -1:
                    break
                content = (
                    content[:begin_pos]
                    + " "
                    + content[end_pos + len(end_pattern) :]
                )

            # Remove LaTeX commands
            result = ""
            i = 0
            while i < len(content):
                if (
                    content[i] == "\\"
                    and i + 1 < len(content)
                    and content[i + 1].isalpha()
                ):
                    # Found command, skip it
                    j = i + 2
                    while j < len(content) and content[j].isalpha():
                        j += 1
                    # Check for optional *
                    if j < len(content) and content[j] == "*":
                        j += 1
                    # Skip whitespace
                    while j < len(content) and content[j] in " \t":
                        j += 1
                    # Skip arguments in braces
                    if j < len(content) and content[j] == "{":
                        brace_count = 1
                        j += 1
                        while j < len(content) and brace_count > 0:
                            if content[j] == "{" and (
                                j == 0 or content[j - 1] != "\\"
                            ):
                                brace_count += 1
                            elif content[j] == "}" and (
                                j == 0 or content[j - 1] != "\\"
                            ):
                                brace_count -= 1
                            j += 1
                    result += " "
                    i = j
                elif content[i] in "{}[]":
                    result += " "
                    i += 1
                elif content[i : i + 2] == "\\\\":
                    result += " "
                    i += 2
                elif content[i] == "&":
                    result += " "
                    i += 1
                else:
                    result += content[i]
                    i += 1
            content = result

            # Count words
            words = content.split()
            return len(words)

        except Exception as e:
            print(f"Error counting TeX words: {e}")
            return 0

    def _count_pdf_words(self, pdf_text: str) -> dict:
        """Count words in PDF text, separating body from references."""
        counts = {"total": 0, "body": 0, "references": 0}

        try:
            # Try to find where references start
            ref_patterns = [
                "References",
                "REFERENCES",
                "Bibliography",
                "BIBLIOGRAPHY",
            ]

            ref_start = -1
            lines = pdf_text.split("\n")

            for i, line in enumerate(lines):
                line_stripped = line.strip()
                for pattern in ref_patterns:
                    if (
                        line_stripped == pattern
                        or line_stripped.lower() == pattern.lower()
                    ):
                        ref_start = i
                        break
                if ref_start >= 0:
                    break

            if ref_start >= 0:
                # Split into body and references
                body_text = "\n".join(lines[:ref_start])
                ref_text = "\n".join(lines[ref_start:])

                body_words = body_text.split()
                ref_words = ref_text.split()

                counts["body"] = len(body_words)
                counts["references"] = len(ref_words)
                counts["total"] = counts["body"] + counts["references"]
            else:
                # No clear reference section found
                words = pdf_text.split()
                counts["total"] = len(words)
                counts["body"] = len(words)
                counts["references"] = 0

        except Exception as e:
            print(f"Error counting PDF words: {e}")

        return counts

    def _parse_latex_output(self, output: str, results: dict) -> None:
        """Parse LaTeX output for errors and warnings."""
        lines = output.split("\n")

        for i, line in enumerate(lines):
            # Check for undefined citations
            if "Warning" in line and "Citation" in line and "undefined" in line:
                # Extract citation key between backticks
                start = line.find("`")
                if start != -1:
                    end = line.find("'", start + 1)
                    if end != -1:
                        citation = line[start + 1 : end]
                        if citation not in results["undefined_citations"]:
                            results["undefined_citations"].append(citation)

            # Check for LaTeX errors
            if line.startswith("! "):
                error_msg = line[2:].strip()
                # Get context (next few lines)
                context = []
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].strip():
                        context.append(lines[j].strip())

                results["errors"].append(
                    {"message": error_msg, "context": context, "line": i}
                )

            # Check for warnings
            if "Warning" in line and "citation" not in line.lower():
                results["warnings"].append(line.strip())

    def _parse_bibtex_output(
        self, stdout: str, stderr: str, results: dict
    ) -> None:
        """Parse BibTeX output for errors."""
        output = stdout + "\n" + stderr
        lines = output.split("\n")

        for line in lines:
            # Check for repeated entries
            if "Repeated entry" in line:
                # Look for @type{key pattern
                at_pos = line.find("@")
                if at_pos != -1:
                    # Find entry type
                    type_start = at_pos + 1
                    type_end = type_start
                    while type_end < len(line) and line[type_end].isalnum():
                        type_end += 1
                    if type_end < len(line) and line[type_end] == "{":
                        entry_type = line[type_start:type_end]
                        # Find key
                        key_start = type_end + 1
                        key_end = key_start
                        while (
                            key_end < len(line) and line[key_end] not in r",\s"
                        ):
                            key_end += 1
                        entry_key = line[key_start:key_end].strip()
                        if entry_type and entry_key:
                            results["duplicate_entries"].append(
                                f"{entry_type}:{entry_key}"
                            )

            # Check for missing fields
            if "Warning--" in line:
                if "missing" in line.lower():
                    results["missing_fields"].append(line.strip())

            # Check for undefined entries
            if "didn't find a database entry for" in line:
                # Extract text between quotes
                start = line.find('"')
                if start != -1:
                    end = line.find('"', start + 1)
                    if end != -1:
                        citation = line[start + 1 : end]
                        if citation not in results["undefined_citations"]:
                            results["undefined_citations"].append(citation)

    def analyze_bibliography(self, bib_file: Path) -> dict:
        """Analyze bibliography file for common issues."""
        print(f"\nAnalyzing bibliography: {bib_file}")

        with open(bib_file, encoding="utf-8") as f:
            bib_database = bibtexparser.load(f)

        issues = {
            "duplicate_keys": [],
            "missing_required_fields": [],
            "malformed_authors": [],
            "suspicious_entries": [],
            "empty_fields": [],
            "invalid_characters": [],
        }

        seen_keys = set()

        for entry in bib_database.entries:
            key = entry.get("ID", "")

            # Check for duplicates
            if key in seen_keys:
                issues["duplicate_keys"].append(key)
            seen_keys.add(key)

            # Check for required fields based on entry type
            entry_type = entry.get("ENTRYTYPE", "misc")
            required_fields = self._get_required_fields(entry_type)

            for field in required_fields:
                if field not in entry or not entry[field].strip():
                    issues["missing_required_fields"].append(
                        {"key": key, "type": entry_type, "field": field}
                    )

            # Check authors
            authors = entry.get("author", "")
            if authors:
                # Check for malformed patterns
                if authors.startswith("al, ") or authors == "al":
                    issues["malformed_authors"].append(
                        {
                            "key": key,
                            "authors": authors,
                            "issue": "et al catastrophe",
                        }
                    )
                elif " et al" in authors and "and" not in authors:
                    issues["suspicious_entries"].append(
                        {
                            "key": key,
                            "authors": authors,
                            "issue": "et al without other authors",
                        }
                    )
                elif (
                    authors and " " not in authors and "," not in authors
                ):  # Single word
                    issues["malformed_authors"].append(
                        {
                            "key": key,
                            "authors": authors,
                            "issue": "single name only",
                        }
                    )

            # Check for empty fields
            for field, value in entry.items():
                if field not in ["ID", "ENTRYTYPE"] and not value.strip():
                    issues["empty_fields"].append({"key": key, "field": field})

            # Check for invalid LaTeX characters
            for field, value in entry.items():
                if field in ["title", "author", "journal", "booktitle"]:
                    if self._has_invalid_latex_chars(value):
                        issues["invalid_characters"].append(
                            {
                                "key": key,
                                "field": field,
                                "value": value[:50] + "..."
                                if len(value) > 50
                                else value,
                            }
                        )

        return issues

    def _get_required_fields(self, entry_type: str) -> list[str]:
        """Get required fields for BibTeX entry type."""
        required = {
            "article": ["author", "title", "journal", "year"],
            "inproceedings": ["author", "title", "booktitle", "year"],
            "book": ["author", "title", "publisher", "year"],
            "misc": ["author", "title", "year"],
            "techreport": ["author", "title", "institution", "year"],
            "phdthesis": ["author", "title", "school", "year"],
        }
        return required.get(entry_type.lower(), ["author", "title", "year"])

    def _has_invalid_latex_chars(self, text: str) -> bool:
        """Check for characters that cause LaTeX problems."""
        # Check for HTML entities
        if any(
            entity in text
            for entity in [
                "&amp;",
                "&lt;",
                "&gt;",
                "&nbsp;",
                "<span>",
                "</span>",
            ]
        ):
            return True

        # Common problematic characters that need escaping
        problematic = ["#", "$", "%", "&", "_", "{", "}", "~", "^", "<", ">"]

        # Check if any problematic char is unescaped
        for char in problematic:
            # Check if character appears without preceding backslash
            i = 0
            while i < len(text):
                pos = text.find(char, i)
                if pos == -1:
                    break
                if pos == 0 or text[pos - 1] != "\\":
                    return True
                i = pos + 1

        return False

    def fix_bibliography(
        self, bib_file: Path, issues: dict, compilation_results: dict
    ) -> Path:
        """Fix bibliography based on identified issues."""
        print("\nFixing bibliography issues...")

        with open(bib_file, encoding="utf-8") as f:
            bib_database = bibtexparser.load(f)

        fixes_applied = 0

        # Note: undefined citations are citations IN the document but MISSING from bibliography
        # We should NOT remove these - they indicate missing entries!
        if compilation_results.get("undefined_citations"):
            print(
                f"WARNING: Found {len(compilation_results['undefined_citations'])} undefined citations"
            )
            print(
                "These citations are used in the document but missing from bibliography:"
            )
            for cite in compilation_results["undefined_citations"][:10]:
                print(f"  - {cite}")
            if len(compilation_results["undefined_citations"]) > 10:
                print(
                    f"  ... and {len(compilation_results['undefined_citations']) - 10} more"
                )

        # Fix duplicate entries by keeping only the first occurrence
        print("Removing duplicate entries...")
        seen = set()
        new_entries = []
        duplicates_removed = 0

        for entry in bib_database.entries:
            key = entry.get("ID")
            if key not in seen:
                new_entries.append(entry)
                seen.add(key)
            else:
                # Skip duplicate - in markdown multiple citations of same paper
                # should map to single bibtex entry
                duplicates_removed += 1

        if duplicates_removed > 0:
            print(f"Removed {duplicates_removed} duplicate entries")
            fixes_applied += duplicates_removed
            bib_database.entries = new_entries

        # Fix malformed authors
        for issue in issues.get("malformed_authors", []):
            key = issue["key"]
            for entry in bib_database.entries:
                if entry.get("ID") == key:
                    if issue["issue"] == "et al catastrophe":
                        # Remove the malformed author
                        entry["author"] = "Unknown"
                        entry["note"] = (
                            entry.get("note", "")
                            + "; Author needs manual correction"
                        )
                        fixes_applied += 1
                    elif issue["issue"] == "single name only":
                        # Add placeholder first name
                        entry["author"] = f"{entry['author']}, Unknown"
                        entry["note"] = (
                            entry.get("note", "") + "; Author name incomplete"
                        )
                        fixes_applied += 1

        # Escape problematic characters in ALL entries, not just flagged ones
        print("Escaping LaTeX special characters in all entries...")
        for entry in bib_database.entries:
            # Escape characters in all text fields
            fields_to_escape = [
                "title",
                "author",
                "journal",
                "booktitle",
                "publisher",
                "school",
                "institution",
                "note",
                "series",
                "address",
                "organization",
            ]

            for field in fields_to_escape:
                if field in entry and entry[field]:
                    original = entry[field]
                    escaped = self._escape_latex_chars(original)
                    if original != escaped:
                        entry[field] = escaped
                        fixes_applied += 1

        # Write fixed bibliography
        output_file = bib_file.parent / f"{bib_file.stem}_pdf_ready.bib"

        writer = BibTexWriter()
        writer.indent = "  "
        writer.order_entries_by = "ID"
        writer.align_values = True

        with open(output_file, "w", encoding="utf-8") as f:
            bibtexparser.dump(bib_database, f, writer)

        print(f"Applied {fixes_applied} fixes")
        print(f"Fixed bibliography written to: {output_file}")

        return output_file

    def _escape_latex_chars(self, text: str) -> str:
        """Escape special LaTeX characters comprehensively."""
        # First, decode HTML entities that might be present
        import html

        text = html.unescape(text)

        # Handle special cases first
        # Remove HTML tags
        while True:
            start = text.find("<")
            if start == -1:
                break
            end = text.find(">", start)
            if end == -1:
                break
            text = text[:start] + text[end + 1 :]

        # Replace common HTML entities
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&nbsp;", " ")

        # Now escape LaTeX special characters
        replacements = [
            # Order matters! Do backslash first
            ("\\", r"\textbackslash{}"),
            ("&", r"\&"),
            ("%", r"\%"),
            ("$", r"\$"),
            ("#", r"\#"),
            ("_", r"\_"),
            ("{", r"\{"),
            ("}", r"\}"),
            ("~", r"\textasciitilde{}"),
            ("^", r"\textasciicircum{}"),
            ("<", r"\textless{}"),
            (">", r"\textgreater{}"),
        ]

        for char, replacement in replacements:
            # Only replace if not already escaped
            result = ""
            i = 0
            while i < len(text):
                if text[i] == char and (i == 0 or text[i - 1] != "\\"):
                    result += replacement
                else:
                    result += text[i]
                i += 1
            text = result

        return text

    def generate_report(
        self, tex_file: Path, compilation_results: dict, bib_issues: dict
    ) -> Path:
        """Generate comprehensive quality report."""
        report_file = tex_file.parent / "PDF_COMPILATION_REPORT.md"

        with open(report_file, "w") as f:
            f.write("# PDF Compilation Quality Report\n\n")
            f.write(f"**LaTeX File**: {tex_file.name}\n")
            f.write(
                f"**Status**: {'Success' if compilation_results['success'] else 'Failed'}\n"
            )
            f.write(
                f"**PDF Created**: {'Yes' if compilation_results['pdf_created'] else 'No'}\n"
            )

            # Add PDF validation results if available
            if (
                "pdf_validation" in compilation_results
                and compilation_results["pdf_created"]
            ):
                val = compilation_results["pdf_validation"]
                f.write(f"**PDF Valid**: {'Yes' if val['valid'] else 'No'}\n")
                if val.get("page_count"):
                    f.write(f"**Page Count**: {val['page_count']}\n")
                if val.get("has_question_marks"):
                    f.write("**Undefined Citations**: Yes (multiple ? found)\n")

                # Word count validation
                if val.get("tex_word_count", 0) > 0:
                    f.write("\n**Word Count Analysis**:\n")
                    f.write(
                        f"  - Source (TeX): ~{val['tex_word_count']:,} words\n"
                    )
                    f.write(
                        f"  - PDF Total: {val.get('pdf_word_count', 0):,} words\n"
                    )
                    f.write(
                        f"  - PDF Body: {val.get('pdf_body_words', 0):,} words\n"
                    )
                    f.write(
                        f"  - PDF References: {val.get('pdf_ref_words', 0):,} words\n"
                    )

                    if val.get("pdf_body_words", 0) > 0:
                        ratio = val["pdf_body_words"] / val["tex_word_count"]
                        f.write(f"  - Body/Source Ratio: {ratio:.1%}\n")
                        if ratio < 0.7:
                            f.write("  - **WARNING**: PDF appears truncated\n")

                if val.get("issues"):
                    f.write("\n**Validation Issues**:\n")
                    for issue in val["issues"]:
                        f.write(f"  - {issue}\n")
            f.write("\n")

            # Compilation errors
            if compilation_results["errors"]:
                f.write("## Compilation Errors\n\n")
                for error in compilation_results["errors"]:
                    f.write(f"- **Error**: {error['message']}\n")
                    if error["context"]:
                        f.write(
                            f"  **Context**: {' | '.join(error['context'][:2])}\n"
                        )
                    f.write("\n")

            # Citation issues
            if compilation_results["undefined_citations"]:
                f.write(
                    f"## Undefined Citations ({len(compilation_results['undefined_citations'])})\n\n"
                )
                for cite in compilation_results["undefined_citations"][:20]:
                    f.write(f"- `{cite}`\n")
                if len(compilation_results["undefined_citations"]) > 20:
                    f.write(
                        f"- ... and {len(compilation_results['undefined_citations']) - 20} more\n"
                    )
                f.write("\n")

            # Bibliography issues
            if any(bib_issues.values()):
                f.write("## Bibliography Issues\n\n")

                if bib_issues["duplicate_keys"]:
                    f.write(
                        f"### Duplicate Keys ({len(bib_issues['duplicate_keys'])})\n"
                    )
                    for key in bib_issues["duplicate_keys"][:10]:
                        f.write(f"- `{key}`\n")
                    f.write("\n")

                if bib_issues["malformed_authors"]:
                    f.write(
                        f"### Malformed Authors ({len(bib_issues['malformed_authors'])})\n"
                    )
                    for issue in bib_issues["malformed_authors"][:10]:
                        f.write(
                            f"- `{issue['key']}`: {issue['authors']} ({issue['issue']})\n"
                        )
                    f.write("\n")

                if bib_issues["invalid_characters"]:
                    f.write(
                        f"### Invalid LaTeX Characters ({len(bib_issues['invalid_characters'])})\n"
                    )
                    for issue in bib_issues["invalid_characters"][:10]:
                        f.write(
                            f"- `{issue['key']}` in {issue['field']}: {issue['value']}\n"
                        )
                    f.write("\n")

            # Recommendations
            f.write("## Recommendations\n\n")
            if not compilation_results["success"]:
                f.write("1. Fix compilation errors before proceeding\n")
            if compilation_results["undefined_citations"]:
                f.write("2. Check citation keys match bibliography entries\n")
            if bib_issues["duplicate_keys"]:
                f.write("3. Resolve duplicate bibliography keys\n")
            if bib_issues["malformed_authors"]:
                f.write("4. Fix malformed author names\n")
            if bib_issues["invalid_characters"]:
                f.write("5. Escape special LaTeX characters\n")

        print(f"\nQuality report written to: {report_file}")
        return report_file


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Analyze and fix LaTeX/PDF compilation issues",
        epilog="""
This script helps ensure your LaTeX document compiles cleanly to PDF by:
1. Running LaTeX and BibTeX to identify all errors
2. Analyzing the bibliography for common issues
3. Automatically fixing what can be fixed
4. Generating a comprehensive quality report

Example:
  %(prog)s document.tex --fix --engine xelatex
""",
    )

    parser.add_argument("tex_file", type=Path, help="LaTeX file to compile")
    parser.add_argument(
        "--bib-file",
        type=Path,
        help="Bibliography file (auto-detected if not specified)",
    )
    parser.add_argument(
        "--fix", action="store_true", help="Automatically fix issues"
    )
    parser.add_argument(
        "--engine",
        choices=["pdflatex", "xelatex", "lualatex"],
        default="xelatex",
        help="LaTeX engine to use",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug output"
    )

    args = parser.parse_args()

    if not args.tex_file.exists():
        print(f"Error: File not found: {args.tex_file}")
        return 1

    try:
        corrector = PDFCitationCorrector(debug=args.debug)

        # Find bibliography file if not specified
        if not args.bib_file:
            # Look for references.bib in same directory
            bib_file = args.tex_file.parent / "references.bib"
            if not bib_file.exists():
                # Try to extract from LaTeX file
                with open(args.tex_file) as f:
                    content = f.read()
                    # Look for \bibliography{...}
                    bib_pos = content.find("\\bibliography{")
                    if bib_pos != -1:
                        start = bib_pos + 14
                        end = content.find("}", start)
                        if end != -1:
                            bib_name = content[start:end]
                            if not bib_name.endswith(".bib"):
                                bib_name += ".bib"
                            bib_file = args.tex_file.parent / bib_name

            if bib_file.exists():
                args.bib_file = bib_file
            else:
                print("Warning: No bibliography file found")

        # Compile LaTeX
        compilation_results = corrector.compile_latex(
            args.tex_file, engine=args.engine
        )

        # Analyze bibliography if available
        bib_issues = {}
        if args.bib_file and args.bib_file.exists():
            bib_issues = corrector.analyze_bibliography(args.bib_file)

        # Generate report
        corrector.generate_report(
            args.tex_file, compilation_results, bib_issues
        )

        # Fix issues if requested
        if args.fix and args.bib_file and not compilation_results["success"]:
            fixed_bib = corrector.fix_bibliography(
                args.bib_file, bib_issues, compilation_results
            )
            print(f"\nFixed bibliography created: {fixed_bib}")
            print(
                "Update your LaTeX file to use the fixed bibliography and recompile"
            )

        return 0 if compilation_results["success"] else 1

    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
