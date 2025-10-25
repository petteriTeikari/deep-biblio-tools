#!/usr/bin/env python3
"""Simple conversion of DronePosition.md to LaTeX without metadata fetching."""

# import re  # Banned - using string methods instead
import sys
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import pypandoc  # noqa: E402, I001


def clean_citations(content):
    """Replace markdown citations with LaTeX citations."""
    result = []
    i = 0

    while i < len(content):
        # Look for pattern [text](url)
        if content[i] == "[" and i < len(content) - 1:
            # Find the closing ]
            j = i + 1
            bracket_count = 1
            while j < len(content) and bracket_count > 0:
                if content[j] == "[":
                    bracket_count += 1
                elif content[j] == "]":
                    bracket_count -= 1
                j += 1

            if bracket_count == 0 and j < len(content) and content[j] == "(":
                # Found potential citation, extract text
                text = content[i + 1 : j - 1]

                # Find closing )
                k = j + 1
                paren_count = 1
                while k < len(content) and paren_count > 0:
                    if content[k] == "(":
                        paren_count += 1
                    elif content[k] == ")":
                        paren_count -= 1
                    k += 1

                if paren_count == 0:
                    # Found complete citation pattern
                    # Extract year from text
                    year = None
                    year_start = -1

                    # Look for 4-digit year starting with 19 or 20
                    for idx in range(len(text) - 3):
                        if (
                            text[idx : idx + 2] in ["19", "20"]
                            and text[idx : idx + 4].isdigit()
                            and (idx == 0 or not text[idx - 1].isdigit())
                            and (
                                idx + 4 >= len(text)
                                or not text[idx + 4].isdigit()
                            )
                        ):
                            year = text[idx : idx + 4]
                            year_start = idx
                            break

                    if year:
                        # Extract authors (everything before the year)
                        authors_part = text[:year_start].strip()
                        # Remove trailing parenthesis and spaces
                        while authors_part and authors_part[-1] in " (":
                            authors_part = authors_part[:-1]

                        # Generate citation key
                        first_author = (
                            authors_part.split()[0]
                            if authors_part
                            else "unknown"
                        )
                        # Keep only letters
                        first_author_clean = "".join(
                            c for c in first_author if c.isalpha()
                        ).lower()
                        key = f"{first_author_clean}{year}"
                    else:
                        # No year found, use cleaned text
                        key = "".join(c for c in text if c.isalnum()).lower()[
                            :20
                        ]

                    # Add LaTeX citation
                    result.append(f"\\cite{{{key}}}")
                    i = k
                    continue

        result.append(content[i])
        i += 1

    return "".join(result)


