# Ruff Best Practices and Common Issues

## Common Ruff Errors and Systematic Fixes

### 1. F841: Local variable is assigned to but never used

**Example:**
```python
year = match.group(3)  # F841: year is assigned but never used
```

**Systematic Approaches:**

#### Option 1: Remove the unused variable
If the variable truly isn't needed:
```python
# Before
year = match.group(3)

# After - just remove it
```

#### Option 2: Use underscore for intentionally unused variables
If you need to unpack values but don't use some:
```python
# Before
author, year, title = parse_citation()  # year unused

# After
author, _, title = parse_citation()
```

#### Option 3: Add `# noqa: F841` if extraction is needed for clarity
Sometimes you extract variables for documentation/clarity:
```python
year = match.group(3)  # noqa: F841  # Extracted for debugging
```

### 2. Pre-commit Integration Best Practices

To avoid committing code with ruff errors:

1. **Always run pre-commit before committing:**
   ```bash
   pre-commit run --all-files
   ```

2. **Enable automatic fixes:**
   ```bash
   uv run ruff check --fix .
   ```

3. **Configure ruff in `pyproject.toml` to match project needs:**
   ```toml
   [tool.ruff]
   # Ignore specific rules if needed for the project
   ignore = [
       "E501",  # Line too long (if you have specific formatting needs)
   ]

   # Enable automatic fixes for safe fixes
   fix = true
   ```

### 3. Systematic Prevention Strategies

1. **IDE Integration:**
   - Configure VS Code/PyCharm to run ruff on save
   - Enable ruff as the default linter

2. **CI/CD Integration:**
   - Run ruff in GitHub Actions (already configured)
   - Block PRs that fail ruff checks

3. **Team Practices:**
   - Document which ruff rules are enforced
   - Share IDE configurations for consistent development

4. **Regular Cleanup:**
   ```bash
   # Fix all auto-fixable issues
   uv run ruff check --fix .

   # Format code
   uv run ruff format .

   # Check what would be fixed
   uv run ruff check --diff .
   ```

### 4. Common Patterns to Avoid F841

1. **Destructuring assignments:**
   ```python
   # Instead of
   data = response.json()
   status = data['status']  # F841 if unused
   result = data['result']

   # Do this
   data = response.json()
   result = data['result']
   ```

2. **Loop variables:**
   ```python
   # Instead of
   for index, value in enumerate(items):  # F841 if index unused
       process(value)

   # Do this
   for _, value in enumerate(items):
       process(value)
   ```

3. **Try-except blocks:**
   ```python
   # Instead of
   try:
       result = risky_operation()
   except Exception as e:  # F841 if e unused
       log.error("Operation failed")

   # Do this
   try:
       result = risky_operation()
   except Exception:
       log.error("Operation failed")
   ```

### 5. Project-Specific Configuration

For this project, consider adding to `pyproject.toml`:

```toml
[tool.ruff]
line-length = 80  # Set to 80 to avoid formatter oscillations
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
]

# Allow unused variables in test files
[tool.ruff.lint.per-file-ignores]
"tests/*" = ["F841"]
```

## Workflow Recommendations

1. **Before committing:**
   ```bash
   uv run ruff check --fix .
   uv run ruff format .
   pre-commit run --all-files
   ```

2. **If pre-commit fails:**
   - Check the specific error
   - Run with `--fix` to auto-fix if possible
   - Manually fix if auto-fix isn't available
   - Re-run pre-commit to verify

3. **For CI/CD failures:**
   - Run the same commands locally
   - Ensure your local environment matches CI (use uv)
   - Check for version mismatches in ruff

This systematic approach helps maintain code quality while minimizing disruption to the development workflow.
