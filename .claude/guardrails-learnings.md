# Claude Guardrails Debugging Learnings

This document captures important learnings from debugging Claude Guardrails validation failures to help with future troubleshooting.

## Key Learnings from Guardrails Validation Errors

### 1. File Location Requirements

The GitHub Actions validation (`validate-claude-guardrails.yml`) requires **FOUR specific files** in exact locations:

1. **`CLAUDE.md`** (root directory)
   - MUST exist in the repository root, not just in `.claude/`
   - MUST contain the exact phrase: `refer to **.claude/CLAUDE.md**`
   - Acts as the entry point for Claude Code guardrails

2. **`.claude/CLAUDE.md`**
   - Contains detailed behavioral contract
   - MUST include these exact section headers:
     - `## Forbidden Actions`
     - `## Required Patterns`
     - `## Architecture Context`
     - `## Development Workflow`

3. **`.claude/golden-paths.md`**
   - Common development workflows

4. **`.claude/auto-context.yaml`**
   - MUST contain a `patterns:` section

### 2. Common Validation Failures

#### Error: "Missing required Claude Code guardrail files: CLAUDE.md"
**Cause**: No `CLAUDE.md` in root directory (only in `.claude/`)
**Solution**: Create root `CLAUDE.md` with reference to `.claude/CLAUDE.md`

#### Error: "CLAUDE.md must reference .claude/CLAUDE.md"
**Cause**: The validation script uses grep with a specific pattern
**Solution**: Include exact text: `refer to **.claude/CLAUDE.md**`

#### Error: "Missing required section in .claude/CLAUDE.md: [Section Name]"
**Cause**: Missing or incorrectly named section headers
**Solution**: Add exact section headers as listed above

### 3. Validation Script Patterns

The validation script (`validate-claude-guardrails.yml`) checks:

```bash
# For root CLAUDE.md reference:
grep -q "refer to \*\*\.claude/CLAUDE\.md\*\*" CLAUDE.md

# For section headers:
grep -q "$section" "$claude_file"  # where $section is exact header

# For auto-context.yaml:
grep -q "patterns:" ".claude/auto-context.yaml"
```

### 4. Debugging Tips

1. **Run validation locally**: Extract the validation commands from the workflow and run them manually
2. **Check exact patterns**: The validation uses exact string matching, not fuzzy matching
3. **Preserve file locations**: Never move these files without updating the GitHub Actions workflow

### 5. Repository Structure Best Practice

```
/
├── CLAUDE.md                    # Entry point (references .claude/CLAUDE.md)
├── .claude/
│   ├── CLAUDE.md               # Detailed guardrails
│   ├── golden-paths.md         # Workflows
│   ├── auto-context.yaml       # Auto-context config
│   └── guardrails-learnings.md # This file
└── .github/
    └── workflows/
        └── validate-claude-guardrails.yml
```

### 6. Prevention Checklist

Before refactoring or reorganizing:
- [ ] Keep all 4 guardrail files in their required locations
- [ ] Maintain exact section headers in `.claude/CLAUDE.md`
- [ ] Ensure root `CLAUDE.md` references `.claude/CLAUDE.md` with exact pattern
- [ ] Update GitHub Actions if file locations must change
- [ ] Test validation locally before pushing

## Historical Context

**Date**: 2025-08-05
**Issue**: GitHub Actions validation failed after repository refactoring
**Root Cause**: Missing root `CLAUDE.md` file and incorrect section headers
**Resolution**: Created root `CLAUDE.md` and reorganized `.claude/CLAUDE.md` sections

This documentation ensures future developers understand the strict requirements of the Claude Guardrails validation system.
