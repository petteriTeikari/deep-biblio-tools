# BibTeX Citation Key Generation Guide

## Overview

BibTeX citation keys are unique identifiers used to reference bibliography entries in LaTeX documents. Understanding how these keys are generated and managed is crucial for preventing citation errors in the deep-biblio-tools project.

## Key Generation Principles

### 1. Basic Format

The most common citation key format is:
```
AuthorYear
```

Examples:
- `smith2023` - Single author
- `smithjones2023` - Multiple authors (using first author only)
- `smith2023a`, `smith2023b` - Multiple papers by same author in same year

### 2. Better BibTeX Format

Better BibTeX uses a more sophisticated format to reduce collisions:
```
authorTitleWordYear
```

Examples:
- `smithMachineLearning2023` - Includes significant title word
- `jonesDeepNeural2024` - First significant word from title
- `zhangComputerVision2023` - Camel case for readability

### 3. Key Components

#### Author Component
- **Single author**: Use last name only
- **Multiple authors**: Use first author's last name
- **Corporate authors**: Use abbreviated form (e.g., `ieee`, `acm`)
- **No author**: Use first significant word from title or "unknown"
- **Name prefixes**: Include with surname (e.g., `vanDijk`, `deSilva`)

#### Year Component
- Always use 4-digit year
- If no year available, use current year or "n.d."

#### Disambiguation
- When multiple entries share the same author-year combination:
  - Add letters: `smith2023a`, `smith2023b`, `smith2023c`
  - Or add title words: `smithDeep2023`, `smithNeural2023`

## Common Pitfalls and Solutions

### 1. The "et al" Problem

**Problem**: Citations like "Smith et al." being treated as author name
```
# Wrong:
author = "Smith et al."  →  key = "2023" or "unknown2023"

# Correct:
author = "John Smith and Jane Doe and Bob Johnson"  →  key = "smith2023"
```

**Solution**: Always extract the first author's actual name, never include "et al" in the author field.

### 2. Empty Author Fields

**Problem**: Missing or empty author fields generate keys like "2023a", "2023b"
```
# Wrong:
author = ""  →  key = "2023"  # Collides with ALL papers from 2023!

# Correct:
author = ""  →  key = "unknown2023" or use title: "deeplearning2023"
```

### 3. Malformed Author Names

**Problem**: Extra punctuation or malformed names
```
# Wrong:
author = "Smith, J. )"  →  Parsing failure

# Correct:
author = "Smith, J."  →  key = "smith2023"
```

### 4. Corporate/Institutional Authors

**Problem**: Organization names need special handling
```
# Wrong:
author = "National Institute of Standards and Technology"  →  key = "technology2023"

# Correct:
author = "{National Institute of Standards and Technology}"  →  key = "nist2023"
author = "{{NIST}}"  →  key = "nist2023"
```

## Key Generation Algorithm

```python
def generate_citation_key(authors, year, title="", use_better_bibtex=True):
    # 1. Validate inputs
    if not authors or authors.strip() == "":
        if title:
            # Use first significant word from title
            return f"{extract_title_word(title)}{year}"
        return f"unknown{year}"

    # 2. Extract first author
    first_author = authors.split(" and ")[0].strip()

    # 3. Handle "et al." - NEVER include it
    if " et al" in first_author:
        first_author = first_author.split(" et al")[0].strip()

    # 4. Extract last name
    last_name = extract_last_name(first_author)

    # 5. Generate key
    if use_better_bibtex and title:
        title_word = extract_significant_word(title)
        return f"{last_name.lower()}{title_word.capitalize()}{year}"
    else:
        return f"{last_name.lower()}{year}"
```

## Validation Rules

1. **No numbers-only keys**: Keys like "2023", "2024e" indicate extraction failure
2. **No "et al" in keys**: Should never appear in the final key
3. **ASCII only**: Convert special characters (ñ → n, ö → oe)
4. **No spaces or punctuation**: Only alphanumeric characters
5. **Lowercase author**: Except in Better BibTeX camelCase format

## Integration with deep-biblio-tools

### Critical Policy for This Project

1. **LLM-Generated Citations**: Never trust author names from markdown - they're frequently hallucinated
2. **Always Validate**: Check against DOI/CrossRef/arXiv metadata
3. **Auto-Correct**: When validation finds correct authors, replace hallucinated names
4. **Better BibTeX Format**: Use by default for reduced collisions
5. **Fallback Strategy**: If metadata fetch fails, use title-based keys rather than "unknown"

### Error Detection

Watch for these warning signs:
- Keys that are just years: "2023", "2024"
- Keys with letter suffixes on years only: "2023a", "2024e"
- Author fields containing "et al", "and others", "et al."
- Extremely short keys: "a2023", "x2024"

## References

1. Better BibTeX Citation Keys: https://retorquere.github.io/zotero-better-bibtex/citing/
2. JabRef Key Patterns: https://docs.jabref.org/setup/bibtexkeypatterns
3. Standard BibTeX Practices: https://www.bibtex.org/Format/
4. Citation Style Language: https://citationstyles.org/

## Testing Checklist

When implementing citation key generation:

- [ ] Test with single author: "John Smith"
- [ ] Test with multiple authors: "John Smith and Jane Doe"
- [ ] Test with "et al.": "Smith et al."
- [ ] Test with empty author: ""
- [ ] Test with corporate author: "{IEEE}"
- [ ] Test with name prefixes: "van der Waals"
- [ ] Test with non-ASCII: "Müller", "García"
- [ ] Test with malformed input: "Smith, J. )"
- [ ] Test collision handling: Multiple Smith papers in 2023
