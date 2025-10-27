"""LaTeX document builder for markdown to LaTeX conversion."""

import logging

# import re  # Banned - using string methods instead
from datetime import datetime
from pathlib import Path

from src.converters.md_to_latex.utils import clean_pandoc_output

logger = logging.getLogger(__name__)


class LatexBuilder:
    """Builds LaTeX documents with proper structure and formatting."""

    def __init__(
        self,
        title: str | None = None,
        author: str | None = None,
        abstract: str | None = None,
        document_class: str = "article",
        arxiv_ready: bool = True,
        two_column: bool = True,
        bibliography_style: str | None = None,
        font_size: str = "10pt",
    ):
        self.title = title
        self.author = author
        self.abstract = abstract
        self.document_class = document_class
        self.arxiv_ready = arxiv_ready
        self.two_column = two_column
        self.bibliography_style = bibliography_style
        self.font_size = font_size
        self.additional_packages: list[str] = []
        self.custom_commands: list[str] = []

    def add_packages(self, packages: list[str]) -> None:
        """Add additional LaTeX packages."""
        self.additional_packages.extend(packages)

    def add_custom_commands(self, commands: list[str]) -> None:
        """Add custom LaTeX commands."""
        self.custom_commands.extend(commands)

    def build_preamble(self) -> str:
        """Build LaTeX document preamble."""
        lines = []

        # Document class with optional two-column layout
        options = []
        if self.arxiv_ready:
            options.extend([self.font_size, "a4paper"])
        if self.two_column:
            options.append("twocolumn")

        if options:
            lines.append(
                f"\\documentclass[{','.join(options)}]{{{self.document_class}}}"
            )
        else:
            lines.append(f"\\documentclass{{{self.document_class}}}")

        lines.append("")

        # Essential packages (hyperref will be loaded later, near the end)
        essential_packages = [
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage[T1]{fontenc}",
            "\\usepackage{amsmath,amssymb,amsfonts}",
            "\\usepackage{graphicx}",
            "\\usepackage[dvipsnames]{xcolor}",  # Added dvipsnames option for named colors
            "\\usepackage[english]{babel}",
            "\\usepackage{geometry}",
            "\\usepackage{microtype}",  # Added for better typography
            "\\usepackage{listings}",
            "\\usepackage{caption}",
            "\\usepackage{subcaption}",
            "\\usepackage{booktabs}",
            "\\usepackage{longtable}",  # For long tables
            "\\usepackage{multirow}",
            "\\usepackage{array}",
            "\\usepackage{float}",
            "\\usepackage{textcomp}",  # For special symbols
        ]

        # Add balance package only for two-column layout
        if self.two_column:
            essential_packages.append(
                "\\usepackage{balance}"
            )  # Balance columns on last page

        # Add all essential packages
        lines.extend(essential_packages)
        lines.append("")

        # Geometry settings for tight margins (non-draft)
        if self.arxiv_ready:
            # Tight margins for maximum content density
            lines.append(
                "\\geometry{top=0.75in, bottom=0.75in, left=0.75in, right=0.75in, columnsep=0.25in}"
            )
            lines.append("")

        # Bibliography packages
        if self.bibliography_style:
            # Use traditional BibTeX with custom .bst style
            bibliography_packages = [
                "\\usepackage[authoryear,round]{natbib}",
                "",
            ]
        else:
            # Use BibLaTeX (default)
            bibliography_packages = [
                "\\usepackage[backend=biber,style=authoryear-comp,natbib=true]{biblatex}",
                "\\addbibresource{references.bib}",
                "",
                "% Remove all bold formatting from citations",
                "\\renewcommand*{\\mkbibnamefamily}[1]{\\textnormal{#1}}",
                "\\renewcommand*{\\mkbibnamegiven}[1]{\\textnormal{#1}}",
                "\\renewcommand*{\\mkbibnameprefix}[1]{\\textnormal{#1}}",
                "\\renewcommand*{\\mkbibnamesuffix}[1]{\\textnormal{#1}}",
                "",
                "% Redefine citation commands to remove bold",
                "\\DeclareCiteCommand{\\citep}[\\mkbibparens]",
                "  {\\usebibmacro{prenote}}",
                "  {\\usebibmacro{citeindex}%",
                "   \\printtext{\\bibhyperref{\\printnames{labelname}%",
                "   \\setunit{\\nameyeardelim}%",
                "   \\printfield{year}\\printfield{extrayear}}}}",
                "  {\\multicitedelim}",
                "  {\\usebibmacro{postnote}}",
                "",
                "% Ensure year is not bold",
                "\\DeclareFieldFormat{year}{\\textnormal{#1}}",
                "\\DeclareFieldFormat{extrayear}{\\textnormal{#1}}",
                "\\DeclareFieldFormat{labelyear}{\\textnormal{#1}}",
                "\\DeclareFieldFormat{labelendyear}{\\textnormal{#1}}",
            ]
        lines.append("")
        lines.extend(bibliography_packages)
        lines.append("")

        # Add additional packages, but filter out duplicates
        if self.additional_packages:
            # Remove duplicate tcolorbox loading
            filtered_packages = []
            for pkg in self.additional_packages:
                # Skip if it's a tcolorbox package that's not the first one
                if "tcolorbox" in pkg and any(
                    "tcolorbox" in p for p in filtered_packages
                ):
                    continue
                filtered_packages.append(pkg)

            if filtered_packages:
                lines.extend(filtered_packages)
                lines.append("")

        # Hyperref - should be loaded after most other packages
        lines.append("\\usepackage{hyperref}")
        lines.extend(
            [
                "\\hypersetup{",
                "    colorlinks=true,",
                "    linkcolor=NavyBlue,",
                "    citecolor=NavyBlue,",
                "    urlcolor=NavyBlue",
                "}",
                "",
            ]
        )

        # Custom commands for symbols not available in text mode
        # Use \providecommand to avoid redefinition errors (textcomp defines some of these)
        lines.append("% Custom text-mode symbol commands")
        lines.append("\\providecommand{\\textinfty}{\\ensuremath{\\infty}}")
        lines.append("\\providecommand{\\textapprox}{\\ensuremath{\\approx}}")
        lines.append("\\providecommand{\\textdiv}{\\ensuremath{\\div}}")
        lines.append("\\providecommand{\\textneq}{\\ensuremath{\\neq}}")
        lines.append(
            "\\providecommand{\\textgreaterequal}{\\ensuremath{\\geq}}"
        )
        lines.append("\\providecommand{\\textlessequal}{\\ensuremath{\\leq}}")
        lines.append("\\providecommand{\\texttimes}{\\ensuremath{\\times}}")
        lines.append("")

        # Define urlprefix if using spbasic_pt bibliography style
        if self.bibliography_style == "spbasic_pt":
            lines.append("% Define urlprefix for spbasic_pt bibliography style")
            lines.append("\\newcommand{\\urlprefix}{URL: }")
            lines.append("")

        # Other custom commands
        if self.custom_commands:
            lines.append("% Additional custom commands")
            lines.extend(self.custom_commands)
            lines.append("")

        # Title and author
        if self.title:
            lines.append(f"\\title{{{self.title}}}")
        if self.author:
            lines.append(f"\\author{{{self.author}}}")
        lines.append("\\date{\\today}")
        lines.append("")

        return "\n".join(lines)

    def build_document(self, content: str, has_appendix: bool = False) -> str:
        """Build complete LaTeX document.

        Args:
            content: The main document content
            has_appendix: Whether the document has an appendix section
        """
        lines = []

        # Preamble
        lines.append(self.build_preamble())

        # Begin document
        lines.append("\\begin{document}")
        lines.append("")

        # Title page
        if self.title:
            lines.append("\\maketitle")
            lines.append("")

        # Abstract
        if self.abstract:
            lines.append("\\begin{abstract}")
            lines.append(self.abstract)
            lines.append("\\end{abstract}")
            lines.append("")

        # If document has appendix, we need to split content and insert bibliography before appendix
        if has_appendix:
            # Look for appendix section in content without regex
            content_lower = content.lower()
            appendix_pos = -1

            # Look for \section{Appendix...} or \section{Appendices...}
            section_pos = 0
            while True:
                section_pos = content_lower.find("\\section{", section_pos)
                if section_pos == -1:
                    break

                # Find closing brace
                brace_pos = content.find("}", section_pos + 9)
                if brace_pos != -1:
                    section_text = (
                        content[section_pos + 9 : brace_pos].strip().lower()
                    )
                    if section_text.startswith(("appendix", "appendices")):
                        appendix_pos = section_pos
                        break

                section_pos += 1

            if appendix_pos != -1:
                # Split content at appendix
                main_content = content[:appendix_pos].rstrip()
                appendix_content = content[appendix_pos:]

                # Add main content
                lines.append(main_content)
                lines.append("")

                # Add page break before bibliography
                lines.append("\\clearpage")
                lines.append("")

                # Bibliography with scriptsize (8pt)
                lines.append("{\\scriptsize")
                if self.bibliography_style:
                    # Traditional BibTeX style
                    lines.append(
                        f"\\bibliographystyle{{{self.bibliography_style}}}"
                    )
                    lines.append("\\bibliography{references}")
                else:
                    # BibLaTeX style
                    lines.append("\\printbibliography")
                lines.append("}")  # End footnotesize
                lines.append("")

                # Add page break after bibliography
                lines.append("\\clearpage")
                lines.append("")

                # Add appendix content
                lines.append(appendix_content)
                lines.append("")
            else:
                # Appendix pattern not found in LaTeX, add content normally
                lines.append(content)
                lines.append("")

                # Bibliography at end with footnotesize
                lines.append("{\\footnotesize")
                if self.bibliography_style:
                    lines.append(
                        f"\\bibliographystyle{{{self.bibliography_style}}}"
                    )
                    lines.append("\\bibliography{references}")
                else:
                    lines.append("\\printbibliography")
                lines.append("}")
                lines.append("")
        else:
            # No appendix - standard layout
            lines.append(content)
            lines.append("")

            # Bibliography with footnotesize
            lines.append("{\\footnotesize")
            if self.bibliography_style:
                # Traditional BibTeX style
                lines.append(
                    f"\\bibliographystyle{{{self.bibliography_style}}}"
                )
                lines.append("\\bibliography{references}")
            else:
                # BibLaTeX style
                lines.append("\\printbibliography")
            lines.append("}")
            lines.append("")

        # End document
        lines.append("\\end{document}")

        return "\n".join(lines)

    def process_pandoc_output(self, pandoc_output: str) -> str:
        """Process and clean pandoc output."""
        # Clean common pandoc artifacts
        cleaned = clean_pandoc_output(pandoc_output)

        # No longer need to restore placeholders since we're using direct LaTeX commands
        # cleaned = self._restore_unicode_symbols(cleaned)

        # Convert longtables to regular tables in two-column mode
        if self.two_column:
            cleaned = self._convert_longtables_to_tables(cleaned)

        # Fix table column specifications to prevent overfull hbox warnings
        cleaned = self._fix_table_columns(cleaned)

        # Extract only the document body content
        # Look for content between \begin{document} and \end{document}
        # Use string methods instead of regex for robustness
        begin_marker = r"\begin{document}"
        end_marker = r"\end{document}"

        begin_idx = cleaned.find(begin_marker)
        end_idx = cleaned.find(end_marker)

        if begin_idx != -1 and end_idx != -1 and begin_idx < end_idx:
            # Extract content between document markers
            start = begin_idx + len(begin_marker)
            raw_content = cleaned[start:end_idx].strip()

            # CRITICAL FIX: Remove pandoc's conditional preamble blocks
            # Pandoc bug: Places \ifPDFTeX ... \usepackage ... \fi AFTER \begin{document}
            content_lines = []
            skip_depth = 0
            lines = raw_content.split("\n")

            for line in lines:
                stripped = line.strip()

                # Track conditional blocks (can be nested)
                if stripped.startswith(r"\if"):
                    skip_depth += 1
                    continue  # Skip \if line
                if stripped.startswith(r"\else"):
                    continue  # Skip \else line
                if stripped.startswith(r"\fi"):
                    skip_depth = max(0, skip_depth - 1)
                    continue  # Skip \fi line

                # Inside conditional block - skip everything
                if skip_depth > 0:
                    continue

                # Outside conditionals - check for preamble commands
                # These should NEVER appear after \begin{document}
                is_preamble = (
                    stripped.startswith(r"\usepackage")
                    or stripped.startswith(r"\documentclass")
                    or stripped.startswith(r"\setcounter")
                    or stripped.startswith(r"\defaultfontfeatures")
                    or stripped.startswith(r"\UseMicrotypeSet")
                    or stripped.startswith(r"\makesavenoteenv")
                    or stripped.startswith(r"\makeatletter")
                    or stripped.startswith(r"\@ifundefined")
                    or stripped.startswith(r"\IfFileExists")
                    or stripped.startswith(r"\PassOptionsToPackage")
                    or stripped.startswith(r"\KOMAoptions")
                    or stripped.startswith(r"\providecommand")
                    or stripped.endswith(
                        r"]{article}"
                    )  # Pandoc bug: article declaration after \begin{document}
                )

                if not is_preamble:
                    content_lines.append(line)

            content = "\n".join(content_lines)
        else:
            # If no document markers found, remove obvious preamble commands
            lines = cleaned.split("\n")
            content_lines = []

            # Skip initial preamble-like content using string methods
            started = False
            for line in lines:
                # Check if we should skip this line using string methods
                # Use strip() to catch indented preamble commands
                stripped = line.strip()
                should_skip = (
                    stripped.startswith("\\documentclass")
                    or stripped.startswith("\\usepackage")
                    or stripped.startswith("\\author")
                    or stripped.startswith("\\title")
                    or stripped.startswith("\\date")
                    or stripped.startswith("\\begin{document}")
                    or stripped.startswith("\\end{document}")
                    or stripped.startswith("\\maketitle")
                    or stripped.startswith("\\KOMAoptions")
                    or stripped.startswith("\\UseMicrotypeSet")
                    or stripped.startswith("\\makesavenoteenv")
                    or stripped.startswith("\\providecommand")
                    or stripped.startswith("%")
                    or stripped == ""
                )

                if not started and not should_skip and line.strip():
                    started = True

                if started and not (
                    line.startswith("\\documentclass")
                    or line.startswith("\\usepackage")
                    or line.startswith("\\author")
                    or line.startswith("\\title")
                    or line.startswith("\\date")
                    or line.startswith("\\begin{document}")
                    or line.startswith("\\end{document}")
                ):
                    content_lines.append(line)

            content = "\n".join(content_lines)

        # Additional cleanup for any remaining preamble commands using string methods
        lines = content.split("\n")
        cleaned_lines = []

        for line in lines:
            # Skip lines that start with preamble commands
            if (
                line.startswith("\\documentclass")
                or line.startswith("\\usepackage")
                or line.startswith("\\defaultfontfeatures")
                or line.startswith("\\setlength")
                or line.startswith("\\IfFileExists")
                or line.startswith("\\PassOptionsToPackage")
                or line.strip().startswith("%")
            ):
                continue

            # Fix tilde before dollar amounts
            line = line.replace("\\~$", "\\textasciitilde$")

            # Fix escaped parentheses that shouldn't be escaped in LaTeX
            line = line.replace("\\)", ")")
            line = line.replace("\\(", "(")

            cleaned_lines.append(line)

        content = "\n".join(cleaned_lines)

        # Clean up multiple blank lines
        while "\n\n\n" in content:
            content = content.replace("\n\n\n", "\n\n")

        # Since the user never uses $ for math in markdown input,
        # we only need to preserve math mode that was created by clean_pandoc_output
        # from unicode symbols (like ± to $\pm$)

        # IMPORTANT: Pandoc already escapes dollar signs in the markdown,
        # so we should NOT escape them again!

        def is_pandoc_generated_math(text):
            """Check if this is math mode generated by clean_pandoc_output from unicode."""
            # These are the LaTeX commands that clean_pandoc_output creates
            pandoc_math_commands = [
                r"\\approx",
                r"\\pm",
                r"\\times",
                r"\\div",
                r"\\geq",
                r"\\leq",
                r"\\neq",
                r"\\in",
                r"\\notin",
                r"\\cup",
                r"\\cap",
                r"\\subset",
                r"\\supset",
                r"\\emptyset",
                r"\\infty",
                r"\\pi",
                r"\\sigma",
                r"\\mu",
                r"\\lambda",
                r"\\alpha",
                r"\\beta",
                r"\\gamma",
                r"\\delta",
                r"\\epsilon",
                r"\\theta",
                r"\\kappa",
                r"\^\s*\\circ",
            ]
            return any(cmd in text for cmd in pandoc_math_commands)

        # We don't need to escape dollar signs because pandoc already does it
        # We just need to ensure math mode created by clean_pandoc_output stays intact

        # However, pandoc sometimes misses dollar signs in certain contexts (like lists)
        # So we need to escape any unescaped dollar signs that look like currency
        # Pattern: $ followed by digits, optionally with commas, K/M/B suffix, and +/-
        # BUT: avoid matching if we're already inside math mode (between $ signs)

        # First, let's find all math mode regions to protect them
        math_regions = []
        i = 0
        while i < len(content):
            if content[i] == "$" and (i == 0 or content[i - 1] != "\\"):
                # Found start of math mode
                j = i + 1
                while j < len(content):
                    if content[j] == "$" and content[j - 1] != "\\":
                        # Found end of math mode
                        math_regions.append((i, j + 1))
                        i = j
                        break
                    j += 1
            i += 1

        def is_in_math_mode(pos):
            """Check if position is inside a math mode region."""
            for start, end in math_regions:
                if start <= pos < end:
                    return True
            return False

        # Final step: escape any remaining unescaped dollar signs that look like currency
        # This catches cases that pandoc misses in certain contexts
        # Match: $ followed by digits, with optional commas, K/M/B suffix, and +/-
        # But only if not already escaped (no preceding backslash)

        # Split content into lines to handle line-by-line
        lines = content.split("\n")
        new_lines = []

        for line in lines:
            # Skip if line is in a verbatim environment
            if line.strip().startswith(
                "\\begin{verbatim}"
            ) or line.strip().startswith("\\begin{lstlisting}"):
                new_lines.append(line)
                continue

            # Look for unescaped currency patterns
            # Track math mode to avoid escaping $ that close math mode
            i = 0
            new_line = []
            in_math_mode = False
            while i < len(line):
                if line[i] == "$" and (i == 0 or line[i - 1] != "\\"):
                    # Found unescaped dollar sign
                    # If we're in math mode, this closes it - don't escape
                    if in_math_mode:
                        new_line.append(line[i])
                        in_math_mode = False
                        i += 1
                    # If not in math mode, check if it's currency or opening math
                    elif i + 1 < len(line) and line[i + 1].isdigit():
                        # This looks like currency ($50)
                        new_line.append("\\$")
                        i += 1
                    elif (
                        i + 2 < len(line)
                        and line[i + 1] == " "
                        and line[i + 2].isdigit()
                    ):
                        # Currency pattern like "$ 50" with space
                        new_line.append("\\$")
                        i += 1
                    else:
                        # Opening math mode
                        new_line.append(line[i])
                        in_math_mode = True
                        i += 1
                else:
                    new_line.append(line[i])
                    i += 1

            line = "".join(new_line)

            new_lines.append(line)

        content = "\n".join(new_lines)

        return content.strip()

    def _restore_unicode_symbols(self, content: str) -> str:
        """Restore Unicode symbols that were replaced with placeholders.

        This is needed because pandoc converts Unicode math symbols to LaTeX math mode,
        which conflicts with our currency dollar handling.
        """
        # Map placeholders back to appropriate LaTeX commands
        # Using text mode commands to avoid math mode issues
        replacements = {
            "MULTIPLICATION_SIGN_PLACEHOLDER": r"$\times$",  # Keep this in math mode as it's standard
            "PLUS_MINUS_PLACEHOLDER": r"\textpm{}",
            "GREATER_EQUAL_PLACEHOLDER": r"$\geq$",  # Keep in math mode
            "LESS_EQUAL_PLACEHOLDER": r"$\leq$",  # Keep in math mode
            "DEGREE_PLACEHOLDER": r"$^\circ$",  # Keep in math mode for degree symbol
            "MICRO_PLACEHOLDER": r"$\mu$",  # Keep in math mode
            "INFINITY_PLACEHOLDER": r"$\infty$",  # Keep in math mode
            "APPROX_PLACEHOLDER": r"$\approx$",  # Keep in math mode
            "DIVISION_PLACEHOLDER": r"$\div$",  # Keep in math mode
            "NOT_EQUAL_PLACEHOLDER": r"$\neq$",  # Keep in math mode
        }

        for placeholder, symbol in replacements.items():
            content = content.replace(placeholder, symbol)

        return content

    def _convert_longtables_to_tables(self, content: str) -> str:
        """Convert longtable environments to table* for two-column layout."""
        # Find and replace longtable environments without regex
        result_lines = []
        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            if "\\begin{longtable}" in line:
                # Found start of longtable
                table_lines = [line]
                i += 1

                # Collect lines until end of longtable
                while i < len(lines) and "\\end{longtable}" not in lines[i]:
                    table_lines.append(lines[i])
                    i += 1

                if i < len(lines):
                    # Add the end line
                    table_lines.append(lines[i])

                    # Process the longtable
                    table_content = "\n".join(
                        table_lines[1:-1]
                    )  # Exclude begin/end lines

                    # Extract column specification
                    col_spec = ""
                    bracket_start = table_lines[0].find("[")
                    if bracket_start != -1:
                        bracket_end = table_lines[0].find("]", bracket_start)
                        if bracket_end != -1:
                            brace_start = table_lines[0].find("{", bracket_end)
                            brace_end = table_lines[0].find("}", brace_start)
                            if brace_start != -1 and brace_end != -1:
                                col_spec = table_lines[0][
                                    brace_start + 1 : brace_end
                                ]

                    # Count columns
                    num_cols = (
                        col_spec.count("l")
                        + col_spec.count("c")
                        + col_spec.count("r")
                        + col_spec.count("p")
                    )

                    if num_cols == 0:
                        num_cols = col_spec.count("@") + 1
                        if num_cols <= 1:
                            num_cols = 3

                    # Create new column spec
                    if num_cols == 2:
                        new_col_spec = "{p{0.48\\textwidth}p{0.48\\textwidth}}"
                    elif num_cols == 3:
                        new_col_spec = "{p{0.32\\textwidth}p{0.32\\textwidth}p{0.32\\textwidth}}"
                    elif num_cols == 4:
                        new_col_spec = "{p{0.24\\textwidth}p{0.24\\textwidth}p{0.24\\textwidth}p{0.24\\textwidth}}"
                    else:
                        width = 0.96 / num_cols
                        new_col_spec = (
                            "{"
                            + ("p{" + f"{width:.2f}\\textwidth" + "}")
                            * num_cols
                            + "}"
                        )

                    # Process table content
                    # Replace \real{...} with actual value
                    while "\\real{" in table_content:
                        start = table_content.find("\\real{")
                        if start != -1:
                            end = table_content.find("}", start + 6)
                            if end != -1:
                                value = table_content[start + 6 : end]
                                table_content = (
                                    table_content[:start]
                                    + value
                                    + table_content[end + 1 :]
                                )
                            else:
                                break

                    # Replace \columnwidth
                    table_content = table_content.replace(
                        r"\columnwidth", "0.5\\textwidth"
                    )

                    # Remove minipage environments
                    while "\\begin{minipage}" in table_content:
                        start = table_content.find("\\begin{minipage}")
                        if start != -1:
                            # Find the closing bracket
                            bracket_count = 0
                            j = start + 15  # Skip past \begin{minipage}
                            found_end = False
                            while j < len(table_content):
                                if table_content[j] == "[":
                                    bracket_count += 1
                                elif table_content[j] == "]":
                                    bracket_count -= 1
                                    if bracket_count == 0:
                                        # Find the next } and skip raggedright if present
                                        brace_pos = table_content.find("}", j)
                                        if brace_pos != -1:
                                            # Check for raggedright
                                            after_brace = table_content[
                                                brace_pos + 1 :
                                            ].lstrip()
                                            if after_brace.startswith(
                                                "\\raggedright"
                                            ):
                                                skip_len = len("\\raggedright")
                                                table_content = (
                                                    table_content[:start]
                                                    + table_content[
                                                        brace_pos
                                                        + 1
                                                        + skip_len :
                                                    ]
                                                )
                                            else:
                                                table_content = (
                                                    table_content[:start]
                                                    + table_content[
                                                        brace_pos + 1 :
                                                    ]
                                                )
                                        found_end = True
                                        break
                                j += 1
                            if not found_end:
                                break
                        else:
                            break

                    # Remove \end{minipage}
                    table_content = table_content.replace("\\end{minipage}", "")

                    # Fix escaped ampersands
                    table_content = table_content.replace(r"\&", "&")

                    # Create table* output
                    result_lines.append("\\begin{table*}[htbp]")
                    result_lines.append("\\centering")
                    result_lines.append("\\footnotesize")
                    result_lines.append("\\begin{tabular}" + new_col_spec)
                    result_lines.extend(table_content.split("\n"))
                    result_lines.append("\\end{tabular}")
                    result_lines.append("\\end{table*}")

                i += 1
            else:
                result_lines.append(line)
                i += 1

        content = "\n".join(result_lines)

        # Remove longtable-specific commands
        content = content.replace("\\endhead", "")
        content = content.replace("\\endfoot", "")
        content = content.replace("\\endlastfoot", "")
        content = content.replace("\\endfirsthead", "")

        # Clean up extra whitespace
        lines = content.split("\n")
        cleaned_lines = []
        for line in lines:
            cleaned_line = line.rstrip()
            if cleaned_line or (cleaned_lines and cleaned_lines[-1].strip()):
                cleaned_lines.append(cleaned_line)

        content = "\n".join(cleaned_lines)

        # Fix table columns
        content = self._fix_table_columns(content)

        return content

    def _fix_table_columns(self, content: str) -> str:
        """Fix complex column specifications in table and table* environments."""
        # Fix both table* and regular table environments
        content = self._fix_table_type(content, "table*")
        content = self._fix_table_type(content, "table")
        return content

    def _fix_table_type(self, content: str, table_type: str) -> str:
        """Fix complex column specifications in specific table type."""
        # Process tables without regex
        lines = content.split("\n")
        result_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Look for table environments
            if table_type == "table*" and "\\begin{table*}" in line:
                # Found table*, collect lines until we find \begin{tabular}
                table_lines = [line]
                i += 1

                while i < len(lines):
                    table_lines.append(lines[i])
                    if "\\begin{tabular}" in lines[i]:
                        # Found tabular, now look for column spec and toprule
                        tabular_line = lines[i]
                        spec_start = tabular_line.find("\\begin{tabular}")
                        if spec_start != -1:
                            spec_start += len("\\begin{tabular}")
                            # Extract column spec
                            spec_end = tabular_line.find(
                                "\\toprule", spec_start
                            )
                            if spec_end == -1:
                                # Look on next lines for toprule
                                j = i + 1
                                while (
                                    j < len(lines) and j < i + 5
                                ):  # Look ahead up to 5 lines
                                    if "\\toprule" in lines[j]:
                                        # Found toprule
                                        column_spec = tabular_line[spec_start:]
                                        for k in range(i + 1, j):
                                            column_spec += "\n" + lines[k]

                                        # Process column spec
                                        new_spec = self._process_column_spec(
                                            column_spec
                                        )

                                        # Replace in result
                                        result_lines.extend(table_lines[:-1])
                                        result_lines.append(
                                            "\\begin{tabular}" + new_spec
                                        )
                                        i = j
                                        break
                                    j += 1
                                else:
                                    # No toprule found, keep as is
                                    result_lines.extend(table_lines)
                                    i += 1
                                    continue
                            else:
                                # toprule on same line
                                column_spec = tabular_line[spec_start:spec_end]
                                new_spec = self._process_column_spec(
                                    column_spec
                                )
                                result_lines.extend(table_lines[:-1])
                                result_lines.append(
                                    "\\begin{tabular}" + new_spec + "\\toprule"
                                )
                        else:
                            result_lines.extend(table_lines)
                        break
                    i += 1
            elif "\\begin{tabular}" in line:
                # Found tabular environment
                spec_start = line.find("\\begin{tabular}")
                if spec_start != -1:
                    prefix = line[: spec_start + len("\\begin{tabular}")]
                    remainder = line[spec_start + len("\\begin{tabular}") :]

                    # Check if we have toprule or midrule on same line
                    toprule_pos = remainder.find("\\toprule")
                    midrule_pos = remainder.find("\\midrule")

                    if toprule_pos != -1:
                        column_spec = remainder[:toprule_pos]
                        suffix = remainder[toprule_pos:]
                    elif midrule_pos != -1:
                        column_spec = remainder[:midrule_pos]
                        suffix = remainder[midrule_pos:]
                    else:
                        # Look for end of column spec (newline or next command)
                        column_spec = remainder
                        suffix = ""

                    # Process column spec if it contains width specifications
                    if "\\tabcolsep" in column_spec or "p{" in column_spec:
                        new_spec = self._process_column_spec(column_spec)
                        result_lines.append(prefix + new_spec + suffix)
                    else:
                        result_lines.append(line)
                else:
                    result_lines.append(line)
                i += 1
            else:
                result_lines.append(line)
                i += 1

        return "\n".join(result_lines)

    def _process_column_spec(self, column_spec: str) -> str:
        """Process a column specification and return simplified version."""
        # Count columns
        num_cols = column_spec.count("p{")

        if num_cols == 0:
            return column_spec

        logger.debug(f"Found table with {num_cols} columns")

        if num_cols == 2:
            return "[]{@{}p{0.48\\textwidth} p{0.48\\textwidth}@{}}"
        elif num_cols == 3:
            return "[]{@{}p{0.32\\textwidth} p{0.32\\textwidth} p{0.32\\textwidth}@{}}"
        elif num_cols == 4:
            return "[]{@{}p{0.24\\textwidth} p{0.24\\textwidth} p{0.24\\textwidth} p{0.24\\textwidth}@{}}"
        elif num_cols == 5:
            return "[]{@{}p{0.19\\textwidth} p{0.19\\textwidth} p{0.19\\textwidth} p{0.19\\textwidth} p{0.19\\textwidth}@{}}"
        elif num_cols == 6:
            return "[]{@{}p{0.16\\textwidth} p{0.16\\textwidth} p{0.16\\textwidth} p{0.16\\textwidth} p{0.16\\textwidth} p{0.16\\textwidth}@{}}"
        elif num_cols == 7:
            return "[]{@{}p{0.13\\textwidth} p{0.13\\textwidth} p{0.13\\textwidth} p{0.13\\textwidth} p{0.13\\textwidth} p{0.13\\textwidth} p{0.13\\textwidth}@{}}"
        elif num_cols == 8:
            return "[]{@{}llllllll@{}}"
        elif num_cols == 9:
            return "[]{@{}lllllllll@{}}"
        elif num_cols >= 10:
            l_cols = "l" * num_cols
            return f"[]{{@{{}}{l_cols}@{{}}}}"
        else:
            # Use simple equal-width columns
            width = min(0.96 / num_cols, 0.16)
            p_spec = f"p{{{width:.2f}\\textwidth}} " * num_cols
            return f"[]{{@{{}}{p_spec.strip()}@{{}}}}"

    def create_makefile(
        self, output_dir: Path, main_file: str = "main.tex"
    ) -> None:
        """Create a Makefile for compiling the LaTeX document."""
        # Choose bibtex or biber based on bibliography style
        bibtex_cmd = "bibtex" if self.bibliography_style else "biber"

        makefile_content = f"""# Makefile for compiling LaTeX document
# Generated by deep-biblio-tools

MAIN = {main_file.replace(".tex", "")}
LATEX = xelatex
BIBTEX = {bibtex_cmd}

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex references.bib
\t$(LATEX) $(MAIN)
\t$(BIBTEX) $(MAIN)
\t$(LATEX) $(MAIN)
\t$(LATEX) $(MAIN)

clean:
\t@rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).bcf $(MAIN).blg $(MAIN).log $(MAIN).out $(MAIN).run.xml $(MAIN).toc

distclean: clean
\t@rm -f $(MAIN).pdf

.PHONY: all clean distclean
"""

        makefile_path = output_dir / "Makefile"
        with open(makefile_path, "w") as f:
            f.write(makefile_content)

        logger.info(f"Created Makefile: {makefile_path}")

    def create_readme(self, output_dir: Path) -> None:
        """Create a README with compilation instructions."""
        readme_content = f"""# LaTeX Document Compilation Instructions

This document was generated from Markdown using deep-biblio-tools on {datetime.now().strftime("%Y-%m-%d")}.

## Requirements

- LaTeX distribution (TeX Live, MiKTeX, or MacTeX)
- XeLaTeX compiler
- Biber for bibliography processing

## Compilation

### Using Make

If you have `make` installed:

```bash
make
```

To clean auxiliary files:

```bash
make clean
```

To remove all generated files including PDF:

```bash
make distclean
```

### Manual Compilation

If you don't have `make`, run these commands:

```bash
xelatex main
biber main
xelatex main
xelatex main
```

## Files

- `main.tex` - The main LaTeX document
- `references.bib` - Bibliography file
- `Makefile` - Build automation

## Troubleshooting

1. **Missing packages**: Install required LaTeX packages using your distribution's package manager
2. **Bibliography not showing**: Make sure to run biber after the first xelatex compilation
3. **Encoding issues**: The document uses UTF-8 encoding

## arXiv Submission

This document is formatted to be arXiv-ready. To submit:

1. Compile the document locally to ensure it works
2. Create a ZIP file with all necessary files (`.tex`, `.bib`, any figures)
3. Upload to arXiv following their submission guidelines

Generated by [deep-biblio-tools](https://github.com/petteriTeikari/deep-biblio-tools)
"""

        readme_path = output_dir / "README.md"
        with open(readme_path, "w") as f:
            f.write(readme_content)

        logger.info(f"Created README: {readme_path}")
