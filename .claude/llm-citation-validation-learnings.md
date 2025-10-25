# LLM Citation Validation Learnings

## Critical Learning (2025-08-02)

### The Problem
When validating LLM-generated citations, the system was finding correct author data but NOT automatically correcting the entries. For example:

```bibtex
# What we had (WRONG):
@misc{bhat2024,
  author  = {al, Bhat et},
  note    = {VALIDATION FAILED - authors may be incorrect!},
  url     = {https://arxiv.org/abs/2412.14103},
  ...
}

# What validation found:
Authors: Marsal, Rémi, Chapoutot, Alexandre, Xu, Philippe (+3 more)
Title: "A Simple yet Effective Test-Time Adaptation for Zero-Shot Monocular Metric Depth Estimation"

# What we SHOULD have done:
@misc{marsal2025,
  author  = {Marsal, Rémi and Chapoutot, Alexandre and Xu, Philippe and others},
  title   = {A Simple yet Effective Test-Time Adaptation for Zero-Shot Monocular Metric Depth Estimation},
  url     = {https://arxiv.org/abs/2412.14103},
  ...
}
```

### The Solution
**ALWAYS auto-correct entries when validation provides correct data**. The papers/URLs are more trustworthy than the LLM-generated author names.

### Implementation Requirements

1. **In validation scripts**: When validation finds correct authors, update the entry immediately
2. **In fix scripts**: Use validation results to replace incorrect data
3. **BibTeX key**: Update to use the first author's actual last name (e.g., `bhat2024` → `marsal2025`)
4. **Entry type**: Use correct type based on source (arXiv → `@article` or `@misc`)

### Code Pattern

```python
if result.validation_status == "validated" and result.validated_authors:
    # ALWAYS update with validated data
    entry['author'] = ' and '.join(result.validated_authors)

    # Update BibTeX key to match first author
    first_author_lastname = result.validated_authors[0].split(',')[0].lower()
    new_id = f"{first_author_lastname}{entry.get('year', '')}"
    entry['ID'] = new_id

    # Update other metadata
    if result.metadata.get('title'):
        entry['title'] = result.metadata['title']
```

### Why This Matters

1. **User Trust**: Users trust the papers more than the names
2. **Data Quality**: Leaving malformed entries like "al, Bhat et" is unacceptable when we have correct data
3. **Efficiency**: Users shouldn't have to manually fix what we already validated
4. **Accuracy**: The validated data from DOI/arXiv is authoritative

### Test Cases

1. "et al" catastrophe: `al, Author et` → Fetch and use full author list
2. Hallucinated names: `Bhat et al` → `Marsal et al` (when that's what the paper shows)
3. Missing first names: `Smith and Jones` → `Smith, John and Jones, Jane`
4. Organization names: Format properly as `{Organization Name}`

### Never Leave These Patterns

- `al, Author et` - Always fix with correct authors
- `Author et al` when we have full author list
- Single last names when first names are available
- Hallucinated author names when validation found correct ones
