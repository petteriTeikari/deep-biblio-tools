"""
AST-based validation utilities for bibliographic tools.

Uses proper parsers instead of regex for structured format validation.
"""

import datetime
from urllib.parse import urlparse

from src.parsers import BibtexParser, LatexParser, MarkdownParser


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_doi(doi: str) -> bool:
    """
    Validate DOI format without regex.

    Args:
        doi: DOI string to validate

    Returns:
        True if DOI format is valid
    """
    # DOI format: 10.{registrant code}/{suffix}
    doi = doi.strip()

    # Must start with "10."
    if not doi.startswith("10."):
        return False

    # Must have a slash after the prefix
    if "/" not in doi:
        return False

    # Split into prefix and suffix
    parts = doi.split("/", 1)
    if len(parts) != 2:
        return False

    prefix, suffix = parts

    # Prefix must be "10." followed by digits
    if not prefix.startswith("10."):
        return False

    registrant = prefix[3:]  # Remove "10."
    if not registrant or not registrant.replace(".", "").isdigit():
        return False

    # Suffix must not be empty
    if not suffix:
        return False

    return True


def validate_url(url: str) -> bool:
    """
    Validate URL format.

    Args:
        url: URL to validate

    Returns:
        True if URL format is valid
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_citation_format(citation: str) -> tuple[bool, list[str]]:
    """
    Validate citation format using AST parsing.

    Args:
        citation: Citation string to validate

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    # Try to parse as LaTeX first (for \cite commands)
    if citation.strip().startswith("\\"):
        parser = LatexParser()
        try:
            doc = parser.parse(citation)

            # Check for citation nodes
            citation_nodes = [n for n in doc.nodes if n.type == "citation"]
            if not citation_nodes:
                issues.append("No valid citation command found")
            else:
                # Validate citation content
                for node in citation_nodes:
                    keys = node.metadata.get("citation_keys", [])
                    if not keys:
                        issues.append("Citation command has no keys")
                    for key in keys:
                        if not key.strip():
                            issues.append("Empty citation key")

        except Exception as e:
            issues.append(f"LaTeX parsing error: {str(e)}")

    else:
        # Check as plain text citation (Author Year) format
        # Year check - look for 4-digit year
        has_year = False
        words = citation.split()
        for word in words:
            # Remove parentheses and punctuation
            clean_word = word.strip("().,;:")
            if len(clean_word) == 4 and clean_word.isdigit():
                year = int(clean_word)
                if 1900 <= year <= 2100:
                    has_year = True
                    break

        if not has_year:
            issues.append("Missing year (19xx or 20xx)")

        # Author check - at least one capitalized word
        has_author = False
        for word in words:
            clean_word = word.strip("().,;:")
            if clean_word and clean_word[0].isupper() and len(clean_word) > 1:
                if clean_word[1:].islower():
                    has_author = True
                    break

        if not has_author:
            issues.append("Missing proper author name (capitalized word)")

        # Common formatting issues
        if "  " in citation:
            issues.append("Contains double spaces")

        if citation.startswith(" ") or citation.endswith(" "):
            issues.append("Leading or trailing whitespace")

    return len(issues) == 0, issues


