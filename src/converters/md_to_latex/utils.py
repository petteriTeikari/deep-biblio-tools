"""Utility functions for markdown to LaTeX conversion."""

# Standard library imports
import hashlib
import html
import logging
import tempfile
from pathlib import Path

# import re  # Banned - using string methods instead

logger = logging.getLogger(__name__)


def convert_unicode_to_latex(text: str) -> str:
    """Convert common Unicode characters to LaTeX commands.

    This handles characters that can't be directly used in LaTeX without
    proper setup (like Greek letters, special symbols, etc.).

    Args:
        text: Text that may contain Unicode characters

    Returns:
        Text with Unicode characters converted to LaTeX commands
    """
    if not text:
        return text

    # Greek letters (most common in scientific text)
    unicode_map = {
        "α": r"$\alpha$",
        "β": r"$\beta$",
        "γ": r"$\gamma$",
        "δ": r"$\delta$",
        "ε": r"$\epsilon$",
        "ζ": r"$\zeta$",
        "η": r"$\eta$",
        "θ": r"$\theta$",
        "ι": r"$\iota$",
        "κ": r"$\kappa$",
        "λ": r"$\lambda$",
        "μ": r"$\mu$",
        "ν": r"$\nu$",
        "ξ": r"$\xi$",
        "ο": r"$o$",
        "π": r"$\pi$",
        "ρ": r"$\rho$",
        "σ": r"$\sigma$",
        "τ": r"$\tau$",
        "υ": r"$\upsilon$",
        "φ": r"$\phi$",
        "χ": r"$\chi$",
        "ψ": r"$\psi$",
        "ω": r"$\omega$",
        # Capital Greek letters
        "Α": r"$A$",
        "Β": r"$B$",
        "Γ": r"$\Gamma$",
        "Δ": r"$\Delta$",
        "Ε": r"$E$",
        "Ζ": r"$Z$",
        "Η": r"$H$",
        "Θ": r"$\Theta$",
        "Ι": r"$I$",
        "Κ": r"$K$",
        "Λ": r"$\Lambda$",
        "Μ": r"$M$",
        "Ν": r"$N$",
        "Ξ": r"$\Xi$",
        "Ο": r"$O$",
        "Π": r"$\Pi$",
        "Ρ": r"$P$",
        "Σ": r"$\Sigma$",
        "Τ": r"$T$",
        "Υ": r"$\Upsilon$",
        "Φ": r"$\Phi$",
        "Χ": r"$X$",
        "Ψ": r"$\Psi$",
        "Ω": r"$\Omega$",
        # Common math symbols
        "≈": r"$\approx$",
        "≠": r"$\neq$",
        "≤": r"$\leq$",
        "≥": r"$\geq$",
        "×": r"$\times$",
        "÷": r"$\div$",
        "±": r"$\pm$",
        "∞": r"$\infty$",
        "∑": r"$\sum$",
        "∏": r"$\prod$",
        "∫": r"$\int$",
        "√": r"$\sqrt{}$",
        "∂": r"$\partial$",
        "∇": r"$\nabla$",
        # Arrows
        "→": r"$\rightarrow$",
        "←": r"$\leftarrow$",
        "↔": r"$\leftrightarrow$",
        "⇒": r"$\Rightarrow$",
        "⇐": r"$\Leftarrow$",
        "⇔": r"$\Leftrightarrow$",
    }

    for unicode_char, latex_cmd in unicode_map.items():
        text = text.replace(unicode_char, latex_cmd)

    return text


def convert_html_entities(text: str) -> str:
    r"""Convert HTML entities to plain text.

    This should be called BEFORE sanitize_latex() to avoid double-encoding.

    Examples:
        "&amp;" → "&"
        "&lt;" → "<"
        "&gt;" → ">"
        "&quot;" → '"'
        "H&amp;M" → "H&M" (then sanitize_latex will make it "H\&M")
    """
    if not text:
        return text

    # Use Python's built-in HTML entity decoder
    return html.unescape(text)


