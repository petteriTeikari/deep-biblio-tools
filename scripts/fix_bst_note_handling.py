#!/usr/bin/env python3
"""
Fix the BST file to handle note field properly in BibTeX's stack language.
"""

from pathlib import Path


def fix_bst_note_handling():
    compact_path = (
        Path(__file__).parent.parent / "templates" / "spbasic_pt_compact.bst"
    )

    with open(compact_path) as f:
        content = f.read()

    # Replace the problematic note functions with properly formatted ones
    # In BibTeX, field names need to be quoted strings

    # Fix format.note.filtered
    content = content.replace(
        """FUNCTION {format.note.filtered}
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
}""",
        """FUNCTION {format.note.filtered}
{ note empty$
    { "" }
    { note #1 #14 substring$ "Metadata from:" =
      note #1 #14 substring$ "metadata from:" = or
      note #1 #8 substring$ "CrossRef" = or
      note #1 #8 substring$ "crossref" = or
      note #1 #9 substring$ "Cross-Ref" = or
        { "" }
        { note }
      if$
    }
  if$
}""",
    )

    # Fix format.note
    content = content.replace(
        """FUNCTION {format.note}
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
}""",
        """FUNCTION {format.note}
{ note empty$
    { "" }
    { note #1 #13 substring$ "Metadata from" =
      note #1 #13 substring$ "metadata from" = or
      note #1 #8 substring$ "CrossRef" = or
      note #1 #8 substring$ "crossref" = or
      note #1 #9 substring$ "Cross-Ref" = or
        { "" }
        { note output.state mid.sentence =
            { ", " note * }
            { note }
          if$
        }
      if$
    }
  if$
}""",
    )

    # Write the fixed content
    with open(compact_path, "w") as f:
        f.write(content)

    print("Fixed note handling in compact BST")


if __name__ == "__main__":
    fix_bst_note_handling()
