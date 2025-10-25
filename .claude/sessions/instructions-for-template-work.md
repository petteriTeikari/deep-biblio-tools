# Instructions for Future Claude Sessions

## When Working on the Cookiecutter Template

### Starting a Template Fix Session

1. **Change to template directory**:
   ```bash
   cd ../claude-code-guardrails-template
   ```

2. **Read the plan documents** (in this order):
   - `../deep-biblio-tools/.claude/sessions/cookiecutter-template-fixes-plan.md` (detailed implementation)
   - `../deep-biblio-tools/.claude/sessions/template-fix-checklist.md` (quick reference)
   - `../deep-biblio-tools/.claude/sessions/migration-learnings-2025-07-28.md` (context)

3. **Check current status** against the checklist

4. **Pick next priority item** from Phase 1 (Critical) first

### Template Testing Protocol

**After EVERY change**:
```bash
# 1. Generate test project
cookiecutter . --no-input project_name="Test Project"

# 2. Test basic functionality
cd test-project
uv sync
uv run pytest tests/

# 3. Test Docker (if applicable)
docker build -t template-test .

# 4. Clean up
cd ..
rm -rf test-project

# 5. Document what worked/didn't work
```

### Key Files to Modify

**In the template repository**:
- `cookiecutter.json` - Add new template variables
- `{{cookiecutter.project_slug}}/pyproject.toml` - Fix dependencies
- `{{cookiecutter.project_slug}}/.claude/auto-context.yaml` - Create missing file
- `{{cookiecutter.project_slug}}/Dockerfile` - Fix Docker issues
- `{{cookiecutter.project_slug}}/.github/workflows/` - Fix CI/CD

### Success Criteria for Each Fix

1. **Template generates without errors**
2. **Generated project works immediately** (no manual fixes)
3. **All tests pass**
4. **Docker builds successfully**
5. **GitHub Actions pass**

### Common Pitfalls

- **Don't skip testing**: Template issues only appear in fresh generation
- **Test multiple configurations**: Python versions, project types, frameworks
- **Keep changes minimal**: One fix at a time, test thoroughly
- **Document everything**: Update the plan documents with new learnings

### When You Complete an Item

1. **Update the checklist** (mark item as ✅)
2. **Test the full pipeline** (generation → dependencies → tests → Docker)
3. **Document any new issues discovered**
4. **Commit the change** with clear commit message
5. **Move to next priority item**

### Emergency Context

If you need to understand why these fixes are needed, the root cause is:
- User tried to migrate existing code to a fresh cookiecutter template
- Multiple systematic failures occurred that prevent template from working
- Every issue documented represents a **guaranteed failure** for future users
- The template must work perfectly on first generation with zero manual fixes

### End Goal

A cookiecutter template that:
- Generates all required files
- Has consistent configuration across all tools
- Works with Docker immediately
- Passes GitHub Actions without modification
- Requires zero manual fixes after generation

This will enable organizational adoption and smooth migration from existing repositories.
