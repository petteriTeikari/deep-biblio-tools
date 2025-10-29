# Documentation Reorganization Plan

**Date**: 2025-10-29
**Issue**: Scattered markdown files violating naming conventions and organization

---

## Current Mess

### Repository Root (13 files - should be 1-2)
```
/CITATION-REPLACEMENT-FAILURE-REPORT.md    → docs/troubleshooting/
/DEEP-CODE-REVIEW-AND-CONTINUATION-PLAN.md → docs/planning/
/ROOT-CAUSE-ANALYSIS-AND-FIX-PLAN.md       → docs/planning/
/SYSTEMATIC_FIX_PLAN.md                    → docs/planning/
/PHASE3-5-IMPLEMENTATION-REPORT.md         → docs/retrospectives/
/AMPERSAND_ISSUE_ANALYSIS.md               → docs/troubleshooting/
/MULTI-HYPOTHESIS-DIAGNOSTIC-PLAN.md       → docs/planning/
/architecture.md                           → docs/architecture/
/ecosystem.md                              → docs/architecture/
/consolidation-summary.md                  → docs/retrospectives/
/readme-deep-biblio-tools.md               → MERGE into README.md
```

### .claude/ vs docs/ Overlap

**Problem**: Unclear what belongs in .claude/ (Claude-specific) vs docs/ (general documentation)

**Proposed Rule**:
- `.claude/` = Claude Code behavior contract, guardrails, policies, session notes
- `docs/` = User-facing documentation, architecture, guides, planning

