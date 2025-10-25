"""
Citation style fixer using LLM to detect and correct author-citation redundancy.

This module handles cases where author names appear both in the sentence text
and in the citation, creating redundancy like:
"Smith and Jones (Smith and Jones 2023) found that..."
which should be:
"Smith and Jones (2023) found that..."
"""

import logging

# import re  # Banned - using string methods instead
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CitationStyleIssue:
    """Represents a citation style issue that needs correction."""

    line_number: int
    original_text: str
    corrected_text: str
    explanation: str
    confidence: float


class CitationStyleFixer:
    """Fixes citation style issues using pattern matching and LLM analysis."""

    def __init__(self, llm_client=None):
        """
        Initialize the citation style fixer.

        Args:
            llm_client: Optional LLM client for advanced context analysis.
                       If None, uses rule-based detection only.
        """
        self.llm_client = llm_client

    def detect_author_repetition(self, text: str) -> list[CitationStyleIssue]:
        """
        Detect cases where author names are repeated in citations.

        Args:
            text: The text to analyze

        Returns:
            List of detected citation style issues
        """
        issues = []
        lines = text.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Find potential author-citation pairs using string methods
            issues_in_line = self._find_author_repetitions_in_line(
                line, line_num
            )
            issues.extend(issues_in_line)

        # If LLM client is available, use it for more sophisticated detection
        if self.llm_client and issues:
            issues = self._refine_with_llm(text, issues)

        return issues

    def _find_author_repetitions_in_line(
        self, line: str, line_num: int
    ) -> list[CitationStyleIssue]:
        """Find author repetitions in a single line using string methods."""
        issues = []

        # Look for patterns like "Author (Author (Year))" or "Author ([Author (Year)](URL))"
        i = 0
        while i < len(line):
            # Find opening parenthesis
            paren_start = line.find("(", i)
            if paren_start == -1:
                break

            # Check if there's an author name before the parenthesis
            author_before = self._extract_author_before_paren(
                line[:paren_start]
            )
            if not author_before:
                i = paren_start + 1
                continue

            # Check what's inside the parenthesis
            paren_content, paren_end = self._extract_parenthesis_content(
                line, paren_start
            )
            if not paren_content or paren_end == -1:
                i = paren_start + 1
                continue

            # Check if it contains a citation pattern
            citation_info = self._parse_citation_content(paren_content)
            if citation_info and citation_info.get("authors"):
                # Check if authors match
                if self._authors_match(author_before, citation_info["authors"]):
                    # Create correction
                    original = line[
                        paren_start - len(author_before) - 1 : paren_end + 1
                    ]

                    if citation_info.get("url"):
                        corrected = f"{author_before} ([{citation_info['year']}]({citation_info['url']}))"
                    else:
                        corrected = f"{author_before} ({citation_info['year']})"

                    issue = CitationStyleIssue(
                        line_number=line_num,
                        original_text=original.strip(),
                        corrected_text=corrected,
                        explanation="Removed redundant author names from citation",
                        confidence=0.9,
                    )
                    issues.append(issue)

            i = paren_end + 1 if paren_end != -1 else paren_start + 1

        return issues

    def _extract_author_before_paren(self, text: str) -> str:
        """Extract author names before a parenthesis."""
        text = text.rstrip()
        if not text:
            return ""

        # Look for capitalized words at the end of the text
        words = text.split()
        author_words = []

        # Walk backwards through words
        for i in range(len(words) - 1, -1, -1):
            word = words[i]
            # Check if it's a connector or author name
            if word.lower() in ["and", "&", "et"]:
                author_words.insert(0, word)
            elif i < len(words) - 1 and words[i + 1].lower() == "al.":
                author_words.insert(0, word)
                author_words.insert(1, words[i + 1])
            elif word and word[0].isupper():
                author_words.insert(0, word)
            else:
                break

        return " ".join(author_words) if author_words else ""

    def _extract_parenthesis_content(
        self, text: str, start: int
    ) -> tuple[str, int]:
        """Extract content within parentheses, handling nested parentheses."""
        if start >= len(text) or text[start] != "(":
            return "", -1

        paren_count = 1
        i = start + 1
        content_start = i

        while i < len(text) and paren_count > 0:
            if text[i] == "(":
                paren_count += 1
            elif text[i] == ")":
                paren_count -= 1
            i += 1

        if paren_count == 0:
            return text[content_start : i - 1], i - 1
        return "", -1

    def _parse_citation_content(self, content: str) -> dict | None:
        """Parse citation content to extract authors, year, and URL."""
        # Handle markdown link format: [Author (Year)](URL)
        if "[" in content and "]" in content and "(" in content:
            bracket_start = content.find("[")
            bracket_end = content.find("]", bracket_start)
            if (
                bracket_end != -1
                and bracket_end + 1 < len(content)
                and content[bracket_end + 1] == "("
            ):
                # Extract citation text and URL
                citation_text = content[bracket_start + 1 : bracket_end]
                url_end = content.find(")", bracket_end + 2)
                if url_end != -1:
                    url = content[bracket_end + 2 : url_end]
                    # Parse citation text
                    year_info = self._extract_year_from_citation(citation_text)
                    if year_info:
                        return {
                            "authors": year_info["authors"],
                            "year": year_info["year"],
                            "url": url,
                        }

        # Handle simple format: Author (Year)
        year_info = self._extract_year_from_citation(content)
        if year_info:
            return year_info

        return None

    def _extract_year_from_citation(self, text: str) -> dict | None:
        """Extract authors and year from citation text."""
        # Look for 4-digit year in parentheses
        year_start = text.rfind("(")
        if year_start == -1:
            return None

        year_end = text.find(")", year_start)
        if year_end == -1:
            return None

        potential_year = text[year_start + 1 : year_end].strip()
        if len(potential_year) == 4 and potential_year.isdigit():
            # Extract authors (everything before the year parentheses)
            authors = text[:year_start].strip()
            return {"authors": authors, "year": potential_year, "url": None}

        return None

    def _authors_match(self, author1: str, author2: str) -> bool:
        """Check if two author strings refer to the same authors."""
        # Normalize the strings
        a1 = author1.lower().strip()
        a2 = author2.lower().strip()

        # Direct match
        if a1 == a2:
            return True

        # Check if one is contained in the other (for cases like "Der Kiureghian" vs "Kiureghian")
        if a1 in a2 or a2 in a1:
            return True

        # Check last names only
        # Extract last names (assume last word is last name)
        last_names1 = [
            word for word in a1.split() if word not in ["and", "&", "et", "al."]
        ]
        last_names2 = [
            word for word in a2.split() if word not in ["and", "&", "et", "al."]
        ]

        if last_names1 and last_names2:
            # Check if the last names match
            if len(last_names1) == len(last_names2):
                return all(n1 in a2 for n1 in last_names1[-len(last_names2) :])

        return False

    def _refine_with_llm(
        self, full_text: str, issues: list[CitationStyleIssue]
    ) -> list[CitationStyleIssue]:
        """
        Use LLM to refine and validate detected issues.

        This would send context to an LLM to verify that the correction makes sense
        in the broader context of the paragraph.
        """
        # This is a placeholder for LLM integration
        # In a real implementation, this would:
        # 1. Send the surrounding context to an LLM
        # 2. Ask if the author names truly refer to the same people
        # 3. Validate that the correction maintains the intended meaning
        # 4. Adjust confidence scores based on LLM feedback

        logger.info(f"LLM refinement would process {len(issues)} issues")
        return issues

    def fix_document(self, text: str) -> tuple[str, list[CitationStyleIssue]]:
        """
        Fix all citation style issues in a document.

        Args:
            text: The document text

        Returns:
            Tuple of (corrected_text, list_of_issues)
        """
        issues = self.detect_author_repetition(text)

        if not issues:
            return text, []

        # Sort issues by line number in reverse order to maintain positions
        issues.sort(key=lambda x: x.line_number, reverse=True)

        # Apply corrections
        lines = text.split("\n")
        for issue in issues:
            if 0 < issue.line_number <= len(lines):
                line = lines[issue.line_number - 1]
                corrected_line = line.replace(
                    issue.original_text, issue.corrected_text
                )
                lines[issue.line_number - 1] = corrected_line
                logger.info(
                    f"Line {issue.line_number}: Fixed redundant citation format"
                )

        corrected_text = "\n".join(lines)
        return corrected_text, issues

    def generate_report(self, issues: list[CitationStyleIssue]) -> str:
        """
        Generate a human-readable report of detected issues.

        Args:
            issues: List of detected issues

        Returns:
            Formatted report string
        """
        if not issues:
            return "No citation style issues detected."

        report = [f"Found {len(issues)} citation style issues:\n"]

        for i, issue in enumerate(issues, 1):
            report.append(f"{i}. Line {issue.line_number}:")
            report.append(f"   Original: {issue.original_text}")
            report.append(f"   Corrected: {issue.corrected_text}")
            report.append(f"   Explanation: {issue.explanation}")
            report.append(f"   Confidence: {issue.confidence:.0%}\n")

        return "\n".join(report)


# Example usage
if __name__ == "__main__":
    sample_text = """
    Smith and Jones (Smith and Jones 2023) demonstrated that the method works well.
    According to Williams ([Williams (2022)](https://example.com)), the results are significant.
    Johnson et al. (Johnson et al. (2021)) found similar patterns.
    However, Brown (2020) used a different approach entirely.
    """

    fixer = CitationStyleFixer()
    corrected_text, issues = fixer.fix_document(sample_text)

    print("Original text:")
    print(sample_text)
    print("\nCorrected text:")
    print(corrected_text)
    print("\nReport:")
    print(fixer.generate_report(issues))
