# Editor Linting Integration Guide

This document provides setup instructions for integrating linting and code quality tools with popular code editors, ensuring consistent code style and automatic enforcement of project standards.

## Overview

Deep-biblio-tools uses several code quality tools:
- **Ruff**: Fast Python linter and formatter
- **Pre-commit hooks**: Automatic validation on git commits
- **Import sorting**: Enforces stdlib → third-party → local import order
- **No-regex policy**: Custom enforcement for our regex-free codebase

## Windsurf/VSCode Setup

### 1. Install Required Extensions

**Ruff Extension (Primary)**
```
Name: Ruff
ID: charliefriedman.ruff-vscode
Publisher: Astral Software
```

**Optional but Recommended**
```
Name: Python
ID: ms-python.python
Publisher: Microsoft
```

### 2. Configure User Settings

Open VSCode settings (Ctrl/Cmd + Shift + P → "Preferences: Open Settings (JSON)") and add:

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliefriedman.ruff-vscode",
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    },
    "editor.formatOnSave": true,
    "editor.formatOnPaste": true
  },
  "ruff.lint.enable": true,
  "ruff.format.enable": true,
  "ruff.showNotifications": "always",
  "ruff.args": ["--config=pyproject.toml"],
  "ruff.logLevel": "info"
}
```

### 3. Project-Specific Settings

Create `.vscode/settings.json` in your project root:

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "ruff.args": [
    "--config=pyproject.toml",
    "--select=I,E,W,F",
    "--ignore=COM812,ISC001"
  ],
  "ruff.lint.args": ["--config=pyproject.toml"],
  "files.associations": {
    "*.bib": "bibtex",
    "*.cls": "latex",
    "*.sty": "latex"
  },
  "python.terminal.activateEnvironment": true
}
```

### 4. Real-time Features

Once configured, you'll get:

**Immediate Feedback**
- Red squiggles for linting errors
- Yellow squiggles for warnings
- Blue squiggles for style suggestions

**Auto-fix on Save**
- Import organization (stdlib → third-party → local)
- Code formatting (line length, spacing)
- Quote style normalization
- Trailing whitespace removal

**Manual Actions**
- Right-click → "Quick Fix" for suggested solutions
- Ctrl/Cmd + Shift + P → "Ruff: Fix all auto-fixable problems"
- Ctrl/Cmd + Shift + P → "Ruff: Format document"

### 5. Troubleshooting

**Extension Not Working**
1. Check Python interpreter is set correctly
2. Verify ruff is installed: `pip install ruff`
3. Reload VSCode window: Ctrl/Cmd + Shift + P → "Developer: Reload Window"

**Import Errors**
- Ensure virtual environment is activated
- Check PYTHONPATH in terminal: `echo $PYTHONPATH`
- Verify project structure matches imports

**Settings Not Applied**
- Check for syntax errors in settings.json
- Try workspace settings instead of user settings
- Restart VSCode after major changes

## PyCharm/IntelliJ IDEA Setup

### 1. Install Ruff Plugin

1. Go to File → Settings → Plugins
2. Search for "Ruff"
3. Install the official Ruff plugin
4. Restart IDE

### 2. Configure Ruff Integration

1. Go to File → Settings → Tools → Ruff
2. Set Ruff executable path: `/path/to/venv/bin/ruff`
3. Enable "Run ruff on file save"
4. Set configuration file: `pyproject.toml`

### 3. Import Optimization

1. Go to File → Settings → Editor → Code Style → Python → Imports
2. Enable "Optimize imports on the fly"
3. Set import layout:
   ```
   import <standard library>
   <blank line>
   import <third-party>
   <blank line>
   from <project> import <modules>
   ```

## Vim/Neovim Setup

### 1. Using ALE (Asynchronous Lint Engine)

Add to your `.vimrc` or `init.vim`:

```vim
" Install ALE if not already installed
" Plug 'dense-analysis/ale'

let g:ale_linters = {
\\   'python': ['ruff'],
\\}

let g:ale_fixers = {
\\   'python': ['ruff'],
\\}

let g:ale_fix_on_save = 1
let g:ale_python_ruff_options = '--config pyproject.toml'
```

### 2. Using Native LSP (Neovim 0.5+)

```lua
-- In your init.lua
require('lspconfig').ruff_lsp.setup{
  init_options = {
    settings = {
      args = {'--config=pyproject.toml'},
    }
  }
}
```

## Emacs Setup

### 1. Using Flycheck

