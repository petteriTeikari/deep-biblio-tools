# BibTeX Key Formats: Standard vs Better BibTeX

## Overview

When managing bibliographies with Zotero, users can choose between two key generation systems:

### 1. Standard BibTeX Keys (Short Format)
- **Pattern**: `[author][year]` with optional suffix for duplicates
- **Examples**:
  - `held2024` - Single author, year
  - `smith2024a`, `smith2024b` - Multiple papers by same author in same year
  - `alexandrov2023` - Two authors, uses first author only

### 2. Better BibTeX Keys (Long Format)
- **Pattern**: `[authorLastName][ShortTitle][Year]`
- **Examples**:
  - `held3DConvexSplatting2024` - Held + "3D Convex Splatting" + 2024
  - `marsalFoundationModelsMeet2024` - Marsal + "Foundation Models Meet" + 2024
  - `alexandrovBiasDecisionMaking2023` - Alexandrov + "Bias Decision Making" + 2023

## Key Differences

| Aspect | Standard Keys | Better BibTeX Keys |
|--------|---------------|-------------------|
| **Length** | Short (8-15 chars) | Long (20-40+ chars) |
| **Uniqueness** | Uses suffixes (a,b,c) for duplicates | Title words ensure uniqueness |
| **Readability** | Less descriptive | Self-documenting |
| **Portability** | Universal | Requires Better BibTeX plugin |
| **Memory** | Easy to remember | Harder to type manually |

## Why This Matters

### The Problem
When you have two .bib files with different key formats for the same papers:
```bibtex
# references.bib (standard)
@article{held2024,
  author = "Jan Held and ...",
  title = "3D Convex Splatting: Radiance Field Rendering with 3D Smooth Convexes",
  ...
}

# uad_1st.bib (Better BibTeX)
@article{held3DConvexSplatting2024,
  author = {Held, Jan and ...},
  title = {{3D} convex splatting: {Radiance} field rendering with {3D} smooth convexes},
  ...
}
```

### Consequences
1. **Duplicate entries** when merging files
2. **Missing citations** if LaTeX uses one key format but .bib has another
3. **Confusion** when switching between projects

## Better BibTeX Configuration

Better BibTeX allows customizable key patterns. Common patterns:

### Default Pattern
```
[auth][shorttitle][year]
```

### Components
- `[auth]` - First author's last name
- `[shorttitle]` - First significant words of title (camelCase)
- `[year]` - Publication year
- `[a-z]` - Suffix for duplicates

### Customization Examples
- `[auth:lower][year]` → `held2024` (mimics standard)
- `[auth][year][shorttitle]` → `held2024ConvexSplatting`
- `[auth:lower]_[veryshorttitle:lower]_[year]` → `held_3d_2024`

## Conversion Strategy

### From Better BibTeX to Standard
```
held3DConvexSplatting2024 → held2024
marsalFoundationModelsMeet2024 → marsal2024
```

### Challenges
1. **Collisions**: Multiple papers by same author/year need suffixes
2. **Multi-author papers**: Better BibTeX may include all authors
3. **Case sensitivity**: Better BibTeX preserves case, standard doesn't

## Best Practices

### For New Projects
1. **Choose one format** and stick to it
2. **Document your choice** in README
3. **Configure Zotero** Better BibTeX to match project needs

### For Existing Projects
1. **Identify format** used in .tex files
2. **Convert bibliography** to match
3. **Remove duplicates** after merging
4. **Validate** all citations resolve

### For Collaboration
1. **Agree on format** with co-authors
2. **Share Zotero settings** if using Better BibTeX
3. **Include both keys** as aliases if needed

## Detection Patterns

### Regex to Identify Format
```python
# Standard format
standard_pattern = r'^[a-z]+\d{4}[a-z]?$'
# Examples: held2024, smith2024a

# Better BibTeX format
better_pattern = r'^[a-z]+[A-Z][A-Za-z]+\d{4}[a-z]?$'
# Examples: held3DConvexSplatting2024, marsalFoundationModelsMeet2024
```

## Tools Needed

1. **Key converter**: Transform between formats
2. **Duplicate detector**: Find same paper with different keys
3. **Citation updater**: Update .tex files after key changes
4. **Merger**: Combine .bib files intelligently
