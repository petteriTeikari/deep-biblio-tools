# Template Fix Checklist - Quick Reference

## Critical Fixes (Must Do First)

### ✅ Phase 1: File Generation
- [ ] **Create `.claude/auto-context.yaml` template**
  - Location: `{{cookiecutter.project_slug}}/.claude/auto-context.yaml`
  - Test: GitHub Actions pass without "missing files" error

- [ ] **Fix dependency group mismatch**
  - Add `test` group to pyproject.toml template
  - Update GitHub Actions to use consistent groups
  - Test: `uv sync --group test` works

- [ ] **Add Python version requirements**
  - Add `requires-python = "{{cookiecutter.python_min_version}}"` to pyproject.toml
  - Add python_version and python_min_version to cookiecutter.json
  - Test: Docker and local environments use same Python version

### 🐳 Phase 2: Docker Fixes
- [ ] **Fix virtual environment portability**
  - Update Dockerfile to handle uv virtual env absolute paths
  - Choose strategy: no-install-project vs pip fallback
  - Test: Docker container starts successfully

- [ ] **Create application entry points**
  - Add conditional main.py generation based on framework
  - Update Dockerfile CMD to use generated entry point
  - Test: FastAPI app serves correctly in container

### 🧪 Phase 3: Testing Infrastructure
- [ ] **Create template validation script**
  - Script: `scripts/validate-template.py`
  - Tests: generation, files exist, dependencies, Docker, CI
  - Test: All validations pass for fresh template generation

- [ ] **Add CI/CD for template**
  - Test multiple Python versions (3.12, 3.13)
  - Test multiple project types and frameworks
  - Test: Template changes don't break existing functionality

### 📚 Phase 4: Documentation
- [ ] **Create migration guide**
  - Document: step-by-step migration process
  - Include: common issues and solutions
  - Include: pre-migration validation checklist

- [ ] **Build migration tools**
  - Script: pre-migration validation
  - Script: automated migration assistance
  - Test: Existing projects migrate successfully

## Testing Commands

After each fix, run these commands to validate:

```bash
# Generate test project
cookiecutter ../claude-code-guardrails-template --no-input

# Test basic functionality
cd [generated-project]
uv sync
uv run pytest

# Test Docker
docker build -t template-test .
docker run -p 8000:8000 template-test

# Test GitHub Actions locally (if act installed)
act
```

## Success Metrics

- ✅ Template generates without errors
- ✅ All required files present
- ✅ Dependencies install cleanly
- ✅ Tests pass immediately
- ✅ Docker builds and runs
- ✅ GitHub Actions pass
- ✅ No manual fixes needed

## Priority Order

1. **auto-context.yaml** (GitHub Actions blocker)
2. **dependency groups** (CI/CD blocker)
3. **requires-python** (Docker blocker)
4. **Docker strategy** (deployment blocker)
5. **Entry points** (application blocker)
6. **Testing** (quality assurance)
7. **Documentation** (user experience)

## Notes for Claude Sessions

- Start with the cookiecutter template repo: `cd ../claude-code-guardrails-template`
- Test every change immediately: don't accumulate fixes
- Each fix should make the template work better, not require more manual work
- Document discoveries in the main plan document
- Update this checklist as you complete items

The goal: **Zero manual fixes needed after template generation**