Add to your `.emacs` or `init.el`:

```elisp
(use-package flycheck
  :ensure t
  :init (global-flycheck-mode))

(use-package flycheck-ruff
  :ensure t
  :after flycheck
  :config
  (add-hook 'python-mode-hook
    (lambda ()
      (setq flycheck-python-ruff-config "pyproject.toml")
      (flycheck-select-checker 'python-ruff))))
```

## Sublime Text Setup

### 1. Install SublimeLinter

1. Install Package Control if not already installed
2. Install SublimeLinter: Ctrl/Cmd + Shift + P → "Package Control: Install Package" → "SublimeLinter"
3. Install SublimeLinter-ruff: "Package Control: Install Package" → "SublimeLinter-ruff"

### 2. Configure Settings

Add to Sublime Text settings:

```json
{
  "SublimeLinter.linters.ruff.args": ["--config=pyproject.toml"],
  "SublimeLinter.linters.ruff.executable": "/path/to/venv/bin/ruff"
}
```

## Command Line Integration

For any editor, you can also run linting manually:

### Basic Commands

```bash
# Check all files
ruff check .

# Fix auto-fixable issues
ruff check . --fix

# Format code
ruff format .

# Check specific file
ruff check src/core/biblio_checker.py

# Show configuration
ruff config
```

### Pre-commit Integration

Our project includes pre-commit hooks that run automatically:

```bash
# Install pre-commit hooks (one-time setup)
pre-commit install

# Run hooks manually
pre-commit run --all-files

# Run specific hook
pre-commit run ruff

# Skip hooks temporarily (not recommended)
git commit --no-verify
```

## Project-Specific Standards

### Import Order

Our project enforces this import structure:
```python
# 1. Standard library imports
import os
import sys
from pathlib import Path

# 2. Third-party imports
import requests
from tqdm import tqdm

# 3. Local imports
from .core import BiblioChecker
from ..utils import validate_doi
```

### Regex Policy

We maintain a **strict no-regex policy**:
- ❌ `import re` is banned
- ❌ `re.search()`, `re.findall()` are prohibited
- ✅ Use string methods: `text.startswith()`, `text.find()`
- ✅ Use AST parsers: `markdown-it-py`, `pylatexenc`

Your editor will highlight regex usage as violations.

### File Naming

Avoid version suffixes in filenames:
- ❌ `parser_new.py`, `module_v2.py`, `file_final.py`
- ✅ Use git for version control instead

## Integration Testing

To verify your setup works correctly:

### 1. Create a Test File

```python
# test_linting.py
import sys
import re  # Should trigger violation
from tqdm import tqdm
import os  # Should be reordered

def test_function( ):  # Should fix spacing
    text="hello world"  # Should add spaces
    if text.find( "hello" )>=0:  # Should be cleaned up
        print("found")
    return True
```

### 2. Expected Behavior

Your editor should:
- Show red squiggles on `import re`
- Reorder imports automatically
- Fix spacing issues on save
- Show import order violations

### 3. Manual Verification

```bash
# Run linting
ruff check test_linting.py

# Should output violations and suggestions
# Fix automatically
ruff check test_linting.py --fix
```

## Support and Troubleshooting

### Common Issues

**"Ruff not found" Error**
- Ensure ruff is installed in your Python environment
- Check PATH includes your virtual environment
- Verify editor is using correct Python interpreter

**Import Errors in Editor**
- Check PYTHONPATH environment variable
- Verify project root is properly detected
- Ensure __init__.py files exist in package directories

**Pre-commit Hooks Failing**
- Run `pre-commit install` to set up hooks
- Check `.pre-commit-config.yaml` is present
- Verify all required tools are installed

### Getting Help

1. **Project Documentation**: See `docs/development/` for more guides
2. **Ruff Documentation**: https://docs.astral.sh/ruff/
3. **VSCode Python**: https://code.visualstudio.com/docs/python/
4. **Pre-commit**: https://pre-commit.com/

### Contributing

When contributing to this project:
1. Set up linting integration as described above
2. Ensure all pre-commit hooks pass
3. Follow the no-regex policy strictly
4. Use proper import organization
5. Test your changes with `ruff check . --fix`

## Summary

Proper editor integration provides:
- ✅ Real-time error detection
- ✅ Automatic code formatting
- ✅ Import organization
- ✅ Consistent code style
- ✅ Policy enforcement (no-regex, file naming)
- ✅ Reduced manual work

This setup ensures code quality and consistency across the entire development team.
