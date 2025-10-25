"""AI-powered summarization using Claude or OpenAI."""

import os
import time
from datetime import datetime
from typing import Any

# Try to import AI clients
try:
    from anthropic import Anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class AISummarizer:
    """AI-powered text summarization using Claude or OpenAI models."""

    def __init__(self, config: dict[str, Any] = None):
        # Rate limiting attributes
        self._last_request_time = None
        self._request_count = 0
        self._rate_limit_window_start = datetime.now()
        self._min_request_interval = 1.0  # Minimum seconds between requests
        import yaml

        # Load config from file if not provided
        if config is None:
            config_path = os.path.expanduser("~/.literature-reviewer.yml")
            if os.path.exists(config_path):
                with open(config_path) as f:
                    config = yaml.safe_load(f)
            else:
                config = {}

        self.config = config
        self.ai_config = self.config.get("ai", {})
        self.provider = self.ai_config.get("provider", "anthropic")

        # Initialize the appropriate client
        if self.provider == "anthropic" and ANTHROPIC_AVAILABLE:
            api_key = self.ai_config.get("anthropic", {}).get("api_key")
            if not api_key:
                api_key = os.getenv("ANTHROPIC_API_KEY")
            self.client = Anthropic(api_key=api_key)
            self.model = self.ai_config.get("anthropic", {}).get(
                "model", "claude-3-5-sonnet-20241022"
            )
            self.temperature = self.ai_config.get("anthropic", {}).get(
                "temperature", 0.3
            )
            self.max_tokens = self.ai_config.get("anthropic", {}).get(
                "max_tokens",
                8000,  # Increased for longer summaries
            )
        elif self.provider == "openai" and OPENAI_AVAILABLE:
            api_key = self.ai_config.get("openai", {}).get("api_key")
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
            self.client = OpenAI(api_key=api_key)
            self.model = self.ai_config.get("openai", {}).get(
                "model", "gpt-4o-mini"
            )
            self.temperature = self.ai_config.get("openai", {}).get(
                "temperature", 0.3
            )
            self.max_tokens = self.ai_config.get("openai", {}).get(
                "max_tokens",
                8000,  # Increased for longer summaries
            )
        else:
            raise RuntimeError(
                f"AI provider '{self.provider}' not available or not configured"
            )

    def create_summary(
        self,
        sections: list[dict[str, Any]],
        metadata: dict[str, Any],
        target_compression: float = 0.25,
        section_based: bool = False,
    ) -> str:
        """Create AI-powered summary of sections."""
        # Check if we should do section-based processing
        if section_based:
            return self._create_section_based_summary(
                sections, metadata, target_compression
            )

        # Build the content for summarization
        full_content = self._build_content_for_summary(sections, metadata)

        # Calculate target length based on the full paper content
        # Get the full content character count from metadata if available
        total_chars = sum(
            len(s["content"]) for s in sections
        )  # Calculate for debug output

        if metadata.get("word_count"):
            # Use actual word count from paper
            original_words = metadata["word_count"]
            # Adjust compression to be less extreme - aim for actual 25% compression
            adjusted_compression = target_compression  # Use the target directly
            target_words = int(original_words * adjusted_compression)
            target_chars = (
                target_words * 6
            )  # Average 6 chars per word including spaces
        else:
            # Fallback to section content calculation
            adjusted_compression = target_compression
            target_chars = int(total_chars * adjusted_compression)
            target_words = int(target_chars / 6)

        # Ensure minimum word count for comprehensive summaries
        # Set minimum to avoid over-compression
        if metadata.get("word_count"):
            # For comprehensive summaries, aim for at least 20% of original
            min_words = max(int(original_words * 0.20), 1500)
            # Boost target if it's too low
            if target_words < min_words:
                target_words = int(min_words * 1.2)  # Add 20% buffer
        else:
            min_words = 2000  # Default minimum
            if target_words < min_words:
                target_words = min_words

        target_chars = target_words * 6

        # Debug output
        import sys

        print(
            f"[DEBUG] AI Summarizer: Total chars: {total_chars}, Target compression: {target_compression}, Adjusted: {adjusted_compression}",
            file=sys.stderr,
        )
        print(
            f"[DEBUG] AI Summarizer: Target words: {target_words}, Target chars: {target_chars}",
            file=sys.stderr,
        )
        if metadata.get("word_count"):
            print(
                f"[DEBUG] AI Summarizer: Using word count from paper: {metadata['word_count']}",
                file=sys.stderr,
            )

        # Create the prompt with very specific instructions
        prompt = f"""Create a COMPREHENSIVE academic summary that preserves the paper's key insights, technical details, and research contributions. Aim for approximately {target_words} words, but prioritize completeness over brevity.

GUIDING PRINCIPLE: This is an academic summary for researchers who need to understand the paper's contributions, methods, and implications in detail. Do NOT over-compress - include sufficient detail for readers to grasp the technical approach and findings.

REQUIRED SECTIONS AND CONTENT:

## Executive Summary
Provide a thorough overview that captures the essence of the paper:
- Full author list, complete title, journal/conference, year, DOI if available
- The core problem being addressed and why it matters
- Main contribution explained clearly
- Key innovations or novel approaches
- Validation methodology and datasets used
- ALL quantitative results and performance metrics
- Significance and impact of the work

## Key Technical Contributions
For EACH major contribution, provide IN-DEPTH coverage:
- Detailed technical explanation that a researcher could understand and potentially implement
- Include ALL code snippets, algorithms, or pseudocode shown in the paper
- Preserve mathematical formulas, equations, and proofs
- Describe system architectures with component interactions
- Include any diagrams or figure descriptions
- Preserve tables and structured data
- Use multiple subsections to organize complex contributions

### Example structure for each contribution:
#### [Contribution Name]
**Motivation**: Why this contribution is needed
**Technical Approach**: Detailed methodology
**Implementation**: Code, algorithms, specifications
**Innovation**: What makes this novel
**Validation**: How it was tested/proven

## Comprehensive Methodology
Provide sufficient detail for reproducibility:
- Complete system architecture and design decisions
- Step-by-step workflow with rationale for each step
- All algorithms with complexity analysis
- Implementation details (languages, libraries, tools, versions)
- Parameter settings and configurations
- Any assumptions or constraints
- Pseudocode or actual code for key components

## Validation and Results
Include ALL experimental details and findings:
- Complete experimental setup and environment
- Datasets used with statistics (size, characteristics, source)
- Baseline methods and comparison approaches
- EVERY numerical result, percentage, metric mentioned
- Tables of results (recreate if shown in paper)
- Statistical analysis and significance tests
- Performance analysis across different conditions
- Ablation studies if performed
- Case studies or examples

## Discussion and Implications
Thorough analysis of the work:
- Interpretation of all key findings
- Comparison with prior work (with specific citations and performance differences)
- Strengths of the approach with evidence
- Limitations and failure cases explicitly acknowledged by authors
- Broader implications for the field
- Potential applications and use cases
- Ethical considerations if mentioned

## Future Work and Research Gaps
[PRESERVE THE AUTHORS' EXACT WORDS] Include everything mentioned about:
- Unresolved challenges and open problems
- Planned extensions or improvements
- Suggested research directions
- Limitations that need addressing
- Potential new applications
- Timeline or priority of future work (if mentioned)
- Required resources or collaborations

## References
[COMPLETE LIST] Include EVERY reference cited in the paper:
Author(s). (Year). Title. Journal/Conference, Volume(Issue), Pages. DOI/URL.

CONTENT PRESERVATION RULES:
1. CODE/ALGORITHMS: Include ALL code snippets, pseudocode, or algorithms
2. TECHNICAL DETAILS: Preserve system architectures, formulas, specifications
3. NUMBERS: Include EVERY numerical result, percentage, metric
4. CITATIONS: Use (Author et al., Year) format for all citations
5. TABLES/LISTS: Recreate tables and structured lists from the paper
6. QUOTES: Use direct quotes for important definitions or findings

Paper content to summarize:
{full_content}

COMPREHENSIVENESS GUIDELINES:
- This summary should be detailed enough for a researcher to understand the paper without reading the original
- Each section should feel complete, not rushed or overly compressed
- Include context and explanations, not just bare facts
- When in doubt, include more detail rather than less
- Use examples and clarifications where helpful
- Connect ideas between sections with transitions

FORMATTING REQUIREMENTS:
- Use clear markdown formatting (##, ###, **, `, ```)
- Include code blocks with proper language specification
- Format tables using markdown syntax
- Use bullet points and numbered lists for clarity
- Bold key terms, concepts, and important findings
- Use blockquotes for important definitions or direct quotes

QUALITY CHECKLIST:
 Every major contribution is explained in detail
 All citations from the paper are included with (Author, Year) format
 All code/algorithms are preserved
 Every numerical result and metric is included
 Technical details are sufficient for understanding/reproduction
 Future work section preserves authors' exact words
 Complete reference list with all papers cited
 Summary reads as a comprehensive research document, not a brief abstract

REMEMBER: The goal is a thorough academic summary that captures the paper's full contribution to the field. Prioritize completeness and clarity over brevity."""

        # Call the appropriate AI service with rate limiting
        if self.provider == "anthropic":
            # Apply rate limiting
            self._apply_rate_limit()

            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
            except Exception as e:
                if "rate_limit" in str(e):
                    print("[WARNING] Rate limit hit, waiting 60 seconds...")
                    time.sleep(60)
                    # Retry once after waiting
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    return response.content[0].text
                else:
                    raise
        elif self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        else:
            raise RuntimeError(f"Unknown provider: {self.provider}")

    def _build_content_for_summary(
        self, sections: list[dict[str, Any]], metadata: dict[str, Any]
    ) -> str:
        """Build structured content for AI summarization."""
        parts = []

        # Add metadata
        if metadata.get("title"):
            parts.append(f"Title: {metadata['title']}")

        if metadata.get("authors"):
            authors_str = ", ".join(metadata["authors"])
            parts.append(f"Authors: {authors_str}")

        parts.append("")  # Empty line

        # Sort sections by importance
        sorted_sections = sorted(
            sections, key=lambda x: x["importance"], reverse=True
        )

        # Add sections
        for section in sorted_sections:
            parts.append(f"## {section['title']}")
            parts.append(section["content"])
            parts.append("")  # Empty line between sections

        return "\n".join(parts)

    def _apply_rate_limit(self):
        """Apply rate limiting to avoid hitting API limits."""
        if self._last_request_time:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_request_interval:
                sleep_time = self._min_request_interval - elapsed
                time.sleep(sleep_time)

        self._last_request_time = time.time()
        self._request_count += 1

    def _create_section_based_summary(
        self,
        sections: list[dict[str, Any]],
        metadata: dict[str, Any],
        target_compression: float,
    ) -> str:
        """Create summary by processing each major section separately."""

        # Section types and their compression ratios
        section_configs = {
            "abstract": {"compression": 0.95, "preserve": True},
            "introduction": {"compression": 0.10, "preserve": True},
            "related work": {"compression": 0.15, "preserve": True},
            "methodology": {"compression": 0.30, "preserve": False},
            "results": {"compression": 0.40, "preserve": False},
            "discussion": {"compression": 0.30, "preserve": False},
            "future work": {"compression": 0.05, "preserve": True},
            "conclusion": {"compression": 0.10, "preserve": True},
            "references": {"compression": 1.0, "preserve": True},
        }

        section_summaries = []

        # Process each section
        for section in sections:
            section_title_lower = section["title"].lower()

            # Find matching section config
            config = None
            for key, cfg in section_configs.items():
                if key in section_title_lower:
                    config = cfg
                    break

            if not config:
                # Default config for unknown sections
                config = {"compression": 0.50, "preserve": False}

            # Create section-specific prompt
            if config["preserve"]:
                prompt = f"""Process this section from an academic paper with MINIMAL compression.

Section: {section["title"]}

INSTRUCTIONS:
- Preserve approximately {int((1 - config["compression"]) * 100)}% of the content
- Keep ALL citations in (Author, Year) format
- Maintain all technical details, numbers, and specific findings
- Only remove redundancy and improve clarity
- Preserve the author's exact wording for important statements

Content:
{section["content"]}

Provide a comprehensive summary that preserves nearly all important information:"""
            else:
                prompt = f"""Summarize this section from an academic paper.

Section: {section["title"]}

INSTRUCTIONS:
- Target approximately {int((1 - config["compression"]) * 100)}% of original length
- Include all key points and findings
- Preserve all citations in (Author, Year) format
- Keep all numerical results and technical details

Content:
{section["content"]}

Provide a clear, comprehensive summary:"""

            # Process with AI
            try:
                if self.provider == "anthropic":
                    self._apply_rate_limit()
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=4096,  # Smaller token limit for sections
                        temperature=self.temperature,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    summary = response.content[0].text
                elif self.provider == "openai":
                    response = self.client.chat.completions.create(
                        model=self.model,
                        max_tokens=4096,
                        temperature=self.temperature,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    summary = response.choices[0].message.content

                section_summaries.append(
                    f"## {section['title']}\n\n{summary}\n\n"
                )

            except Exception as e:
                print(f"Error processing section {section['title']}: {e}")
                # Include original content if processing fails
                section_summaries.append(
                    f"## {section['title']}\n\n{section['content'][:1000]}...\n\n"
                )

        # Combine all sections
        full_summary = "".join(section_summaries)
        return full_summary
