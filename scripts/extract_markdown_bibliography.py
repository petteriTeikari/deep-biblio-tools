#!/usr/bin/env python3
"""
Extract bibliography from markdown file with inline citations and convert to BibTeX.

This script parses a markdown file to extract all inline citations and converts
them to properly formatted BibTeX entries.
"""

import json

# import re  # Banned - using string methods instead


class MarkdownBibliographyExtractor:
    """Extract and convert inline citations from markdown to BibTeX."""

    def __init__(self):
        # We'll manually parse citations instead of using regex patterns
        pass

        # Common publisher domains to entry type mapping
        self.domain_mapping = {
            "doi.org": "article",
            "arxiv.org": "article",
            "ssrn.com": "article",
            "amazon.com": "book",
            "simonandschuster.com": "book",
            "oup.com": "book",
            "hbs.edu": "book",
            "appraisalinstitute.org": "misc",
            "fanniemae.com": "misc",
            "freddiemac.com": "misc",
            "urban.org": "misc",
            "nar.realtor": "misc",
            "reggora.com": "misc",
            "ibisworld.com": "misc",
        }

    def extract_citations(self, markdown_file: str) -> list[dict]:
        """Extract all citations from markdown file."""
        with open(markdown_file, encoding="utf-8") as f:
            content = f.read()

        citations = []
        seen_keys = set()

        # Manual parsing of citations
        lines = content.split("\n")
        for line in lines:
            # Find all potential citations in format [text](url)
            start = 0
            while True:
                bracket_start = line.find("[", start)
                if bracket_start == -1:
                    break

                bracket_end = line.find("]", bracket_start)
                if bracket_end == -1:
                    start = bracket_start + 1
                    continue

                # Check if followed by (url)
                if bracket_end + 1 < len(line) and line[bracket_end + 1] == "(":
                    paren_end = line.find(")", bracket_end + 2)
                    if paren_end != -1:
                        text_content = line[bracket_start + 1 : bracket_end]
                        url = line[bracket_end + 2 : paren_end]

                        # Check if it's a URL
                        if url.startswith("http://") or url.startswith(
                            "https://"
                        ):
                            # Try to parse as citation
                            entry = None

                            # Check for year in parentheses within text
                            year_start = text_content.rfind("(")
                            if year_start != -1:
                                year_end = text_content.find(")", year_start)
                                if year_end != -1:
                                    potential_year = text_content[
                                        year_start + 1 : year_end
                                    ]
                                    if (
                                        len(potential_year) == 4
                                        and potential_year.isdigit()
                                    ):
                                        author_text = text_content[
                                            :year_start
                                        ].strip()
                                        entry = self._parse_citation(
                                            author_text, potential_year, url
                                        )

                            # Check for year after author name
                            if not entry:
                                words = text_content.split()
                                if len(words) >= 2:
                                    last_word = words[-1]
                                    # Remove trailing letters like 'a', 'b' from year
                                    year_candidate = last_word.rstrip(
                                        "abcdefghijklmnopqrstuvwxyz"
                                    )
                                    if (
                                        len(year_candidate) == 4
                                        and year_candidate.isdigit()
                                    ):
                                        author_text = " ".join(words[:-1])
                                        entry = self._parse_citation(
                                            author_text, last_word, url
                                        )

                            # Otherwise treat as title/URL
                            if not entry:
                                entry = self._parse_url_citation(
                                    text_content, url
                                )

                            if entry and entry["key"] not in seen_keys:
                                citations.append(entry)
                                seen_keys.add(entry["key"])

                        start = paren_end + 1
                    else:
                        start = bracket_end + 1
                else:
                    start = bracket_end + 1

        return citations

    def _parse_citation(self, author_text: str, year: str, url: str) -> dict:
        """Parse individual citation into structured format."""
        # Clean author text
        author_text = author_text.strip()

        # Generate BibTeX key
        key = self._generate_key(author_text, year, url)
        if not key:
            return None

        # Determine entry type from URL
        entry_type = self._determine_entry_type(url)

        # Parse authors
        authors = self._parse_authors(author_text)

        # Extract title from URL if possible
        title = self._extract_title_from_context(author_text, url)

        entry = {
            "key": key,
            "type": entry_type,
            "year": year,
            "authors": authors,
            "title": title,
            "url": url,
            "original_text": f"[{author_text} ({year})]({url})",
        }

        # Add additional fields based on URL
        self._add_url_specific_fields(entry, url)

        return entry

    def _parse_url_citation(self, title_text: str, url: str) -> dict:
        """Parse URL-only citation."""
        # Try to extract year from title or URL
        year = "2024"  # default
        combined = title_text + url

        # Look for 4-digit year
        for i in range(len(combined) - 3):
            if combined[i : i + 4].isdigit():
                potential_year = int(combined[i : i + 4])
                # Reasonable year range
                if 1900 <= potential_year <= 2030:
                    year = combined[i : i + 4]
                    break

        # Generate key from title
        key = self._generate_key_from_title(title_text, year)
        if not key:
            return None

        entry_type = self._determine_entry_type(url)

        return {
            "key": key,
            "type": entry_type,
            "year": year,
            "title": title_text,
            "url": url,
            "original_text": f"[{title_text}]({url})",
        }

    def _generate_key(self, author_text: str, year: str, url: str) -> str:
        """Generate BibTeX key from author and year."""
        # Handle various author formats
        if "et al." in author_text.lower():
            # Extract first author before 'et al.'
            first_author = author_text.split("et al.")[0].strip()
            key_base = self._clean_author_name(first_author)
        elif " and " in author_text:
            # Multiple authors separated by 'and'
            first_author = author_text.split(" and ")[0].strip()
            key_base = self._clean_author_name(first_author)
        elif "," in author_text:
            # Single author in "Last, First" format
            key_base = self._clean_author_name(
                author_text.split(",")[0].strip()
            )
        else:
            # Single name or organization
            key_base = self._clean_author_name(author_text)

        if not key_base:
            return None

        return f"{key_base.lower()}{year}"

    def _generate_key_from_title(self, title: str, year: str) -> str:
        """Generate key from title when author is not available."""
        # Take first significant word from title
        words = []
        current_word = ""
        for char in title.lower():
            if char.isalpha():
                current_word += char
            elif current_word:
                words.append(current_word)
                current_word = ""
        if current_word:
            words.append(current_word)

        key_base = words[0] if words else "misc"
        return f"{key_base}{year}"

    def _clean_author_name(self, name: str) -> str:
        """Clean author name for use in BibTeX key."""
        # Remove common prefixes and clean
        prefixes = [
            "Dr.",
            "Dr",
            "Prof.",
            "Prof",
            "Mr.",
            "Mr",
            "Ms.",
            "Ms",
            "Mrs.",
            "Mrs",
        ]
        for prefix in prefixes:
            if name.startswith(prefix + " "):
                name = name[len(prefix) + 1 :]
                break

        # Extract last name (assume last word is surname)
        words = name.strip().split()
        if words:
            # Remove non-alphabetic characters
            last_word = words[-1]
            cleaned = ""
            for char in last_word:
                if char.isalpha():
                    cleaned += char
            return cleaned
        return ""

    def _parse_authors(self, author_text: str) -> str:
        """Parse author text into BibTeX format."""
        if "et al." in author_text.lower():
            # Extract first author and add "and others"
            first_author = author_text.split("et al.")[0].strip()
            return f"{first_author} and others"
        elif " and " in author_text:
            # Multiple authors - keep as is
            return author_text
        else:
            # Single author
            return author_text

    def _determine_entry_type(self, url: str) -> str:
        """Determine BibTeX entry type from URL."""
        url_lower = url.lower()

        for domain, entry_type in self.domain_mapping.items():
            if domain in url_lower:
                return entry_type

        # Default based on URL patterns
        if "arxiv.org" in url_lower:
            return "article"
        elif any(term in url_lower for term in ["book", "isbn"]):
            return "book"
        elif any(term in url_lower for term in ["conference", "proceedings"]):
            return "inproceedings"
        else:
            return "misc"

    def _extract_title_from_context(self, author_text: str, url: str) -> str:
        """Extract or infer title from context."""
        # This is a placeholder - in practice, you'd need more sophisticated
        # title extraction from the surrounding markdown context
        return f"Work by {author_text}"

    def _add_url_specific_fields(self, entry: dict, url: str):
        """Add URL-specific fields to entry."""
        if "doi.org" in url:
            entry["doi"] = url.replace("https://doi.org/", "")
        elif "arxiv.org" in url:
            # Extract arXiv ID
            if "/abs/" in url:
                start_idx = url.find("/abs/") + 5
                remaining = url[start_idx:]
                arxiv_id = ""
                for char in remaining:
                    if char.isdigit() or char == ".":
                        arxiv_id += char
                    else:
                        break
                if arxiv_id and "." in arxiv_id:
                    entry["eprint"] = arxiv_id
                    entry["archivePrefix"] = "arXiv"

        # Add URL field for all entries
        if "url" not in entry:
            entry["url"] = url

    def citations_to_bibtex(self, citations: list[dict]) -> str:
        """Convert citations to BibTeX format."""
        bibtex_entries = []

        for citation in citations:
            entry_lines = [f"@{citation['type']}{{{citation['key']},"]

            # Add title
            if "title" in citation and citation["title"]:
                entry_lines.append(f"  title={{{citation['title']}}},")

            # Add authors
            if "authors" in citation and citation["authors"]:
                entry_lines.append(f"  author={{{citation['authors']}}},")

            # Add year
            if "year" in citation:
                entry_lines.append(f"  year={{{citation['year']}}},")

            # Add DOI if present
            if "doi" in citation:
                entry_lines.append(f"  doi={{{citation['doi']}}},")

            # Add arXiv fields if present
            if "eprint" in citation:
                entry_lines.append(f"  eprint={{{citation['eprint']}}},")
                entry_lines.append(
                    f"  archivePrefix={{{citation['archivePrefix']}}},"
                )

            # Add URL
            if "url" in citation:
                entry_lines.append(f"  url={{{citation['url']}}},")

            # Add note with original text
            entry_lines.append(
                f"  note={{Extracted from: {citation['original_text']}}}"
            )

            entry_lines.append("}")
            bibtex_entries.append("\n".join(entry_lines))

        return "\n\n".join(bibtex_entries)

    def create_citation_mapping(self, citations: list[dict]) -> dict[str, str]:
        """Create mapping from markdown citations to BibTeX keys."""
        mapping = {}
        for citation in citations:
            mapping[citation["original_text"]] = citation["key"]
        return mapping


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract bibliography from markdown"
    )
    parser.add_argument("markdown_file", help="Input markdown file")
    parser.add_argument("--output", "-o", help="Output BibTeX file")
    parser.add_argument("--mapping", help="Output citation mapping JSON")

    args = parser.parse_args()

    extractor = MarkdownBibliographyExtractor()
    citations = extractor.extract_citations(args.markdown_file)

    print(f"Extracted {len(citations)} citations")

    # Generate BibTeX
    bibtex = extractor.citations_to_bibtex(citations)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(bibtex)
        print(f"BibTeX saved to {args.output}")
    else:
        print("\nBibTeX output:")
        print(bibtex[:1000] + "..." if len(bibtex) > 1000 else bibtex)

    # Generate mapping
    if args.mapping:
        mapping = extractor.create_citation_mapping(citations)
        with open(args.mapping, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
        print(f"Citation mapping saved to {args.mapping}")


if __name__ == "__main__":
    main()
