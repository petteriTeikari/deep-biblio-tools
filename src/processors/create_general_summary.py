#!/usr/bin/env python3
"""
Create a comprehensive 25% summary of academic papers from markdown files.
"""

import re  # Banned - legacy code for simple pattern matching
import sys
import traceback
from pathlib import Path


def create_25_percent_summary(markdown_path, target_percentage=0.25):
    """Create a 25% summary from markdown content."""

    with open(markdown_path, encoding="utf-8") as f:
        content = f.read()

    # Calculate target length
    original_length = len(content)
    target_length = int(original_length * target_percentage)

    # Parse sections from markdown
    sections = []
    current_section = {"title": "", "content": []}

    lines = content.split("\n")
    for line in lines:
        if line.startswith("# "):  # Main title
            if current_section["content"]:
                sections.append(current_section)
            current_section = {
                "title": line[2:].strip(),
                "content": [],
                "level": 1,
            }
        elif line.startswith("## "):  # Section header
            if current_section["content"]:
                sections.append(current_section)
            current_section = {
                "title": line[3:].strip(),
                "content": [],
                "level": 2,
            }
        elif line.startswith("### "):  # Subsection header
            if current_section["content"]:
                sections.append(current_section)
            current_section = {
                "title": line[4:].strip(),
                "content": [],
                "level": 3,
            }
        else:
            if line.strip():  # Non-empty line
                current_section["content"].append(line)

    if current_section["content"]:
        sections.append(current_section)

    # Extract key information
    title = ""
    authors = ""
    abstract = ""
    references = []

    for section in sections:
        if section["level"] == 1:
            title = section["title"]
        elif "author" in section["title"].lower():
            authors = "\n".join(section["content"])
        elif "abstract" in section["title"].lower():
            abstract = "\n".join(section["content"])
        elif "reference" in section["title"].lower():
            references = section["content"]

    # Build summary
    summary_parts = []

    # Title and metadata
    if title:
        summary_parts.append(f"# {title}\n")

    if authors:
        summary_parts.append(f"## Authors\n{authors}\n")

    # Abstract (keep full abstract as it's usually already concise)
    if abstract:
        summary_parts.append(f"## Abstract\n{abstract}\n")

    # Key sections - summarize each to roughly 25% of original
    important_sections = [
        "Introduction",
        "Methodology",
        "Methods",
        "Results",
        "Discussion",
        "Conclusion",
        "Conclusions",
    ]

    for section in sections:
        if any(imp in section["title"] for imp in important_sections):
            content = "\n".join(section["content"])
            if content:
                # Simple summarization: take first few sentences and key points
                sentences = re.split(r"[.!?]\s+", content)

                # Calculate how many sentences to keep
                num_sentences = max(
                    2, len(sentences) // 4
                )  # Keep ~25% of sentences

                # Prioritize sentences with key terms
                key_terms = [
                    "propose",
                    "develop",
                    "demonstrate",
                    "show",
                    "result",
                    "conclude",
                    "find",
                    "significant",
                    "novel",
                    "approach",
                    "method",
                    "contribution",
                    "important",
                    "key",
                ]

                scored_sentences = []
                for sent in sentences:
                    score = sum(1 for term in key_terms if term in sent.lower())
                    scored_sentences.append((score, sent))

                # Sort by score and take top sentences
                scored_sentences.sort(key=lambda x: x[0], reverse=True)
                selected = [
                    sent for _, sent in scored_sentences[:num_sentences]
                ]

                # Add section to summary
                level_marker = "#" * section["level"]
                summary_parts.append(f"\n{level_marker} {section['title']}\n")
                summary_parts.append(". ".join(selected) + ".\n")

    # Add key references (first 10)
    if references:
        summary_parts.append("\n## Key References\n")
        for ref in references[:10]:
            if ref.strip():
                summary_parts.append(f"- {ref}\n")

    # Combine all parts
    summary = "\n".join(summary_parts)

    # Ensure we're close to target length
    if len(summary) > target_length:
        # Trim to target length at sentence boundary
        sentences = re.split(r"[.!?]\s+", summary)
        trimmed = []
        current_length = 0
        for sent in sentences:
            if current_length + len(sent) < target_length:
                trimmed.append(sent)
                current_length += len(sent)
            else:
                break
        summary = ". ".join(trimmed) + "."

    # Add summary statistics
    summary += f"\n\n---\n*Summary: {len(summary)} characters (~{len(summary) // 5} words)"
    summary += f" - approximately {(len(summary) / original_length) * 100:.1f}% of original*"

    return summary


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python create_general_summary.py <input_markdown> <output_summary>"
        )
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    try:
        summary = create_25_percent_summary(input_path)

        # Save summary
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary)

        print(f"Summary created at: {output_path}")

    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
