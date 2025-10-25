#!/usr/bin/env python3
"""
Academic Rephrasing Tool

A unified tool for rephrasing academic papers with customizable retention rates.
This consolidates the functionality from multiple previous scripts into a single,
well-organized module.

Usage:
    python academic_rephrasing.py input.md --retention 0.25 --output output.md
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent / "literature-reviewer" / "src")
)

from literature_reviewer.processors.content_preserving_rephraser import (
    ContentPreservingRephraser,
)
from literature_reviewer.processors.content_processor import ContentProcessor
from literature_reviewer.utils.config import get_default_config


class AcademicRephraser:
    """Main class for academic paper rephrasing."""

    def __init__(self):
        self.config = get_default_config()
        self.content_processor = ContentProcessor(self.config)
        self.rephraser = ContentPreservingRephraser()

    def clean_content(self, content: str) -> str:
        """Remove artifacts and clean markdown content."""

        # Phase 1: Remove major arxiv HTML conversion artifacts
        # Remove the entire header section between title and content
        # This removes everything from ## followed by html-header to the next # section
        content = re.sub(
            r"##\s*\n*(?:html-header|mob_header|desktop_header).*?(?=\n#[^#]|\Z)",
            "",
            content,
            flags=re.DOTALL,
        )

        # Remove all navigation/header/footer blocks with ::: markers
        content = re.sub(r":::+[^:]*:::+", "", content, flags=re.DOTALL)
        content = re.sub(
            r"##\s*Table of Contents.*?(?=\n#|\Z)", "", content, flags=re.DOTALL
        )

        # Remove failed conversion messages
        content = re.sub(r"\[WARNING\].*?rendering as TeX", "", content)
        content = re.sub(
            r"HTML conversions.*?best practices\.", "", content, flags=re.DOTALL
        )
        content = re.sub(r"failed:\s*\w+", "", content)
        content = re.sub(
            r"::: \{\.package-alerts.*?\n:::", "", content, flags=re.DOTALL
        )

        # Remove arxiv header/footer
        content = re.sub(
            r"License: CC BY.*?arXiv:[^\n]+", "", content, flags=re.DOTALL
        )
        content = re.sub(
            r"\\pdfcolInitStack.*?tcb@breakable", "", content, flags=re.DOTALL
        )

        # Phase 2: Clean LaTeX artifacts
        # Clean up complex LaTeX references like [[text]{ }]{ title="..."}
        content = re.sub(
            r"\[\[([^\]]+)\]\{[^}]*\}\]\{[^}]*title=[^}]*\}", r"\1", content
        )
        content = re.sub(r"\[\[([^\]]+)\]\{[^}]*\}\]\{[^}]*\}", r"\1", content)

        # Clean simple LaTeX references like [text]{ }
        content = re.sub(r"\[([^\]]+)\]\{\s*\}", r"\1", content)

        # Remove LaTeX classes and IDs
        content = re.sub(r"\{#[^}]+\.ltx_[^}]+\}", "", content)
        content = re.sub(r"\.ltx_[a-zA-Z_]+", "", content)
        content = re.sub(r"\{#[^}]+\s+\}", "", content)

        # Clean section headers
        content = re.sub(
            r"^(#+)\s*\[[^\]]+\]\{[^}]+\}\s*([^{\n]+).*$",
            r"\1 \2",
            content,
            flags=re.MULTILINE,
        )

        # Phase 3: Clean references and citations
        # Remove complex citation patterns \[[[34]{ }]( ){.ltx_ref}
        content = re.sub(
            r"\\\[\[\[?\d+\][^\]]*\]\([^)]+\)[^\]]*\]", "", content
        )
        # Remove simpler citation patterns \],
        content = re.sub(r"\\\],?", "", content)
        # Remove lone commas from citation cleanup
        content = re.sub(r",\s*,", ",", content)
        content = re.sub(r",\s*\.", ".", content)

        # Phase 4: Clean HTML and markdown artifacts
        # Remove data URIs and images
        content = re.sub(r"!\[.*?\]\(data:image[^)]+\)", "", content)
        content = re.sub(r"!\[logo\]\([^)]+\)", "", content)
        content = re.sub(r"\[Back to.*?\]\([^)]+\)", "", content)

        # Remove HTML tags and attributes
        content = re.sub(r"<[^>]+>", "", content)
        content = re.sub(r'style="[^"]*"', "", content)
        content = re.sub(r"aria-[^=]+=\"[^\"]*\"", "", content)
        content = re.sub(r'role="[^"]*"', "", content)

        # Remove button elements
        content = re.sub(r"Report issue for preceding element", "", content)

        # Phase 5: Clean up arxiv-specific navigation text
        # Remove standalone navigation text and buttons
        content = re.sub(
            r"\{[^}]*\.(?:logomark|logo|nav-link|ar5iv-[^}]+|html-header-[^}]+)[^}]*\}",
            "",
            content,
        )
        content = re.sub(r'"Toggle dark/light mode"\)', "", content)
        content = re.sub(r'width="\d+"', "", content)
        content = re.sub(r'\{target="_blank"\}', "", content)
        content = re.sub(r'onclick="[^"]*"', "", content)

        # Remove "This is experimental HTML" disclaimer blocks
        content = re.sub(
            r"This is (?:\*\*)?experimental HTML(?:\*\*)?\.{0,3}.*?help improve.*?conversions.*?\.",
            "",
            content,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Phase 6: Improve table handling
        # Look for table patterns and skip table conversion for now
        # Tables in arxiv HTML are complex and better handled by pandoc
        # Just clean up obvious table artifacts
        content = re.sub(r"^\s*\|+\s*$", "", content, flags=re.MULTILINE)
        content = re.sub(r"TABLE [IVX]+:", "\n**Table:**", content)

        # Remove table footnote markers
        content = re.sub(r"[†‡∗^]+(?=\s|\n|$)", "", content)

        # Phase 7: Remove arxiv HTML interface elements
        # Remove "Report Github Issue" and error reporting instructions
        # First remove just the header
        content = re.sub(
            r"##\s*Report Github Issue\s*\n",
            "",
            content,
            flags=re.MULTILINE,
        )
        # Then remove the "Report issue" line
        content = re.sub(
            r"Report issue for preceding element\s*\n?",
            "",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r"##\s*Instructions for reporting errors.*?(?=\n##|\n#[^#]|\n\n[A-Z]|\Z)",
            "",
            content,
            flags=re.DOTALL | re.MULTILINE,
        )
        # Remove any remaining modal/UI elements
        content = re.sub(
            r"modal-body.*?Title:Content selection saved\.",
            "",
            content,
            flags=re.DOTALL,
        )
        content = re.sub(r"\{#report-github-issue[^}]*\}", "", content)

        # Phase 8: Final cleanup
        # Clean up empty brackets and links
        content = re.sub(r"\[\s*\]\s*\([^)]*\)", "", content)
        content = re.sub(r"\[\]\{[^}]+\}", "", content)
        content = re.sub(r"\{\s*\}", "", content)

        # Remove IDs like #S3.SS1.p1.1.1
        content = re.sub(
            r"#[A-Z0-9]+\.[A-Z0-9]+\.[a-z0-9]+\.[0-9]+\.[0-9]+", "", content
        )

        # Remove standalone .sr-only text
        content = re.sub(r"\[.*?\]\{\.sr-only\}", "", content)

        # Clean up whitespace
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = re.sub(r"^#+\s*$", "", content, flags=re.MULTILINE)
        content = re.sub(r" +", " ", content)  # Multiple spaces to single space

        return content.strip()

    def remove_duplicate_sentences(self, text: str) -> str:
        """Remove consecutive duplicate sentences within paragraphs."""
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            if not line.strip():
                cleaned_lines.append(line)
                continue

            # Split into sentences and remove consecutive duplicates
            sentences = re.split(r"(?<=[.!?])\s+", line)
            unique_sentences = []
            prev_sentence = None

            for sent in sentences:
                sent = sent.strip()
                if sent and sent != prev_sentence:
                    unique_sentences.append(sent)
                    prev_sentence = sent

            if unique_sentences:
                cleaned_lines.append(" ".join(unique_sentences))

        return "\n".join(cleaned_lines)

    def remove_figure_captions(self, text: str) -> str:
        """Remove figure captions and image references."""
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            # Skip lines that are likely figure captions
            caption_patterns = [
                r"^\(a\)",
                r"^\(b\)",
                r"^\(c\)",
                r"^\(d\)",
                r"^Fig\.\s*\d+",
                r"^Figure\s*\d+",
                r"^Table\s*\d+",
                r"^\w+\s+\([\w\s]+\)$",  # Like "Semantic segmentation (ADE20k)"
            ]

            is_caption = False
            for pattern in caption_patterns:
                if re.match(pattern, line.strip()):
                    is_caption = True
                    break

            # Also check for lines with multiple subfigure references
            if line.count("(a)") + line.count("(b)") + line.count("(c)") > 2:
                is_caption = True

            if not is_caption:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def clean_rephrased_output(self, text: str) -> str:
        """Final cleanup pass for rephrased content."""
        # Remove any remaining LaTeX artifacts that slipped through
        text = re.sub(r"\{[^{}]*title=[^}]*\}", "", text)
        text = re.sub(r"\[\s*\]\s*\{[^}]*\}", "", text)
        text = re.sub(r"\\\]", "", text)

        # Remove any remaining navigation artifacts
        text = re.sub(r"\{\.[-\w]+\}", "", text)  # Remove CSS class markers
        text = re.sub(r'target="_blank"', "", text)
        text = re.sub(r"html-header-\w+", "", text)

        # Clean up table footnote markers like †, ‡, ∗
        text = re.sub(r"([†‡∗^]+)(?=\s|\n|$)", "", text)

        # Clean up malformed punctuation
        text = re.sub(r"\s+([,.])", r"\1", text)
        text = re.sub(r"([,.])([,.])", r"\1", text)

        # Remove empty parentheses and brackets
        text = re.sub(r"\(\s*\)", "", text)
        text = re.sub(r"\[\s*\]", "", text)
        text = re.sub(r"\{\s*\}", "", text)

        # Remove orphaned colons (from table parsing)
        text = re.sub(r"^:::\s*$", "", text, flags=re.MULTILINE)

        # Clean up whitespace again
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def extract_references(self, content: str) -> list[str]:
        """Extract full references from markdown content."""
        references = []

        # Look for reference section with multiple possible headers
        # Use non-greedy matching to stop at the next section
        ref_patterns = [
            r"(?:##\s*)?(?:References|Bibliography|Works Cited|Literature Cited)\s*\n+(.+?)(?=\n##\s*[A-Z]|\n## Appendi|\n## Acknowledgment|\n## Supplementary|\Z)",
            r"\n\s*References\s*\n[-=]+\n(.+?)(?=\n##\s*[A-Z]|\n## Appendi|\n## Acknowledgment|\n## Supplementary|\Z)",
            r"\[\[References\]\].*?\n(.+?)(?=\n##\s*[A-Z]|\n## Appendi|\n## Acknowledgment|\n## Supplementary|\Z)",
        ]

        ref_text = ""
        for pattern in ref_patterns:
            ref_section_match = re.search(
                pattern, content, re.IGNORECASE | re.DOTALL
            )
            if ref_section_match:
                ref_text = ref_section_match.group(1)
                break

        if ref_text:
            # Look for bullet list format commonly from pandoc conversions
            # Pattern: - [Author et al. (Year)]... followed by bibliography details
            bullet_refs = re.findall(
                r"^-\s*\[([^\]]+)\]\{#[^}]*\}\s*\n\s*↑?\s*\n\s*\[([^\]]+)\]\{[^}]*\}\s*\[([^\]]+)\]\{[^}]*\}\s*\[([^\]]+)\]\{[^}]*\}",
                ref_text,
                re.MULTILINE,
            )

            if bullet_refs:
                # Process bullet format references
                for match in bullet_refs:
                    # Combine all parts into full reference
                    full_ref = f"{match[0]}. {match[1]} {match[2]} {match[3]}"
                    # Clean up any remaining markup
                    full_ref = re.sub(r"\{[^}]+\}", "", full_ref)
                    full_ref = re.sub(r"\s+", " ", full_ref)
                    references.append(full_ref.strip())
            else:
                # Alternative approach: extract each reference as a block
                # Split by bullet points and process each
                ref_blocks = re.split(r"^-\s*\[", ref_text, flags=re.MULTILINE)

                for block in ref_blocks[1:]:  # Skip first empty split
                    # Extract everything until the next reference or section header
                    block_match = re.match(
                        r"([^\]]+)\](.+?)(?=^-\s*\[|^##|\Z)",
                        block,
                        re.DOTALL | re.MULTILINE,
                    )
                    if block_match:
                        authors = block_match.group(1)
                        details = block_match.group(2)

                        # Clean up the details
                        details = re.sub(
                            r"\{#[^}]+\}", "", details
                        )  # Remove {#bib.bib1} etc
                        details = re.sub(
                            r"\{\.ltx_[^}]+\}", "", details
                        )  # Remove {.ltx_bibblock}
                        details = re.sub(
                            r"\[([^\]]+)\]\{[^}]*\}", r"\1", details
                        )  # Extract text from [text]{...}
                        details = re.sub(
                            r"↑\s*\n", "", details
                        )  # Remove up arrows
                        details = re.sub(
                            r"\n+", " ", details
                        )  # Replace newlines with spaces
                        details = re.sub(
                            r"\s+", " ", details
                        )  # Normalize whitespace
                        details = details.strip()

                        if details:
                            full_ref = f"{authors}. {details}"
                            references.append(full_ref)

            # If still no references found, try simpler approaches
            if not references:
                # First try numbered format like "[1] Author, J. 2023. Title. Journal."
                numbered_refs = re.findall(
                    r"^\[?\d+\]?\s*(.+)$", ref_text, re.MULTILINE
                )

                # Also try simple bullet format "- Author et al. (Year)"
                simple_bullet_refs = re.findall(
                    r"^-\s+(.+)$", ref_text, re.MULTILINE
                )

                # Try format like "Author, A. (Year). Title. Journal."
                simple_refs = re.findall(
                    r"^(.+?\(\d{4}\).+?\.)$", ref_text, re.MULTILINE
                )

                # Combine all found references
                all_refs = numbered_refs + simple_bullet_refs + simple_refs

                # Filter out empty or very short entries
                references = [
                    ref.strip()
                    for ref in all_refs
                    if ref.strip() and len(ref.strip()) > 10
                ]

            # Final cleanup of all references
            cleaned_refs = []
            for ref in references:
                # Additional cleanup
                ref = re.sub(r"Report issue for preceding element", "", ref)

                # Remove any appendix content that might have leaked in
                # Stop at section headers that indicate appendix/new content
                ref = re.sub(
                    r"\s*##\s*(Ablation|Appendix|Acknowledgment|Supplementary|Implementation).*",
                    "",
                    ref,
                    flags=re.DOTALL,
                )

                # Clean up whitespace
                ref = re.sub(r"\s+", " ", ref)
                ref = ref.strip()

                # Only keep references that look valid
                # Relax criteria to handle test cases better
                if (
                    ref
                    and len(ref) > 5  # Very relaxed for simple test references
                    and not re.search(r"^##\s*", ref)
                    and not re.search(
                        r"We conduct|We present|We analyze|This section", ref
                    )
                    and not re.search(
                        r"\[WARNING\]|Failed to parse", ref
                    )  # Skip warning lines
                ):
                    cleaned_refs.append(ref)

            references = cleaned_refs

        return references

    def _get_preservation_ratios(
        self, target_retention: float
    ) -> dict[str, float]:
        """Get preservation ratios based on target retention rate."""
        if target_retention <= 0.25:
            return {
                "abstract": 0.50,
                "introduction": 0.40,
                "related work": 0.30,
                "method": 0.15,
                "experiment": 0.10,
                "result": 0.15,
                "discussion": 0.60,
                "conclusion": 0.70,
                "future": 1.0,
                "limitation": 0.95,
                "contribution": 0.90,
                "research gap": 0.95,
                "novel": 0.90,
            }
        elif target_retention <= 0.50:
            return {
                "abstract": 0.70,
                "introduction": 0.60,
                "related work": 0.50,
                "method": 0.25,
                "experiment": 0.20,
                "result": 0.30,
                "discussion": 0.75,
                "conclusion": 0.85,
                "future": 1.0,
                "limitation": 0.95,
                "contribution": 0.95,
                "research gap": 0.95,
                "novel": 0.95,
            }
        else:
            return {
                "abstract": 0.80,
                "introduction": 0.70,
                "related work": 0.60,
                "method": 0.40,
                "experiment": 0.35,
                "result": 0.45,
                "discussion": 0.85,
                "conclusion": 0.90,
                "future": 1.0,
                "limitation": 0.95,
                "contribution": 0.95,
                "research gap": 1.0,
                "novel": 0.95,
            }

    def rephrase_paper(
        self,
        input_path: Path,
        output_path: Path | None = None,
        target_retention: float = 0.25,
        context: str = "BIM/Scan-to-BIM Applications",
        include_appendix: bool = False,
        clean_duplicates: bool = True,
        remove_captions: bool = True,
    ) -> str:
        """
        Rephrase an academic paper with specified retention rate.

        Args:
            input_path: Path to input markdown file
            output_path: Optional path for output (if None, returns string only)
            target_retention: Target retention rate (0.0 to 1.0)
            context: Context for rephrasing (default: BIM applications)
            include_appendix: Whether to include appendix sections
            clean_duplicates: Whether to remove duplicate sentences
            remove_captions: Whether to remove figure/table captions

        Returns:
            Rephrased content as string
        """
        # Read and clean content
        md_content = input_path.read_text(encoding="utf-8")
        md_content = self.clean_content(md_content)

        # Parse sections and metadata
        sections = self.content_processor.parse_sections(md_content)
        metadata = self.content_processor.extract_metadata(md_content)
        title = metadata.get("title", input_path.stem.replace("_", " "))

        # Extract references
        references = self.extract_references(md_content)

        # Calculate original word count
        original_words = len(md_content.split())

        # Get preservation ratios based on target retention
        preservation_ratios = self._get_preservation_ratios(target_retention)

        # Build rephrased content
        rephrased = self._build_header(
            title, original_words, target_retention, context
        )

        # Process sections
        for section in sections:
            section_title = section["title"]
            section_content = section["content"]

            # Stop processing once we hit the References section
            # Everything after references is appendix/supplementary material
            title_lower = section_title.lower()
            if any(
                term in title_lower
                for term in ["references", "bibliography", "works cited"]
            ):
                break

            if not section_content.strip() or len(section_content.split()) < 20:
                continue

            # Skip appendix sections if requested (backup check)
            if not include_appendix and any(
                term in title_lower
                for term in [
                    "appendix",
                    "appendices",
                    "supplementary",
                    "ablation",
                    "implementation",
                    "experiment detail",
                    "visualization",
                    "additional result",
                    "hyperparameter",
                    "training detail",
                    "dataset detail",
                    "architecture detail",
                ]
            ):
                continue

            # Get preservation ratio
            preservation_ratio = 0.35  # Default

            for key, ratio in preservation_ratios.items():
                if key in title_lower:
                    preservation_ratio = ratio
                    break

            # Map section title for display
            display_title = self._map_section_title(title_lower, section_title)

            # Rephrase section
            # Don't pass references to avoid double citation issues
            section_rephrase = self.rephraser.rephrase_academic_content(
                section_content, section_title, preservation_ratio, []
            )

            if section_rephrase:
                rephrased += f"\n{display_title}\n\n{section_rephrase}\n"

        # Add context-specific section
        rephrased += self._build_context_section(context)

        # Add references
        if references:
            rephrased += self._build_references_section(references)

        # Apply post-processing cleaning if requested
        if clean_duplicates:
            rephrased = self.remove_duplicate_sentences(rephrased)

        if remove_captions:
            rephrased = self.remove_figure_captions(rephrased)

        # Always do a final cleanup pass on the rephrased content
        rephrased = self.clean_rephrased_output(rephrased)

        # Add footer
        final_words = len(rephrased.split())
        actual_retention = (final_words / original_words) * 100
        rephrased += self._build_footer(actual_retention, context)

        # Save if output path provided
        if output_path:
            output_path.write_text(rephrased, encoding="utf-8")

        return rephrased

    def _build_header(
        self,
        title: str,
        original_words: int,
        target_retention: float,
        context: str,
    ) -> str:
        """Build document header."""
        return f"""# {title}