def sanitize_latex(text: str) -> str:
    """Sanitize text for LaTeX output.

    Important: Call convert_html_entities() first if text may contain HTML entities.

    This escapes LaTeX special characters:
        & → \\&
        _ → \\_
        % → \\%
        $ → \\$
        # → \\#
        ^ → \\^{}
        ~ → \\~{}
        { → \\{
        } → \\}
        \\ → \textbackslash{}
    """
    if not text:
        return text

    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
        "&": r"\&",
        "#": r"\#",
        "^": r"\^{}",
        "_": r"\_",
        "~": r"\~{}",
        "%": r"\%",
    }

    # First replace backslashes, then other characters
    text = text.replace("\\", replacements["\\"])
    for char, replacement in replacements.items():
        if char != "\\":
            text = text.replace(char, replacement)

    return text


def sanitize_bibtex_field(text: str) -> str:
    r"""Sanitize text for BibTeX field values.

    This is a convenience function that combines HTML entity conversion
    and LaTeX escaping, which is the common pattern for BibTeX fields.

    Pipeline:
        1. Convert HTML entities (&amp; → &)
        2. Escape LaTeX special characters (& → \&)

    Args:
        text: Raw text that may contain HTML entities and needs LaTeX escaping

    Returns:
        Text safe for use in BibTeX field values
    """
    if not text:
        return text

    # First convert HTML entities, then escape for LaTeX
    text = convert_html_entities(text)
    text = sanitize_latex(text)
    return text


def generate_citation_key(
    authors: str, year: str, title: str = "", use_better_bibtex: bool = True
) -> str:
    """Generate a citation key from authors, year, and optionally title.

    Args:
        authors: Author string (e.g., "Smith, John and Doe, Jane")
        year: Publication year
        title: Paper title (used for Better BibTeX style keys)
        use_better_bibtex: If True, use Better BibTeX style (default),
                          otherwise use simple authorYear style

    Returns:
        Citation key in either Better BibTeX format (smithMachineLearning2023)
        or simple format (smith2023)
    """
    # CRITICAL FIX: Handle empty or invalid author strings
    if not authors or authors.strip() == "":
        # Generate a fallback key using year and part of title if available
        if title:
            # Use first significant word from title without regex
            # Remove non-alphabetic characters
            clean_title = []
            for char in title:
                if char.isalpha() or char.isspace():
                    clean_title.append(char)
                else:
                    clean_title.append(" ")
            title_words = "".join(clean_title).split()

            for word in title_words:
                if len(word) > 3:  # Skip short words
                    return f"{word.lower()}{year}"
        return f"unknown{year}"

    # Extract first author's last name
    first_author = authors.split(",")[0].split(" and ")[0].strip()

    # Handle "et al." cases - IMPROVED HANDLING
    if " et al." in first_author or " et al" in first_author:
        # Extract just the first author before "et al"
        first_author = first_author.split(" et al")[0].strip()
        # If we still have nothing, fallback
        if not first_author:
            return f"unknown{year}"

    # For last name, handle name prefixes properly
    author_parts = first_author.split()
    if author_parts:
        # Check for name prefixes that should be included with the surname
        prefixes = [
            "van",
            "von",
            "de",
            "del",
            "della",
            "di",
            "da",
            "das",
            "dos",
            "der",
            "la",
            "le",
        ]

        # Better approach: look for prefixes and combine them with surname
        surname_parts = []
        found_prefix = False

        for i, part in enumerate(author_parts):
            if part.lower() in prefixes:
                surname_parts.append(part)
                found_prefix = True
            elif (
                found_prefix or i == len(author_parts) - 1
            ):  # Include all remaining parts after prefix
                surname_parts.append(part)

        if not surname_parts:
            last_name = author_parts[-1]  # Fallback to last word
        else:
            last_name = "".join(surname_parts)
    else:
        last_name = "unknown"

    # Remove special characters from author name - ASCII ONLY for BibTeX compatibility
    # Use ASCII transliteration for common non-ASCII characters
    transliteration = {
        "ä": "a",
        "ö": "o",
        "ü": "u",
        "ß": "ss",
        "à": "a",
        "á": "a",
        "â": "a",
        "ã": "a",
        "å": "a",
        "è": "e",
        "é": "e",
        "ê": "e",
        "ë": "e",
        "ì": "i",
        "í": "i",
        "î": "i",
        "ï": "i",
        "ò": "o",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ù": "u",
        "ú": "u",
        "û": "u",
        "ñ": "n",
        "ç": "c",
    }
    clean_name = []
    for char in last_name:
        if char.lower() in transliteration:
            clean_name.append(transliteration[char.lower()])
        elif (
            char.isascii() and char.isalpha()
        ):  # ONLY ASCII alphabetic characters
            clean_name.append(char)
    last_name = "".join(clean_name)

    if use_better_bibtex and title:
        # Better BibTeX style: authorTitleWord(s)Year
        # Clean and extract title words
        # Remove common words and punctuation
        stop_words = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "for",
            "with",
            "without",
            "of",
            "in",
            "on",
            "at",
            "to",
            "from",
            "by",
            "as",
            "is",
            "are",
            "was",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "into",
            "upon",
            "about",
        }

        # Clean title: remove special chars but keep spaces
        clean_title = []
        for char in title:
            if char.isalpha() or char.isspace():
                clean_title.append(char)
            else:
                clean_title.append(" ")
        title_words = "".join(clean_title).split()

        # Filter significant words
        significant_words = [
            word
            for word in title_words
            if word.lower() not in stop_words and len(word) > 2
        ]

        # Take first 1-3 significant words for the title part
        if significant_words:
            # Capitalize each word
            title_part = "".join(
                [word.capitalize() for word in significant_words[:3]]
            )
        else:
            # Fallback if no significant words
            title_part = "Paper"

        # Better BibTeX format with lowercase first letter of author
        if last_name:
            key = f"{last_name[0].lower()}{last_name[1:]}{title_part}{year}"
        else:
            key = f"unknown{title_part}{year}"
    else:
        # Simple format: authorYear (all lowercase)
        key = f"{last_name.lower()}{year}"

    return key


