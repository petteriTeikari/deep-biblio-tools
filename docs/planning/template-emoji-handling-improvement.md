# Template Emoji Handling Improvement Plan

## Problem Statement

The current Claude Code guardrails template allows emojis in Python files, which causes unnecessary pre-commit failures. Emojis should be restricted to specific file types where they're appropriate (markdown, documentation).

## Current Behavior

- Template's `.claude/CLAUDE.md` doesn't differentiate emoji usage by file type
- Pre-commit hook catches emojis in all files
- Leads to frequent failures for AI-generated Python code with status indicators

## Proposed Solution

### 1. Update Template's CLAUDE.md

Add clear file-type-specific emoji policies:

```markdown
## Emoji Usage Policy (File-Type Specific)

### ALLOWED in these files:
- **Markdown files (*.md)**: Documentation, READMEs, planning docs
- **Text files (*.txt)**: Notes, changelogs
- **JSON/YAML configs**: Where used for display purposes
- **Comments in code**: ONLY if essential for clarity

### FORBIDDEN in these files:
- **Python files (*.py)**: Use text indicators like [PASS], [FAIL], [INFO]
- **Shell scripts (*.sh)**: Use text indicators
- **Source code**: Any production code files
- **Test files**: Keep output clean and parseable

### Text Indicator Replacements:
Instead of emojis, use these text indicators in code:
- ✅ → [PASS] or [OK]
- ❌ → [FAIL] or [ERROR]
- ⚠️ → [WARNING] or [WARN]
- 📝 → [INFO] or [NOTE]
- 🔍 → [DEBUG] or [CHECK]
- 🎯 → [TARGET] or [GOAL]
- 💡 → [TIP] or [HINT]
```

### 2. Enhance Pre-commit Hook

Update the emoji check to be file-type aware:

```python
# scripts/check_no_emojis.py
EMOJI_ALLOWED_EXTENSIONS = {'.md', '.txt', '.rst'}
EMOJI_FORBIDDEN_EXTENSIONS = {'.py', '.sh', '.js', '.ts', '.go', '.rs'}

def check_file(filepath):
    ext = Path(filepath).suffix

    # Skip if extension allows emojis
    if ext in EMOJI_ALLOWED_EXTENSIONS:
        return []

    # Extra strict for code files
    if ext in EMOJI_FORBIDDEN_EXTENSIONS:
        # Check entire file, including comments
        return find_emojis(filepath, check_comments=True)
```

### 3. Add AI Context Hints

Create `.claude/emoji-policy.yaml`:

```yaml
# Emoji usage policy for AI assistants
file_policies:
  python:
    allowed: false
    alternatives:
      success: "[PASS]"
      failure: "[FAIL]"
      warning: "[WARNING]"
      info: "[INFO]"

  markdown:
    allowed: true
    guidelines: "Use sparingly for emphasis"

  shell:
    allowed: false
    reason: "May break in some terminals"

enforcement:
  pre_commit: strict
  ai_reminder: "Check file type before using emojis"
```

### 4. Generator Updates

Update template generators to include emoji-free status messages:

```python
# hooks/generators/python_generator.py
STATUS_INDICATORS = {
    'success': '[PASS]',
    'failure': '[FAIL]',
    'warning': '[WARNING]',
    'info': '[INFO]',
    'debug': '[DEBUG]',
}
```

### 5. Template Post-Generation Hook

Add automatic emoji removal for generated Python files:

```python
# hooks/post_gen_project.py
def ensure_no_emojis_in_code():
    """Remove any emojis from generated Python/shell files."""
    code_patterns = ['**/*.py', '**/*.sh', '**/*.js']

    for pattern in code_patterns:
        for file in Path('.').glob(pattern):
            content = file.read_text(encoding='utf-8')
            if has_emojis(content):
                cleaned = remove_emojis(content)
                file.write_text(cleaned, encoding='utf-8')
```

## Implementation Priority

1. **Immediate**: Update CLAUDE.md with file-type-specific rules
2. **Next**: Enhance pre-commit hook to be file-type aware
3. **Later**: Add context hints and generator updates

## Expected Benefits

1. No more unnecessary emoji-related commit failures
2. Clear guidance for AI on where emojis are appropriate
3. Cleaner, more professional code output
4. Better cross-platform compatibility

## Migration Path

For existing projects:
1. Run emoji removal script on all code files
2. Update pre-commit configuration
3. Communicate new policy in team docs
