#!/usr/bin/env python3
"""
EMERGENCY CONVERTER - Convert markdown with inline citations to LaTeX/PDF.
Uses local JSON export - NO Zotero API.

This converts [Author, Year](URL) to pandoc [@citationkey] format.
"""

import json
import subprocess
import sys
from pathlib import Path


def load_json_database(json_path: Path) -> tuple[dict[str, dict], list[dict]]:
    """Load CSL JSON and create lookup indexes."""
    with open(json_path) as f:
        entries = json.load(f)

    # Create multiple indexes for matching
    doi_index = {}
    url_index = {}
    arxiv_index = {}

    for entry in entries:
        # DOI index
        if "DOI" in entry:
            doi_index[entry["DOI"].lower()] = entry

        # URL index
        if "URL" in entry:
            url_norm = entry["URL"].lower().rstrip("/")
            url_index[url_norm] = entry

        # arXiv index
        if "note" in entry and "arXiv" in entry["note"]:
            # Extract arXiv ID from note like "arXiv:2311.14570"
            for part in entry["note"].split():
                if "arXiv:" in part:
                    arxiv_id = part.split(":")[-1]
                    arxiv_index[arxiv_id] = entry

    print(f"Loaded {len(entries)} entries")
    print(f"  DOI index: {len(doi_index)} entries")
    print(f"  URL index: {len(url_index)} entries")
    print(f"  arXiv index: {len(arxiv_index)} entries")

    return entries, doi_index, url_index, arxiv_index


def match_url_to_entry(
    url: str, doi_index, url_index, arxiv_index, all_entries
) -> dict:
    """Try to match a URL to a database entry."""
    url_norm = url.lower().rstrip("/")

    # Try direct URL match
    if url_norm in url_index:
        return url_index[url_norm]

    # Try DOI match
    if "doi.org/" in url_norm:
        doi = url_norm.split("doi.org/")[-1].strip("/")
        if doi in doi_index:
            return doi_index[doi]

    # Try arXiv match
    if "arxiv.org/abs/" in url_norm:
        arxiv_id = url_norm.split("/abs/")[-1].strip("/")
        if arxiv_id in arxiv_index:
            return arxiv_index[arxiv_id]

    return None


def convert_markdown_citations(
    md_path: Path,
    output_path: Path,
    doi_index,
    url_index,
    arxiv_index,
    all_entries,
) -> tuple[int, int, list[str]]:
    """Convert [Author, Year](URL) to [@citationkey] format."""
    import re

    with open(md_path) as f:
        content = f.read()

    # Find all citation patterns: [text](url)
    pattern = r"\[([^\]]+)\]\(([^\)]+)\)"

    matched_count = 0
    unmatched = []

    def replace_citation(match):
        nonlocal matched_count
        text = match.group(1)
        url = match.group(2)

        # Check if this looks like a citation (has year/digits and parentheses/commas)
        if not any(c.isdigit() for c in text):
            return match.group(0)  # Not a citation, keep as-is

        # Try to match URL to database entry
        entry = match_url_to_entry(
            url, doi_index, url_index, arxiv_index, all_entries
        )

        if entry:
            citation_key = entry["id"]
            matched_count += 1
            # Convert to pandoc format
            return f"[@{citation_key}]"
        else:
            unmatched.append(f"[{text}]({url})")
            # Keep as hyperlink but mark as unmatched
            return match.group(0)

    # Replace all citations
    converted = re.sub(pattern, replace_citation, content)

    # Write converted markdown
    with open(output_path, "w") as f:
        f.write(converted)

    print(f"Converted {matched_count} citations")
    print(f"Could not match {len(unmatched)} citations")

    return matched_count, len(unmatched), unmatched


def generate_bibtex_from_json(entries: list[dict], output_path: Path):
    """Convert ALL CSL JSON entries to BibTeX."""
    with open(output_path, "w") as f:
        for entry in entries:
            bib_entry = csl_to_bibtex(entry)
            f.write(bib_entry)
            f.write("\n\n")

    print(f"Generated {output_path} with {len(entries)} entries")


