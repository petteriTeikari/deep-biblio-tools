# GitHub Issues to Create from TODO Comments

## Issue 1: Implement reference link validation
**File:** `src/parsers/markdown_parser.py:367`
**TODO Comment:**
```python
# TODO: Implement reference link validation
```

**Description:**
Add validation for markdown reference-style links to ensure:
- Link references are defined
- No dangling references
- No duplicate definitions

**Priority:** Medium
**Labels:** enhancement, markdown-parser

---

## Issue 2: Implement author similarity check
**File:** `src/bibliography/validator.py:514`
**TODO Comment:**
```python
# TODO: Implement author similarity check
```

**Description:**
Add fuzzy matching for author names to detect potential duplicates:
- Handle name variations (J. Smith vs John Smith)
- Detect typos in author names
- Suggest similar entries for manual review

**Priority:** Medium
**Labels:** enhancement, bibliography, validation

---

## Issue 3: Add dry-run preview functionality
**File:** `src/main.py:91`
**TODO Comment:**
```python
# TODO: Add dry-run preview functionality
```

**Description:**
Add `--dry-run` flag to main CLI that:
- Shows what changes would be made without applying them
- Displays diff preview
- Useful for validation before committing changes

**Priority:** Low
**Labels:** enhancement, cli, ux

---
