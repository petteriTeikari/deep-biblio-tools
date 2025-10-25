# PR Lessons for Claude Code Guardrails Template

## Self-Reflection: Lessons from the PR for Claude Guardrails

### 1. **Import Management Challenges**

**What happened:**
- Import path confusion between relative (`..core.exceptions`) and absolute (`src.core.exceptions`) imports
- Pre-commit hooks caught imports inside functions instead of at module level
- Different import styles across the codebase

**Lessons for guardrails:**
- Need clear import style guidelines (prefer absolute imports from `src`)
- Import validation hooks are valuable but need good error messages
- Consider adding an import style checker that runs before commits
- Template should include examples of correct import patterns

### 2. **Docker Environment Differences**

**What happened:**
- Tests passed locally but failed in Docker due to missing tex2lyx configuration
- Required environment-specific workarounds (CONTAINER_ENV flag)
- Highlighted the gap between development and CI environments

**Lessons for guardrails:**
- Always test in Docker locally before pushing
- Document system dependencies clearly
- Consider having `make test-docker` command in template
- Environment parity is crucial - what works locally should work in CI
- Document when functionality is environment-specific

### 3. **Regex Policy Enforcement**

**What happened:**
- Project has a "no regex" policy but 88 files still use regex
- Some files claim `# import re # Banned` but still contain regex patterns
- Clear policy exists but enforcement is incomplete

**Lessons for guardrails:**
- Policies need automated enforcement from day one
- Gradual migration strategies should be documented
- Consider having "allowed exceptions" file for legacy code
- Pre-commit hooks should catch policy violations

### 4. **Error Handling Patterns**

**What happened:**
- Bug where code called `.group(1)` on a string instead of a regex match
- Missing error handling in some API calls
- Inconsistent error handling patterns

**Lessons for guardrails:**
- Type hints are crucial for preventing runtime errors
- Consider requiring explicit type checking for dynamic operations
- Error handling patterns should be standardized
- Template should include error handling examples

### 5. **Test-Driven Debugging**

**What happened:**
- PR review identified issues but actual test failures revealed different problems
- Tests helped identify the real issues vs assumed issues
- Local testing didn't catch Docker-specific failures

**Lessons for guardrails:**
- Always run full test suite before committing
- PR templates should include test checklist
- Consider requiring test output in PR descriptions
- Docker-based testing should be part of standard workflow

### 6. **Documentation and Planning**

**What happened:**
- Created detailed plan for tex2lyx Docker fix instead of hacky solution
- Documented the issue for future implementation

**Lessons for guardrails:**
- When blocked, document the plan instead of implementing hacks
- Technical debt should be tracked (e.g., in issues or docs/)
- Template should include docs/ directory structure
- Encourage "plan first, implement second" approach

### 7. **Pre-commit Hook Value**

**What happened:**
- Caught import violations
- Enforced code formatting automatically
- Prevented emojis and other policy violations
- Sometimes needed multiple attempts due to auto-formatting

**Lessons for guardrails:**
- Pre-commit hooks are invaluable for maintaining standards
- Auto-formatting should run before other checks
- Hook messages should be clear about what needs fixing
- Consider having `make pre-commit-install` in template

### 8. **Incremental Problem Solving**

**What happened:**
- Used TodoWrite tool to track multiple issues
- Fixed issues one at a time
- Committed fixes incrementally

**Lessons for guardrails:**
- Breaking down complex issues into tasks is valuable
- Incremental commits make debugging easier
- TodoWrite or similar tracking helps maintain focus
- Template could include task tracking recommendations

### 9. **Version and Dependency Management**

**What happened:**
- pyproject.toml version configuration was already correct
- Some assumed issues weren't actually problems

**Lessons for guardrails:**
- Don't assume - verify actual state
- Version management should be centralized
- Template should have clear version update instructions

### 10. **Communication and Context**

**What happened:**
- Initial PR review listed many issues
- Actual test failures were different from review concerns
- Had to distinguish between real issues and false alarms

**Lessons for guardrails:**
- Automated checks are more reliable than manual reviews
- Context matters - understand the actual failure before fixing
- Template should encourage evidence-based debugging

## Key Recommendations for claude-code-guardrails-template

1. **Standardize imports**: Provide clear examples and enforce with pre-commit
2. **Docker-first testing**: Include Docker test commands in Makefile
3. **Policy enforcement**: Automate policy checks from project start
4. **Error handling patterns**: Include standardized error handling examples
5. **Documentation structure**: Provide docs/ template with key sections
6. **Pre-commit configuration**: Include comprehensive hooks with clear messages
7. **Task tracking**: Recommend approach for complex multi-step tasks
8. **Environment parity**: Ensure dev, test, and CI environments match
9. **Incremental development**: Encourage small, focused commits
10. **Technical debt tracking**: Provide structure for documenting blocked issues

## The Most Important Insight

**Good guardrails catch issues early and provide clear guidance on fixing them**. The goal isn't just to prevent bad code, but to guide developers toward good patterns.

## Specific Examples from This PR

### Import Fix Example
```python
# Bad - relative import that breaks in some contexts
from ..core.exceptions import ParsingError

# Good - absolute import from src
from src.core.exceptions import ParsingError
```

### Docker Environment Check
```python
# Workaround for environment differences
if not Path.home().exists() or os.environ.get("CONTAINER_ENV"):
    # Handle Docker environment
    pass
```

### Pre-commit Hook Success
```
ruff.....................................................................Passed
ruff-format..............................................................Passed
trim trailing whitespace.................................................Passed
fix end of files.........................................................Passed
check for added large files..............................................Passed
check for merge conflicts................................................Passed
detect private key.......................................................Passed
check for case conflicts.................................................Passed
No emojis allowed (except in markdown files).............................Passed
Check Claude guardrails compliance.......................................Passed
No regex for structured parsing..........................................Passed
Comprehensive regex policy enforcement...................................Passed
Validate import structure................................................Passed
```

### Task Tracking Example
```
Todo List:
1. [completed] Fix import name mismatch in src/cli.py
2. [completed] Fix incorrect import path in src/bibliography/core.py
3. [completed] Fix version configuration in pyproject.toml
4. [pending] Address regex policy violations across codebase
5. [completed] Check and run tests to verify fixes
6. [completed] Fix tex2lyx user directory issue in Docker environment
7. [completed] Fix NeRF citation title extraction from arXiv
8. [completed] Run all tests to verify all fixes
```

## Actionable Improvements for Template

1. **Add import style guide**: Create `docs/python-import-style.md`
2. **Docker test command**: Add to Makefile: `test-docker: docker build -f Dockerfile.test -t test . && docker run --rm test`
3. **Pre-commit setup**: Add `make pre-commit-install` target
4. **Error handling examples**: Create `docs/error-handling-patterns.md`
5. **Technical debt tracking**: Add `docs/technical-debt/` directory
6. **Environment checks**: Add `scripts/check-environment-parity.py`
7. **Policy exceptions**: Create `.policy-exceptions.yaml` for legacy code
8. **Test checklist**: Add to `.github/pull_request_template.md`
9. **Debugging guide**: Create `docs/debugging-guide.md`
10. **Incremental development**: Add guidance to `CONTRIBUTING.md`