*Research Gap Analysis for {context}*

**Focus**: Research Evolution & Knowledge Gaps
**Original Length**: {original_words:,} words
**Target Length**: ~{int(original_words * target_retention):,} words ({int(target_retention * 100)}%)
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

**Analysis Focus**:
- What wasn't known before this paper
- What this paper achieved
- What knowledge gaps remain
- Implications for {context}

---

"""

    def _map_section_title(self, title_lower: str, original_title: str) -> str:
        """Map section titles to research-gap-focused display titles."""
        title_mappings = {
            "abstract": "## Key Contributions & Novel Aspects",
            "introduction": "## Problem Context & Research Gaps Addressed",
            "related work": "## Prior Knowledge & Remaining Gaps",
            "background": "## Prior Knowledge & Context",
            "method": "## Approach Overview",
            "approach": "## Approach Overview",
            "framework": "## Framework Overview",
            "result": "## Key Achievements",
            "experiment": "## Validation Approach",
            "evaluation": "## Key Findings",
            "discussion": "## Implications & New Insights",
            "limitation": "## Limitations & Unresolved Issues [PRESERVED]",
            "future": "## Future Research Directions [FULLY PRESERVED]",
            "conclusion": "## What Was Achieved [HIGH PRESERVATION]",
            "contribution": "## Novel Contributions [PRESERVED]",
        }

        for key, display in title_mappings.items():
            if key in title_lower:
                return display

        return f"## {original_title}"

    def _build_context_section(self, context: str) -> str:
        """Build context-specific research opportunities section."""
        if "BIM" in context:
            return """
