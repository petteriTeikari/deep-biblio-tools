#!/usr/bin/env python3
"""
Create a comprehensive 25% summary of academic papers with proper citations.
Maintains author-year citations and includes complete reference list.
"""

import os
import sys
from pathlib import Path


def extract_citations_and_references(content):
    """Extract citations and their corresponding references, preserving hyperlinks."""
    citations = {}
    references = []

    # Look for reference section
    lines = content.split("\n")
    in_references = False
    current_ref = []

    for i, line in enumerate(lines):
        # Check for reference section start
        if line.strip().lower() in [
            "references",
            "bibliography",
            "## references",
            "### references",
        ]:
            in_references = True
            continue

        if in_references:
            # Each reference typically starts with a number or bullet
            if line.strip() and (
                line.strip()[0].isdigit()
                or line.strip().startswith("-")
                or line.strip().startswith("•")
                or line.strip().startswith("[")
            ):
                if current_ref:
                    references.append(" ".join(current_ref))
                current_ref = [line.strip()]
            elif line.strip() and current_ref:
                current_ref.append(line.strip())
        else:
            # Look for inline citations with hyperlinks [Author et al., Year](url)
            if "[" in line and "](" in line:
                start = 0
                while True:
                    bracket_start = line.find("[", start)
                    if bracket_start == -1:
                        break
                    bracket_end = line.find("]", bracket_start)
                    if bracket_end == -1:
                        break
                    paren_start = line.find("(", bracket_end)
                    if paren_start != bracket_end + 1:
                        start = bracket_end + 1
                        continue
                    paren_end = line.find(")", paren_start)
                    if paren_end == -1:
                        break

                    text = line[bracket_start + 1 : bracket_end]
                    url = line[paren_start + 1 : paren_end]

                    # Check if this is a citation (contains year)
                    if any(
                        year in text for year in ["199", "200", "201", "202"]
                    ):
                        citations[text] = url

                    start = paren_end + 1

    if current_ref:
        references.append(" ".join(current_ref))

    return citations, references


def extract_paper_metadata(content):
    """Extract title, authors, journal, year, DOI from the content."""
    metadata = {
        "title": "",
        "authors": [],
        "journal": "",
        "year": "",
        "doi": "",
        "keywords": [],
    }

    lines = content.split("\n")

    # Extract title (usually first heading)
    for line in lines:
        if line.strip().startswith("# ") and not metadata["title"]:
            metadata["title"] = line[2:].strip()
            break

    # Look for author information
    for i, line in enumerate(lines):
        if "Author" in line and "links" in line:
            # Get the next few lines which typically contain author names
            for j in range(i + 1, min(i + 10, len(lines))):
                if lines[j].strip() and not lines[j].startswith("#"):
                    # Simple heuristic: lines with mostly capitalized words are likely author names
                    words = lines[j].split()
                    if (
                        words
                        and sum(1 for w in words if w[0].isupper())
                        > len(words) / 2
                    ):
                        metadata["authors"].extend(
                            [w for w in words if w[0].isupper()]
                        )

        # Extract DOI
        if "doi" in line.lower() or "10." in line:
            doi_start = line.find("10.")
            if doi_start != -1:
                doi_end = line.find(" ", doi_start)
                if doi_end == -1:
                    doi_end = len(line)
                metadata["doi"] = line[doi_start:doi_end].strip()

        # Extract year (4-digit number between 1900-2099)
        for word in line.split():
            if word.isdigit() and 1900 <= int(word) <= 2099:
                metadata["year"] = word
                break

        # Extract keywords
        if "keywords" in line.lower():
            keywords_text = lines[i : i + 5]  # Check next few lines
            for kw_line in keywords_text:
                if "•" in kw_line or ";" in kw_line or "," in kw_line:
                    # Split by common delimiters
                    for delimiter in ["•", ";", ","]:
                        if delimiter in kw_line:
                            keywords = [
                                k.strip()
                                for k in kw_line.split(delimiter)
                                if k.strip()
                            ]
                            metadata["keywords"].extend(keywords)

    return metadata


