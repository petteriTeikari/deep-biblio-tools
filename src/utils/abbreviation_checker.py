"""
Abbreviation checker for scientific texts.

This module detects abbreviations/acronyms that are used without prior definition.
Good scientific writing introduces abbreviations when first used, e.g.:
"Local Interpretable Model-agnostic Explanations (LIME) is a technique..."
Then subsequent uses of "LIME" are acceptable.
"""

import logging

# import re  # Banned - using string methods instead
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AbbreviationIssue:
    """Represents an undefined abbreviation found in text."""

    abbreviation: str
    line_number: int
    position: int
    context: str
    suggested_definition: str | None = None
    confidence: float = 1.0


@dataclass
class AbbreviationDefinition:
    """Represents a defined abbreviation in the text."""

    abbreviation: str
    full_form: str
    line_number: int
    position: int


class AbbreviationChecker:
    """Checks for undefined abbreviations in scientific text."""

    def __init__(self, common_abbreviations: set[str] | None = None):
        """
        Initialize the abbreviation checker.

        Args:
            common_abbreviations: Set of common abbreviations that don't need definition
                                (e.g., 'USA', 'PhD', 'etc.', 'i.e.', 'e.g.')
        """
        self.common_abbreviations = (
            common_abbreviations or self._get_default_common_abbreviations()
        )

    def _get_default_common_abbreviations(self) -> set[str]:
        """Get default set of common abbreviations that don't need definition."""
        return {
            # Common academic
            "PhD",
            "MD",
            "BA",
            "BS",
            "MA",
            "MS",
            "MBA",
            "JD",
            "LLB",
            # Countries and places
            "USA",
            "UK",
            "EU",
            "UN",
            "US",
            "USSR",
            "UAE",
            "NYC",
            "LA",
            # Time
            "AM",
            "PM",
            "AD",
            "BC",
            "BCE",
            "CE",
            # Common terms
            "ID",
            "URL",
            "API",
            "FAQ",
            "CEO",
            "CFO",
            "CTO",
            "HR",
            # Latin abbreviations
            "etc",
            "vs",
            "cf",
            "ibid",
            "op",
            "cit",
            "et",
            "al",
            # Units (though these should often be lowercase)
            "KB",
            "MB",
            "GB",
            "TB",
            "GHz",
            "MHz",
            # Common in ML/AI papers
            "AI",
            "ML",
            "DL",
            "RL",
            "NLP",
            "CV",
            "GPU",
            "CPU",
            "RAM",
            "IEEE",
            "ACM",
            "ICML",
            "NIPS",
            "CVPR",
            "ICCV",
            "ECCV",
            # Statistical
            "CI",
            "SD",
            "SE",
            "IQR",
            "ANOVA",
            "RMSE",
            "MAE",
            "ROC",
            "AUC",
            # Other common
            "PDF",
            "HTML",
            "XML",
            "JSON",
            "CSV",
            "SQL",
            "HTTP",
            "HTTPS",
            "DOI",
            "ISBN",
            "ISSN",
        }

    def check_document(
        self, text: str
    ) -> tuple[list[AbbreviationIssue], list[AbbreviationDefinition]]:
        """
        Check a document for undefined abbreviations.

        Args:
            text: The document text

        Returns:
            Tuple of (list of issues, list of definitions found)
        """
        lines = text.split("\n")

        # First, find all definitions
        definitions = self._find_definitions(lines)
        defined_abbrs = {d.abbreviation: d for d in definitions}

        # Then, find all abbreviation uses
        issues = []
        seen_abbrs = set()

        for line_num, line in enumerate(lines, 1):
            # Skip if line is likely a reference or bibliography entry
            if self._is_reference_line(line):
                continue

            # Find all potential abbreviations in this line
            potential_abbrs = self._find_abbreviations_in_line(line)

            for abbr, position in potential_abbrs:
                # Skip if it's a common abbreviation
                if abbr in self.common_abbreviations:
                    continue

                # Skip if it's already been defined
                if abbr in defined_abbrs:
                    # Check if this use comes before the definition
                    if line_num < defined_abbrs[abbr].line_number:
                        # Used before definition!
                        issue = AbbreviationIssue(
                            abbreviation=abbr,
                            line_number=line_num,
                            position=position,
                            context=self._get_context(
                                line, position, position + len(abbr)
                            ),
                            suggested_definition=defined_abbrs[abbr].full_form,
                        )
                        issues.append(issue)
                    continue

                # Skip if we've already reported this abbreviation
                if abbr in seen_abbrs:
                    continue

                # Check if it might be a variable name or code
                if self._is_likely_code_or_variable(abbr, line):
                    continue

                # This is an undefined abbreviation
                seen_abbrs.add(abbr)
                issue = AbbreviationIssue(
                    abbreviation=abbr,
                    line_number=line_num,
                    position=position,
                    context=self._get_context(
                        line, position, position + len(abbr)
                    ),
                    suggested_definition=self._suggest_definition(abbr),
                )
                issues.append(issue)

        return issues, definitions

    def _find_abbreviations_in_line(self, line: str) -> list[tuple[str, int]]:
        """Find potential abbreviations in a line using string methods."""
        abbreviations = []
        words = line.split()
        current_pos = 0

        for word in words:
            # Find the actual position of this word in the line
            word_pos = line.find(word, current_pos)
            if word_pos == -1:
                continue
            current_pos = word_pos + len(word)

            # Remove punctuation from word
            clean_word = word.strip(".,;:!?\"'()")

            # Check different abbreviation patterns

            # 1. All caps abbreviations (2+ letters): NASA, WHO, LSTM
            if (
                len(clean_word) >= 2
                and clean_word.isupper()
                and clean_word.isalpha()
            ):
                abbreviations.append((clean_word, word_pos))

            # 2. Mixed case with dots: Ph.D., M.D.
            elif "." in clean_word and self._is_dotted_abbreviation(clean_word):
                abbreviations.append((clean_word, word_pos))

            # 3. CamelCase abbreviations: CatBoost, NeRF
            elif self._is_camelcase_abbreviation(clean_word):
                abbreviations.append((clean_word, word_pos))

            # 4. Special patterns: 3D, 2FA, B2B
            elif self._is_special_pattern_abbreviation(clean_word):
                abbreviations.append((clean_word, word_pos))

        return abbreviations

    def _is_dotted_abbreviation(self, word: str) -> bool:
        """Check if word is a dotted abbreviation like Ph.D."""
        parts = word.split(".")
        if len(parts) < 2:
            return False

        # Check each part (except the last which might be empty)
        for part in parts[:-1]:
            if not part or len(part) > 2:
                return False
            if not part[0].isupper():
                return False

        return True

    def _is_camelcase_abbreviation(self, word: str) -> bool:
        """Check if word is a CamelCase abbreviation."""
        if len(word) < 3:
            return False

        # Must start with uppercase
        if not word[0].isupper():
            return False

        # Must have at least one more uppercase letter
        has_another_upper = False
        has_lower = False

        for char in word[1:]:
            if char.isupper():
                has_another_upper = True
            elif char.islower():
                has_lower = True

        return has_another_upper and has_lower

    def _is_special_pattern_abbreviation(self, word: str) -> bool:
        """Check for special patterns like 3D, 2FA, B2B."""
        if len(word) < 2:
            return False

        # Pattern: digits followed by letters (3D, 2FA)
        has_digit = False
        has_letter = False

        for char in word:
            if char.isdigit():
                has_digit = True
            elif char.isupper():
                has_letter = True

        return has_digit and has_letter

    def _find_definitions(
        self, lines: list[str]
    ) -> list[AbbreviationDefinition]:
        """Find all abbreviation definitions in the text using string methods."""
        definitions = []

        for line_num, line in enumerate(lines, 1):
            # Look for patterns like "Full Name (ABBR)" or "ABBR (Full Name)"
            definitions.extend(self._find_definitions_in_line(line, line_num))

        return definitions

    def _find_definitions_in_line(
        self, line: str, line_num: int
    ) -> list[AbbreviationDefinition]:
        """Find definitions in a single line."""
        definitions = []

        # Find all parentheses pairs
        i = 0
        while i < len(line):
            start = line.find("(", i)
            if start == -1:
                break

            end = line.find(")", start)
            if end == -1:
                i = start + 1
                continue

            # Extract content inside parentheses
            paren_content = line[start + 1 : end].strip()

            # Check if it's an abbreviation (all caps, 2+ letters)
            if (
                len(paren_content) >= 2
                and paren_content.isupper()
                and paren_content.isalpha()
            ):
                # Look for full form before the parentheses
                before_paren = line[:start].strip()

                # Extract potential full form (capitalized words before parentheses)
                words_before = before_paren.split()
                if words_before:
                    # Find continuous capitalized words
                    full_form_words = []
                    for j in range(len(words_before) - 1, -1, -1):
                        word = words_before[j]
                        if word and word[0].isupper():
                            full_form_words.insert(0, word)
                        else:
                            break

                    if full_form_words:
                        full_form = " ".join(full_form_words)

                        # Validate that the abbreviation matches the full form
                        if self._abbreviation_matches_full_form(
                            paren_content, full_form
                        ):
                            definitions.append(
                                AbbreviationDefinition(
                                    abbreviation=paren_content,
                                    full_form=full_form,
                                    line_number=line_num,
                                    position=start,
                                )
                            )

            # Also check reverse pattern: ABBR (Full Name)
            elif (
                paren_content
                and paren_content[0].isupper()
                and " " in paren_content
            ):
                # Check if text before parentheses is an abbreviation
                words_before = line[:start].strip().split()
                if words_before:
                    potential_abbr = words_before[-1]
                    if (
                        len(potential_abbr) >= 2
                        and potential_abbr.isupper()
                        and potential_abbr.isalpha()
                    ):
                        if self._abbreviation_matches_full_form(
                            potential_abbr, paren_content
                        ):
                            definitions.append(
                                AbbreviationDefinition(
                                    abbreviation=potential_abbr,
                                    full_form=paren_content,
                                    line_number=line_num,
                                    position=line.rfind(
                                        potential_abbr, 0, start
                                    ),
                                )
                            )

            i = end + 1

        return definitions

    def _abbreviation_matches_full_form(
        self, abbr: str, full_form: str
    ) -> bool:
        """Check if an abbreviation reasonably matches its full form."""
        # Simple heuristic: first letters of words should match abbreviation
        words = full_form.split()
        first_letters = "".join(
            w[0].upper() for w in words if w and w[0].isalpha()
        )

        # Allow some flexibility (e.g., some words might be skipped)
        if abbr == first_letters:
            return True

        # Check if abbreviation letters appear in order in the full form
        abbr_idx = 0
        for char in full_form.upper():
            if abbr_idx < len(abbr) and char == abbr[abbr_idx]:
                abbr_idx += 1

        return abbr_idx == len(abbr)

    def _is_reference_line(self, line: str) -> bool:
        """Check if a line is likely part of a reference/bibliography."""
        line = line.strip()

        # [1] style references
        if line.startswith("[") and len(line) > 2 and line[1].isdigit():
            close_bracket = line.find("]")
            if close_bracket > 1:
                # Check if everything between brackets is digits
                between = line[1:close_bracket]
                if between.isdigit():
                    return True

        # Numbered references (1. Author et al...)
        if line and line[0].isdigit():
            # Find the first non-digit character
            i = 1
            while i < len(line) and line[i].isdigit():
                i += 1
            if i < len(line) and line[i] == ".":
                # Check if it contains typical reference patterns
                if "(" in line and ")" in line:
                    return True

        # URL lines
        if line.startswith("http"):
            return True

        return False

    def _is_likely_code_or_variable(self, abbr: str, line: str) -> bool:
        """Check if an abbreviation is likely a code variable or function name."""
        # Check for code indicators
        code_indicators = [
            "=",
            "{",
            "}",
            "()",
            "->",
            "=>",
            "function",
            "def",
            "class",
            "var",
            "let",
            "const",
        ]
        return any(indicator in line for indicator in code_indicators)

    def _get_context(
        self, line: str, start: int, end: int, context_chars: int = 40
    ) -> str:
        """Get context around an abbreviation."""
        context_start = max(0, start - context_chars)
        context_end = min(len(line), end + context_chars)

        prefix = "..." if context_start > 0 else ""
        suffix = "..." if context_end < len(line) else ""

        return prefix + line[context_start:context_end] + suffix

    def _suggest_definition(self, abbr: str) -> str | None:
        """Suggest a possible definition for an abbreviation."""
        # This could be enhanced with an LLM or a database of common abbreviations
        known_abbreviations = {
            "LIME": "Local Interpretable Model-agnostic Explanations",
            "SHAP": "SHapley Additive exPlanations",
            "GAM": "Generalized Additive Model",
            "AVM": "Automated Valuation Model",
            "UAD": "Uniform Appraisal Dataset",
            "MLS": "Multiple Listing Service",
            "NeRF": "Neural Radiance Field",
            "LSTM": "Long Short-Term Memory",
            "GRU": "Gated Recurrent Unit",
            "CNN": "Convolutional Neural Network",
            "RNN": "Recurrent Neural Network",
            "GAN": "Generative Adversarial Network",
            "VAE": "Variational Autoencoder",
            "SVM": "Support Vector Machine",
            "KNN": "K-Nearest Neighbors",
            "PCA": "Principal Component Analysis",
            "API": "Application Programming Interface",
            "REST": "Representational State Transfer",
            "CRUD": "Create, Read, Update, Delete",
            "SDK": "Software Development Kit",
            "IDE": "Integrated Development Environment",
            "CLI": "Command Line Interface",
            "GUI": "Graphical User Interface",
        }

        return known_abbreviations.get(abbr)


def check_abbreviations(
    text: str, common_abbreviations: set[str] | None = None
) -> tuple[list[AbbreviationIssue], list[AbbreviationDefinition]]:
    """
    Convenience function to check for undefined abbreviations.

    Args:
        text: The text to check
        common_abbreviations: Optional set of abbreviations that don't need definition

    Returns:
        Tuple of (issues, definitions)
    """
    checker = AbbreviationChecker(common_abbreviations)
    return checker.check_document(text)
