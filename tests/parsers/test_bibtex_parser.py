"""Tests for BibTeX parser."""

from src.parsers import BibtexParser


class TestBibtexParser:
    """Test BibTeX parser functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = BibtexParser()

    def test_parse_simple_entry(self):
        """Test parsing simple BibTeX entry."""
        text = """
        @article{Smith2020,
            author = {John Smith},
            title = {A Great Paper},
            journal = {Nature},
            year = {2020}
        }
        """

        doc = self.parser.parse(text)

        assert doc.raw_text == text
        assert len(doc.nodes) == 1
        assert doc.nodes[0].type == "entry"
        assert doc.nodes[0].content == "Smith2020"
        assert doc.metadata["num_entries"] == 1

    def test_extract_entries(self):
        """Test extracting multiple entries."""
        text = """
        @article{Smith2020,
            author = {John Smith},
            title = {Paper One},
            journal = {Nature},
            year = {2020}
        }

        @book{Jones2019,
            author = {Jane Jones},
            title = {A Good Book},
            publisher = {Academic Press},
            year = {2019}
        }
        """

        entries = self.parser.extract_entries(text)

        assert len(entries) == 2
        assert entries[0]["id"] == "Smith2020"
        assert entries[0]["type"] == "article"
        assert entries[1]["id"] == "Jones2019"
        assert entries[1]["type"] == "book"

    def test_get_entry_by_id(self):
        """Test getting specific entry by ID."""
        text = """
        @article{Smith2020,
            author = {John Smith},
            title = {A Great Paper},
            journal = {Nature},
            year = {2020},
            pages = {1--10}
        }
        """

        entry = self.parser.get_entry_by_id(text, "Smith2020")

        assert entry is not None
        assert entry["id"] == "Smith2020"
        assert entry["fields"]["author"] == "John Smith"
        assert entry["fields"]["pages"] == "1--10"

    def test_extract_field(self):
        """Test extracting specific field."""
        text = """
        @article{Smith2020,
            author = {John Smith and Jane Doe},
            title = {A Collaborative Work},
            year = {2020}
        }
        """

        author = self.parser.extract_field(text, "Smith2020", "author")
        title = self.parser.extract_field(text, "Smith2020", "title")

        assert author == "John Smith and Jane Doe"
        assert title == "A Collaborative Work"

    def test_update_field(self):
        """Test updating field value."""
        text = """
        @article{Smith2020,
            author = {John Smith},
            title = {Original Title},
            year = {2020}
        }
        """

        updated_text = self.parser.update_field(
            text, "Smith2020", "title", "Updated Title"
        )

        # Parse updated text to verify
        updated_entry = self.parser.get_entry_by_id(updated_text, "Smith2020")
        assert updated_entry["fields"]["title"] == "Updated Title"

    def test_validate_valid_bibtex(self):
        """Test validation of valid BibTeX."""
        text = """
        @article{Valid2020,
            author = {A. Author},
            title = {Valid Entry},
            journal = {Journal},
            year = {2020}
        }
        """

        errors = self.parser.validate(text)
        assert len(errors) == 0

    def test_validate_missing_required_fields(self):
        """Test validation with missing required fields."""
        text = """
        @article{Invalid2020,
            author = {A. Author},
            title = {Missing Journal}
        }
        """

        errors = self.parser.validate(text)
        assert len(errors) > 0
        assert any("journal" in error.lower() for error in errors)
        assert any("year" in error.lower() for error in errors)

    def test_validate_empty_id(self):
        """Test validation with empty ID."""
        text = """
        @article{,
            author = {A. Author},
            title = {No ID},
            year = {2020}
        }
        """

        errors = self.parser.validate(text)
        assert len(errors) > 0
        assert any("empty id" in error.lower() for error in errors)

    def test_parse_different_entry_types(self):
        """Test parsing different entry types."""
        text = """
        @article{Art2020,
            author = {Author},
            title = {Article},
            journal = {Journal},
            year = {2020}
        }

        @inproceedings{Conf2021,
            author = {Speaker},
            title = {Conference Paper},
            booktitle = {Proceedings},
            year = {2021}
        }

        @book{Book2019,
            author = {Writer},
            title = {Book Title},
            publisher = {Publisher},
            year = {2019}
        }
        """

        doc = self.parser.parse(text)

        assert doc.metadata["num_entries"] == 3
        assert set(doc.metadata["entry_types"]) == {
            "article",
            "inproceedings",
            "book",
        }

    def test_parse_with_special_characters(self):
        """Test parsing entries with special characters."""
        text = r"""
        @article{Special2020,
            author = {M\"uller, Hans},
            title = {Special \& Characters},
            journal = {Journal of \LaTeX},
            year = {2020}
        }
        """

        entry = self.parser.get_entry_by_id(text, "Special2020")

        assert entry is not None
        # bibtexparser converts LaTeX special chars to Unicode, which is good
        assert "Müller" in entry["fields"]["author"]
        assert "&" in entry["fields"]["title"]
