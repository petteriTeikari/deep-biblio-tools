# Suggested Emoji Policy Section for Template's CLAUDE.md

Add this section to the claude-code-guardrails-template's `.claude/CLAUDE.md`:

```markdown
### Emoji Usage Policy (CRITICAL - File-Type Specific)

**CORE PRINCIPLE**: Emojis cause unnecessary pre-commit failures in code files. Be file-type aware!

#### FORBIDDEN in Code Files
- **Python files (*.py)**: NEVER use emojis, even in print statements or comments
  - Use `print("[PASS] All tests passed")` NOT `print("✅ All tests passed")`
  - Use `# [TODO] Fix this issue` NOT `# 🔧 Fix this issue`
- **Shell scripts (*.sh)**: NEVER use emojis (terminal compatibility issues)
- **Source code files**: Any language (*.js, *.ts, *.go, *.rs, *.java, etc.)
- **Configuration files**: That are executed or parsed by programs

#### ALLOWED in Documentation
- **Markdown files (*.md)**: Use sparingly for emphasis in docs
- **README files**: Acceptable for project personality
- **Text files (*.txt)**: If used for human-readable notes
- **Comments**: ONLY in markdown files, never in code

#### Required Text Replacements for Code
When you want to use an emoji in code, use these replacements:
```python
# Status Indicators
"✅" → "[PASS]" or "[OK]"
"❌" → "[FAIL]" or "[ERROR]"
"⚠️" → "[WARNING]" or "[WARN]"
"🚀" → "[LAUNCH]" or "[START]"
"🛑" → "[STOP]" or "[HALT]"
"📝" → "[INFO]" or "[NOTE]"
"🔍" → "[DEBUG]" or "[INSPECT]"
"🎯" → "[TARGET]" or "[GOAL]"
"💡" → "[TIP]" or "[HINT]"
"🔧" → "[FIX]" or "[TODO]"
"📦" → "[PACKAGE]" or "[MODULE]"
"🧪" → "[TEST]" or "[CHECK]"
"📊" → "[STATS]" or "[METRICS]"
"🔒" → "[SECURE]" or "[LOCKED]"
"🗑️" → "[DELETE]" or "[REMOVE]"
```

#### Examples of Correct Usage

**Python file (script.py)** - NO EMOJIS:
```python
def validate_input(data):
    if not data:
        print("[FAIL] No data provided")
        return False
    print("[PASS] Validation successful")
    return True
```

**Markdown file (README.md)** - EMOJIS OK:
```markdown
# 🚀 My Awesome Project

✅ Fast and reliable
❌ No external dependencies
```

#### Pre-commit Enforcement
- The `no-emojis` pre-commit hook WILL fail if emojis are found in code files
- This is NOT negotiable - it ensures cross-platform compatibility
- Run `python scripts/remove_emojis.py` to automatically clean files

#### RATIONALE
1. **Terminal Compatibility**: Not all terminals handle emojis correctly
2. **CI/CD Systems**: May have issues with Unicode in logs
3. **Code Review**: Emojis can be distracting in code reviews
4. **Professionalism**: Production code should use clear text indicators
5. **Parsing**: Log parsers work better with consistent text patterns
```

## Implementation in Template

1. Add this section to `.claude/CLAUDE.md` after the "Forbidden Actions" section
2. Update the `no-emojis` pre-commit hook to be file-type aware
3. Add the text replacement mapping to `hooks/generators/`
4. Include in the guardrails validation
