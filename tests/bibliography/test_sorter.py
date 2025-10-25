"""Tests for bibliography sorter module."""

from src.bibliography import Bibliography, BibliographyEntry, BibliographySorter


class TestBibliographySorter:
    """Test BibliographySorter class."""

    def test_sort_empty_bibliography(self):
        """Test sorting empty bibliography."""
        bib = Bibliography()
        sorter = BibliographySorter()

        sorted_bib = sorter.process(bib)
        assert len(sorted_bib) == 0

    def test_sort_by_author_default(self):
        """Test default sorting by author name."""
        bib = Bibliography()

        # Add entries in reverse alphabetical order
        entries = [
            BibliographyEntry(
                "article", "zhang2023", {"author": "Zhang, Wei", "year": "2023"}
            ),
            BibliographyEntry(
                "article",
                "smith2023",
                {"author": "Smith, John", "year": "2023"},
            ),
            BibliographyEntry(
                "article",
                "adams2023",
                {"author": "Adams, Alice", "year": "2023"},
            ),
        ]

        for entry in entries:
            bib.add_entry(entry)

        sorter = BibliographySorter()
        sorted_bib = sorter.process(bib)

        # Check entries are in alphabetical order by author
        sorted_entries = list(sorted_bib)
        assert sorted_entries[0].get_field("author") == "Adams, Alice"
        assert sorted_entries[1].get_field("author") == "Smith, John"
        assert sorted_entries[2].get_field("author") == "Zhang, Wei"

    def test_sort_by_year(self):
        """Test sorting by year."""
        bib = Bibliography()

        entries = [
            BibliographyEntry(
                "article", "new", {"author": "New, Author", "year": "2023"}
            ),
            BibliographyEntry(
                "article", "old", {"author": "Old, Author", "year": "2020"}
            ),
            BibliographyEntry(
                "article",
                "middle",
                {"author": "Middle, Author", "year": "2021"},
            ),
        ]

        for entry in entries:
            bib.add_entry(entry)

        sorter = BibliographySorter(sort_by="year")
        sorted_bib = sorter.process(bib)

        sorted_entries = list(sorted_bib)
        assert sorted_entries[0].get_field("year") == "2020"
        assert sorted_entries[1].get_field("year") == "2021"
        assert sorted_entries[2].get_field("year") == "2023"

    def test_sort_by_year_descending(self):
        """Test sorting by year in descending order."""
        bib = Bibliography()

        entries = [
            BibliographyEntry(
                "article", "old", {"author": "Old, Author", "year": "2020"}
            ),
            BibliographyEntry(
                "article", "new", {"author": "New, Author", "year": "2023"}
            ),
            BibliographyEntry(
                "article",
                "middle",
                {"author": "Middle, Author", "year": "2021"},
            ),
        ]

        for entry in entries:
            bib.add_entry(entry)

        sorter = BibliographySorter(sort_by="year", reverse=True)
        sorted_bib = sorter.process(bib)

        sorted_entries = list(sorted_bib)
        assert sorted_entries[0].get_field("year") == "2023"
        assert sorted_entries[1].get_field("year") == "2021"
        assert sorted_entries[2].get_field("year") == "2020"

    def test_sort_by_title(self):
        """Test sorting by title."""
        bib = Bibliography()

        entries = [
            BibliographyEntry(
                "article", "c", {"title": "Zebra Stripes", "author": "A"}
            ),
            BibliographyEntry(
                "article", "a", {"title": "Aardvark Behavior", "author": "B"}
            ),
            BibliographyEntry(
                "article", "b", {"title": "Machine Learning", "author": "C"}
            ),
        ]

        for entry in entries:
            bib.add_entry(entry)

        sorter = BibliographySorter(sort_by="title")
        sorted_bib = sorter.process(bib)

        sorted_entries = list(sorted_bib)
        assert sorted_entries[0].get_field("title") == "Aardvark Behavior"
        assert sorted_entries[1].get_field("title") == "Machine Learning"
        assert sorted_entries[2].get_field("title") == "Zebra Stripes"

    def test_sort_by_key(self):
        """Test sorting by citation key."""
        bib = Bibliography()

        entries = [
            BibliographyEntry("article", "zeta2023", {"author": "Author A"}),
            BibliographyEntry("article", "alpha2023", {"author": "Author B"}),
            BibliographyEntry("article", "beta2023", {"author": "Author C"}),
        ]

        for entry in entries:
            bib.add_entry(entry)

        sorter = BibliographySorter(sort_by="key")
        sorted_bib = sorter.process(bib)

        sorted_entries = list(sorted_bib)
        assert sorted_entries[0].key == "alpha2023"
        assert sorted_entries[1].key == "beta2023"
        assert sorted_entries[2].key == "zeta2023"

    def test_sort_with_missing_fields(self):
        """Test sorting when some entries are missing sort field."""
        bib = Bibliography()

        # Mix of entries with and without year
        entries = [
            BibliographyEntry(
                "article", "has_year", {"author": "A", "year": "2023"}
            ),
            BibliographyEntry(
                "article", "no_year", {"author": "B"}
            ),  # Missing year
            BibliographyEntry(
                "article", "old_year", {"author": "C", "year": "2020"}
            ),
        ]

        for entry in entries:
            bib.add_entry(entry)

        sorter = BibliographySorter(sort_by="year")
        sorted_bib = sorter.process(bib)

        sorted_entries = list(sorted_bib)
        # Entries without year should come last
        assert sorted_entries[0].key == "old_year"
        assert sorted_entries[1].key == "has_year"
        assert sorted_entries[2].key == "no_year"

    def test_sort_by_author_lastname(self):
        """Test sorting handles author last names correctly."""
        bib = Bibliography()

        entries = [
            BibliographyEntry(
                "article", "1", {"author": "van Beethoven, Ludwig"}
            ),
            BibliographyEntry("article", "2", {"author": "de Gaulle, Charles"}),
            BibliographyEntry("article", "3", {"author": "O'Brien, Patrick"}),
            BibliographyEntry("article", "4", {"author": "MacDonald, Ronald"}),
        ]

        for entry in entries:
            bib.add_entry(entry)

        sorter = BibliographySorter(sort_by="author")
        sorted_bib = sorter.process(bib)

        sorted_entries = list(sorted_bib)
        # Should handle prefixes correctly
        authors = [e.get_field("author") for e in sorted_entries]
        assert authors[0] == "de Gaulle, Charles"
        assert authors[1] == "MacDonald, Ronald"
        assert authors[2] == "O'Brien, Patrick"
        assert authors[3] == "van Beethoven, Ludwig"

    def test_sort_multiple_authors(self):
        """Test sorting with multiple authors."""
        bib = Bibliography()

        entries = [
            BibliographyEntry(
                "article", "1", {"author": "Smith, John and Doe, Jane"}
            ),
            BibliographyEntry(
                "article", "2", {"author": "Adams, Alice and Brown, Bob"}
            ),
            BibliographyEntry(
                "article", "3", {"author": "Smith, John and Adams, Alice"}
            ),
        ]

        for entry in entries:
            bib.add_entry(entry)

        sorter = BibliographySorter(sort_by="author")
        sorted_bib = sorter.process(bib)

        sorted_entries = list(sorted_bib)
        # Should sort by first author
        assert "Adams, Alice" in sorted_entries[0].get_field("author")
        assert sorted_entries[1].get_field("author").startswith("Smith, John")
        assert sorted_entries[2].get_field("author").startswith("Smith, John")

    def test_stable_sort(self):
        """Test that sorting is stable for equal values."""
        bib = Bibliography()

        # Entries with same year but different keys
        entries = [
            BibliographyEntry(
                "article", "first2023", {"author": "A", "year": "2023"}
            ),
            BibliographyEntry(
                "article", "second2023", {"author": "B", "year": "2023"}
            ),
            BibliographyEntry(
                "article", "third2023", {"author": "C", "year": "2023"}
            ),
        ]

        for entry in entries:
            bib.add_entry(entry)

        sorter = BibliographySorter(sort_by="year")
        sorted_bib = sorter.process(bib)

        sorted_entries = list(sorted_bib)
        # Order should be preserved for equal years
        assert sorted_entries[0].key == "first2023"
        assert sorted_entries[1].key == "second2023"
        assert sorted_entries[2].key == "third2023"

    def test_sort_entry_types(self):
        """Test sorting different entry types."""
        bib = Bibliography()

        entries = [
            BibliographyEntry(
                "inproceedings", "conf", {"author": "A", "year": "2023"}
            ),
            BibliographyEntry(
                "article", "art", {"author": "B", "year": "2023"}
            ),
            BibliographyEntry("book", "book", {"author": "C", "year": "2023"}),
        ]

        for entry in entries:
            bib.add_entry(entry)

        sorter = BibliographySorter(sort_by="type")
        sorted_bib = sorter.process(bib)

        sorted_entries = list(sorted_bib)
        # Should sort by entry type alphabetically
        assert sorted_entries[0].entry_type == "article"
        assert sorted_entries[1].entry_type == "book"
        assert sorted_entries[2].entry_type == "inproceedings"
