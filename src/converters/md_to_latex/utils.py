"""Utility functions for markdown to LaTeX conversion."""

# Standard library imports
import hashlib
import html
import logging
import tempfile
import urllib.parse
from pathlib import Path

# import re  # Banned - using string methods instead

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """
    Normalize URLs for reliable citation matching.

    Handles:
    - http vs https protocol normalization
    - Trailing slash removal
    - URL decoding (percent-encoded characters)
    - DOI canonicalization (dx.doi.org → doi.org)
    - Case normalization for domains (but not paths)
    - Query parameter sorting for consistent comparison

    Args:
        url: URL to normalize

    Returns:
        Normalized URL string
    """
    if not url:
        return ""

    url = url.strip()

    # DOI-specific normalization
    if "doi.org" in url or url.startswith("10."):
        # Normalize DOI resolver
        url = url.replace("dx.doi.org", "doi.org")
        url = url.replace("http://doi.org", "https://doi.org")

        # If DOI without resolver, add it
        if url.startswith("10."):
            url = f"https://doi.org/{url}"

    # Protocol normalization: prefer https
    if url.startswith("http://"):
        # Convert to https for common academic sites
        domain_start = len("http://")
        domain_end = url.find("/", domain_start)
        if domain_end == -1:
            domain_end = len(url)
        domain = url[domain_start:domain_end].lower()

        # Sites that support https
        https_sites = [
            "doi.org",
            "arxiv.org",
            "scholar.google.com",
            "ieeexplore.ieee.org",
            "dl.acm.org",
            "springer.com",
            "sciencedirect.com",
        ]

        if any(site in domain for site in https_sites):
            url = "https://" + url[domain_start:]

    # Remove trailing slashes (but not for URLs that are just domain)
    if url.endswith("/") and url.count("/") > 2:
        url = url.rstrip("/")

    # Case normalization: lowercase domain but preserve path case
    if "://" in url:
        protocol, rest = url.split("://", 1)
        if "/" in rest:
            domain, path = rest.split("/", 1)
            url = f"{protocol}://{domain.lower()}/{path}"
        else:
            url = f"{protocol}://{rest.lower()}"

    # URL decode (handles %20, etc.)
    url = urllib.parse.unquote(url)

    return url


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

    # Accented characters (for BibTeX sortify compatibility - must be ASCII-only)
    # For BibTeX: transliterate to plain ASCII (sortify only accepts ASCII)
    # LaTeX rendering will be handled separately
    unicode_map = {
        # Special characters and punctuation
        "\u00a0": " ",  # Non-breaking space → regular space
        "\u00ae": "(R)",  # ®
        "\u2013": "--",  # en dash
        "\u2014": "---",  # em dash
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        # Latin accents - lowercase (transliterate to base letter for BibTeX)
        "à": "a",
        "á": "a",
        "â": "a",
        "ä": "a",
        "ã": "a",
        "å": "a",
        "æ": "ae",
        "ç": "c",
        "è": "e",
        "é": "e",
        "ê": "e",
        "ë": "e",
        "ì": "i",
        "í": "i",
        "î": "i",
        "ï": "i",
        "ñ": "n",
        "ò": "o",
        "ó": "o",
        "ô": "o",
        "ö": "o",
        "õ": "o",
        "ø": "o",
        "ù": "u",
        "ú": "u",
        "û": "u",
        "ü": "u",
        "ý": "y",
        "ÿ": "y",
        "ß": "ss",  # German sharp s
        "š": "s",  # s with caron
        "ș": "s",  # s with comma below
        # Latin accents - uppercase
        "À": "A",
        "Á": "A",
        "Â": "A",
        "Ä": "A",
        "Ã": "A",
        "Å": "A",
        "Æ": "AE",
        "Ç": "C",
        "È": "E",
        "É": "E",
        "Ê": "E",
        "Ë": "E",
        "Ì": "I",
        "Í": "I",
        "Î": "I",
        "Ï": "I",
        "Ñ": "N",
        "Ò": "O",
        "Ó": "O",
        "Ô": "O",
        "Ö": "O",
        "Õ": "O",
        "Ø": "O",
        "Ù": "U",
        "Ú": "U",
        "Û": "U",
        "Ü": "U",
        "Ý": "Y",
        "Ż": "Z",  # Z with dot above
        "Ž": "Z",  # Z with caron
        # Greek letters (most common in scientific text)
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


def parse_bibtex_entries(bibtex_content: str) -> dict[str, dict]:
    """Parse BibTeX content and extract citation keys with metadata.

    Args:
        bibtex_content: Complete BibTeX file content

    Returns:
        Dictionary mapping citation keys to metadata dicts containing:
        - url: URL from the entry
        - doi: DOI if present
        - arxiv_id: arXiv ID if present
        - raw_entry: Complete BibTeX entry text
    """
    entries = {}

    # Find all BibTeX entries without regex
    pos = 0
    while True:
        # Find next @entry
        at_pos = bibtex_content.find("@", pos)
        if at_pos == -1:
            break

        # Find opening brace
        brace_pos = bibtex_content.find("{", at_pos)
        if brace_pos == -1:
            break

        # Find citation key (between { and ,)
        comma_pos = bibtex_content.find(",", brace_pos)
        if comma_pos == -1:
            break

        citation_key = bibtex_content[brace_pos + 1 : comma_pos].strip()

        # Find closing brace (matching the opening one)
        # Count braces to handle nested structures
        brace_count = 1
        search_pos = brace_pos + 1
        while search_pos < len(bibtex_content) and brace_count > 0:
            if bibtex_content[search_pos] == "{":
                brace_count += 1
            elif bibtex_content[search_pos] == "}":
                brace_count -= 1
            search_pos += 1

        if brace_count == 0:
            # Found complete entry
            entry_end = search_pos
            raw_entry = bibtex_content[at_pos:entry_end]

            # Extract URL, DOI, arXiv ID
            metadata = {
                "raw_entry": raw_entry,
                "url": None,
                "doi": None,
                "arxiv_id": None,
            }

            # Extract URL
            url_start = raw_entry.find("url = ")
            if url_start >= 0:
                url_start += 6  # Skip "url = "
                # Find quote or brace
                if url_start < len(raw_entry):
                    if raw_entry[url_start] == "{":
                        url_end = raw_entry.find("}", url_start + 1)
                        if url_end > url_start:
                            metadata["url"] = raw_entry[
                                url_start + 1 : url_end
                            ].strip()
                    elif raw_entry[url_start] == '"':
                        url_end = raw_entry.find('"', url_start + 1)
                        if url_end > url_start:
                            metadata["url"] = raw_entry[
                                url_start + 1 : url_end
                            ].strip()

            # Extract DOI
            doi_start = raw_entry.find("doi = ")
            if doi_start >= 0:
                doi_start += 6
                if doi_start < len(raw_entry):
                    if raw_entry[doi_start] == "{":
                        doi_end = raw_entry.find("}", doi_start + 1)
                        if doi_end > doi_start:
                            metadata["doi"] = raw_entry[
                                doi_start + 1 : doi_end
                            ].strip()
                    elif raw_entry[doi_start] == '"':
                        doi_end = raw_entry.find('"', doi_start + 1)
                        if doi_end > doi_start:
                            metadata["doi"] = raw_entry[
                                doi_start + 1 : doi_end
                            ].strip()

            # Extract arXiv ID from URL
            if metadata["url"] and "arxiv.org" in metadata["url"]:
                if "arxiv.org/abs/" in metadata["url"]:
                    abs_pos = metadata["url"].find("arxiv.org/abs/")
                    arxiv_id_start = abs_pos + 14
                    remaining = metadata["url"][arxiv_id_start:]
                    # Extract ID (YYYY.NNNNN or subject/NNNNNNN)
                    # Stop at ?, /, or end of string
                    id_end = len(remaining)
                    for char_pos, char in enumerate(remaining):
                        if char in ["?", "#"]:
                            id_end = char_pos
                            break
                    metadata["arxiv_id"] = remaining[:id_end]

            entries[citation_key] = metadata
            pos = entry_end
        else:
            # Malformed entry, skip
            pos = brace_pos + 1

    return entries


def normalize_arxiv_url(url: str) -> str:
    """Normalize arXiv URL by removing version specifiers.

    Converts:
    - https://arxiv.org/abs/2508.12683v1 -> https://arxiv.org/abs/2508.12683
    - https://arxiv.org/abs/2508.12683v2 -> https://arxiv.org/abs/2508.12683
    - https://arxiv.org/html/2410.20199v1 -> https://arxiv.org/abs/2410.20199

    Args:
        url: Original arXiv URL (may include version)

    Returns:
        Normalized URL without version, always using /abs/ format
    """
    if not url or "arxiv.org" not in url:
        return url

    # Normalize to use /abs/ instead of /html/ or /pdf/
    url = url.replace("arxiv.org/html/", "arxiv.org/abs/")
    url = url.replace("arxiv.org/pdf/", "arxiv.org/abs/")

    # Remove version specifier (vN at the end)
    if "arxiv.org/abs/" in url:
        abs_pos = url.find("arxiv.org/abs/")
        after_abs = url[abs_pos + 14 :]

        # Find where the ID ends (look for v followed by digits)
        for i in range(len(after_abs)):
            if after_abs[i] == "v" and i > 0:
                # Check if followed by digits
                remaining = after_abs[i + 1 :]
                if (
                    remaining
                    and remaining.split("/")[0].split("?")[0].isdigit()
                ):
                    # Found version specifier, remove it
                    url = url[: abs_pos + 14 + i]
                    break

    return url


def generate_citation_key(*args, **kwargs) -> str:
    """FORBIDDEN: Citation keys must come from Zotero Better BibTeX.

    This function is intentionally disabled. Citation keys must ONLY come from
    Zotero Better BibTeX export. Never generate keys locally.

    Raises:
        RuntimeError: Always - this function must never be called

    See:
        docs/better-bibtex-key-strategy.md for implementation details
        .claude/CLAUDE.md for design principles
    """
    raise RuntimeError(
        "Citation key generation is FORBIDDEN.\n"
        "Keys must come from Zotero Better BibTeX export.\n"
        "Use load_collection_with_keys() to get keys from Zotero.\n"
        "See docs/better-bibtex-key-strategy.md"
    )


def is_better_bibtex_key(key: str) -> bool:
    """Validate Better BibTeX key format without regex.

    Better BibTeX keys have pattern: [author][ShortTitle][year]
    Example: adisornDigitalProductPassport2021

    Characteristics:
    - Length: Typically >= 12 characters
    - Contains both uppercase and lowercase (camelCase)
    - Ends with 4-digit year
    - NOT just authorYear (e.g., adisorn2021 is invalid)

    Args:
        key: Citation key to validate

    Returns:
        True if key matches Better BibTeX format, False otherwise
    """
    if not key or not isinstance(key, str):
        return False

    if len(key) < 12:
        return False

    # Must end with 4-digit year
    if not (len(key) >= 4 and key[-4:].isdigit()):
        return False

    # Reject simple authorYear pattern (e.g., "adisorn2021")
    # Check if everything before year is just lowercase letters
    before_year = key[:-4]
    if before_year.isalpha() and before_year.islower():
        return False

    # Better BibTeX keys have mixed case (camelCase)
    has_upper = any(c.isupper() for c in key)
    has_lower = any(c.islower() for c in key)

    return has_upper and has_lower


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

    # Determine where the DOI starts
    doi_start = -1
    if "doi.org/" in url_lower:
        doi_start = url_lower.find("doi.org/") + 8
    elif "dx.doi.org/" in url_lower:
        doi_start = url_lower.find("dx.doi.org/") + 11
    elif "/doi/" in url_lower:
        # Generic DOI path pattern (e.g., journal.com/doi/10.1234/example)
        doi_start = url_lower.find("/doi/") + 5

    if doi_start == -1:
        return None

    doi = url[doi_start:].strip()

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

    # Validate DOI format - must start with "10."
    if not doi.startswith("10."):
        return None

    return doi


def extract_isbn_from_url(url: str) -> str | None:
    """Extract ISBN from URL if present (e.g., Amazon, Google Books)."""
    url_lower = url.lower()

    # Amazon pattern: /dp/{ISBN}
    if "/dp/" in url_lower:
        start = url_lower.find("/dp/") + 4
        rest = url[start:]
        # ISBN is next segment (10 or 13 digits)
        end = rest.find("/")
        if end == -1:
            end = rest.find("?")
        if end == -1:
            end = len(rest)
        isbn = rest[:end].strip()

        # Validate ISBN length (10 or 13 digits, possibly with hyphens)
        digits_only = "".join(c for c in isbn if c.isdigit())
        if len(digits_only) in [10, 13]:
            return digits_only

    # Google Books pattern: /books?id=...&isbn=...
    if "books.google" in url_lower and "isbn=" in url_lower:
        start = url_lower.find("isbn=") + 5
        rest = url[start:]
        end = rest.find("&")
        if end == -1:
            end = len(rest)
        isbn = rest[:end].strip()
        digits_only = "".join(c for c in isbn if c.isdigit())
        if len(digits_only) in [10, 13]:
            return digits_only

    return None


def extract_arxiv_id(url: str) -> str | None:
    """Extract arXiv ID from URL if present."""
    url_lower = url.lower()

    if "arxiv.org" not in url_lower:
        return None

    # Pattern: arxiv.org/abs/2410.10762 or arxiv.org/html/2509.10691v1
    for pattern in ["/abs/", "/html/", "/pdf/"]:
        if pattern in url_lower:
            start = url_lower.find(pattern) + len(pattern)
            rest = url[start:]

            # arXiv ID is next segment
            end = rest.find("/")
            if end == -1:
                end = rest.find("?")
            if end == -1:
                end = rest.find("#")
            if end == -1:
                end = len(rest)

            arxiv_id = rest[:end].strip()

            # Remove version suffix if present (e.g., "v1")
            if "v" in arxiv_id:
                v_pos = arxiv_id.rfind("v")
                # Check if everything after 'v' is digits
                version_part = arxiv_id[v_pos + 1 :]
                if version_part.isdigit():
                    arxiv_id = arxiv_id[:v_pos]

            # Validate format: YYMM.NNNNN or YYMM.NNNN
            if "." in arxiv_id:
                left, right = arxiv_id.split(".", 1)
                if (
                    len(left) == 4
                    and left.isdigit()
                    and len(right) in [4, 5]
                    and right.isdigit()
                ):
                    return arxiv_id

    return None

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
