# File Naming Conventions

## No Version Suffixes in Filenames

### ❌ Don't Do This
```
citation_extractor.py
citation_extractor_new.py      # Bad!
citation_extractor_v2.py       # Bad!
citation_extractor_final.py    # Bad!
citation_extractor_revised.py  # Bad!
```

### ✅ Do This
```
citation_extractor.py          # Just modify the file
```

## Why No Version Suffixes?

1. **Git tracks history**: Use `git log` and `git diff` to see changes
2. **Confusion**: Which version should be imported? Which is current?
3. **Technical debt**: Old versions accumulate and nobody deletes them
4. **Import complexity**: Changing filenames breaks imports everywhere

## Proper Versioning Workflow

### When refactoring a module:

```bash
# 1. Create a feature branch
git checkout -b refactor/citation-extractor

# 2. Modify the file directly
vim src/citation_extractor.py

# 3. Test your changes
pytest tests/test_citation_extractor.py

# 4. Commit with clear message
git add src/citation_extractor.py
git commit -m "refactor: migrate citation extractor to AST parser"

# 5. If you need the old version, use git
git show HEAD~1:src/citation_extractor.py
```

## Acceptable Patterns

### Different Implementations (Strategy Pattern)
When you have genuinely different approaches that coexist:
```
citation_extractor_ast.py      # AST-based implementation
citation_extractor_regex.py    # Regex-based implementation
citation_extractor_mistletoe.py # Mistletoe-based implementation
```

### Temporary Migration Files
Only during active migration, and document removal plan:
```python
# citation_extractor_legacy.py
"""DEPRECATED: Remove after 2024-01-01.
Use citation_extractor.py instead.
"""
```

## For AI Assistants

**NEVER create files with these suffixes:**
- `_new`
- `_v2`, `_v3`, etc.
- `_final`
- `_revised`
- `_updated`
- `_fixed`

**INSTEAD:**
1. Modify the existing file directly
2. Ensure tests pass
3. Commit with descriptive message
4. If refactoring is large, use a feature branch

## If You Find Versioned Files

Clean them up:
```bash
# 1. Determine which is the active version
grep -r "import.*_new" .

# 2. Merge any useful changes into the main file
diff file.py file_new.py

# 3. Update all imports
find . -name "*.py" -exec sed -i 's/file_new/file/g' {} \;

# 4. Delete the versioned file
git rm file_new.py

# 5. Commit
git commit -m "cleanup: merge and remove file_new.py"
```

## Summary

- **One file, one purpose**
- **Git tracks history**
- **Direct modification, not duplication**
- **Clear commit messages instead of filename versions**

Remember: The repository should contain the current working state, not a museum of previous attempts.