def create_comprehensive_summary(input_path, output_path):
    """Create a 25% comprehensive summary maintaining citations."""

    # Read input content
    with open(input_path, encoding="utf-8") as f:
        content = f.read()

    original_size = len(content)
    target_size = int(original_size * 0.25)

    # Extract metadata
    metadata = extract_paper_metadata(content)

    # Extract citations and references
    citations, references = extract_citations_and_references(content)

    # Parse content into sections
    sections = []
    current_section = {"title": "", "content": [], "importance": 0}

    lines = content.split("\n")
    for line in lines:
        if line.startswith("#"):
            if current_section["content"]:
                sections.append(current_section)
            # Determine section importance based on keywords
            importance = 0
            lower_line = line.lower()
            if any(
                word in lower_line
                for word in [
                    "abstract",
                    "summary",
                    "conclusion",
                    "results",
                    "findings",
                ]
            ):
                importance = 10
            elif any(
                word in lower_line
                for word in ["introduction", "method", "approach"]
            ):
                importance = 8
            elif any(
                word in lower_line
                for word in ["related", "background", "literature"]
            ):
                importance = 6
            else:
                importance = 5

            current_section = {
                "title": line,
                "content": [],
                "importance": importance,
            }
        else:
            if line.strip():
                current_section["content"].append(line)

    if current_section["content"]:
        sections.append(current_section)

    # Sort sections by importance
    sections.sort(key=lambda x: x["importance"], reverse=True)

    # Build summary
    summary_lines = []

    # Add title and metadata
    summary_lines.append(f"# {metadata['title']} - Comprehensive Summary (25%)")
    summary_lines.append("")

    if metadata["authors"]:
        summary_lines.append(
            f"**Authors:** {', '.join(metadata['authors'][:10])}"
        )
    if metadata["journal"]:
        summary_lines.append(f"**Journal:** {metadata['journal']}")
    if metadata["year"]:
        summary_lines.append(f"**Year:** {metadata['year']}")
    if metadata["doi"]:
        summary_lines.append(f"**DOI:** {metadata['doi']}")
    if metadata["keywords"]:
        summary_lines.append(
            f"**Keywords:** {', '.join(metadata['keywords'][:10])}"
        )

    summary_lines.append("")
    summary_lines.append("---")
    summary_lines.append("")

    # Add sections until we reach target size
    current_size = sum(len(line) for line in summary_lines)

    for section in sections:
        if current_size >= target_size:
            break

        summary_lines.append(section["title"])
        summary_lines.append("")

        # Calculate how much of this section we can include
        remaining_size = target_size - current_size
        section_content = "\n".join(section["content"])

        if len(section_content) <= remaining_size:
            # Include entire section
            summary_lines.extend(section["content"])
        else:
            # Include partial section
            # Prioritize complete sentences
            sentences = []
            current_sentence = []

            for line in section["content"]:
                words = line.split()
                for word in words:
                    current_sentence.append(word)
                    if word.endswith((".", "!", "?")):
                        sentences.append(" ".join(current_sentence))
                        current_sentence = []

                if current_sentence:
                    sentences.append(" ".join(current_sentence))
                    current_sentence = []

            # Add sentences until we reach the limit
            for sentence in sentences:
                if current_size + len(sentence) > target_size:
                    break
                summary_lines.append(sentence)
                current_size += len(sentence)

        summary_lines.append("")
        current_size = sum(len(line) for line in summary_lines)

    # Add references section at the end
    if references:
        summary_lines.append("")
        summary_lines.append("---")
        summary_lines.append("")
        summary_lines.append("## References")
        summary_lines.append("")
        for ref in references[:50]:  # Limit to 50 references
            summary_lines.append(ref)
            summary_lines.append("")

    # Write output
    output_content = "\n".join(summary_lines)

    # Ensure we're close to target size
    actual_size = len(output_content)
    compression_ratio = (actual_size / original_size) * 100

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_content)

    print(f"Created summary: {Path(output_path).name}")
    print(f"  Original size: {original_size:,} chars")
    print(f"  Summary size: {actual_size:,} chars ({compression_ratio:.1f}%)")
    print(f"  Target was: {target_size:,} chars (25.0%)")

    return True


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python create_literature_summary.py <input_file> <output_file>"
        )
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    try:
        create_comprehensive_summary(input_file, output_file)
    except Exception as e:
        print(f"Error creating summary: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
