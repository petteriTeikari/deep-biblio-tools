# Immediate Action Plan for Deep Biblio Tools Refactoring

## Phase 0: Foundation (Today)

### 1. Create Proper Directory Structure
```bash
# Create directories
mkdir -p .claude
mkdir -p docs/{planning,architecture,retrospectives}
mkdir -p src/deep_biblio_tools/bibliography
```

### 2. Move and Organize Documentation

#### Move to `.claude/`:
- `CLAUDE.md` → `.claude/CLAUDE.md`

#### Move to `docs/planning/`:
- `refactoring-proposal.md`
- `refactoring-context-for-ai.md`
- `implementation-roadmap.md`
- `claude-code-integration.md`

#### Move to `docs/planning/gemini-analysis/`:
- `gemini-questions.md`
- `gemini-gaps.md`
- `gemini-answer.md`

#### Move to `docs/architecture/`:
- `bibtex-key-formats.md`
- `manual-bibliography-knowledge.md`
- `arxiv-missing-citations-report.md`

#### Move to `docs/retrospectives/`:
- `latex-bibliography-conversion-retrospective.md`
- `self-reflection-and-broader-context.md`
- `current-state-analysis.md`

#### Delete or Archive:
- `hardcode_biblio.md` (duplicate of institutional-knowledge version)

### 3. Create Essential `.claude/` Files

#### `.claude/golden-paths.md`
Document the most common workflows:
- Process a bibliography from markdown
- Fix citation formatting issues
- Validate against CrossRef
- Generate LaTeX bibliography

#### `.claude/no-regex-policy.md`
Copy from guardrails template and adapt:
- Use AST parsers for all structured text
- List approved parsers (bibtexparser, markdown-it-py, etc.)

#### `.claude/docker-first.md`
Define container-based development:
- Local development matches CI/CD exactly
- All dependencies in Docker
- No "works on my machine" issues

## Phase 1: Script Consolidation Analysis (Week 1, Day 1-2)

### 1. Categorize All Scripts
Create a spreadsheet/markdown table:
- Script name
- Primary function
- Dependencies
- Duplicate functionality
- Keep/Merge/Archive decision

### 2. Identify Core Patterns
Extract common operations:
- Bibliography parsing
- Citation extraction
- Metadata fetching
- Validation logic
- Formatting/output

### 3. Design Unified API
```python
# Example unified interface
from deep_biblio_tools import Bibliography

# Single entry point
bib = Bibliography.from_file("references.bib")
bib.validate()
bib.fix_all()
bib.to_file("fixed_references.bib")
```

## Phase 2: Create Core Library Modules (Week 1, Day 3-5)

### 1. `src/deep_biblio_tools/bibliography/__init__.py`
- Main Bibliography class
- Factory methods for different formats

### 2. `src/deep_biblio_tools/bibliography/parser.py`
- AST-based parsing only
- Support BibTeX, CSL-JSON, RIS

### 3. `src/deep_biblio_tools/bibliography/validator.py`
- Validation rules engine
- Configurable rule sets
- Clear error reporting

### 4. `src/deep_biblio_tools/bibliography/fixer.py`
- Individual fix strategies
- Composable fix pipeline
- Audit trail generation

### 5. `src/deep_biblio_tools/bibliography/metadata.py`
- API client abstraction
- Rate limiting
- Caching layer
- Fallback chains

## Phase 3: Migration Strategy (Week 2)

### 1. Create Compatibility Layer
```python
# scripts/legacy_compatibility.py
# Maps old script names to new API calls
def fix_bibliography_main():
    """Compatibility wrapper for fix_bibliography.py"""
    print("Deprecated: Use 'biblio-tools fix' instead")
    # Call new API
```

### 2. Update Tests
- Ensure all existing tests pass
- Add tests for new modules
- Remove tests for deprecated scripts

### 3. Documentation Migration
- Update all references to old scripts
- Create migration guide
- Document breaking changes

## Daily Checklist

### Day 1 (Today)
- [ ] Create directory structure
- [ ] Move all markdown files
- [ ] Create `.claude/` essential files
- [ ] Commit with clear message
- [ ] Update README with new structure

### Day 2
- [ ] Analyze all scripts
- [ ] Create categorization spreadsheet
- [ ] Identify top 5 duplicate patterns
- [ ] Design core API structure

### Day 3
- [ ] Implement Bibliography class
- [ ] Create parser module
- [ ] Write first integration test

### Day 4
- [ ] Implement validator module
- [ ] Create fixer module
- [ ] Add rate limiting to metadata

### Day 5
- [ ] Create CLI entry point
- [ ] Test end-to-end workflow
- [ ] Document new API

## Risk Mitigation

1. **Backward Compatibility**
   - Keep old scripts but add deprecation warnings
   - Provide clear migration path
   - Maintain old tests during transition

2. **Gradual Rollout**
   - Feature flag for new vs. old implementation
   - Beta test with small group
   - Monitor error rates

3. **Documentation First**
   - Document before implementing
   - Get feedback early
   - Keep decision log

## Communication Plan

1. **Daily Status**
   - Update this document with progress
   - Note any blockers
   - Track metric improvements

2. **Weekly Review**
   - Demo new functionality
   - Gather feedback
   - Adjust plan as needed

3. **Stakeholder Updates**
   - Clear migration timeline
   - Breaking change notifications
   - Success metrics tracking