def extract_url_from_link(link: str) -> str | None:
    """Extract URL from markdown link format."""
    # Match markdown link format [text](url) without regex
    if "[" in link and "](" in link and link.endswith(")"):
        bracket_start = link.find("[")
        bracket_end = link.find("]", bracket_start)
        paren_start = link.find("](", bracket_start)

        if bracket_start >= 0 and bracket_end >= 0 and paren_start >= 0:
            if bracket_start < bracket_end and bracket_end == paren_start:
                url = link[paren_start + 2 : -1]
                return url
    return None


def extract_doi_from_url(url: str) -> str | None:
    """Extract DOI from URL if present."""
    # Look for common DOI patterns without regex
    url_lower = url.lower()

    # Check for doi.org pattern
    if "doi.org/" in url_lower:
        start = url_lower.find("doi.org/") + 8
        doi = url[start:].strip()

        # Clean up DOI
        # Remove query parameters
        if "?" in doi:
            doi = doi[: doi.find("?")]

        # Remove fragment
        if "#" in doi:
            doi = doi[: doi.find("#")]

        # Remove trailing punctuation
        while doi and doi[-1] in ")]}>,;:":
            doi = doi[:-1]

        # Remove "full/" prefix if present
        if doi.startswith("full/"):
            doi = doi[5:]

        # Replace escaped parentheses
        doi = doi.replace(r"\(", "(").replace(r"\)", ")")

        return doi

    # Check for doi: pattern
    if "doi:" in url_lower:
        start = url_lower.find("doi:") + 4
        doi = url[start:].strip()

        # Clean up as above
        if " " in doi:
            doi = doi[: doi.find(" ")]
        if "?" in doi:
            doi = doi[: doi.find("?")]
        if "#" in doi:
            doi = doi[: doi.find("#")]

        while doi and doi[-1] in ")]}>,;:":
            doi = doi[:-1]

        return doi

    # Check for /doi/ pattern
    if "/doi/" in url_lower:
        start = url_lower.find("/doi/") + 5
        doi = url[start:].strip()

        # Clean up as above
        if " " in doi:
            doi = doi[: doi.find(" ")]
        if "?" in doi:
            doi = doi[: doi.find("?")]
        if "#" in doi:
            doi = doi[: doi.find("#")]

        while doi and doi[-1] in ")]}>,;:":
            doi = doi[:-1]

        return doi

    return None


