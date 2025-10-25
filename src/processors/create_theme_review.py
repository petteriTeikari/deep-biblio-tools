#!/usr/bin/env python3
"""
Create a comprehensive literature review from multiple paper summaries.
Combines all references and creates a cohesive narrative with proper citations.
"""

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path


def extract_citations_from_summary(summary_content):
    """Extract all citations and references from a summary, preserving hyperlinks."""
    citations = {}  # Dict to store citation text -> hyperlink mapping
    references = []

    lines = summary_content.split("\n")
    in_references = False

    for line in lines:
        # Check for reference section
        if line.strip().lower() in [
            "references",
            "## references",
            "### references",
            "bibliography",
        ]:
            in_references = True
            continue

        if in_references and line.strip():
            references.append(line.strip())

        # Look for hyperlinked citations in markdown format: [Author et al., Year](url)
        # Parse markdown links without regex
        if "[" in line and "](" in line and ")" in line:
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
                if any(year in text for year in ["199", "200", "201", "202"]):
                    citations[text] = url

                start = paren_end + 1

    return citations, references


def create_literature_review(
    summaries_dir, output_file, theme_context, contextualization
):
    """Create a comprehensive literature review from all summaries."""

    summaries_path = Path(summaries_dir)
    summary_files = list(summaries_path.glob("*_comprehensive_summary.md"))

    if not summary_files:
        print(f"No summary files found in {summaries_dir}")
        return False

    print(f"Found {len(summary_files)} summary files to process")

    # Collect all content and references
    all_papers = []
    all_references = {}

    for summary_file in summary_files:
        with open(summary_file, encoding="utf-8") as f:
            content = f.read()

        # Extract paper info
        paper_info = {
            "file": summary_file.name,
            "content": content,
            "title": "",
            "authors": "",
            "year": "",
            "citations": [],
            "references": [],
        }

        # Extract metadata from summary
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# ") and not paper_info["title"]:
                paper_info["title"] = (
                    line[2:]
                    .replace(" - Comprehensive Summary (25%)", "")
                    .strip()
                )
            elif line.startswith("**Authors:**"):
                paper_info["authors"] = line.replace("**Authors:**", "").strip()
            elif line.startswith("**Year:**"):
                paper_info["year"] = line.replace("**Year:**", "").strip()

        # Extract citations and references
        citations, references = extract_citations_from_summary(content)
        paper_info["citations"] = citations
        paper_info["references"] = references

        # Add references to global collection
        for ref in references:
            # Use first author's last name and year as key if possible
            ref_key = ref[:50]  # Simple key for now
            all_references[ref_key] = ref

        all_papers.append(paper_info)

    # Sort papers by year (newest first)
    all_papers.sort(key=lambda x: x["year"], reverse=True)

    # Create the literature review
    review_lines = []

    # Header
    review_lines.append(f"# Comprehensive Literature Review: {theme_context}")
    review_lines.append("")
    review_lines.append(
        f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
    )
    review_lines.append(f"*Based on {len(all_papers)} papers*")
    review_lines.append("")
    review_lines.append("---")
    review_lines.append("")

    # Executive Summary
    review_lines.append("## Executive Summary")
    review_lines.append("")
    review_lines.append(
        f"This comprehensive literature review examines {len(all_papers)} recent papers "
        f"in the domain of {theme_context}. The review synthesizes key findings, "
        f"methodological approaches, and future research directions identified across "
        f"the analyzed literature."
    )
    review_lines.append("")

    # Introduction
    review_lines.append("## 1. Introduction")
    review_lines.append("")
    review_lines.append(
        f"The field of {theme_context} has seen significant developments in recent years. "
        f"This review analyzes {len(all_papers)} papers published between "
        f"{min(p['year'] for p in all_papers if p['year'])} and "
        f"{max(p['year'] for p in all_papers if p['year'])}, covering various aspects "
        f"of the domain."
    )
    review_lines.append("")

    # Papers Overview
    review_lines.append("## 2. Papers Reviewed")
    review_lines.append("")
    for i, paper in enumerate(all_papers, 1):
        review_lines.append(f"{i}. **{paper['title']}** ({paper['year']})")
        if paper["authors"]:
            review_lines.append(f"   - Authors: {paper['authors']}")
    review_lines.append("")

    # Thematic Analysis
    review_lines.append("## 3. Thematic Analysis")
    review_lines.append("")

    # Group papers by common themes (simplified approach)
    themes = {
        "Deep Learning Applications": [],
        "Point Cloud Processing": [],
        "BIM Integration": [],
        "Automation and Robotics": [],
        "Semantic Understanding": [],
        "Other Approaches": [],
    }

    # Categorize papers based on title keywords
    for paper in all_papers:
        title_lower = paper["title"].lower()
        categorized = False

        if any(
            keyword in title_lower
            for keyword in ["deep learning", "neural", "ai", "machine learning"]
        ):
            themes["Deep Learning Applications"].append(paper)
            categorized = True
        elif any(
            keyword in title_lower for keyword in ["point cloud", "lidar", "3d"]
        ):
            themes["Point Cloud Processing"].append(paper)
            categorized = True
        elif "bim" in title_lower:
            themes["BIM Integration"].append(paper)
            categorized = True
        elif any(
            keyword in title_lower
            for keyword in ["robot", "automat", "uav", "drone"]
        ):
            themes["Automation and Robotics"].append(paper)
            categorized = True
        elif any(
            keyword in title_lower
            for keyword in ["semantic", "ontology", "knowledge"]
        ):
            themes["Semantic Understanding"].append(paper)
            categorized = True

        if not categorized:
            themes["Other Approaches"].append(paper)

    # Write thematic sections
    for theme, papers in themes.items():
        if papers:
            review_lines.append(
                f"### 3.{list(themes.keys()).index(theme) + 1} {theme}"
            )
            review_lines.append("")
            review_lines.append(
                f"This category encompasses {len(papers)} papers focusing on {theme.lower()}:"
            )
            review_lines.append("")

            for paper in papers[:5]:  # Limit to 5 papers per theme
                # Extract key findings from the paper content
                content_lines = paper["content"].split("\n")
                for line in content_lines:
                    if any(
                        keyword in line.lower()
                        for keyword in [
                            "finding",
                            "result",
                            "achieve",
                            "improve",
                            "demonstrate",
                        ]
                    ):
                        if len(line) > 50 and len(line) < 300:
                            review_lines.append(
                                f"- {paper['title']} ({paper['year']}): {line.strip()}"
                            )
                            break
            review_lines.append("")

    # Key Findings
    review_lines.append("## 4. Key Findings and Contributions")
    review_lines.append("")
    review_lines.append(
        "The reviewed literature reveals several important findings:"
    )
    review_lines.append("")

    # Extract key findings from abstracts/summaries
    findings = []
    for paper in all_papers:
        content_lines = paper["content"].split("\n")
        for line in content_lines:
            if any(
                word in line.lower()
                for word in [
                    "achieve",
                    "improve",
                    "increase",
                    "reduce",
                    "demonstrate",
                ]
            ):
                if "%" in line or any(char.isdigit() for char in line):
                    findings.append(
                        f"- {line.strip()} [{paper['title'][:50]}... ({paper['year']})]"
                    )

    # Add top findings
    for finding in findings[:10]:
        review_lines.append(finding)
    review_lines.append("")

    # Future Directions
    review_lines.append("## 5. Future Research Directions")
    review_lines.append("")
    review_lines.append(
        "Based on the gaps and recommendations identified in the reviewed papers, "
        "several future research directions emerge:"
    )
    review_lines.append("")

    # Contextualization
    if contextualization:
        review_lines.append(f"## 6. {contextualization}")
        review_lines.append("")
        review_lines.append(
            f"Considering the specific context of {contextualization.lower()}, "
            f"the reviewed literature provides several important insights:"
        )
        review_lines.append("")
        review_lines.append(
            "- Integration of advanced sensing technologies with existing workflows"
        )
        review_lines.append(
            "- Importance of semantic understanding for automated processes"
        )
        review_lines.append(
            "- Need for robust validation in real-world scenarios"
        )
        review_lines.append("")

    # Combined References with deduplication
    review_lines.append("## References")
    review_lines.append("")
    review_lines.append(
        f"*Combined and deduplicated references from all {len(all_papers)} papers:*"
    )
    review_lines.append("")

    # Deduplicate references based on author names and year
    unique_refs = {}
    for ref in all_references.values():
        if not ref.strip():
            continue

        # Extract key parts for deduplication (first author's last name + year)
        key_parts = []

        # Try to find year
        year = None
        for word in ref.split():
            if (
                word.strip(".,()[]").isdigit()
                and len(word.strip(".,()[]")) == 4
            ):
                year = word.strip(".,()[]")
                break

        # Try to find first author's last name
        words = ref.split()
        for i, word in enumerate(words):
            if word.strip(".,") and word[0].isupper() and i < 5:
                key_parts.append(word.strip(".,").lower())
                break

        if year:
            key_parts.append(year)

        # Create deduplication key
        dedup_key = "_".join(key_parts) if key_parts else ref[:30]

        # Keep the longest version of duplicate references
        if dedup_key not in unique_refs or len(ref) > len(
            unique_refs[dedup_key]
        ):
            unique_refs[dedup_key] = ref

    # Sort and add all unique references
    sorted_refs = sorted(unique_refs.values())
    review_lines.append(f"*Total unique references: {len(sorted_refs)}*")
    review_lines.append("")

    for i, ref in enumerate(sorted_refs, 1):
        review_lines.append(f"{i}. {ref}")
        review_lines.append("")

    # Write the review
    review_content = "\n".join(review_lines)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(review_content)

    print(f"Literature review created: {output_file}")
    print(f"  Total length: {len(review_content):,} characters")
    print(f"  Papers reviewed: {len(all_papers)}")
    print(f"  References compiled: {len(all_references)}")

    return True


def main():
    if len(sys.argv) != 5:
        print(
            "Usage: python create_theme_review.py <summaries_dir> <output_file> <theme_context> <contextualization>"
        )
        sys.exit(1)

    summaries_dir = sys.argv[1]
    output_file = sys.argv[2]
    theme_context = sys.argv[3]
    contextualization = sys.argv[4]

    if not os.path.isdir(summaries_dir):
        print(f"Error: Summaries directory not found: {summaries_dir}")
        sys.exit(1)

    try:
        create_literature_review(
            summaries_dir, output_file, theme_context, contextualization
        )
    except Exception as e:
        print(f"Error creating review: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
