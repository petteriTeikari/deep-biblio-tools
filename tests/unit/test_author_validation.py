"""Unit tests for author validation improvements.

Tests the fixes for false positives in author completeness validation.
Main issue: 86% false positive rate flagging complete entries as incomplete.

Test cases cover:
- BibTeX author field parsing
- Large author lists (6+ authors)
- "et al" handling for very large lists (15+ authors)
- CrossRef metadata comparison
"""

from scripts.validate_bib_source import (
    count_bibtex_authors,
    validate_author_completeness,
)

# ----------------------
# BibTeX Author Parsing Tests
# ----------------------


def test_count_bibtex_authors_single():
    """Test parsing single author."""
    result = count_bibtex_authors("Duan, Jinhao")
    assert result == 1


def test_count_bibtex_authors_two():
    """Test parsing two authors."""
    result = count_bibtex_authors("Duan, Jinhao and Diffenderfer, James")
    assert result == 2


def test_count_bibtex_authors_six():
    """Test parsing six authors (duan2025 example)."""
    author_field = (
        "Duan, Jinhao and Diffenderfer, James and Chandra, Bhavya and "
        "Cheng, Guenther and Yildirim, Sinan and Hickmann, Sven"
    )
    result = count_bibtex_authors(author_field)
    assert result == 6


def test_count_bibtex_authors_twelve():
    """Test parsing twelve authors (beigi2024 example)."""
    author_field = (
        "Beigi, Alireza and Chakraborty, Ankita and Wang, Ruocheng and Chang, Wei-Li and "
        "Li, Yimin and Sanguansak, Theeranan and Yu, Mingsi and Jiang, Xubin and "
        "Li, Yifan and Iyyer, Arman and Rahman, Muntasir and Liu, Huan"
    )
    result = count_bibtex_authors(author_field)
    assert result == 12


def test_count_bibtex_authors_empty():
    """Test parsing empty author field."""
    result = count_bibtex_authors("")
    assert result == 0


def test_count_bibtex_authors_with_others():
    """Test parsing author field with 'others' (truncated list)."""
    result = count_bibtex_authors("Agrawal and others")
    assert result == -1  # Negative indicates truncation


def test_count_bibtex_authors_with_et_al():
    """Test parsing author field with 'et al' (truncated list)."""
    result = count_bibtex_authors("Smith, John et al")
    assert result == -1  # Negative indicates truncation


# ----------------------
# Author Validation Tests
# ----------------------


def test_validate_author_completeness_six_authors_no_issues():
    """Test that 6 complete authors are NOT flagged (duan2025 case)."""
    entry = {
        "author": (
            "Duan, Jinhao and Diffenderfer, James and Chandra, Bhavya and "
            "Cheng, Guenther and Yildirim, Sinan and Hickmann, Sven"
        ),
        "title": "Sample Paper",
    }

    issues = validate_author_completeness(entry)

    # Should have NO issues
    assert len(issues) == 0, f"Unexpected issues: {issues}"


def test_validate_author_completeness_twelve_authors_no_issues():
    """Test that 12 complete authors are NOT flagged (beigi2024 case)."""
    entry = {
        "author": (
            "Beigi, Alireza and Chakraborty, Ankita and Wang, Ruocheng and Chang, Wei-Li and "
            "Li, Yimin and Sanguansak, Theeranan and Yu, Mingsi and Jiang, Xubin and "
            "Li, Yifan and Iyyer, Arman and Rahman, Muntasir and Liu, Huan"
        ),
        "title": "Sample Paper",
    }

    issues = validate_author_completeness(entry)

    # Should have NO issues
    assert len(issues) == 0, f"Unexpected issues: {issues}"


def test_validate_author_completeness_single_author_with_others():
    """Test that 'others' in single author entry is flagged."""
    entry = {
        "author": "Agrawal and others",
        "title": "Sample Paper",
    }

    # Without DOI metadata, should flag as potentially incomplete
    issues = validate_author_completeness(entry)

    assert len(issues) > 0
    assert any(
        "et al" in issue.lower() or "others" in issue.lower()
        for issue in issues
    )


def test_validate_author_completeness_et_al_large_paper():
    """Test that 'et al' is ACCEPTABLE for papers with 15+ authors."""
    entry = {
        "author": "Smith, John and Jones, Jane et al",
        "title": "Large Collaboration Paper",
    }

    # Mock DOI metadata with 20 expected authors
    doi_metadata = {
        "author": [
            {"family": f"Author{i}", "given": f"First{i}"} for i in range(20)
        ]
    }

    issues = validate_author_completeness(entry, doi_metadata)

    # Should have NO issues (15+ authors means "et al" is acceptable)
    assert len(issues) == 0


