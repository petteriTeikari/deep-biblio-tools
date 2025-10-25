# Migration Usage Examples

## Overview

This document shows how to use the new consolidated bibliography module and CLI.

## Python API Usage

### Basic Bibliography Operations

```python
from src.bibliography import Bibliography, BibliographyEntry

# Load a bibliography
bib = Bibliography.from_file("references.bib")

# Access entries
for entry in bib:
    print(f"{entry.key}: {entry.get_field('title')}")

# Get specific entry
entry = bib.get_entry("Smith2023")
if entry:
    print(entry.get_field("author"))

# Add new entry
new_entry = BibliographyEntry(
    "article",
    "Jones2024",
    {
        "author": "Jones, Jane",
        "title": "New Research",
        "journal": "Nature",
        "year": "2024"
    }
)
bib.add_entry(new_entry)

# Save
bib.to_file("references_updated.bib")
```

### Formatting Citation Keys

```python
from src.bibliography import Bibliography, CitationKeyFormatter

# Load bibliography
bib = Bibliography.from_file("references.bib")

# Create formatter
formatter = CitationKeyFormatter()

# Convert all keys to author-year format
formatter.standardize_keys(bib, style="authoryear")

# Fix arXiv-specific keys
formatter.fix_arxiv_keys(bib)

# Save with new keys
bib.to_file("references_formatted.bib")
```

### Validating Entries

```python
from src.bibliography import Bibliography, BibliographyValidator

# Load bibliography
bib = Bibliography.from_file("references.bib")

# Create validator
validator = BibliographyValidator(check_urls=False)

# Validate all entries
errors = validator.process(bib)

# Print errors
for error in errors:
    print(f"Error: {error}")

# Validate single entry
entry = bib.get_entry("Smith2023")
if entry:
    entry_errors = validator.validate_entry(entry)
    if entry_errors:
        print(f"Entry has {len(entry_errors)} errors")
```

### Fixing Bibliography Errors

```python
from src.bibliography import Bibliography, BibliographyFixer

# Load bibliography
bib = Bibliography.from_file("references.bib")

# Create fixer
fixer = BibliographyFixer()

# Fix all entries
fixes_applied = fixer.process(bib)
print(f"Applied {fixes_applied} fixes")

# Fix specific issues
for entry in bib:
    fixer.fix_encoding(entry)
    fixer.fix_author_names(entry)
    fixer.fix_ampersands(entry)
    fixer.fix_quotes(entry)

# Save fixed bibliography
bib.to_file("references_fixed.bib")
```

### Sorting Bibliography

```python
from src.bibliography import Bibliography, BibliographySorter

# Load bibliography
bib = Bibliography.from_file("references.bib")

# Sort by author-year
sorted_entries = BibliographySorter.sort_by_author_year(bib)

# Apply sort to bibliography
BibliographySorter.apply_sort(bib, sorted_entries)

# Save sorted bibliography
bib.to_file("references_sorted.bib")
```

## CLI Usage

The new unified CLI provides all bibliography operations:

### Validate Bibliography

```bash
# Basic validation
deep-biblio bib validate references.bib

# Validate and save report
deep-biblio bib validate references.bib > validation_report.txt
```

### Fix Bibliography Errors

```bash
# Fix all issues
deep-biblio bib fix references.bib

# Fix specific issues
deep-biblio bib fix references.bib --no-quotes --no-ampersands

# Fix and save to new file
deep-biblio bib fix references.bib -o references_fixed.bib
```

### Format Citation Keys

```bash
# Convert to author-year format
deep-biblio bib format-keys references.bib

# Save to new file
deep-biblio bib format-keys references.bib -o references_formatted.bib
```

### Sort Bibliography

```bash
# Sort by author-year (default)
deep-biblio bib sort references.bib

# Sort by year (newest first)
deep-biblio bib sort references.bib --by year --reverse

# Sort by key
deep-biblio bib sort references.bib --by key
```

### Merge Multiple Files

```bash
# Merge bibliography files
deep-biblio bib merge refs1.bib refs2.bib refs3.bib -o merged.bib
```

## Migration from Old Scripts

### Old Script → New Command Mapping

| Old Script | New Command |
|------------|-------------|
| `sort_bibliography.py` | `deep-biblio bib sort` |
| `fix_bibliography.py` | `deep-biblio bib fix` |
| `validate_bibliography.py` | `deep-biblio bib validate` |
| `merge_bibliographies.py` | `deep-biblio bib merge` |
| `convert_bib_keys_to_authoryear.py` | `deep-biblio bib format-keys --style authoryear` |

### Using Compatibility Wrappers

During the transition, compatibility wrappers are available:

```bash
# Old way (deprecated)
python scripts/sort_bibliography_wrapper.py references.bib --by author

# New way (recommended)
deep-biblio bib sort references.bib --by author
```

The wrappers will show deprecation warnings and guide users to the new commands.

## Advanced Usage

### Custom Sorting

```python
from src.bibliography import Bibliography, BibliographySorter

# Custom sort by journal then year
def custom_key(entry):
    journal = entry.get_field("journal", "zzz")
    year = entry.get_field("year", "9999")
    return (journal.lower(), year)

bib = Bibliography.from_file("references.bib")
sorted_entries = BibliographySorter.sort_by_custom(bib, custom_key)
BibliographySorter.apply_sort(bib, sorted_entries)
```

### LLM Citation Validation

```python
from src.bibliography import Bibliography, LLMCitationValidator

# Use specialized validator for LLM-generated citations
bib = Bibliography.from_file("llm_references.bib")
validator = LLMCitationValidator(check_urls=True)

errors = validator.process(bib)
# This will check for patterns common in hallucinated citations
```

### Batch Processing

```python
from pathlib import Path
from src.bibliography import Bibliography, BibliographyFixer, BibliographyValidator

# Process all .bib files in directory
bib_files = Path("bibliographies").glob("*.bib")

for bib_file in bib_files:
    print(f"Processing {bib_file}")

    # Load
    bib = Bibliography.from_file(bib_file)

    # Validate
    validator = BibliographyValidator()
    errors = validator.process(bib)
    if errors:
        print(f"  {len(errors)} validation errors")

    # Fix
    fixer = BibliographyFixer()
    fixes = fixer.process(bib)
    print(f"  {fixes} fixes applied")

    # Save
    bib.to_file(bib_file.with_suffix(".fixed.bib"))
```
