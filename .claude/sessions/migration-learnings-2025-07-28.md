# Migration Learnings: Template to Existing Repository (2025-07-28)

## Summary
This document captures critical learnings from the first attempt to migrate functional code from an existing repository (`../biblioTools_old`) to a new Claude Guardrails template. This migration revealed several systematic issues that must be addressed for future template deployments.

## Root Cause Issues Discovered

### 1. Missing Claude Guardrails Files
**Issue**: GitHub Actions failed because `.claude/auto-context.yaml` was missing
- **Impact**: CI/CD pipeline completely blocked
- **Root Cause**: Template generation didn't include all required guardrail files
- **Fix Applied**: Created missing auto-context.yaml with proper project configuration
- **Template Fix Needed**: Ensure cookiecutter generates ALL required guardrail files

### 2. Dependency Group Mismatch
**Issue**: GitHub Actions expected `test` dependency group, but template used `dev`
- **Impact**: CI/CD failure with "Group `test` is not defined"
- **Root Cause**: Inconsistency between template and CI workflow expectations
- **Fix Applied**: Added `test` dependency group mirroring `dev` dependencies
- **Template Fix Needed**: Standardize dependency group naming across template and workflows

### 3. Python Version Lock File Issues
**Issue**: `uv.lock` generated with Python 3.13 but Docker uses Python 3.12
- **Impact**: Complete Docker build failure
- **Root Cause**: Lock file created on developer machine with different Python version
- **Fix Applied**: Regenerated lock file with correct Python version requirements
- **Template Fix Needed**: Include `requires-python` field and ensure consistent Python versions

### 4. Docker Virtual Environment Portability
**Issue**: uv-generated virtual environments contain absolute paths, not portable to containers
- **Impact**: Container startup failures with "no such file or directory"
- **Root Cause**: uv creates symlinks to host-specific Python paths
- **Current Workaround**: Use `--no-install-project` flag in Docker builds
- **Long-term Fix Needed**: Docker strategy needs rethinking for uv-based projects

### 5. Missing Application Entry Point
**Issue**: No main.py file for FastAPI application
- **Impact**: Docker container has no executable entry point
- **Fix Applied**: Created `src/deep_biblio_tools/main.py` with FastAPI app
- **Template Fix Needed**: Generate proper application entry points for each project type

### 6. Missing FastAPI Dependencies
**Issue**: FastAPI file upload endpoints require `python-multipart` but it's not included
- **Impact**: FastAPI application crashes on startup with "Form data requires python-multipart"
- **Fix Applied**: Added `python-multipart>=0.0.5` to dependencies
- **Template Fix Needed**: Include all required FastAPI dependencies in template

### 7. Double API Route Prefix
**Issue**: Router already has `/api/v1` prefix but main.py adds it again
- **Impact**: Endpoints appear as `/api/v1/api/v1/...` instead of `/api/v1/...`
- **Fix Applied**: Removed prefix from `app.include_router()` call
- **Template Fix Needed**: Ensure consistent routing patterns in generated code

### 8. Docker Virtual Environment Installation Strategy
**Issue**: uv-generated virtual environments work differently in containers than expected
- **Impact**: Project not properly installed in container environment
- **Fix Applied**: Use `uv sync --frozen` in final Docker stage to install project properly
- **Template Fix Needed**: Docker strategy must account for uv's virtual environment handling

### 9. UV Dependency Groups Syntax Error (CRITICAL)
**Issue**: GitHub Actions expects `[dependency-groups]` table but we only had `[project.optional-dependencies]`
- **Impact**: Complete CI/CD failure with "Group `test` is not defined in the project's dependency-groups table"
- **Root Cause**: uv's new syntax requires dependency-groups table, not just optional-dependencies
- **Fix Applied**: Added `[dependency-groups]` section with both `test` and `dev` groups
- **Template Fix Needed**: CRITICAL - Template must generate proper dependency-groups syntax for uv

## Migration Process Improvements Needed

### For Individual Repository Updates
1. **Pre-migration Checklist**:
   - Verify all `.claude/` files exist and are up-to-date
   - Check dependency group consistency
   - Validate Python version requirements
   - Ensure application entry points exist

2. **Migration Testing Protocol**:
   - Local test suite execution
   - Docker build validation
   - GitHub Actions dry-run
   - API functionality verification

### For Organizational Guardrails Management

#### Option 1: Package-Based Approach (Recommended)
Create a separate `claude-guardrails` package that can be installed via uv:

```bash
# In each project
uv add --dev claude-guardrails@latest
# Run guardrails update
uv run claude-guardrails update
```

**Benefits**:
- Centralized guardrails management
- Version-controlled updates
- Easy rollout across organization
- Consistent tooling

#### Option 2: Template Synchronization Tool
Create a tool that can update existing repositories with latest template changes:

```bash
# Update guardrails in existing repo
claude-template sync --template-version=v2.1.0
```

#### Option 3: Git Subtree/Submodule Approach
Manage `.claude/` directory as a shared subtree across all repositories.

## Critical Template Updates Needed

### 1. Complete File Generation
- Ensure all required files are generated:
  - `.claude/auto-context.yaml`
  - `.claude/golden-paths.md`
  - `.claude/sessions/` directory
  - All workflow dependency files

### 2. Consistency Fixes
- Standardize dependency groups (`dev` vs `test`)
- Align Python version requirements across all files
- Ensure Docker strategy works with uv

### 3. Migration Documentation
- Create step-by-step migration guide
- Provide pre-migration validation scripts
- Include troubleshooting for common issues

### 4. Testing Infrastructure
- Add Docker build tests to template CI/CD
- Test with multiple Python versions
- Validate all dependency groups

## Action Items for Template Maintenance

### Immediate (High Priority)
1. Fix auto-context.yaml generation in cookiecutter
2. Standardize dependency group naming
3. Add requires-python to pyproject.toml template
4. Update Docker strategy for uv compatibility

### Medium Term
1. Create claude-guardrails package approach
2. Build template synchronization tooling
3. Add comprehensive migration documentation
4. Implement pre-migration validation scripts

### Long Term
1. Establish organizational guardrails update process
2. Create automated template updates via CI/CD
3. Build metrics and monitoring for guardrails compliance
4. Develop organization-wide best practices enforcement

## Key Learnings Summary

1. **Template and reality must align**: CI workflows, Docker files, and pyproject.toml must all use the same conventions
2. **Lock files are not portable**: Python version consistency is critical across development and deployment
3. **Virtual environments need container strategy**: uv's approach requires different Docker patterns
4. **Missing files cause complete failures**: Template must generate ALL required files
5. **Organization needs systematic approach**: Individual repo updates are not scalable

This migration revealed that the template ecosystem needs significant work to be production-ready for organizational adoption. The issues found here will likely affect every migration attempt until systematically addressed.
