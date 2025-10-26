#!/usr/bin/env python3
"""Find citations in .tex that are missing from .bib"""

# import re  # Banned - using manual parsing instead

tex_file = "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v3.tex"
bib_file = "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/references.bib"

# Extract citation keys from .tex
with open(tex_file) as f:
    tex_content = f.read()

# Find all \citep{...} and \citet{...} commands using manual parsing
tex_keys = set()
i = 0
while i < len(tex_content):
    if tex_content[i : i + 6] in ("\\citep", "\\citet"):
        # Find opening brace
        brace_start = tex_content.find("{", i)
        if brace_start == -1:
            break
        # Find matching closing brace
        brace_end = tex_content.find("}", brace_start)
        if brace_end == -1:
            break
        # Extract citation keys
        keys_str = tex_content[brace_start + 1 : brace_end]
        # Split by comma for multiple citations
        keys = [k.strip() for k in keys_str.split(",")]
        tex_keys.update(keys)
        i = brace_end + 1
    else:
        i += 1

print(f"Total unique citation keys in .tex: {len(tex_keys)}")

# Extract citation keys from .bib
with open(bib_file) as f:
    bib_content = f.read()

# Extract BibTeX keys using manual parsing
bib_keys = set()
for line in bib_content.split("\n"):
    line = line.strip()
    if line.startswith("@"):
        # Find opening brace
        brace_start = line.find("{")
        if brace_start == -1:
            continue
        # Find comma after key
        comma_pos = line.find(",", brace_start)
        if comma_pos == -1:
            continue
        # Extract key
        key = line[brace_start + 1 : comma_pos].strip()
        bib_keys.add(key)

print(f"Total entries in .bib: {len(bib_keys)}")

# Find missing
missing = tex_keys - bib_keys

print(f"\nMissing citations: {len(missing)}")
print("=" * 80)

for key in sorted(missing):
    print(f"  - {key}")

# Find unused (in bib but not cited)
unused = bib_keys - tex_keys
print(f"\nUnused bib entries: {len(unused)}")