def validate_bibtex_entry(bibtex: str) -> tuple[bool, list[str]]:
    """
    Validate BibTeX entry format using AST parser.

    Args:
        bibtex: BibTeX string to validate

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    parser = BibtexParser()
    try:
        entries = parser.parse(bibtex)

        if not entries.nodes:
            issues.append("No valid BibTeX entries found")
        else:
            for entry in entries.nodes:
                # Check entry type
                if entry.type != "entry":
                    continue

                metadata = entry.metadata

                # Check required fields based on entry type
                entry_type = metadata.get("entry_type", "").lower()

                # Common required fields for most entry types
                required_fields = ["author", "title", "year"]

                # Add type-specific requirements
                if entry_type == "article":
                    required_fields.extend(["journal"])
                elif entry_type == "book":
                    required_fields.extend(["publisher"])
                elif entry_type == "inproceedings":
                    required_fields.extend(["booktitle"])

                # Check for missing fields
                fields = metadata.get("fields", {})
                for field in required_fields:
                    if field not in fields or not fields[field].strip():
                        issues.append(f"Missing or empty {field} field")

                # Validate specific field formats
                if "year" in fields:
                    year = fields["year"].strip()
                    try:
                        year_int = int(year)
                        if year_int < 1900 or year_int > 2100:
                            issues.append(f"Suspicious year value: {year}")
                    except ValueError:
                        issues.append(f"Invalid year format: {year}")

    except Exception as e:
        issues.append(f"BibTeX parsing error: {str(e)}")

    return len(issues) == 0, issues


def detect_potential_hallucination(
    citation: str, context: str = ""
) -> tuple[bool, str]:
    """
    Detect potential hallucination in citations using AST parsing where applicable.

    Args:
        citation: Citation to check
        context: Optional context for additional validation

    Returns:
        Tuple of (is_likely_hallucinated, reason)
    """
    # For structured citations, parse them first
    if citation.strip().startswith("@"):
        # BibTeX entry
        parser = BibtexParser()
        try:
            entries = parser.parse(citation)
            if entries.nodes:
                entry = entries.nodes[0]
                fields = entry.metadata.get("fields", {})

                # Check year
                year = fields.get("year", "")
                if year:
                    try:
                        year_int = int(year)

                        current_year = datetime.datetime.now().year
                        if year_int > current_year:
                            return True, f"Future year: {year}"
                    except ValueError:
                        pass

                # Check author names
                authors = fields.get("author", "")
                if any(
                    word in authors.upper()
                    for word in ["GPT", "CHATGPT", "CLAUDE", "LLM"]
                ):
                    return True, "Contains AI model names in author field"

        except Exception:
            pass

    # Check for suspicious patterns without regex

    current_year = datetime.datetime.now().year

    # Check for future years
    words = citation.split()
    for word in words:
        clean_word = word.strip("().,;:")
        if len(clean_word) == 4 and clean_word.isdigit():
            year = int(clean_word)
            if year > current_year:
                return True, f"Future year: {year}"

    # Check for AI model names
    citation_upper = citation.upper()
    ai_names = ["GPT", "CHATGPT", "CLAUDE", "LLM", "BARD", "GEMINI"]
    for ai_name in ai_names:
        if ai_name in citation_upper:
            return True, "Contains AI model names"

    # Check for placeholder text
    placeholder_words = [
        "EXAMPLE",
        "SAMPLE",
        "TEST",
        "PLACEHOLDER",
        "TODO",
        "FIXME",
    ]
    for placeholder in placeholder_words:
        if placeholder in citation_upper:
            return True, "Contains placeholder text"

    # Check for unusual format (many consecutive capitals)
    consecutive_caps = 0
    max_consecutive = 0
    for char in citation:
        if char.isupper():
            consecutive_caps += 1
            max_consecutive = max(max_consecutive, consecutive_caps)
        else:
            consecutive_caps = 0

    if max_consecutive >= 4:
        return True, "Unusual format (multiple consecutive capitals)"

    return False, ""


def validate_markdown_link(link_text: str, url: str) -> tuple[bool, list[str]]:
    """
    Validate markdown link format and consistency using AST parser.

    Args:
        link_text: The text of the link
        url: The URL of the link

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    # Validate URL
    if not validate_url(url):
        issues.append("Invalid URL format")

    # Check for empty link text
    if not link_text.strip():
        issues.append("Empty link text")

    # Check for non-descriptive link text
    non_descriptive = ["click here", "link", "url", "reference", "here", "this"]
    if link_text.strip().lower() in non_descriptive:
        issues.append("Non-descriptive link text")

    # Parse the link as markdown to ensure it's valid
    parser = MarkdownParser()
    try:
        # Create a test markdown with the link
        test_md = f"[{link_text}]({url})"
        doc = parser.parse(test_md)

        # Check if a link node was created
        link_nodes = [n for n in doc.nodes if n.type == "link"]
        if not link_nodes:
            issues.append("Failed to parse as valid markdown link")

    except Exception as e:
        issues.append(f"Markdown parsing error: {str(e)}")

    return len(issues) == 0, issues


def validate_latex_citation(latex_text: str) -> tuple[bool, list[str]]:
    """
    Validate LaTeX citations using AST parser.

    Args:
        latex_text: LaTeX text containing citations

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    parser = LatexParser()
    try:
        parser.parse(latex_text)
        citations = parser.extract_citations(latex_text)

        if not citations:
            issues.append("No citations found in LaTeX text")

        for citation in citations:
            # Check citation type
            cite_type = citation.get("type", "")
            if cite_type not in [
                "cite",
                "citep",
                "citet",
                "textcite",
                "citeauthor",
                "citeyear",
            ]:
                issues.append(f"Unknown citation command: \\{cite_type}")

            # Check keys
            keys = citation.get("keys", [])
            if not keys:
                issues.append(
                    f"Citation at line {citation.get('line', '?')} has no keys"
                )

            for key in keys:
                if not key.strip():
                    issues.append("Empty citation key")
                elif " " in key:
                    issues.append(f"Citation key contains spaces: {key}")
                elif (
                    not key.replace("_", "")
                    .replace("-", "")
                    .replace(":", "")
                    .isalnum()
                ):
                    issues.append(
                        f"Citation key contains invalid characters: {key}"
                    )

    except Exception as e:
        issues.append(f"LaTeX parsing error: {str(e)}")

    return len(issues) == 0, issues
