"""Diagnose root causes of bibliography formatting issues.

This script reads the bibliography analysis CSV and the source references.bib file
to trace each formatting issue back to its root cause.
"""

import csv
import sys
from pathlib import Path


def parse_bib_file(bib_path: Path) -> dict:
    """Parse references.bib file to extract all entries."""
    entries = {}

    with open(bib_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into individual entries
    # Each entry starts with @type{key,
    current_entry = None
    current_key = None
    in_entry = False

    lines = content.split('\n')

    for line in lines:
        stripped = line.strip()

        # Start of a new entry
        if stripped.startswith('@'):
            # Save previous entry
            if current_entry is not None and current_key:
                entries[current_key] = parse_bib_entry(current_entry)

            # Parse entry type and key
            # Format: @article{key,
            if '{' in stripped:
                parts = stripped.split('{')
                entry_type = parts[0][1:].strip()  # Remove @ sign
                key_part = parts[1] if len(parts) > 1 else ''
                current_key = key_part.rstrip(',').strip()
                current_entry = {'type': entry_type, 'raw': line + '\n'}
                in_entry = True
            continue

        if in_entry:
            current_entry['raw'] += line + '\n'

            # Check if entry ends
            if stripped == '}' and line.startswith('}'):
                # Entry complete
                entries[current_key] = parse_bib_entry(current_entry)
                current_entry = None
                current_key = None
                in_entry = False

    # Don't forget last entry
    if current_entry is not None and current_key:
        entries[current_key] = parse_bib_entry(current_entry)

    return entries


def parse_bib_entry(entry_data: dict) -> dict:
    """Parse a single BibTeX entry to extract fields."""
    raw = entry_data['raw']
    entry = {'type': entry_data['type'], 'raw': raw}

    # Extract fields using simple string parsing
    lines = raw.split('\n')

    for line in lines:
        stripped = line.strip()

        # Skip entry start and end
        if stripped.startswith('@') or stripped == '}':
            continue

        # Parse field = "value" or field = {value}
        if '=' in stripped:
            field_name, _, rest = stripped.partition('=')
            field_name = field_name.strip()
            rest = rest.strip()

            # Remove trailing comma
            if rest.endswith(','):
                rest = rest[:-1].strip()

            # Remove quotes or braces
            if rest.startswith('"') and rest.endswith('"'):
                value = rest[1:-1]
            elif rest.startswith('{') and rest.endswith('}'):
                value = rest[1:-1]
            else:
                value = rest

            entry[field_name] = value

    return entry


def diagnose_entry(citation_key: str, bib_entry: dict) -> dict:
    """Diagnose issues with a single bibliography entry."""
    diagnosis = {
        'citation_key': citation_key,
        'entry_type': bib_entry.get('type', 'unknown'),
        'has_title': 'title' in bib_entry,
        'has_author': 'author' in bib_entry,
        'has_year': 'year' in bib_entry,
        'has_doi': 'doi' in bib_entry,
        'has_url': 'url' in bib_entry,
        'has_journal': 'journal' in bib_entry,
        'root_causes': [],
        'author_value': bib_entry.get('author', ''),
        'title_value': bib_entry.get('title', ''),
        'journal_value': bib_entry.get('journal', ''),
        'doi_value': bib_entry.get('doi', ''),
    }

    # Identify root causes
    if not diagnosis['has_title']:
        diagnosis['root_causes'].append('MISSING_TITLE_IN_BIB')

    if not diagnosis['has_journal'] and bib_entry.get('type') == 'article':
        diagnosis['root_causes'].append('MISSING_JOURNAL_IN_BIB')

    if diagnosis['has_author']:
        author = diagnosis['author_value']
        if 'and others' in author or 'et al' in author:
            diagnosis['root_causes'].append('INCOMPLETE_AUTHORS')
        if len(author) < 10:
            diagnosis['root_causes'].append('SUSPICIOUSLY_SHORT_AUTHOR')

    if diagnosis['has_title']:
        title = diagnosis['title_value']
        if len(title) < 10:
            diagnosis['root_causes'].append('SUSPICIOUSLY_SHORT_TITLE')
        if 'Web page' in title or 'Unknown' in title:
            diagnosis['root_causes'].append('PLACEHOLDER_TITLE')

    # Check for minimal entries (only DOI/URL with minimal metadata)
    required_fields = ['title', 'author', 'year']
    present_fields = [f for f in required_fields if diagnosis[f'has_{f}']]

    if len(present_fields) < len(required_fields):
        diagnosis['root_causes'].append('INCOMPLETE_METADATA')

    return diagnosis


def main():
    if len(sys.argv) < 3:
        print("Usage: python diagnose_bib_issues.py <analysis_csv> <references_bib>")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    bib_path = Path(sys.argv[2])

    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        sys.exit(1)

    if not bib_path.exists():
        print(f"ERROR: BibTeX file not found: {bib_path}")
        sys.exit(1)

    print(f"📖 Parsing {bib_path}...")
    bib_entries = parse_bib_file(bib_path)
    print(f"   Found {len(bib_entries)} entries in references.bib")

    print(f"\n📊 Reading analysis from {csv_path}...")
    problematic_entries = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['has_issues'] == 'True':
                problematic_entries.append(row)

    print(f"   Found {len(problematic_entries)} entries with formatting issues")

    print(f"\n🔍 Diagnosing root causes...")
    diagnoses = []

    for entry in problematic_entries:
        citation_key = entry['citation_key']

        # Skip parse errors for now
        if citation_key == 'PARSE_ERROR':
            continue

        if citation_key in bib_entries:
            diagnosis = diagnose_entry(citation_key, bib_entries[citation_key])
            diagnosis['formatting_issues'] = entry['issues']
            diagnoses.append(diagnosis)
        else:
            print(f"   WARNING: Citation key '{citation_key}' not found in references.bib")

    # Write enhanced diagnosis
    output_path = csv_path.parent / f"{csv_path.stem}_diagnosis.csv"
    print(f"\n💾 Writing diagnosis to {output_path}...")

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'citation_key', 'entry_type', 'formatting_issues', 'root_causes',
            'has_title', 'has_author', 'has_journal', 'has_doi',
            'author_value', 'title_value', 'journal_value', 'doi_value'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for d in diagnoses:
            # Convert lists to strings
            d['root_causes'] = '; '.join(d['root_causes'])
            writer.writerow(d)

    print(f"✅ Wrote {len(diagnoses)} diagnosed entries")

    # Print summary statistics
    print(f"\n📈 Root Cause Summary:")
    root_cause_counts = {}
    for d in diagnoses:
        for cause in d['root_causes'].split('; '):
            if cause:
                root_cause_counts[cause] = root_cause_counts.get(cause, 0) + 1

    for cause, count in sorted(root_cause_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {cause}: {count}")

    # Show examples of critical issues
    print(f"\n⚠️  Critical Examples:")
    for d in diagnoses[:5]:  # Show first 5
        if 'MISSING_TITLE_IN_BIB' in d['root_causes']:
            print(f"   {d['citation_key']}: Missing title (DOI: {d['doi_value']})")


if __name__ == '__main__':
    main()