def ensure_directory(path: Path) -> None:
    """Ensure directory exists, create if not."""
    path.mkdir(parents=True, exist_ok=True)


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def parse_citation_text(
    citation: str,
) -> tuple[str | None, str | None, str | None]:
    """Parse citation text to extract authors, year, and URL.

    Expected format: [Author et al. (Year)](URL)
    """
    # Parse without regex
    if not citation.startswith("[") or not citation.endswith(")"):
        return None, None, None

    # Find the components
    bracket_end = citation.find("]")
    if bracket_end == -1:
        return None, None, None

    # Check for (URL) part
    if bracket_end + 1 >= len(citation) or citation[bracket_end + 1] != "(":
        return None, None, None

    # Extract URL
    url = citation[bracket_end + 2 : -1].strip()

    # Extract author and year from [Author et al. (Year)]
    inner = citation[1:bracket_end]

    # Find year in parentheses
    if "(" in inner and ")" in inner:
        year_start = inner.rfind("(")
        year_end = inner.rfind(")")

        if year_start < year_end:
            year_str = inner[year_start + 1 : year_end].strip()
            # Check if it's a 4-digit year
            if len(year_str) == 4 and year_str.isdigit():
                authors = inner[:year_start].strip()
                return authors, year_str, url

    return None, None, None


