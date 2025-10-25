#!/usr/bin/env python3
"""
Create a simpler compact BST that focuses on DOI/URL handling and arXiv formatting.
"""

from pathlib import Path


def create_simple_compact_bst():
    # Start fresh from the original
    bst_path = Path(__file__).parent.parent / "templates" / "spbasic_pt.bst"
    compact_path = (
        Path(__file__).parent.parent / "templates" / "spbasic_pt_compact.bst"
    )

    with open(bst_path) as f:
        content = f.read()

    # Update the header
    content = content.replace(
        "%% This is file `spbasic.bst',",
        "%% This is file `spbasic_pt_compact.bst',",
    )
    content = content.replace(
        "%% For Springer medical",
        "%% Compact version with cleaner DOI/URL handling\n%% For Springer medical",
    )

    # Find format.url function and add our new functions after it
    format_url_pos = content.find("FUNCTION {format.url}")
    next_func_pos = content.find("\nFUNCTION", format_url_pos + 1)

    # Add DOI handling that creates hyperlinks
    new_functions = """
FUNCTION {format.doi}
{ doi empty$
    { "" }
    { "doi: \\href{https://doi.org/" doi * "}{" * doi * "}" * }
  if$
}

FUNCTION {format.doi.url}
{ doi empty$
    { url empty$
        { "" }
        { url "https://doi.org/" doi * =
          url "http://doi.org/" doi * = or
          url "https://dx.doi.org/" doi * = or
            { "" }  % Skip redundant DOI URL
            { format.url }
          if$
        }
      if$
    }
    { format.doi }
  if$
}

FUNCTION {format.eprint.arxiv}
{ eprint empty$
    { "" }
    { "\\href{https://arxiv.org/abs/" eprint * "}{arXiv: " * eprint * "}" * }
  if$
}
"""

    # Insert new functions
    content = content[:next_func_pos] + new_functions + content[next_func_pos:]

    # Replace format.url output with format.doi.url output
    content = content.replace("format.url output", "format.doi.url output")

    # Replace format.eprint output with format.eprint.arxiv output
    content = content.replace(
        "format.eprint output", "format.eprint.arxiv output"
    )

    # Add hyperref and URL handling to the preamble
    preamble_pos = content.find("FUNCTION {begin.bib}")
    if preamble_pos != -1:
        # Find the write$ commands in begin.bib
        end_bib_pos = content.find("FUNCTION {end.bib}", preamble_pos)
        begin_bib_section = content[preamble_pos:end_bib_pos]

        # Add hyperref loading if not present
        if "hyperref" not in begin_bib_section:
            content = content.replace(
                '"\\providecommand{\\urlprefix}{URL }"',
                '"\\IfFileExists{hyperref.sty}{\\usepackage{hyperref}}{}"'
                "\n  write$ newline$\n"
                '  "\\providecommand{\\urlprefix}{URL }"',
            )

    with open(compact_path, "w") as f:
        f.write(content)

    print("Created simple compact bibliography style")
    return True


if __name__ == "__main__":
    create_simple_compact_bst()
