#!/usr/bin/env python3
"""
Create a compact version of spbasic_pt.bst that:
1. Formats DOIs as hyperlinks without redundant URLs
2. Removes metadata notes
3. Formats arXiv entries properly
"""

# import re  # Banned - using string methods instead
import sys
from pathlib import Path


def create_compact_bst():
    # Read the original BST file
    bst_path = Path(__file__).parent.parent / "templates" / "spbasic_pt.bst"
    compact_path = (
        Path(__file__).parent.parent / "templates" / "spbasic_pt_compact.bst"
    )

    with open(bst_path) as f:
        content = f.read()

    # Add new functions after the format.url function
    format_url_pos = content.find("FUNCTION {format.url}")
    if format_url_pos == -1:
        print("Error: Could not find format.url function")
        return False

    # Find the end of format.url function
    next_function_pos = content.find("\nFUNCTION", format_url_pos + 1)

    # Insert new functions for DOI and note handling
    new_functions = """
FUNCTION {format.doi}
{ doi empty$
    { "" }
    { "\\href{https://doi.org/" doi * "}{" * doi * "}" * }
  if$
}

FUNCTION {format.doi.url}
{ doi empty$
    { url empty$
        { "" }
        { format.url }
      if$
    }
    { "doi: " format.doi * }
  if$
}

FUNCTION {should.skip.url}
{ doi empty$
    { #0 }  % false - don't skip if no DOI
    { url empty$
        { #0 }  % false - don't skip if no URL
        { url "https://doi.org/" doi * =
          url "http://doi.org/" doi * = or
          url "https://dx.doi.org/" doi * = or
          url "http://dx.doi.org/" doi * = or
        }  % true if URL is just DOI link
      if$
    }
  if$
}

FUNCTION {format.eprint.compact}
{ eprint duplicate$ empty$
    'skip$
    { archive empty$
        { "\\href{https://arxiv.org/abs/" eprint * "}{arXiv: " * eprint * "}" * }
        { archive "arXiv" =
            { "\\href{https://arxiv.org/abs/" eprint * "}{arXiv: " * eprint * "}" * }
            { "\\eprint[" archive * "]{" * eprint * "}" * }
          if$
        }
      if$
    }
  if$
}

FUNCTION {format.note.filtered}
{ note empty$
    { "" }
    { note "Metadata from:" #1 #14 substring$ "Metadata from:" =
      note "metadata from:" #1 #14 substring$ "metadata from:" = or
      note "CrossRef" #1 #8 substring$ "CrossRef" = or
      note "crossref" #1 #8 substring$ "crossref" = or
        { "" }  % Skip metadata notes
        { note }
      if$
    }
  if$
}
"""

    # Insert the new functions
    content = (
        content[:next_function_pos]
        + new_functions
        + content[next_function_pos:]
    )

    # Replace format.url output with format.doi.url output in all entry types
    content = content.replace("format.url output", "format.doi.url output")

    # Replace format.eprint with format.eprint.compact
    content = content.replace(
        "format.eprint output", "format.eprint.compact output"
    )

    # Find and modify the fin.entry function to handle notes
    fin_start = content.find("FUNCTION {fin.entry}")
    if fin_start != -1:
        # Find the end of this function
        brace_count = 0
        found_start_brace = False
        i = fin_start + len("FUNCTION {fin.entry}")

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
                        fin_end = i + 1
                        break
            i += 1

        if fin_end > fin_start:
            old_fin_entry = content[fin_start:fin_end]
            # Add note filtering before fin.entry
            new_fin_entry = """FUNCTION {fin.entry}
{ format.note.filtered "note" output.check
  duplicate$ empty$
    'pop$
    'write$
  if$
  newline$
}"""
            content = content.replace(old_fin_entry, new_fin_entry)

    # Update the header comment
    content = content.replace(
        "%% This is file `spbasic.bst',",
        "%% This is file `spbasic_pt_compact.bst',",
    )
    content = content.replace(
        "%% For Springer medical",
        "%% Compact version of spbasic_pt.bst with cleaner DOI/URL handling\n%% For Springer medical",
    )

    # Write the modified content
    with open(compact_path, "w") as f:
        f.write(content)

    print(f"Created compact bibliography style: {compact_path}")
    return True


if __name__ == "__main__":
    if create_compact_bst():
        sys.exit(0)
    else:
        sys.exit(1)
