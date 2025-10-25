"""Section-based summarization for academic papers."""

import re

from ..processors.ai_summarizer import AISummarizer
from ..utils.config import get_default_config


class SectionBasedSummarizer:
    """Summarize papers by processing major sections separately."""

    # Common section patterns in academic papers
    SECTION_PATTERNS = [
        # Standard sections
        (r"^#+\s*(abstract|summary)\s*$", "abstract", 0.95),
        (r"^#+\s*(introduction|background)\s*$", "introduction", 0.10),
        (
            r"^#+\s*(related\s+work|literature\s+review|previous\s+work)\s*$",
            "related_work",
            0.15,
        ),
        (
            r"^#+\s*(method|methodology|approach|framework|system)\s*$",
            "methodology",
            0.30,
        ),
        (
            r"^#+\s*(experiment|evaluation|result|validation)\s*$",
            "results",
            0.40,
        ),
        (r"^#+\s*(discussion|analysis|implication)\s*$", "discussion", 0.30),
        (
            r"^#+\s*(future\s+work|limitation|conclusion)\s*$",
            "future_work",
            0.05,
        ),
        (r"^#+\s*(reference|bibliography)\s*$", "references", 1.0),
        # Roman numeral sections
        (r"^#+\s*I+\.\s*(introduction|background)", "introduction", 0.10),
        (r"^#+\s*I+\.\s*(related|literature)", "related_work", 0.15),
        (r"^#+\s*I+V?\.\s*(method|approach|framework)", "methodology", 0.30),
        (r"^#+\s*V+\.\s*(experiment|result|evaluation)", "results", 0.40),
        (r"^#+\s*V+I*\.\s*(discussion|conclusion)", "discussion", 0.30),
    ]

    def __init__(self, config: dict = None):
        self.config = config or get_default_config()
        self.ai_summarizer = AISummarizer(config)

    def extract_sections(self, content: str) -> list[dict[str, any]]:
        """Extract major sections from paper content."""
        lines = content.split("\n")
        sections = []
        current_section = None
        current_content = []

        for i, line in enumerate(lines):
            # Check if this line is a section header
            is_header = False
            for pattern, section_type, compression in self.SECTION_PATTERNS:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    # Save previous section if exists
                    if current_section:
                        sections.append(
                            {
                                "type": current_section["type"],
                                "title": current_section["title"],
                                "content": "\n".join(current_content),
                                "compression": current_section["compression"],
                            }
                        )

                    # Start new section
                    current_section = {
                        "type": section_type,
                        "title": line.strip(),
                        "compression": compression,
                    }
                    current_content = []
                    is_header = True
                    break

            if not is_header and current_section:
                current_content.append(line)

        # Save last section
        if current_section:
            sections.append(
                {
                    "type": current_section["type"],
                    "title": current_section["title"],
                    "content": "\n".join(current_content),
                    "compression": current_section["compression"],
                }
            )

        return sections

    def create_section_prompt(self, section: dict[str, any]) -> str:
        """Create a specialized prompt for each section type."""

        prompts = {
            "abstract": """Preserve this abstract with minimal changes. Only fix obvious formatting issues.""",
            "introduction": """Provide a comprehensive summary of this introduction section. Include:
- The complete problem statement
- ALL citations mentioned (preserve in Author, Year format)
- All research gaps identified
- The paper's contributions as stated
- Research questions or hypotheses
Keep approximately 90% of the original content.""",
            "related_work": """Summarize this related work section while preserving:
- EVERY paper cited (Author, Year)
- Key comparisons between approaches
- Categorizations of prior work
- Timeline of developments if present
- Limitations of existing work
Keep approximately 85% of the original content.""",
            "methodology": """Summarize this methodology section including:
- System architecture and design
- ALL algorithms or pseudocode
- Implementation details
- Technical specifications
- Parameter settings
- Any equations or formulas
Keep approximately 70% of the original content with all technical details.""",
            "results": """Summarize the results section preserving:
- ALL numerical results and percentages
- Performance metrics and comparisons
- Tables and figures descriptions
- Statistical significance
- Experimental setup details
Keep approximately 60% of the original content.""",
            "discussion": """Summarize the discussion including:
- Key findings and their implications
- Comparisons with prior work (with citations)
- Limitations acknowledged
- Broader impacts
- Applications
Keep approximately 70% of the original content.""",
            "future_work": """Preserve this section almost entirely. Include:
- ALL future research directions mentioned
- Challenges and open problems
- Suggested improvements
- Required resources
Keep approximately 95% of the original content.""",
            "references": """Preserve the complete reference list exactly as provided.""",
        }

        base_prompt = prompts.get(
            section["type"],
            """Summarize this section preserving key information and all citations.""",
        )

        return f"""Process this {section["type"]} section from an academic paper.

{base_prompt}

Section content:
{section["content"]}

Provide a comprehensive summary that maintains academic rigor and preserves all important details."""

    def summarize_by_sections(self, content: str, metadata: dict = None) -> str:
        """Create summary by processing each major section separately."""

        # Extract sections
        sections = self.extract_sections(content)

        if not sections:
            # Fallback to regular summarization if no sections found
            return self.ai_summarizer.create_summary(
                sections=[
                    {
                        "title": "Full Paper",
                        "content": content,
                        "importance": 1.0,
                    }
                ],
                metadata=metadata or {},
                target_compression=0.3,
            )

        # Process each section
        section_summaries = []

        # Add metadata
        if metadata:
            section_summaries.append(
                f"# {metadata.get('title', 'Paper Summary')}\n"
            )
            if metadata.get("authors"):
                section_summaries.append(
                    f"**Authors**: {', '.join(metadata['authors'])}\n"
                )
            if metadata.get("year"):
                section_summaries.append(f"**Year**: {metadata['year']}\n")
            section_summaries.append("\n---\n\n")

        # Process each section with appropriate compression
        for section in sections:
            print(
                f"Processing section: {section['title']} (compression: {section['compression']})"
            )

            if section["type"] == "references":
                # Keep references as-is
                section_summaries.append(
                    f"## References\n\n{section['content']}\n\n"
                )
            else:
                # Create section-specific prompt
                prompt = self.create_section_prompt(section)

                # Use AI to process this section
                try:
                    summary = self.process_section_with_ai(prompt, section)
                    section_summaries.append(
                        f"## {section['title']}\n\n{summary}\n\n"
                    )
                except Exception as e:
                    print(f"Error processing section {section['title']}: {e}")
                    # Include original if processing fails
                    section_summaries.append(
                        f"## {section['title']}\n\n{section['content'][:1000]}...\n\n"
                    )

        return "".join(section_summaries)

    def process_section_with_ai(
        self, prompt: str, section: dict[str, any]
    ) -> str:
        """Process a single section with AI."""
        # This would call the AI service with the section-specific prompt
        # For now, return a placeholder
        return f"[Section summary for {section['type']} would go here]"