def test_validate_author_completeness_et_al_small_paper():
    """Test that 'et al' is FLAGGED for papers with <15 authors."""
    entry = {
        "author": "Smith, John et al",
        "title": "Small Paper",
    }

    # Mock DOI metadata with 5 expected authors
    doi_metadata = {
        "author": [
            {"family": "Smith", "given": "John"},
            {"family": "Jones", "given": "Jane"},
            {"family": "Williams", "given": "Bob"},
            {"family": "Brown", "given": "Alice"},
            {"family": "Davis", "given": "Charlie"},
        ]
    }

    issues = validate_author_completeness(entry, doi_metadata)

    # Should flag as incomplete (expected 5, has "et al")
    assert len(issues) > 0
    assert any("incomplete" in issue.lower() for issue in issues)


def test_validate_author_completeness_no_authors():
    """Test that completely empty author field is flagged."""
    entry = {
        "author": "",
        "title": "Sample Paper",
    }

    issues = validate_author_completeness(entry)

    assert len(issues) > 0
    assert any(
        "no_authors" in issue.lower() or "empty" in issue.lower()
        for issue in issues
    )


def test_validate_author_completeness_matches_doi_metadata():
    """Test that author count is validated against DOI metadata when available."""
    entry = {
        "author": "Smith, John and Jones, Jane",  # 2 authors
        "title": "Sample Paper",
    }

    # DOI metadata says there should be 3 authors
    doi_metadata = {
        "author": [
            {"family": "Smith", "given": "John"},
            {"family": "Jones", "given": "Jane"},
            {"family": "Williams", "given": "Bob"},
        ]
    }

    issues = validate_author_completeness(entry, doi_metadata)

    # Should flag as incomplete (has 2, expected 3)
    assert len(issues) > 0
    assert "2" in issues[0] and "3" in issues[0]


def test_validate_author_completeness_no_doi_metadata():
    """Test validation without DOI metadata (less strict)."""
    entry = {
        "author": "Smith, John and Jones, Jane and Williams, Bob",  # 3 authors
        "title": "Sample Paper",
    }

    # No DOI metadata provided
    issues = validate_author_completeness(entry, doi_metadata=None)

    # With 3+ authors and no DOI metadata, should not flag
    # (we can't verify completeness without reference)
    assert len(issues) == 0


# ----------------------
# Edge Cases
# ----------------------


def test_count_bibtex_authors_with_extra_whitespace():
    """Test parsing with extra whitespace."""
    author_field = "Duan, Jinhao  and  Diffenderfer, James"  # Extra spaces
    result = count_bibtex_authors(author_field)
    assert result == 2


def test_count_bibtex_authors_with_special_characters():
    """Test parsing with special characters in names."""
    author_field = "Müller, Hans and O'Brien, Patrick and López, María"
    result = count_bibtex_authors(author_field)
    assert result == 3


def test_validate_author_completeness_exactly_six_authors():
    """Test edge case: exactly 6 authors (threshold for accepting as complete)."""
    entry = {
        "author": " and ".join([f"Author{i}, First{i}" for i in range(6)]),
        "title": "Sample Paper",
    }

    issues = validate_author_completeness(entry)

    # 6 authors should be accepted as complete
    assert len(issues) == 0


def test_validate_author_completeness_five_authors():
    """Test edge case: 5 authors (below threshold, might need DOI check)."""
    entry = {
        "author": " and ".join([f"Author{i}, First{i}" for i in range(5)]),
        "title": "Sample Paper",
    }

    # Without DOI metadata, 5 authors should still be OK
    issues = validate_author_completeness(entry, doi_metadata=None)

    # Should not flag without DOI metadata to compare against
    assert len(issues) == 0


# ----------------------
# Real-World Examples
# ----------------------


def test_duan2025_not_flagged():
    """Regression test: duan2025 should NOT be flagged (was false positive)."""
    # Real entry from mcp-draft-refined-v4.md
    entry = {
        "author": (
            "Duan, Jinhao and Diffenderfer, James and Chandra, Bhavya and "
            "Cheng, Guenther and Yildirim, Sinan and Hickmann, Sven"
        ),
        "title": "uProp: A Memory-Efficient Method for Fine-tuning",
    }

    issues = validate_author_completeness(entry)

    assert len(issues) == 0, (
        f"duan2025 was incorrectly flagged as incomplete (false positive). "
        f"Has 6 complete authors but got issues: {issues}"
    )


def test_beigi2024_not_flagged():
    """Regression test: beigi2024 should NOT be flagged (was false positive)."""
    # Real entry from mcp-draft-refined-v4.md
    entry = {
        "author": (
            "Beigi, Alireza and Chakraborty, Ankita and Wang, Ruocheng and Chang, Wei-Li and "
            "Li, Yimin and Sanguansak, Theeranan and Yu, Mingsi and Jiang, Xubin and "
            "Li, Yifan and Iyyer, Arman and Rahman, Muntasir and Liu, Huan"
        ),
        "title": "Rethinking the Evaluation of Dialogue Systems",
    }

    issues = validate_author_completeness(entry)

    assert len(issues) == 0, (
        f"beigi2024 was incorrectly flagged as incomplete (false positive). "
        f"Has 12 complete authors but got issues: {issues}"
    )