**Files to Move from .claude/ to docs/**:
```
.claude/CITATION-AUDIT-ALL-MANUSCRIPTS.md  → docs/retrospectives/citation-audit-all-manuscripts.md
.claude/CITATION-QUALITY-ISSUES.md         → docs/known-issues/citation-quality-issues.md
.claude/MCP-CITATION-QUALITY-PLAN.md       → docs/planning/mcp-citation-quality-plan.md
.claude/pipeline-analysis.md              → docs/troubleshooting/pipeline-analysis.md
.claude/bibliography-extraction-issues.md → docs/known-issues/bibliography-extraction-issues.md
.claude/bibliography-formatting-rules.md   → docs/standards/bibliography-formatting-rules.md
.claude/bibtex-key-generation-guide.md     → docs/reference/bibtex-key-generation-guide.md
.claude/citation-commands-guide.md         → docs/reference/citation-commands-guide.md
.claude/pdf-compilation-debugging.md       → docs/troubleshooting/pdf-compilation-debugging.md
.claude/docker-first.md                    → docs/development/docker-first.md
.claude/llm-citation-validation-learnings.md → docs/learnings/llm-citation-validation-learnings.md
```

**Keep in .claude/** (Claude Code specific):
```
.claude/CLAUDE.md                          ✅ Behavior contract
.claude/golden-paths.md                    ✅ Common workflows for Claude
.claude/guardrails-learnings.md            ✅ Claude Code learnings
.claude/no-regex-policy.md                 ✅ Core constraint
.claude/ast-regex-refactoring-guidelines.md ✅ Technical policy
.claude/known-issues-acm.md                ✅ Specific known issue
.claude/aidev-tags.md                      ✅ Development tags
.claude/auto-context.yaml                  ✅ Config
.claude/sessions/                          ✅ Session notes
.claude/guides/                            ✅ Claude-specific guides
.claude/analytics/                         ✅ Analytics for Claude
.claude/learned-patterns/                  ✅ Pattern library
```

### Naming Violations

**FILES WITH WRONG NAMING**:
```
CITATION-REPLACEMENT-FAILURE-REPORT.md     → citation-replacement-failure-report.md
DEEP-CODE-REVIEW-AND-CONTINUATION-PLAN.md  → deep-code-review-and-continuation-plan.md
ROOT-CAUSE-ANALYSIS-AND-FIX-PLAN.md        → root-cause-analysis-and-fix-plan.md
SYSTEMATIC_FIX_PLAN.md                     → systematic-fix-plan.md
PHASE3-5-IMPLEMENTATION-REPORT.md          → phase3-5-implementation-report.md
AMPERSAND_ISSUE_ANALYSIS.md                → ampersand-issue-analysis.md
MULTI-HYPOTHESIS-DIAGNOSTIC-PLAN.md        → multi-hypothesis-diagnostic-plan.md
COMPREHENSIVE-CONTEXT-FOR-OPENAI.md        → comprehensive-context-for-openai.md
CITATION-AUDIT-ALL-MANUSCRIPTS.md          → citation-audit-all-manuscripts.md
CITATION-QUALITY-ISSUES.md                 → citation-quality-issues.md
MCP-CITATION-QUALITY-PLAN.md               → mcp-citation-quality-plan.md
COMPREHENSIVE-COMPLETION-PLAN.md           → comprehensive-completion-plan.md
```

**Exception**: CLAUDE.md, README.md, CHANGELOG.md are allowed uppercase

---

## Proposed Structure

```
/
├── README.md                              ✅ Main readme
├── CLAUDE.md                              ✅ Points to .claude/CLAUDE.md
├── CHANGELOG.md                           ✅ Version history (if exists)
│
├── .claude/                               🎯 Claude Code specific
│   ├── CLAUDE.md                          # Behavior contract
│   ├── golden-paths.md                    # Common workflows
│   ├── guardrails-learnings.md            # Claude learnings
│   ├── no-regex-policy.md                 # Core constraint
│   ├── ast-regex-refactoring-guidelines.md
│   ├── known-issues-acm.md
│   ├── auto-context.yaml
│   ├── sessions/                          # Session notes
│   ├── guides/                            # Claude-specific guides
│   └── analytics/                         # Analytics
│
└── docs/                                  📚 User documentation
    ├── README.md                          # Docs index
    ├── index.md                          # Same as README
    │
    ├── 01-getting-started/               # Existing
    ├── 03-tools/                         # Existing
    ├── 05-development/                   # Existing
    │
    ├── architecture/                     # System design
    │   ├── architecture.md               # From root
    │   ├── ecosystem.md                  # From root
    │   └── proposed-architecture.md      # Existing
    │
    ├── planning/                         # Existing
    │   ├── deep-code-review-and-continuation-plan.md
    │   ├── root-cause-analysis-and-fix-plan.md
    │   ├── systematic-fix-plan.md
    │   ├── multi-hypothesis-diagnostic-plan.md
    │   ├── mcp-citation-quality-plan.md
    │   └── comprehensive-context-for-openai.md  # NEW
    │
    ├── retrospectives/                   # Existing
    │   ├── phase3-5-implementation-report.md
    │   ├── consolidation-summary.md
    │   └── citation-audit-all-manuscripts.md
    │
    ├── troubleshooting/                  # Existing
    │   ├── citation-replacement-failure-report.md
    │   ├── ampersand-issue-analysis.md
    │   ├── pipeline-analysis.md
    │   └── pdf-compilation-debugging.md
    │
    ├── known-issues/                     # Existing
    │   ├── citation-quality-issues.md
    │   └── bibliography-extraction-issues.md
    │
    ├── standards/                        # Existing
    │   └── bibliography-formatting-rules.md
    │
    ├── reference/                        # Existing
    │   ├── bibtex-key-generation-guide.md
    │   └── citation-commands-guide.md
    │
    ├── learnings/                        # Existing
    │   └── llm-citation-validation-learnings.md
    │
    ├── development/                      # Existing
    │   └── docker-first.md
    │
    ├── usage/                            # Existing
    └── code-review/                      # Existing
```

---

## Migration Steps

### Step 1: Rename Files (Fix Naming Violations)
```bash
# In .claude/
mv .claude/COMPREHENSIVE-CONTEXT-FOR-OPENAI.md .claude/comprehensive-context-for-openai.md
mv .claude/CITATION-AUDIT-ALL-MANUSCRIPTS.md .claude/citation-audit-all-manuscripts.md
mv .claude/CITATION-QUALITY-ISSUES.md .claude/citation-quality-issues.md
mv .claude/MCP-CITATION-QUALITY-PLAN.md .claude/mcp-citation-quality-plan.md
mv .claude/COMPREHENSIVE-COMPLETION-PLAN.md .claude/comprehensive-completion-plan.md

# In root/
mv CITATION-REPLACEMENT-FAILURE-REPORT.md citation-replacement-failure-report.md
mv DEEP-CODE-REVIEW-AND-CONTINUATION-PLAN.md deep-code-review-and-continuation-plan.md
mv ROOT-CAUSE-ANALYSIS-AND-FIX-PLAN.md root-cause-analysis-and-fix-plan.md
mv SYSTEMATIC_FIX_PLAN.md systematic-fix-plan.md
mv PHASE3-5-IMPLEMENTATION-REPORT.md phase3-5-implementation-report.md
mv AMPERSAND_ISSUE_ANALYSIS.md ampersand-issue-analysis.md
mv MULTI-HYPOTHESIS-DIAGNOSTIC-PLAN.md multi-hypothesis-diagnostic-plan.md
```

### Step 2: Move .claude/ Docs to docs/
```bash
# Move to appropriate subdirectories
mv .claude/citation-audit-all-manuscripts.md docs/retrospectives/
mv .claude/citation-quality-issues.md docs/known-issues/
mv .claude/mcp-citation-quality-plan.md docs/planning/
mv .claude/pipeline-analysis.md docs/troubleshooting/
mv .claude/bibliography-extraction-issues.md docs/known-issues/
mv .claude/bibliography-formatting-rules.md docs/standards/
mv .claude/bibtex-key-generation-guide.md docs/reference/
mv .claude/citation-commands-guide.md docs/reference/
mv .claude/pdf-compilation-debugging.md docs/troubleshooting/
mv .claude/docker-first.md docs/development/
mv .claude/llm-citation-validation-learnings.md docs/learnings/
mv .claude/comprehensive-context-for-openai.md docs/planning/
```

### Step 3: Move Root Docs to docs/
```bash
# Architecture
mv architecture.md docs/architecture/
mv ecosystem.md docs/architecture/

# Planning
mv deep-code-review-and-continuation-plan.md docs/planning/
mv root-cause-analysis-and-fix-plan.md docs/planning/
mv systematic-fix-plan.md docs/planning/
mv multi-hypothesis-diagnostic-plan.md docs/planning/

# Retrospectives
mv phase3-5-implementation-report.md docs/retrospectives/
mv consolidation-summary.md docs/retrospectives/

# Troubleshooting
mv citation-replacement-failure-report.md docs/troubleshooting/
mv ampersand-issue-analysis.md docs/troubleshooting/
```

### Step 4: Merge readme-deep-biblio-tools.md into README.md
```bash
# Review content, merge unique sections, then delete
rm readme-deep-biblio-tools.md
```

### Step 5: Update References

Files that likely reference moved docs:
- `.claude/CLAUDE.md`
- `docs/README.md`
- `docs/index.md`
- Various planning docs

---

## Questions

1. **Should .claude/COMPREHENSIVE-COMPLETION-PLAN.md stay in .claude/ or move to docs/planning/?**
   - It's a planning doc but was written during Claude session
   - Recommendation: Move to docs/planning/

2. **What about duplicate content?**
   - Some docs in root overlap with docs/ content
   - Need to review and merge/delete duplicates

3. **Session notes in .claude/sessions/ - keep all?**
   - Some are outdated
   - Recommendation: Keep for historical context

---

## Post-Reorganization Checklist

- [ ] All root markdown files moved or merged
- [ ] Only README.md and CLAUDE.md remain in root
- [ ] All files use lowercase kebab-case naming
- [ ] .claude/ contains only Claude Code specific docs
- [ ] docs/ contains all user-facing documentation
- [ ] All references updated in:
  - [ ] .claude/CLAUDE.md
  - [ ] docs/README.md
  - [ ] docs/index.md
  - [ ] Planning documents
- [ ] Git commit with clear message about reorganization

---

Generated: 2025-10-29