def main():
    """Convert DronePosition.md to LaTeX using simple approach."""
    # Input file
    input_file = project_root / "drone_data" / "DronePosition.md"

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return 1

    # Output directory
    output_dir = project_root / "drone_data" / "latex_output_simple"
    output_dir.mkdir(exist_ok=True)

    # Read markdown content
    print("Reading markdown file...")
    with open(input_file, encoding="utf-8") as f:
        content = f.read()

    # Extract title and abstract
    lines = content.split("\n")
    title = None
    abstract = None
    abstract_lines = []
    in_abstract = False

    for i, line in enumerate(lines):
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif (
            line.lstrip().lower().startswith("#")
            and "abstract" in line.lower().strip("#").strip()
        ):
            in_abstract = True
            continue
        elif in_abstract and line.lstrip().startswith("#"):
            in_abstract = False
            abstract = "\n".join(abstract_lines).strip()
            break
        elif in_abstract:
            abstract_lines.append(line)

    # Clean title
    if title:
        # Remove bold markers
        while "**" in title:
            start = title.find("**")
            if start >= 0:
                end = title.find("**", start + 2)
                if end >= 0:
                    title = (
                        title[:start]
                        + title[start + 2 : end]
                        + title[end + 2 :]
                    )
                else:
                    break
        content = content.replace(f"# {title}", "", 1)  # Remove from content

    # Remove abstract from content if found
    if abstract:
        # Find and remove abstract section
        lines = content.split("\n")
        new_lines = []
        skip_abstract = False

        for line in lines:
            if (
                line.lstrip().lower().startswith("#")
                and "abstract" in line.lower().strip("#").strip()
            ):
                skip_abstract = True
                continue
            elif skip_abstract and line.lstrip().startswith("#"):
                skip_abstract = False

            if not skip_abstract:
                new_lines.append(line)

        content = "\n".join(new_lines)

    # Clean citations
    print("Processing citations...")
    content = clean_citations(content)

    # Convert to LaTeX using pandoc
    print("Converting with pandoc...")
    latex_body = pypandoc.convert_text(
        content,
        "latex",
        format="markdown+tex_math_dollars+raw_tex",
        extra_args=[
            "--wrap=preserve",
            "--columns=80",
        ],
    )

    # Build LaTeX document
    print("Building LaTeX document...")
    latex_doc = r"""\documentclass[11pt,twocolumn]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\geometry{
    a4paper,
    margin=1in,
    columnsep=0.25in
}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{url}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{listings}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{array}
\usepackage{multirow}
\usepackage{natbib}
\bibliographystyle{spbasic_pt}

"""

    # Add title and author
    if title:
        latex_doc += f"\\title{{{title}}}\n"
    latex_doc += r"\author{Petteri Teikari \and Mike Jarrell \and Irene Bandera Moreno \and Harri Pesola}"
    latex_doc += "\n\\date{\\today}\n\n"

    latex_doc += "\\begin{document}\n"
    latex_doc += "\\maketitle\n\n"

    # Add abstract
    if abstract:
        latex_doc += "\\begin{abstract}\n"
        latex_doc += abstract
        latex_doc += "\n\\end{abstract}\n\n"

    # Add body content
    latex_doc += latex_body

    # Add bibliography
    latex_doc += "\n\\bibliography{references}\n"
    latex_doc += "\\end{document}\n"

    # Write LaTeX file
    output_file = output_dir / "DronePosition_simple.tex"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(latex_doc)

    print(f"LaTeX file written to: {output_file}")

    # Create a simple BibTeX file with placeholder entries
    print("Creating placeholder bibliography...")
    bib_file = output_dir / "references.bib"
    with open(bib_file, "w", encoding="utf-8") as f:
        f.write("% Placeholder bibliography entries\n")
        f.write(
            "% Run the full converter to get complete bibliography with metadata\n\n"
        )

        # Extract unique citation keys from the LaTeX content
        citation_keys = set()
        i = 0
        while i < len(latex_doc):
            if latex_doc[i : i + 6] == "\\cite{":
                j = i + 6
                while j < len(latex_doc) and latex_doc[j] != "}":
                    j += 1
                if j < len(latex_doc):
                    citation_keys.add(latex_doc[i + 6 : j])
                    i = j
                else:
                    i += 1
            else:
                i += 1

        for key in sorted(citation_keys):
            f.write(f"@misc{{{key},\n")
            f.write(f"  title = {{Reference {key}}},\n")
            f.write("  author = {Author},\n")
            f.write("  year = {2025},\n")
            f.write("  note = {Placeholder entry}\n")
            f.write("}\n\n")

    print(f"Bibliography file written to: {bib_file}")
    print(f"Total citations: {len(citation_keys)}")

    # Copy bibliography style file
    import shutil

    bst_source = project_root / "templates" / "spbasic_pt.bst"
    if not bst_source.exists():
        bst_source = project_root / "spbasic_pt.bst"

    if bst_source.exists():
        bst_dest = output_dir / "spbasic_pt.bst"
        shutil.copy2(bst_source, bst_dest)
        print(f"Bibliography style copied to: {bst_dest}")

    # Create Makefile
    makefile_content = """# Makefile for compiling LaTeX document

MAIN = DronePosition_simple
LATEX = pdflatex
BIBTEX = bibtex

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex references.bib
\t$(LATEX) $(MAIN)
\t$(BIBTEX) $(MAIN)
\t$(LATEX) $(MAIN)
\t$(LATEX) $(MAIN)

clean:
\trm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out

.PHONY: all clean
"""

    makefile_path = output_dir / "Makefile"
    with open(makefile_path, "w") as f:
        f.write(makefile_content)

    print(f"Makefile written to: {makefile_path}")
    print("\nConversion complete!")
    print(f"To compile PDF: cd {output_dir} && make")

    return 0


if __name__ == "__main__":
    sys.exit(main())
