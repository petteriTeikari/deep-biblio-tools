# AUTOMATED EXECUTION PLAN - PDF Quality for arXiv Submission

**GOAL**: Perfect PDF output ready for arXiv submission
**METHOD**: Automated fixes → PDF verification → Iterate until perfect
**COMMITS**: After each successful phase

---

## Phase 1: Translation Server (5 min)
**Action**: Start server, verify accessible
**Test**: curl responds 200
**Commit**: "fix: Start translation server for auto-add"

## Phase 2: Health Check (15 min)
**Action**: Add health check to converter.py
**Test**: Conversion fails clearly when server down
**Commit**: "fix: Add translation server health check"

## Phase 3: Fail-Fast (10 min)
**Action**: Set fail_on_temp=True
**Test**: Temp keys cause immediate failure
**Commit**: "fix: Enable fail-fast validation for temp keys"

## Phase 4: Section Generation (15 min)
**Action**: Add --top-level-division=section to pandoc
**Test**: LaTeX has \section{} commands
**Commit**: "fix: Enable section generation in pandoc"

## Phase 5: FULL PDF TEST (15 min)
**Action**: Run complete conversion on mcp-draft-refined-v4.md
**Verify**:
- [ ] PDF generates successfully
- [ ] Headings are formatted (not plain text)
- [ ] No (?) citations (or minimal)
- [ ] Bibliography complete
- [ ] Document structure correct
**Commit**: "test: Verify PDF quality after fixes"

## Phase 6: Iterate Issues (variable)
**Action**: Based on Phase 5 results, fix remaining issues
**Test**: PDF after each fix
**Commit**: After each fix category

## Phase 7: Final Push
**Action**: Push all commits to remote
**Result**: Ready for arXiv submission

---

**EXECUTION STARTS NOW**
