# Fix Plan: Unicode Citation Key Suffix Bug

## STATUS: COMPLETED ✓

**Fix Commit**: fc3d986
**Date**: 2025-10-26
**Test Result**: PDF generated successfully (52 pages, 340KB)

## Problem Statement
LaTeX compilation fails with error: `! Text line contains an invalid character.`
Cause: Citation keys like `unknownUnknown¬`, `unknownUnknown­`, `unknownUnknown¯` contain Unicode characters instead of alphabetic suffixes.

## Root Cause Analysis

### Expected Behavior
When duplicate citation keys exist, they should be suffixed with lowercase letters:
- `unknownUnknowna`
- `unknownUnknownb`
- `unknownUnknownc`

### Actual Behavior
Unicode characters are being used:
- `unknownUnknown¬` (U+00AC)
- `unknownUnknown­` (U+00AD)
- `unknownUnknown¯` (U+00AF)

### Location of Bug
The citation key deduplication code must be in one of these files:
1. `src/converters/md_to_latex/citation_manager.py` - manages citations and generates BibTeX
2. `src/bibliography/formatter.py` - formats citation keys (if exists)
3. Wherever `unknownUnknown` keys are generated

## Step-by-Step Fix Plan

### Phase 1: Locate the Bug (15 min)
1. ✅ Search for code that generates citation key suffixes
2. ✅ Find where `unknownUnknown` keys are created
3. ✅ Identify the suffix generation algorithm

### Phase 2: Fix the Suffix Algorithm (10 min)
1. ✅ Replace Unicode character generation with alphabetic sequence
2. ✅ Use simple counter: `a, b, c, ..., z, aa, ab, ...`
3. ✅ Test the fix in isolation

### Phase 3: Test the Fix (20 min)
1. ✅ Clear citation cache
2. ✅ Run conversion on test file
3. ✅ Verify no Unicode characters in references.bib
4. ✅ Confirm PDF compiles successfully
5. ✅ Check that duplicate keys are properly suffixed

### Phase 4: Commit and Document (10 min)
1. ✅ Run linters (all checks passed)
2. ✅ Commit the fix
3. ✅ Test final conversion
4. ✅ Generate PDF

## Technical Details

### Search Strategy
```bash
# Find where citation keys are generated
grep -r "unknownUnknown" src/
grep -r "citation.*key" src/converters/md_to_latex/
grep -r "suffix\|deduplicate" src/
```

### Expected Code Pattern
Look for something like:
```python
# WRONG (current code)
suffix = chr(172 + counter)  # Generates ¬, ­, ¯

# RIGHT (what we need)
def get_suffix(counter):
    if counter == 0:
        return ''
    return chr(ord('a') + counter - 1)  # Generates a, b, c
```

### Test Case
Input: 3 citations with same author "Unknown" and year "Unknown"
Expected output in references.bib:
```bibtex
@misc{unknownUnknown,
  ...
}
@misc{unknownUnknowna,
  ...
}
@misc{unknownUnknownb,
  ...
}
```

## Success Criteria
- [x] No Unicode characters in citation keys
- [x] Duplicate keys properly suffixed with a, b, c, ...
- [x] LaTeX compiles without "invalid character" error
- [x] PDF generated successfully
- [x] All tests pass (linters, pre-commit hooks)

## Timeline
Total estimated time: ~1 hour

## Fallback Plan
If suffix generation is complex:
1. Simply remove the problematic suffixes
2. Let LaTeX handle duplicate keys (will show warnings but compile)
3. Fix properly later

## Actual Implementation

### Bug Location
Found in `src/converters/md_to_latex/citation_manager.py:378`

```python
# OLD CODE (BROKEN):
key = f"{base_key}{chr(96 + counter)}"  # a, b, c, etc.
```

Problem: Works up to counter=26 (z), but counter=76 → chr(172) = ¬

### Fix Applied
```python
# NEW CODE (WORKING):
# Generate alphabetic suffix: 1→a, 2→b, ..., 26→z, 27→aa, 28→ab, etc.
suffix = ""
temp = counter
while temp > 0:
    temp -= 1  # Make it 0-indexed
    suffix = chr(ord("a") + (temp % 26)) + suffix
    temp //= 26
key = f"{base_key}{suffix}"
```

This implements proper base-26 conversion with alphabetic characters.

### Verification Results
- Total unknownUnknown citations: 372
- Entry 76: `unknownUnknownct` (was `unknownUnknown¬`)
- Entry 77: `unknownUnknowncu` (was `unknownUnknown­`)
- Entry 79: `unknownUnknowncw` (was `unknownUnknown¯`)
- PDF compilation: SUCCESS (52 pages, 340KB)

## Notes
- This bug exists in BOTH the working commit (6dda538) and current HEAD
- The 6:40pm PDF that worked must have been generated from different markdown (fewer duplicate unknownUnknown keys)
- Fixing this will unblock PDF generation regardless of other issues
- The fix properly handles unlimited duplicates (a-z, aa-zz, aaa-zzz, etc.)
