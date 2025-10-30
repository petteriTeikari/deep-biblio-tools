#!/usr/bin/env python3
"""
Simple local markdown to LaTeX converter using local JSON export.
No Zotero API - just local matching.
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    """Normalize URL for matching."""
    # Remove trailing slashes, fragments, etc.
    parsed = urlparse(url)
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
    return normalized.lower()


def load_json_database(json_path: Path) -> Tuple[Dict[str, dict], List[dict]]:
    """Load CSL JSON database and index by URL."""
    with open(json_path) as f:
        entries = json.load(f)

    # Index by URL (and DOI)
    url_index = {}
    for entry in entries:
        # Index by URL
        if 'URL' in entry:
            url_key = normalize_url(entry['URL'])
            url_index[url_key] = entry

        # Also index by DOI URL
        if 'DOI' in entry:
            doi = entry['DOI']
            doi_url1 = normalize_url(f"https://doi.org/{doi}")
            doi_url2 = normalize_url(f"http://dx.doi.org/{doi}")
            url_index[doi_url1] = entry
            url_index[doi_url2] = entry

    print(f"Loaded {len(entries)} entries from JSON database")
    print(f"Created {len(url_index)} URL mappings")
    return url_index, entries


def extract_markdown_links(md_path: Path) -> List[Tuple[str, str]]:
    """Extract all [text](url) links from markdown."""
    import re

    with open(md_path) as f:
        content = f.read()

    # Find all [text](url) patterns
    pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    matches = re.findall(pattern, content)

    print(f"Found {len(matches)} total links in markdown")
    return matches


def match_citations(links: List[Tuple[str, str]], url_index: Dict[str, dict], all_entries: List[dict]) -> Tuple[Dict[str, dict], List[Tuple[str, str]]]:
    """Match markdown links to database entries."""
    matched = {}
    unmatched = []

    print(f"Sample links (first 10):")
    for i, (text, url) in enumerate(links[:10]):
        print(f"  {i+1}. [{text}]({url[:60]}...)")

    for text, url in links:
        # Skip if link text doesn't look like a citation
        # Citations have author names and years
        if '(' not in text or ')' not in text:
            continue

        # Check for year pattern
        if not any(char.isdigit() for char in text):
            continue

        # Try URL matching first
        norm_url = normalize_url(url)
        if norm_url in url_index:
            entry = url_index[norm_url]
            matched[entry['id']] = entry
            continue

        # DEBUG for first few unmatched
        if len(matched) + len(unmatched) < 15:
            print(f"  DEBUG: Could not match URL: {norm_url[:80]}")
            if 'doi.org/' in url:
                print(f"    Trying DOI match...")

        # Try DOI matching
        if 'doi.org/' in url:
            doi = url.split('doi.org/')[-1].strip('/')
            found = False
            for entry in all_entries:
                if 'DOI' in entry and entry['DOI'] == doi:
                    matched[entry['id']] = entry
                    found = True
                    if len(matched) < 15:
                        print(f"    DOI matched: {doi}")
                    break
            if not found:
                if len(unmatched) < 15:
                    print(f"    DOI NOT found in database: {doi}")
                unmatched.append((text, url))
        elif 'arxiv.org/' in url:
            # Extract arXiv ID
            arxiv_id = url.split('arxiv.org/abs/')[-1].strip('/')
            for entry in all_entries:
                if 'note' in entry and arxiv_id in entry['note']:
                    matched[entry['id']] = entry
                    break
                elif 'number' in entry and arxiv_id in str(entry['number']):
                    matched[entry['id']] = entry
                    break
            else:
                unmatched.append((text, url))
        else:
            unmatched.append((text, url))

    print(f"Matched {len(matched)} citations")
    print(f"Unmatched {len(unmatched)} citations")
    return matched, unmatched


def convert_csl_to_bibtex_entry(entry: dict) -> str:
    """Convert single CSL JSON entry to BibTeX format."""
    citation_key = entry['id']
    entry_type = entry.get('type', 'article')

    # Map CSL types to BibTeX types
    type_map = {
        'article': 'article',
        'article-journal': 'article',
        'paper-conference': 'inproceedings',
        'book': 'book',
        'chapter': 'incollection',
        'webpage': 'misc',
        'report': 'techreport',
    }
    bib_type = type_map.get(entry_type, 'misc')

    lines = [f"@{bib_type}{{{citation_key},"]

    # Title
    if 'title' in entry:
        title = entry['title'].replace('{', '\\{').replace('}', '\\}')
        lines.append(f"  title = {{{title}}},")

    # Authors
    if 'author' in entry and len(entry['author']) > 0:
        authors = []
        for author in entry['author']:
            family = author.get('family', '')
            given = author.get('given', '')
            if family or given:  # Only add if we have at least one name part
                authors.append(f"{family}, {given}")
        if authors:
            author_str = " and ".join(authors)
            lines.append(f"  author = {{{author_str}}},")

    # Year - try multiple sources
    year = None
    if 'issued' in entry:
        if isinstance(entry['issued'], dict) and 'date-parts' in entry['issued']:
            year = entry['issued']['date-parts'][0][0]
        elif isinstance(entry['issued'], str):
            # Try to extract year from string
            import re
            year_match = re.search(r'(\d{4})', entry['issued'])
            if year_match:
                year = year_match.group(1)

    if year is None and 'year' in entry:
        year = entry['year']

    if year:
        lines.append(f"  year = {{{year}}},")

    # URL
    if 'URL' in entry:
        lines.append(f"  url = {{{entry['URL']}}},")

    # DOI
    if 'DOI' in entry:
        lines.append(f"  doi = {{{entry['DOI']}}},")

    # Journal/Publisher
    if 'container-title' in entry:
        lines.append(f"  journal = {{{entry['container-title']}}},")
    elif 'publisher' in entry:
        lines.append(f"  publisher = {{{entry['publisher']}}},")

    # Volume, issue, pages
    if 'volume' in entry:
        lines.append(f"  volume = {{{entry['volume']}}},")
    if 'issue' in entry:
        lines.append(f"  number = {{{entry['issue']}}},")
    if 'page' in entry:
        lines.append(f"  pages = {{{entry['page']}}},")

    # Note (for arXiv)
    if 'note' in entry:
        lines.append(f"  note = {{{entry['note']}}},")

    lines.append("}")
    return "\n".join(lines)


def generate_bibtex_file(matched: Dict[str, dict], output_path: Path):
    """Generate references.bib file."""
    with open(output_path, 'w') as f:
        for entry_id, entry in matched.items():
            bib_entry = convert_csl_to_bibtex_entry(entry)
            f.write(bib_entry)
            f.write("\n\n")

    print(f"Generated {output_path} with {len(matched)} entries")


def convert_md_to_tex(md_path: Path, output_dir: Path) -> Path:
    """Convert markdown to LaTeX using pandoc."""
    tex_path = output_dir / md_path.with_suffix('.tex').name
    bib_path = output_dir / "references.bib"

    cmd = [
        'pandoc',
        str(md_path),
        '-o', str(tex_path),
        '--standalone',
        '--bibliography', str(bib_path),
        '--citeproc',
        '--top-level-division=section',
    ]

    print(f"Running pandoc: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Pandoc error: {result.stderr}")
        sys.exit(1)

    print(f"Generated {tex_path}")
    return tex_path


def compile_pdf(tex_path: Path) -> Path:
    """Compile LaTeX to PDF using pdflatex."""
    output_dir = tex_path.parent
    pdf_path = tex_path.with_suffix('.pdf')

    # Run pdflatex twice for references
    for i in range(2):
        cmd = [
            'pdflatex',
            '-interaction=nonstopmode',
            '-output-directory', str(output_dir),
            str(tex_path)
        ]

        print(f"Running pdflatex (pass {i+1}/2)...")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=output_dir, encoding='utf-8', errors='replace')

        if result.returncode != 0:
            print(f"pdflatex error: {result.stderr}")
            # Continue anyway - might still produce PDF

    if pdf_path.exists():
        print(f"✓ Generated {pdf_path}")
        return pdf_path
    else:
        print(f"✗ Failed to generate PDF")
        sys.exit(1)


def write_unmatched_report(unmatched: List[Tuple[str, str]], output_path: Path):
    """Write report of unmatched citations."""
    with open(output_path, 'w') as f:
        f.write("# Unmatched Citations Report\n\n")
        f.write(f"Total unmatched: {len(unmatched)}\n\n")

        for i, (text, url) in enumerate(unmatched, 1):
            f.write(f"{i}. [{text}]({url})\n")

    print(f"Wrote unmatched report to {output_path}")


def main():
    if len(sys.argv) < 3:
        print("Usage: simple_local_converter.py <markdown.md> <database.json> [output_dir]")
        sys.exit(1)

    md_path = Path(sys.argv[1])
    json_path = Path(sys.argv[2])
    output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else md_path.parent / "output"

    # Verify inputs
    if not md_path.exists():
        print(f"Error: {md_path} not found")
        sys.exit(1)
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("SIMPLE LOCAL CONVERTER - No Zotero API")
    print("=" * 60)

    # Step 1: Load database
    print("\n[1/7] Loading JSON database...")
    url_index, all_entries = load_json_database(json_path)

    # Step 2: Extract links
    print("\n[2/7] Extracting markdown links...")
    links = extract_markdown_links(md_path)

    # Step 3: Match citations
    print("\n[3/7] Matching citations...")
    matched, unmatched = match_citations(links, url_index, all_entries)

    # Step 4: Generate BibTeX
    print("\n[4/7] Generating references.bib...")
    bib_path = output_dir / "references.bib"
    generate_bibtex_file(matched, bib_path)

    # Step 5: Convert to LaTeX
    print("\n[5/7] Converting markdown to LaTeX...")
    tex_path = convert_md_to_tex(md_path, output_dir)

    # Step 6: Compile PDF
    print("\n[6/7] Compiling PDF...")
    pdf_path = compile_pdf(tex_path)

    # Step 7: Write unmatched report
    print("\n[7/7] Writing unmatched report...")
    report_path = output_dir / "unmatched_citations.md"
    write_unmatched_report(unmatched, report_path)

    print("\n" + "=" * 60)
    print("CONVERSION COMPLETE")
    print("=" * 60)
    print(f"PDF: {pdf_path}")
    print(f"LaTeX: {tex_path}")
    print(f"BibTeX: {bib_path}")
    print(f"Unmatched: {report_path} ({len(unmatched)} citations)")
    print("=" * 60)


if __name__ == '__main__':
    main()