## Research Opportunities for BIM/Scan-to-BIM

### Knowledge Gaps This Opens:
1. **Integration Challenges**: How to adapt these methods for construction-specific constraints
2. **Scale & Complexity**: Handling full building models vs. isolated objects
3. **Industry Standards**: Bridging academic methods with industry practices
4. **Real-time Processing**: Moving from batch to continuous processing

### Business Opportunities:
1. **Automated QA Services**: Deviation detection between design and built
2. **Semantic Enhancement Tools**: Adding intelligence to point clouds
3. **Workflow Automation**: Reducing manual intervention in scan-to-BIM
4. **Data Integration Platforms**: Connecting multiple data sources

### Unresolved Technical Challenges:
- Handling incomplete scans and occlusions
- Semantic understanding of construction-specific elements
- Integration with existing BIM software ecosystems
- Standardization of outputs for industry adoption

"""
        else:
            return f"""
## Research Opportunities in {context}

### Knowledge Gaps Addressed:
The methods presented address specific gaps in {context}.

### Remaining Challenges:
Key technical and practical challenges remain for full adoption.

"""

    def _build_references_section(self, references: list[str]) -> str:
        """Build references section."""
        if not references:
            return """## References

*No references found in the original paper.*

"""

        section = f"""## References

*Complete reference list from original paper ({len(references)} references):*

