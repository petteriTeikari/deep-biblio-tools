# Temporary Files and Debug Scripts

## Directory Structure

All temporary files, debug scripts, and experiments should be placed in the `tmp/` directory, NOT in the repository root.

```
tmp/
├── .gitignore      # Ignores everything except README
├── README.md       # Usage instructions
├── debug/          # Debug scripts
├── scratch/        # Experiments and drafts
└── cache/          # Temporary cache files
```

## Usage Guidelines

### Creating Debug Scripts

```bash
# WRONG - Don't create in root
python debug_parser.py

# RIGHT - Use tmp/debug/
python tmp/debug/parser_test.py
```

### Running Experiments

```bash
# Create experiment in tmp/scratch/
cp src/module.py tmp/scratch/module_experiment.py
# Edit and test freely
python tmp/scratch/module_experiment.py
```

### Temporary Output

```bash
# Save temporary output to tmp/
python src/main.py > tmp/output.txt
pytest -v > tmp/test_results.txt
```

## Benefits

1. **Clean Repository**: Root directory stays organized
2. **No Accidental Commits**: Everything in `tmp/` is gitignored
3. **Easy Cleanup**: Can delete entire `tmp/` directory anytime
4. **Clear Intent**: Obviously temporary files

## For AI Assistants

When creating debug or test scripts:
- Always use `tmp/debug/` for debug scripts
- Use `tmp/scratch/` for experimental code
- Never create `debug*.py` or `test*.py` in the repository root
- Document any important findings before deleting temp files

## Examples

### Debug Script Template

```python
#!/usr/bin/env python3
"""Debug script for [specific issue].

This script is temporary and should live in tmp/debug/.
"""

# Your debug code here
```

### Moving Existing Files

If you accidentally created files in the root:

```bash
# Move debug files
mv debug*.py tmp/debug/

# Move test outputs
mv test_output.* tmp/

# Move experimental code
mv *_experiment.py tmp/scratch/
```

## Cleanup

Periodically clean the tmp directory:

```bash
# Remove all temporary files (except README and .gitignore)
find tmp -type f -not -name 'README.md' -not -name '.gitignore' -delete

# Remove empty directories
find tmp -type d -empty -delete
```