def clean_pandoc_output(latex_content: str) -> str:
    """Clean up common pandoc artifacts from LaTeX output."""
    # DIAGNOSTIC: Log input state
    logger.debug(
        f"clean_pandoc_output: input size={len(latex_content)}; has_end={r'\\end{document}' in latex_content}"
    )

    # Remove tightlist commands
    latex_content = latex_content.replace("\\tightlist\n", "")
    latex_content = latex_content.replace("\\tightlist ", "")
    latex_content = latex_content.replace("\\tightlist", "")

    # Remove empty hypertarget commands - more complex without regex
    while "\\hypertarget{" in latex_content:
        start = latex_content.find("\\hypertarget{")
        if start == -1:
            break

        # Find matching braces
        brace_count = 1
        i = start + 13  # After \hypertarget{

        while i < len(latex_content) and brace_count > 0:
            if latex_content[i] == "{":
                brace_count += 1
            elif latex_content[i] == "}":
                brace_count -= 1
            i += 1

        if (
            brace_count == 0
            and i < len(latex_content)
            and latex_content[i] == "{"
        ):
            # Second argument
            i += 1
            brace_count = 1
            j = i

            while j < len(latex_content) and brace_count > 0:
                if latex_content[j] == "{":
                    brace_count += 1
                elif latex_content[j] == "}":
                    brace_count -= 1
                j += 1

            if brace_count == 0:
                # Check if content is empty
                content = latex_content[i : j - 1].strip()
                if not content:
                    # Remove the whole hypertarget
                    latex_content = latex_content[:start] + latex_content[j:]
                    continue

        # If we couldn't process it properly, move on
        break

    # Clean up excessive blank lines
    lines = latex_content.split("\n")
    cleaned_lines = []
    blank_count = 0

    for line in lines:
        if not line.strip():
            blank_count += 1
            if blank_count <= 1:
                cleaned_lines.append(line)
        else:
            blank_count = 0
            cleaned_lines.append(line)

    latex_content = "\n".join(cleaned_lines)

    # Remove pandoc's automatic labels - complex without regex
    while "\\label{" in latex_content:
        start = latex_content.find("\\label{")
        if start == -1:
            break

        # Find matching brace
        brace_count = 1
        i = start + 7  # After \label{

        while i < len(latex_content) and brace_count > 0:
            if latex_content[i] == "{":
                brace_count += 1
            elif latex_content[i] == "}":
                brace_count -= 1
            i += 1

        if brace_count == 0:
            # Remove the label
            latex_content = latex_content[:start] + latex_content[i:]
        else:
            break

    # Fix unicode characters
    replacements = {
        "≈": r"$\approx$",
        "↔": r"$\leftrightarrow$",
        "→": r"$\rightarrow$",
        "←": r"$\leftarrow$",
        "≥": r"$\geq$",
        "≤": r"$\leq$",
        "≠": r"$\neq$",
        "∈": r"$\in$",
        "∉": r"$\notin$",
        "∪": r"$\cup$",
        "∩": r"$\cap$",
        "⊂": r"$\subset$",
        "⊃": r"$\supset$",
        "∅": r"$\emptyset$",
        "∞": r"$\infty$",
        "π": r"$\pi$",
        "σ": r"$\sigma$",
        "μ": r"$\mu$",
        "λ": r"$\lambda$",
        "α": r"$\alpha$",
        "β": r"$\beta$",
        "γ": r"$\gamma$",
        "δ": r"$\delta$",
        "ε": r"$\epsilon$",
        "θ": r"$\theta$",
        "κ": r"$\kappa$",
        "—": "---",  # em dash
        "–": "--",  # en dash
        # "'": "`",  # left smart quote - commented due to ruff F601
        "'": "'",  # smart quotes (both left and right)
        """: "``",
        """: "''",
        "…": r"\ldots{}",
        "°": r"$^\circ$",
        "±": r"$\pm$ ",
        "×": r"$\times$",
        "÷": r"$\div$",
        "™": r"\texttrademark{}",
        "®": r"\textregistered{}",
        "©": r"\textcopyright{}",
        "€": r"\texteuro{}",
        "£": r"\pounds{}",
        "¥": r"\textyen{}",
        "§": r"\S{}",
        "¶": r"\P{}",
        "†": r"\dag{}",
        "‡": r"\ddag{}",
        "•": r"\textbullet{}",
    }

    for char, replacement in replacements.items():
        latex_content = latex_content.replace(char, replacement)

    # Fix hash symbols that weren't converted to sections
    lines = latex_content.split("\n")
    new_lines = []

    for line in lines:
        if line.startswith("# "):
            new_lines.append("\\section{" + line[2:].strip() + "}")
        elif line.startswith("## "):
            new_lines.append("\\subsection{" + line[3:].strip() + "}")
        elif line.startswith("### "):
            new_lines.append("\\subsubsection{" + line[4:].strip() + "}")
        elif line.startswith("#### "):
            new_lines.append("\\paragraph{" + line[5:].strip() + "}")
        else:
            new_lines.append(line)

    latex_content = "\n".join(new_lines)

    # Fix unescaped underscores in text mode (not in math mode)
    # This is complex without regex - simplified approach
    result = []
    i = 0
    in_math = False

    while i < len(latex_content):
        if latex_content[i] == "$":
            in_math = not in_math
            result.append(latex_content[i])
        elif latex_content[i] == "_" and not in_math:
            # Check if already escaped
            if i > 0 and latex_content[i - 1] == "\\":
                result.append(latex_content[i])
            else:
                result.append("\\_")
        else:
            result.append(latex_content[i])
        i += 1

    latex_content = "".join(result)

    # Fix unescaped ampersands not in tables
    # Simple approach - escape lone & that aren't followed by \\
    result = []
    i = 0

    while i < len(latex_content):
        if latex_content[i] == "&":
            # Check if already escaped
            if i > 0 and latex_content[i - 1] == "\\":
                result.append(latex_content[i])
            # Check if it's in a table (followed by spaces and \\)
            elif (
                i + 3 < len(latex_content)
                and latex_content[i + 1 : i + 3] == " \\"
            ):
                result.append(latex_content[i])
            else:
                # Look ahead for \\ within reasonable distance
                found_table_end = False
                for j in range(i + 1, min(i + 50, len(latex_content))):
                    if latex_content[j : j + 2] == "\\\\":
                        found_table_end = True
                        break
                    elif latex_content[j] == "\n":
                        break

                if found_table_end:
                    result.append(latex_content[i])
                else:
                    result.append("\\&")
        else:
            result.append(latex_content[i])
        i += 1

    cleaned = "".join(result)

    # DIAGNOSTIC: Log output state and detect if \end{document} was removed
    logger.debug(
        f"clean_pandoc_output: output size={len(cleaned)}; has_end={r'\\end{document}' in cleaned}"
    )
    if r"\end{document}" in latex_content and r"\end{document}" not in cleaned:
        debug_path = (
            Path(tempfile.gettempdir()) / "clean_removed_enddoc_debug.txt"
        )
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(
                "BEFORE TAIL:\n"
                + latex_content[-2000:]
                + "\n\nAFTER TAIL:\n"
                + cleaned[-2000:]
            )
        logger.warning(
            f"clean_pandoc_output removed \\end{{document}} - saved tails to {debug_path}"
        )

    return cleaned


