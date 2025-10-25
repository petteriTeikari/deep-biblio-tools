# Phase 4: AST Refactoring - Implementation Plan

## Overview
This document outlines the remaining work for Phase 4 of the AST refactoring project. The goal is to complete the migration from regex-based parsing to AST-based parsing for all utilities and validators.

## Current Status
- **Branch**: `refactor/bibliography-processing`
- **Completed**: AST parsers created, initial post-processing AST framework
- **Pending**: Utilities migration, document reconstruction, guardrail compliance

## Tasks Breakdown

### 1. Update Validators to Use AST Parsers (HIGH PRIORITY)
**Goal**: Replace regex-based validation with AST parser validation

**Files to modify**:
- `src/core/biblio_checker.py` - Contains multiple regex violations
- Validators in utilities that still use regex patterns

**Implementation steps**:
1. Identify all validation functions using regex
2. Replace with appropriate AST parser calls
3. Update error messages to use structured error reporting
4. Test with existing test cases

**Current regex violations to fix**:
- Citation format validation
- DOI pattern matching (can keep for initial check, but validate structure with parser)
- Author name validation
- Date format validation

### 2. Implement Structured Error Reporting (HIGH PRIORITY)
**Goal**: Provide detailed, actionable error messages with line/column information

**Implementation**:
1. Create error reporting class in `src/parsers/base.py`
2. Include:
   - Line number
   - Column number
   - Error type (enum)
   - Suggested fix (when possible)
   - Context snippet
3. Update all parsers to use new error reporting
4. Update CLI output to display structured errors nicely

### 3. Fix MDPI Workaround Using AST (HIGH PRIORITY)
**Goal**: Replace the regex-based MDPI journal name fix with AST manipulation

**Current implementation**: Uses regex to fix MDPI journal names
**New approach**:
1. Parse the citation with appropriate parser
2. Identify journal field in AST
3. Apply MDPI corrections at AST level
4. Reconstruct citation from modified AST

### 4. Complete Document Reconstruction (HIGH PRIORITY)
**File**: `src/converters/md_to_latex/post_processing_ast.py`

**Current issue**: `_reconstruct_document()` method is not implemented

**Implementation**:
1. Implement proper AST traversal
2. Create visitor pattern for each node type
3. Preserve formatting where possible
4. Handle all LaTeX constructs:
   - Commands
   - Environments
   - Math mode
   - Comments
   - Special characters
5. Add comprehensive tests

### 5. Address Remaining Regex Violations (HIGH PRIORITY)
**File**: `src/core/biblio_checker.py`

**Steps**:
1. Run guardrail checks to list all violations
2. For each regex pattern:
   - Determine if it can be replaced with parser
   - If not, document why regex is necessary
   - Implement parser-based alternative where possible
3. Update tests to ensure functionality preserved

### 6. Rename _new.py Files (MEDIUM PRIORITY)
**Files to rename**:
- `src/converters/md_to_latex/citation_extractor_new.py` → `citation_extractor.py`

**Steps**:
1. Check if old `citation_extractor.py` exists
2. If yes, diff the files and merge functionality
3. Rename file
4. Update all imports
5. Run tests to ensure nothing breaks

### 7. ResearchGate Fixes with AST (MEDIUM PRIORITY)
**Goal**: Handle ResearchGate-specific citation formats using AST

**Implementation**:
1. Identify ResearchGate-specific patterns
2. Create AST-based detection
3. Implement fixes at AST level
4. Add test cases for ResearchGate formats

## Testing Strategy

### Unit Tests
- Test each parser individually
- Test error reporting with malformed inputs
- Test document reconstruction accuracy

### Integration Tests
- Full pipeline tests with real documents
- Performance comparison with regex version
- Edge case handling

### Regression Tests
- Ensure all existing functionality preserved
- Run against corpus of real citations
- Verify output identical or improved

## Success Criteria

1. **No regex violations** in guardrail checks (except documented exceptions)
2. **All tests passing** including new AST-based tests
3. **Document reconstruction** produces valid LaTeX/Markdown
4. **Performance** comparable or better than regex version
5. **Error messages** more helpful with line/column information

## Next Session Checklist

When returning to this work:

1. [ ] Check git status and current branch
2. [ ] Run tests to see current state
3. [ ] Run guardrail checks for regex violations
4. [ ] Start with highest priority task not yet begun
5. [ ] Update this document with progress

## Commands Reference

```bash
# Run tests
pytest tests/

# Check for regex violations
rg "re\.(compile|match|search|findall)" src/

# Run specific test file
pytest tests/test_ast_parsers.py -v

# Check pre-commit hooks
pre-commit run --all-files
```

## Notes

- The AST approach should make the codebase more maintainable
- Some regex may be acceptable for simple patterns (document if kept)
- Focus on correctness first, optimize later
- Keep backwards compatibility where possible

## Questions to Resolve

1. Should we maintain both regex and AST versions temporarily?
2. What's the performance impact of AST parsing vs regex?
3. How to handle malformed citations that don't parse cleanly?
4. Should document reconstruction preserve exact formatting or normalize?

---

*Last updated: 2025-08-05*
*Branch: refactor/bibliography-processing*
