"""Reference management utilities."""

import re


class ReferenceManager:
    """Manage and deduplicate references."""

    def deduplicate_references(self, references: list[str]) -> list[str]:
        """Deduplicate references based on author and year."""
        unique_refs = {}

        for ref in references:
            # Extract key components for deduplication
            key = self._extract_reference_key(ref)

            if key:
                if key not in unique_refs:
                    unique_refs[key] = ref
                else:
                    # Keep the more complete reference
                    if len(ref) > len(unique_refs[key]):
                        unique_refs[key] = ref
            else:
                # If we can't extract a key, include it to be safe
                unique_refs[ref[:50]] = ref

        # Sort by author and year
        sorted_refs = sorted(unique_refs.values(), key=self._reference_sort_key)

        return sorted_refs

    def _extract_reference_key(self, reference: str) -> str:
        """Extract a key from reference for deduplication."""
        # Remove leading numbers and bullets
        ref_clean = re.sub(r"^[\d\.\-\•\[\]]+\s*", "", reference)

        # Try to extract author and year
        # Pattern: Author, A. B. (YYYY) or Author et al. (YYYY)
        author_year_match = re.search(
            r"^([A-Za-z\s,\.]+?)[\s,]*\((\d{4})\)", ref_clean
        )

        if author_year_match:
            author = author_year_match.group(1).strip()
            year = author_year_match.group(2)

            # Normalize author (take first author's last name)
            author_parts = author.split(",")
            if author_parts:
                first_author = author_parts[0].strip()
                # Remove initials
                first_author = re.sub(r"\s+[A-Z]\.\s*", "", first_author)
                return f"{first_author.lower()}_{year}"

        # Alternative pattern: Author (YYYY)
        alt_match = re.search(r"^([A-Za-z]+).*?(\d{4})", ref_clean)
        if alt_match:
            author = alt_match.group(1)
            year = alt_match.group(2)
            return f"{author.lower()}_{year}"

        return None

    def _reference_sort_key(self, reference: str) -> tuple:
        """Generate sort key for reference."""
        # Extract author and year for sorting
        key = self._extract_reference_key(reference)

        if key:
            parts = key.split("_")
            if len(parts) == 2:
                return (parts[0], parts[1])

        # Fallback to beginning of reference
        return (reference[:20].lower(), "9999")

    def format_reference_list(self, references: list[str]) -> list[str]:
        """Format reference list with consistent numbering."""
        formatted = []

        for i, ref in enumerate(references, 1):
            # Remove any existing numbering
            ref_clean = re.sub(r"^[\d\.\-\•\[\]]+\s*", "", ref.strip())

            # Add consistent numbering
            formatted.append(f"{i}. {ref_clean}")

        return formatted

    def extract_citation_keys(self, text: str) -> set[str]:
        """Extract all citation keys from text."""
        keys = set()

        # Pattern for (Author, Year) or (Author et al., Year)
        pattern1 = r"\(([A-Za-z]+(?:\s+et\s+al\.)?),?\s*(\d{4})\)"
        matches = re.findall(pattern1, text)
        for author, year in matches:
            author_clean = author.replace(" et al.", "").strip()
            keys.add(f"{author_clean}_{year}")

        # Pattern for Author (Year)
        pattern2 = r"([A-Za-z]+(?:\s+et\s+al\.)?)\s+\((\d{4})\)"
        matches = re.findall(pattern2, text)
        for author, year in matches:
            author_clean = author.replace(" et al.", "").strip()
            keys.add(f"{author_clean}_{year}")

        return keys