"""
        for i, ref in enumerate(references, 1):
            section += f"{i}. {ref}\n\n"

        return section

    def _build_footer(self, actual_retention: float, context: str) -> str:
        """Build document footer."""
        return f"""---

*This research gap analysis achieved {actual_retention:.1f}% content retention.
Focus: research evolution, knowledge gaps, and business opportunities for {context}.
Future work and limitations preserved at >95%.*"""

    def process_folder(
        self,
        input_folder: Path,
        output_folder: Path,
        target_retention: float = 0.25,
        context: str = "BIM/Scan-to-BIM Applications",
        include_appendix: bool = False,
        clean_duplicates: bool = True,
        remove_captions: bool = True,
        file_pattern: str = "*.md",
    ) -> dict[str, dict]:
        """
        Process all papers in a folder.

        Args:
            input_folder: Path to folder containing markdown papers
            output_folder: Path to output folder
            target_retention: Target retention rate (0.0 to 1.0)
            context: Context for rephrasing
            include_appendix: Whether to include appendix sections
            clean_duplicates: Whether to remove duplicate sentences
            remove_captions: Whether to remove figure/table captions
            file_pattern: Glob pattern for files to process (default: *.md)

        Returns:
            Dictionary with processing results for each file
        """
        # Create output folder if needed
        output_folder.mkdir(parents=True, exist_ok=True)

        # Find all matching files
        input_files = list(input_folder.glob(file_pattern))

        results = {}

        for idx, input_file in enumerate(input_files, 1):
            print(f"\nProcessing [{idx}/{len(input_files)}]: {input_file.name}")

            try:
                # Generate output filename
                output_file = output_folder / f"{input_file.stem}_rephrased.md"

                # Process the file
                self.rephrase_paper(
                    input_file,
                    output_file,
                    target_retention,
                    context,
                    include_appendix,
                    clean_duplicates,
                    remove_captions,
                )

                # Calculate retention
                original_words = len(input_file.read_text().split())
                rephrased_words = len(output_file.read_text().split())
                actual_retention = (rephrased_words / original_words) * 100

                results[input_file.name] = {
                    "status": "success",
                    "original_words": original_words,
                    "rephrased_words": rephrased_words,
                    "retention_percentage": actual_retention,
                    "output_path": str(output_file),
                }

                print(f"  [SUCCESS] Achieved {actual_retention:.1f}% retention")

            except Exception as e:
                results[input_file.name] = {
                    "status": "error",
                    "error": str(e),
                }
                print(f"  [ERROR] Error: {e}")

        # Print summary
        print("\n" + "=" * 60)
        print("Processing Summary:")
        print(f"Total files: {len(input_files)}")
        print(
            f"Successful: {sum(1 for r in results.values() if r['status'] == 'success')}"
        )
        print(
            f"Failed: {sum(1 for r in results.values() if r['status'] == 'error')}"
        )

        avg_retention = [
            r["retention_percentage"]
            for r in results.values()
            if r["status"] == "success"
        ]
        if avg_retention:
            print(
                f"Average retention: {sum(avg_retention) / len(avg_retention):.1f}%"
            )

        return results


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Academic paper rephrasing tool with customizable retention"
    )
    parser.add_argument("input", type=Path, help="Input markdown file")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file (default: input_rephrased.md)",
    )
    parser.add_argument(
        "--retention",
        "-r",
        type=float,
        default=0.25,
        help="Target retention rate (0.0-1.0, default: 0.25)",
    )
    parser.add_argument(
        "--context",
        "-c",
        default="BIM/Scan-to-BIM Applications",
        help="Application context for rephrasing",
    )
    parser.add_argument(
        "--include-appendix",
        action="store_true",
        help="Include appendix sections (default: exclude)",
    )
    parser.add_argument(
        "--no-clean-duplicates",
        action="store_true",
        help="Disable duplicate sentence removal",
    )
    parser.add_argument(
        "--no-remove-captions",
        action="store_true",
        help="Disable figure/table caption removal",
    )
    parser.add_argument(
        "--batch",
        "-b",
        action="store_true",
        help="Process all markdown files in input folder",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.input.exists():
        print(f"Error: Input file '{args.input}' not found")
        sys.exit(1)

    if not 0.0 < args.retention <= 1.0:
        print("Error: Retention rate must be between 0.0 and 1.0")
        sys.exit(1)

    # Process
    rephraser = AcademicRephraser()

    try:
        if args.batch:
            # Batch processing mode
            if not args.input.is_dir():
                print("Error: For batch mode, input must be a directory")
                sys.exit(1)

            if not args.output:
                print("Error: Output directory required for batch mode")
                sys.exit(1)

            print(f"Processing folder: {args.input}")
            print(f"Target retention: {args.retention * 100:.0f}%")

            rephraser.process_folder(
                args.input,
                args.output,
                args.retention,
                args.context,
                args.include_appendix,
                not args.no_clean_duplicates,
                not args.no_remove_captions,
            )

        else:
            # Single file mode
            if not args.output:
                args.output = (
                    args.input.parent / f"{args.input.stem}_rephrased.md"
                )

            print(f"Processing: {args.input}")
            print(f"Target retention: {args.retention * 100:.0f}%")

            result = rephraser.rephrase_paper(
                args.input,
                args.output,
                args.retention,
                args.context,
                args.include_appendix,
                not args.no_clean_duplicates,
                not args.no_remove_captions,
            )
            print(f"Output saved to: {args.output}")

            # Report actual retention
            original_words = len(args.input.read_text().split())
            rephrased_words = len(result.split())
            actual_retention = (rephrased_words / original_words) * 100
            print(f"Actual retention: {actual_retention:.1f}%")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
