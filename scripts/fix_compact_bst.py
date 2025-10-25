#!/usr/bin/env python3
"""
Fix the compact BST to properly handle DOI, URL, and note fields.
"""

# import re  # Banned - using string methods instead
from pathlib import Path


def fix_compact_bst():
    compact_path = (
        Path(__file__).parent.parent / "templates" / "spbasic_pt_compact.bst"
    )

    with open(compact_path) as f:
        content = f.read()

    # First, let's fix the format.doi function to add the "doi: " prefix
    # Find and replace using string methods
    start_marker = "FUNCTION {format.doi}"
    start_pos = content.find(start_marker)
    if start_pos != -1:
        # Find the end of this function (next closing brace at start of line)
        end_pos = start_pos
        brace_count = 0
        found_start_brace = False

        i = start_pos + len(start_marker)
        while i < len(content):
            if content[i] == "{":
                brace_count += 1
                found_start_brace = True
            elif content[i] == "}":
                brace_count -= 1
                if found_start_brace and brace_count == 0:
                    # Check if this } is at the start of a line (with possible whitespace)
                    j = i - 1
                    while j >= 0 and content[j] in " \t":
                        j -= 1
                    if j < 0 or content[j] == "\n":
                        end_pos = i + 1
                        break
            i += 1

        if end_pos > start_pos:
            new_function = """FUNCTION {format.doi}
{ doi empty$
    { "" }
    { "doi: \\\\href{https://doi.org/" doi * "}{" * doi * "}" * }
  if$
}"""
            content = content[:start_pos] + new_function + content[end_pos:]

    # Fix format.doi.url to not add extra "doi: " prefix
    start_marker = "FUNCTION {format.doi.url}"
    start_pos = content.find(start_marker)
    if start_pos != -1:
        # Find the end of this function
        end_pos = start_pos
        brace_count = 0
        found_start_brace = False

        i = start_pos + len(start_marker)
        while i < len(content):
            if content[i] == "{":
                brace_count += 1
                found_start_brace = True
            elif content[i] == "}":
                brace_count -= 1
                if found_start_brace and brace_count == 0:
                    # Check if this } is at the start of a line
                    j = i - 1
                    while j >= 0 and content[j] in " \t":
                        j -= 1
                    if j < 0 or content[j] == "\n":
                        end_pos = i + 1
                        break
            i += 1

        if end_pos > start_pos:
            new_function = """FUNCTION {format.doi.url}
{ doi empty$
    { url empty$
        { "" }
        { format.url }
      if$
    }
    { format.doi }
  if$
}"""
            content = content[:start_pos] + new_function + content[end_pos:]

    # Now fix the fin.entry function - it should handle notes differently
    start_marker = "FUNCTION {fin.entry}"
    start_pos = content.find(start_marker)
    if start_pos != -1:
        # Find the end of this function
        end_pos = start_pos
        brace_count = 0
        found_start_brace = False

        i = start_pos + len(start_marker)
        while i < len(content):
            if content[i] == "{":
                brace_count += 1
                found_start_brace = True
            elif content[i] == "}":
                brace_count -= 1
                if found_start_brace and brace_count == 0:
                    j = i - 1
                    while j >= 0 and content[j] in " \t":
                        j -= 1
                    if j < 0 or content[j] == "\n":
                        end_pos = i + 1
                        break
            i += 1

        if end_pos > start_pos:
            new_function = """FUNCTION {fin.entry}
{ duplicate$ empty$
    'pop$
    'write$
  if$
  newline$
}"""
            content = content[:start_pos] + new_function + content[end_pos:]

    # We need to add handling for notes in the appropriate place
    # Look for where notes are typically output in articles
    # Let's add a function to handle note output properly
    new_note_function = """
FUNCTION {format.note}
{ note empty$
    { "" }
    { note "Metadata from" #1 #13 substring$ "Metadata from" =
      note "metadata from" #1 #13 substring$ "metadata from" = or
      note "CrossRef" #1 #8 substring$ "CrossRef" = or
      note "crossref" #1 #8 substring$ "crossref" = or
      note "Cross-Ref" #1 #9 substring$ "Cross-Ref" = or
        { "" }
        { note output.state mid.sentence =
            { ", " * note * }
            { note }
          if$
        }
      if$
    }
  if$
}
"""

    # Insert the format.note function after format.note.filtered
    pos = content.find("FUNCTION {format.note.filtered}")
    if pos != -1:
        # Find the end of format.note.filtered
        next_func_pos = content.find("\nFUNCTION", pos + 1)
        if next_func_pos != -1:
            content = (
                content[:next_func_pos]
                + new_note_function
                + content[next_func_pos:]
            )

    # Now we need to add note output in the article function and others
    # But first, let's check if notes are already being output somewhere

    # Add the DOI entry to ENTRY list if not already there
    entry_start = content.find("ENTRY")
    if entry_start != -1:
        entry_end = content.find("}", entry_start)
        entry_section = content[entry_start:entry_end]
        if "doi" not in entry_section:
            # Add doi to the entry list
            content = content[:entry_end] + "    doi\n" + content[entry_end:]

    # Also ensure hyperref package is loaded
    preamble_pos = content.find("FUNCTION {begin.bib}")
    if preamble_pos != -1:
        # Find where hyperref is loaded
        hyperref_check = content.find("\\usepackage{hyperref}", preamble_pos)
        if hyperref_check == -1:
            # Add hyperref package loading
            # Find the pattern using string methods
            search_str = "write$ newline$"
            pos = content.find(search_str, preamble_pos)
            if pos != -1:
                # Look for "\\providecommand" after this position
                next_part = content[
                    pos + len(search_str) : pos + len(search_str) + 100
                ]
                # Skip whitespace and quotes
                i = 0
                while i < len(next_part) and next_part[i] in ' \n\t"':
                    i += 1

                if i < len(next_part) and next_part[i:].startswith(
                    "\\\\providecommand"
                ):
                    # Insert the hyperref loading
                    insert_pos = pos + len(search_str)
                    new_text = """\n  "\\\\IfFileExists{hyperref.sty}{\\\\usepackage{hyperref}}{}"
  write$ newline$"""
                    content = (
                        content[:insert_pos] + new_text + content[insert_pos:]
                    )

    # Write the fixed content
    with open(compact_path, "w") as f:
        f.write(content)

    print(f"Fixed compact bibliography style: {compact_path}")
    return True


if __name__ == "__main__":
    fix_compact_bst()
