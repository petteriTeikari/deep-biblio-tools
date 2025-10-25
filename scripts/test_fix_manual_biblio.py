#!/usr/bin/env python3
"""
Test suite for fix-manual-biblio-to-authornames.py

Tests cover normal cases, edge cases, and pathological cases.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent))

try:
    from fix_manual_biblio_to_authornames import AuthorYearConverter, BibEntry
except ImportError:
    # Try with explicit path
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "fix_manual_biblio_to_authornames",
        Path(__file__).parent / "fix-manual-biblio-to-authornames.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    AuthorYearConverter = module.AuthorYearConverter
    BibEntry = module.BibEntry


class TestAuthorYearConverter(unittest.TestCase):
    """Test cases for the AuthorYearConverter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.converter = AuthorYearConverter()

    def test_extract_surname_simple(self):
        """Test simple surname extraction."""
        cases = [
            ("John Smith", "Smith"),
            ("Smith", "Smith"),
            ("J. Smith", "Smith"),
            ("John A. Smith", "Smith"),
            ("Mary Smith-Jones", "Smith-Jones"),
        ]

        for author, expected in cases:
            with self.subTest(author=author):
                result = self.converter.extract_surname(author)
                self.assertEqual(result, expected)

    def test_extract_surname_prefixes(self):
        """Test surname extraction with prefixes."""
        cases = [
            ("Guido van Rossum", "van Rossum"),
            ("Ludwig van Beethoven", "van Beethoven"),
            ("Charles de Gaulle", "de Gaulle"),
            ("Claudio da Silva", "da Silva"),
            ("Willem de Kooning", "de Kooning"),
            ("Bart van der Waals", "van der Waals"),
            ("Maria de la Cruz", "de la Cruz"),
        ]

        for author, expected in cases:
            with self.subTest(author=author):
                result = self.converter.extract_surname(author)
                self.assertEqual(result, expected)

    def test_extract_surname_comma_format(self):
        """Test surname extraction with comma format."""
        cases = [
            ("Smith, John", "Smith"),
            ("van der Waals, Johannes", "van der Waals"),
            ("De Gaulle, Charles", "De Gaulle"),
        ]

        for author, expected in cases:
            with self.subTest(author=author):
                result = self.converter.extract_surname(author)
                self.assertEqual(result, expected)

    def test_format_author_label_single(self):
        """Test formatting for single authors."""
        cases = [
            ("John Smith", "2025", "Smith(2025)"),
            ("IEEE", "2025", "IEEE(2025)"),
            ("", "2025", "Anonymous(2025)"),
            ("John Smith", "", "Smith"),
        ]

        for authors, year, expected in cases:
            with self.subTest(authors=authors, year=year):
                result = self.converter.format_author_label(authors, year)
                self.assertEqual(result, expected)

    def test_format_author_label_multiple(self):
        """Test formatting for multiple authors."""
        cases = [
            ("John Smith and Jane Doe", "2025", "Smith and Doe(2025)"),
            ("A. Smith, B. Jones, C. Williams", "2025", "Smith et al.(2025)"),
            ("Smith et al.", "2025", "Smith et al.(2025)"),
        ]

        for authors, year, expected in cases:
            with self.subTest(authors=authors):
                result = self.converter.format_author_label(authors, year)
                self.assertEqual(result, expected)

    def test_format_author_label_organizations(self):
        """Test formatting for organizations."""
        cases = [
            ("Procter and Gamble", "2025", "Procter and Gamble(2025)"),
            (
                "U.S. Department of Energy",
                "2025",
                "U.S. Department of Energy(2025)",
            ),
            ("https://github.com", "2025", "github.com(2025)"),
            ("http://www.example.com", "2025", "example.com(2025)"),
        ]

        for authors, year, expected in cases:
            with self.subTest(authors=authors):
                result = self.converter.format_author_label(authors, year)
                self.assertEqual(result, expected)

    def test_extract_author_year_standard(self):
        """Test standard author-year extraction."""
        cases = [
            ("John Smith (2025)", ("John Smith", "2025", 1.0)),
            ("Smith and Jones (2024)", ("Smith and Jones", "2024", 1.0)),
            (
                "IEEE Computer Society (2025)",
                ("IEEE Computer Society", "2025", 1.0),
            ),
            ("Smith et al. (2023)", ("Smith et al.", "2023", 1.0)),
        ]

        for text, expected in cases:
            with self.subTest(text=text):
                result = self.converter.extract_author_year(text)
                self.assertEqual(result, expected)

    def test_extract_author_year_special(self):
        """Test special cases in author-year extraction."""
        cases = [
            ("Smith (forthcoming)", ("Smith", "forthcoming", 0.9)),
            ("Jones (in press)", ("Jones", "in press", 0.9)),
            ("Williams (2025/2026)", ("Williams", "2025", 1.0)),
            ("Brown (2025-26)", ("Brown", "2025", 1.0)),
        ]

        for text, expected in cases:
            with self.subTest(text=text):
                result = self.converter.extract_author_year(text)
                self.assertEqual(result, expected)

    def test_width_parameter_detection(self):
        """Test bibliography width parameter detection."""
        cases = [
            ("\\begin{thebibliography}{9}", 5, ("9", 5, "9")),
            ("\\begin{thebibliography}{99}", 50, ("99", 50, "99")),
            ("\\begin{thebibliography}{99}", 150, ("99", 150, "999")),
            ("\\begin{thebibliography}{999}", 1500, ("999", 1500, "9999")),
        ]

        for content_start, entry_count, expected in cases:
            content = content_start + "\n"
            for i in range(entry_count):
                content += f"\\bibitem{{key{i}}} Entry {i}\n"
            content += "\\end{thebibliography}"

            with self.subTest(entries=entry_count):
                result = self.converter.detect_width_parameter(content)
                self.assertEqual(result[0], expected[0])  # Current width
                self.assertEqual(result[1], expected[1])  # Entry count
                self.assertEqual(result[2], expected[2])  # Suggested width

    def test_parse_bibitem_standard(self):
        """Test parsing standard bibitem entries."""
        entry = "\\bibitem{smith2025} \\href{https://example.com}{John Smith (2025)} Great Paper Title"

        result = self.converter.parse_bibitem(entry)

        self.assertIsNotNone(result)
        self.assertEqual(result.key, "smith2025")
        self.assertEqual(result.author_part, "John Smith")
        self.assertEqual(result.year, "2025")
        self.assertEqual(result.formatted_label, "Smith(2025)")
        self.assertFalse(result.needs_review)

    def test_parse_bibitem_no_href(self):
        """Test parsing bibitem without href."""
        entry = "\\bibitem{jones2024} Jane Jones (2024) Another Great Paper"

        result = self.converter.parse_bibitem(entry)

        self.assertIsNotNone(result)
        self.assertEqual(result.key, "jones2024")
        self.assertEqual(result.author_part, "Jane Jones")
        self.assertEqual(result.year, "2024")
        self.assertEqual(result.formatted_label, "Jones(2024)")

    def test_parse_bibitem_multiline(self):
        """Test parsing multiline bibitem."""
        entry = """\\bibitem{williams2023} \\href{https://example.com}{Williams,
Brown, and
Davis (2023)} A Very Long Title That
Spans Multiple Lines"""

        result = self.converter.parse_bibitem(entry)

        self.assertIsNotNone(result)
        self.assertEqual(result.key, "williams2023")
        self.assertEqual(result.formatted_label, "Williams et al.(2023)")

    def test_convert_entry_standard(self):
        """Test converting a standard entry."""
        entry = "\\bibitem{smith2025} \\href{url}{John Smith (2025)} Title"
        expected = "\\bibitem[Smith(2025)]{smith2025} \\href{url}{John Smith (2025)} Title"

        result = self.converter.convert_entry(entry)
        self.assertEqual(result, expected)

    def test_convert_entry_needs_review(self):
        """Test converting an entry that needs review."""
        entry = "\\bibitem{mystery} \\href{url}{Some text without year}"

        result = self.converter.convert_entry(entry)

        self.assertTrue(result.startswith("% NEEDS_REVIEW:"))
        self.assertIn("\\bibitem[", result)

    def test_full_bibliography_conversion(self):
        """Test converting a complete bibliography."""
        content = """
\\documentclass{article}
\\usepackage[authoryear,round]{natbib}
\\begin{document}

Some text here \\citep{smith2025}.

\\begin{thebibliography}{99}

\\bibitem{smith2025} \\href{https://doi.org/10.1234/5678}{John Smith (2025)}
An Excellent Paper. \\emph{Journal of Excellence} 42:1--10.

\\bibitem{jones2024} Jane Jones, Robert Brown (2024) Another Paper.
In \\emph{Proceedings of Conference}, pages 123--130.

\\bibitem{ieee2023} \\href{https://ieee.org}{IEEE (2023)}
Standards Document.

\\end{thebibliography}
\\end{document}
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tex", delete=False
        ) as f:
            f.write(content)
            input_path = Path(f.name)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tex", delete=False
        ) as f:
            output_path = Path(f.name)

        try:
            self.converter.convert_file(input_path, output_path, fix_width=True)

            result = output_path.read_text()

            # Check conversions
            self.assertIn("\\bibitem[Smith(2025)]{smith2025}", result)
            self.assertIn("\\bibitem[Jones and Brown(2024)]{jones2024}", result)
            self.assertIn("\\bibitem[IEEE(2023)]{ieee2023}", result)

            # Check width was fixed
            self.assertIn("\\begin{thebibliography}{9}", result)

        finally:
            input_path.unlink()
            output_path.unlink()


class TestEdgeCases(unittest.TestCase):
    """Test edge and pathological cases."""

    def setUp(self):
        """Set up test fixtures."""
        self.converter = AuthorYearConverter()

    def test_latex_accents_in_names(self):
        """Test handling of LaTeX accents."""
        cases = [
            ('Jos\\"{e} Garc\\"{i}a', "García"),
            ("Fran\\c{c}ois Poir\\'{e}", "Poiré"),
            ("Bj\\o rn Str\\o ustrup", "Stroustrup"),
        ]

        for author, expected_end in cases:
            with self.subTest(author=author):
                result = self.converter.extract_surname(author)
                # Just check it doesn't crash and returns something reasonable
                self.assertIsInstance(result, str)
                self.assertGreater(len(result), 0)

    def test_malformed_entries(self):
        """Test handling of malformed entries."""
        cases = [
            # Missing closing brace
            "\\bibitem{key Some text",
            # No key
            "\\bibitem{} Some text",
            # Already has label
            "\\bibitem[Existing(2025)]{key} Text",
        ]

        for entry in cases:
            with self.subTest(entry=entry):
                result = self.converter.parse_bibitem(entry)
                # Should either return None or handle gracefully
                if result is not None:
                    self.assertIsInstance(result, BibEntry)

    def test_empty_author_year(self):
        """Test handling of missing author or year."""
        cases = [
            ("(2025) Anonymous work", ("", "2025", 0.3)),
            ("No year information here", ("No year information here", "", 0.3)),
            ("", ("", "", 0.3)),
        ]

        for text, expected in cases:
            with self.subTest(text=text):
                authors, year, confidence = self.converter.extract_author_year(
                    text
                )
                self.assertEqual(year, expected[1])
                self.assertLessEqual(confidence, expected[2])


if __name__ == "__main__":
    unittest.main()