def extract_title_from_markdown(content: str) -> str | None:
    """Extract title from markdown content (first H1 heading)."""
    lines = content.split("\n")
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            # Remove markdown formatting like asterisks
            title = title.replace("**", "")
            title = title.replace("*", "")
            return title
    return None


def extract_abstract_from_markdown(content: str) -> str | None:
    """Extract abstract section from markdown content."""
    lines = content.split("\n")
    abstract_lines = []
    in_abstract = False

    for i, line in enumerate(lines):
        if not in_abstract:
            # Check for abstract heading patterns
            line_lower = line.lower().strip()
            if (
                line_lower == "## abstract"
                or line_lower == "**abstract**"
                or line_lower == "### abstract"
            ):
                in_abstract = True
        else:
            # Stop at next section heading
            if line.startswith("#") and not line.startswith("####"):
                break
            abstract_lines.append(line)

    if abstract_lines:
        # Remove empty lines at start and end
        while abstract_lines and not abstract_lines[0].strip():
            abstract_lines.pop(0)
        while abstract_lines and not abstract_lines[-1].strip():
            abstract_lines.pop()

        return "\n".join(abstract_lines)

    return None


def clean_markdown_headings(content: str) -> str:
    """Remove bold formatting and hardcoded numbers from markdown headings.

    Converts headings like:
    - '## **1. Introduction**' to '## Introduction'
    - '### **2.1 Background**' to '### Background'
    - '## 3. Methods' to '## Methods'
    """
    lines = content.split("\n")
    cleaned_lines = []

    for line in lines:
        # Check if this is a heading line
        if line.strip().startswith("#"):
            # Count heading level
            heading_level = 0
            for char in line:
                if char == "#":
                    heading_level += 1
                else:
                    break

            if heading_level > 0:
                # Extract the heading text after # symbols, preserving original spacing
                rest_of_line = line[heading_level:]

                # Find the leading whitespace to preserve it
                leading_space = ""
                i = 0
                while i < len(rest_of_line) and rest_of_line[i].isspace():
                    leading_space += rest_of_line[i]
                    i += 1

                # Get the actual content after leading spaces
                content_part = rest_of_line[i:] if i < len(rest_of_line) else ""

                # Remove bold markers
                content_part = content_part.replace("**", "")

                # Remove leading numbers and dots
                # First handle escaped dots
                content_part = content_part.replace(r"\.", ".")

                # Remove number patterns without regex
                # Skip leading digits and dots
                j = 0
                while j < len(content_part):
                    if content_part[j].isdigit() or content_part[j] == ".":
                        j += 1
                    else:
                        break

                # Skip any whitespace after numbers
                while j < len(content_part) and content_part[j].isspace():
                    j += 1

                content_part = content_part[j:]

                # Reconstruct the heading with original spacing
                cleaned_line = (
                    "#" * heading_level + leading_space + content_part.rstrip()
                )
                cleaned_lines.append(cleaned_line)
            else:
                cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)