def csl_to_bibtex(entry: dict) -> str:
    """Convert CSL JSON to BibTeX entry."""
    citation_key = entry["id"]
    entry_type = entry.get("type", "misc")

    # Map CSL to BibTeX types
    type_map = {
        "article-journal": "article",
        "paper-conference": "inproceedings",
        "book": "book",
        "chapter": "incollection",
        "webpage": "misc",
        "report": "techreport",
    }
    bib_type = type_map.get(entry_type, "misc")

    lines = [f"@{bib_type}{{{citation_key},"]

    # Title
    if "title" in entry:
        title = entry["title"].replace("{", "{{").replace("}", "}}")
        lines.append(f"  title = {{{title}}},")

    # Authors
    if "author" in entry:
        authors = []
        for author in entry["author"]:
            family = author.get("family", "")
            given = author.get("given", "")
            if family or given:
                authors.append(f"{family}, {given}")
        if authors:
            lines.append(f"  author = {{{' and '.join(authors)}}},")

    # Year
    year = None
    if "issued" in entry:
        if (
            isinstance(entry["issued"], dict)
            and "date-parts" in entry["issued"]
        ):
            year = entry["issued"]["date-parts"][0][0]
    if year:
        lines.append(f"  year = {{{year}}},")

    # Journal/Container
    if "container-title" in entry:
        lines.append(f"  journal = {{{entry['container-title']}}},")

    # Volume, Issue, Pages
    if "volume" in entry:
        lines.append(f"  volume = {{{entry['volume']}}},")
    if "issue" in entry:
        lines.append(f"  number = {{{entry['issue']}}},")
    if "page" in entry:
        lines.append(f"  pages = {{{entry['page']}}},")

    # DOI
    if "DOI" in entry:
        lines.append(f"  doi = {{{entry['DOI']}}},")

    # URL
    if "URL" in entry:
        lines.append(f"  url = {{{entry['URL']}}},")

    # Publisher
    if "publisher" in entry:
        lines.append(f"  publisher = {{{entry['publisher']}}},")

    # Note (for arXiv)
    if "note" in entry:
        lines.append(f"  note = {{{entry['note']}}},")

    lines.append("}")
    return "\n".join(lines)


def convert_to_latex(md_path: Path, bib_path: Path, output_dir: Path) -> Path:
    """Convert markdown to LaTeX using pandoc."""
    tex_path = output_dir / md_path.with_suffix(".tex").name

    cmd = [
        "pandoc",
        str(md_path),
        "-o",
        str(tex_path),
        "--standalone",
        "--bibliography",
        str(bib_path),
        "--citeproc",
        "--top-level-division=section",
    ]

    print("Running pandoc...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        sys.exit(1)

    print(f"✓ Generated {tex_path}")
    return tex_path


def compile_pdf(tex_path: Path) -> Path:
    """Compile LaTeX to PDF."""
    output_dir = tex_path.parent
    pdf_path = tex_path.with_suffix(".pdf")

    for i in range(2):
        cmd = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-output-directory",
            str(output_dir),
            str(tex_path),
        ]
        print(f"Running pdflatex (pass {i + 1}/2)...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=output_dir,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0 and i == 1:
            print(f"Warning: pdflatex returned error code {result.returncode}")

    if pdf_path.exists():
        print(f"✓ Generated {pdf_path}")
        return pdf_path
    else:
        print("✗ PDF generation failed")
        sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: emergency_md_converter.py <input.md> <database.json> [output_dir]"
        )
        sys.exit(1)

    md_path = Path(sys.argv[1])
    json_path = Path(sys.argv[2])
    output_dir = (
        Path(sys.argv[3]) if len(sys.argv) > 3 else md_path.parent / "output"
    )

    if not md_path.exists():
        print(f"Error: {md_path} not found")
        sys.exit(1)
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        sys.exit(1)

    output_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("EMERGENCY MARKDOWN CONVERTER - Local JSON Only")
    print("=" * 70)

    # Step 1: Load database
    print("\n[1/6] Loading JSON database...")
    all_entries, doi_index, url_index, arxiv_index = load_json_database(
        json_path
    )

    # Step 2: Convert markdown citations
    print("\n[2/6] Converting markdown citations...")
    converted_md = output_dir / "converted.md"
    matched, unmatched_count, unmatched_list = convert_markdown_citations(
        md_path, converted_md, doi_index, url_index, arxiv_index, all_entries
    )

    # Step 3: Generate BibTeX
    print("\n[3/6] Generating references.bib...")
    bib_path = output_dir / "references.bib"
    generate_bibtex_from_json(all_entries, bib_path)

    # Step 4: Convert to LaTeX
    print("\n[4/6] Converting to LaTeX...")
    tex_path = convert_to_latex(converted_md, bib_path, output_dir)

    # Step 5: Compile PDF
    print("\n[5/6] Compiling PDF...")
    pdf_path = compile_pdf(tex_path)

    # Step 6: Write unmatched report
    print("\n[6/6] Writing unmatched report...")
    report_path = output_dir / "unmatched_citations.md"
    with open(report_path, "w") as f:
        f.write(f"# Unmatched Citations ({unmatched_count})\n\n")
        for citation in unmatched_list:
            f.write(f"- {citation}\n")

    print("\n" + "=" * 70)
    print("CONVERSION COMPLETE")
    print("=" * 70)
    print(f"✓ PDF: {pdf_path}")
    print(f"✓ LaTeX: {tex_path}")
    print(f"✓ BibTeX: {bib_path}")
    print(f"✓ Matched: {matched} citations")
    print(f"✗ Unmatched: {unmatched_count} citations (see {report_path})")
    print("=" * 70)


if __name__ == "__main__":
    main()
