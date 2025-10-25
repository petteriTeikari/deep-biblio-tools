"""Academic rephrasing functionality for BIM and scan-to-BIM contextualization."""

import os
import time
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


class AcademicRephraser:
    """Academic paper rephrasing with BIM/scan-to-BIM contextualization."""

    def __init__(self, config: dict[str, Any] = None):
        self._last_request_time = None
        self._min_request_interval = 1.0

        import yaml

        # Load config
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

        # Initialize AI client
        if self.provider == "anthropic" and ANTHROPIC_AVAILABLE:
            api_key = self.ai_config.get("anthropic", {}).get("api_key")
            if not api_key:
                api_key = os.getenv("ANTHROPIC_API_KEY")
            self.client = Anthropic(api_key=api_key)
            self.model = self.ai_config.get("anthropic", {}).get(
                "model", "claude-3-5-sonnet-20241022"
            )
            self.temperature = 0.3  # Lower for more faithful rephrasing
            self.max_tokens = 8192
        elif self.provider == "openai" and OPENAI_AVAILABLE:
            api_key = self.ai_config.get("openai", {}).get("api_key")
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
            self.client = OpenAI(api_key=api_key)
            self.model = self.ai_config.get("openai", {}).get("model", "gpt-4o")
            self.temperature = 0.3
            self.max_tokens = 8192
        else:
            raise RuntimeError(f"AI provider '{self.provider}' not available")

    def rephrase_for_bim_context(
        self,
        sections: list[dict[str, Any]],
        metadata: dict[str, Any],
        preserve_ratio: float = 0.85,  # Preserve 85% of content by default
    ) -> str:
        """Rephrase paper content for BIM/scan-to-BIM context while preserving most content."""

        # Process sections with preservation-focused approach
        section_results = []

        # Define section handling with emphasis on research gaps and future work
        section_priorities = {
            "future work": 0.95,  # Preserve 95% of future work
            "research gaps": 0.95,
            "limitations": 0.90,
            "discussion": 0.90,
            "results": 0.85,
            "methodology": 0.85,
            "introduction": 0.80,
            "related work": 0.80,
            "abstract": 0.75,
            "conclusion": 0.85,
        }

        for section in sections:
            section_title_lower = section["title"].lower()

            # Determine preservation ratio for this section
            preservation = preserve_ratio
            for key, ratio in section_priorities.items():
                if key in section_title_lower:
                    preservation = ratio
                    break

            # Special handling for future work and research gaps
            is_critical_section = any(
                term in section_title_lower
                for term in [
                    "future",
                    "gap",
                    "limitation",
                    "challenge",
                    "direction",
                ]
            )

            rephrased = self._rephrase_section(
                section, preservation, is_critical_section, metadata
            )

            section_results.append(rephrased)

        # Combine all sections
        return "\n\n".join(section_results)

    def _rephrase_section(
        self,
        section: dict[str, Any],
        preservation_ratio: float,
        is_critical: bool,
        metadata: dict[str, Any],
    ) -> str:
        """Rephrase a single section with BIM/scan-to-BIM contextualization."""

        # Build the prompt
        if is_critical:
            prompt = f"""Rephrase this section from an academic paper for a Building Information Modeling (BIM) and scan-to-BIM research context. This is a CRITICAL section containing research gaps, future directions, or limitations - preserve ALL content with enhanced clarity.

Section: {section["title"]}

CRITICAL PRESERVATION REQUIREMENTS:
- Preserve 95-100% of the original content and ideas
- Maintain ALL specific research gaps, challenges, and future directions mentioned
- Keep EVERY limitation, constraint, or unresolved issue
- Preserve the authors' exact terminology for technical concepts
- Maintain all temporal references (e.g., "currently", "at present", "future work")
- Keep all conditional statements (e.g., "could", "might", "potentially")

REPHRASING GUIDELINES:
1. Academic Writing Style:
   - Maintain formal, scholarly tone
   - Use complete sentences and paragraphs (avoid excessive bullet points)
   - Ensure logical flow between ideas
   - Use appropriate academic transitions

2. BIM/Scan-to-BIM Contextualization:
   - Draw connections to building modeling, point cloud processing, or construction workflows where relevant
   - Highlight implications for digital twin creation, as-built modeling, or facility management
   - Note potential applications in architectural, engineering, and construction (AEC) domains
   - Connect UAV/drone capabilities to building inspection or site monitoring

3. Citation Preservation:
   - Keep ALL inline citations in (Author, Year) format
   - Maintain citation context and relationships
   - Preserve direct quotes with proper attribution

4. Technical Detail Preservation:
   - Keep ALL numerical values, percentages, metrics
   - Maintain technical specifications and parameters
   - Preserve algorithm names, system components, and methodologies
   - Keep all comparisons and benchmarks

5. Research Gap and Future Work Emphasis:
   - Use clear topic sentences to highlight each gap or future direction
   - Expand on implications of each limitation
   - Connect gaps to BIM/scan-to-BIM challenges
   - Preserve priority or timeline information if mentioned

Original Content:
{section["content"]}

Provide the rephrased section that preserves ALL original insights while enhancing clarity and BIM/scan-to-BIM relevance:"""
        else:
            prompt = f"""Rephrase this section from an academic paper for a Building Information Modeling (BIM) and scan-to-BIM research context. Preserve approximately {int(preservation_ratio * 100)}% of the original content while improving clarity and flow.

Section: {section["title"]}

REPHRASING GUIDELINES:
1. Content Preservation ({int(preservation_ratio * 100)}%):
   - Maintain all key concepts, findings, and technical details
   - Keep numerical results, metrics, and comparisons
   - Preserve methodology descriptions and experimental setups
   - Retain all citations in (Author, Year) format

2. Academic Writing Enhancement:
   - Write in formal, scholarly prose with complete paragraphs
   - Ensure logical transitions between ideas
   - Minimize bullet points in favor of flowing text
   - Maintain objective, third-person perspective

3. BIM/Scan-to-BIM Contextualization:
   - Connect concepts to building information modeling where applicable
   - Highlight relevance to point cloud processing and 3D reconstruction
   - Note applications in construction, architecture, or facility management
   - Draw parallels to digital twin creation and as-built documentation

4. Technical Clarity:
   - Define technical terms on first use
   - Explain complex concepts without oversimplification
   - Maintain precision in technical descriptions
   - Preserve all algorithm names and system architectures

5. Citation and Reference Handling:
   - Keep all inline citations as (Author, Year)
   - Maintain citation clustering where multiple sources are cited together
   - Preserve the relationship between claims and their supporting citations

Original Content:
{section["content"]}

Provide the rephrased section with improved academic flow and BIM/scan-to-BIM context:"""

        # Apply rate limiting
        self._apply_rate_limit()

        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
                rephrased = response.content[0].text
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
                rephrased = response.choices[0].message.content

            # Format the section
            return f"## {section['title']}\n\n{rephrased}"

        except Exception as e:
            print(f"Error rephrasing section {section['title']}: {e}")
            # Return original with minimal formatting
            return f"## {section['title']}\n\n{section['content']}"

    def _apply_rate_limit(self):
        """Apply rate limiting to avoid API limits."""
        if self._last_request_time:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_request_interval:
                sleep_time = self._min_request_interval - elapsed
                time.sleep(sleep_time)

        self._last_request_time = time.time()

    def create_comprehensive_rephrase(
        self,
        sections: list[dict[str, Any]],
        metadata: dict[str, Any],
        citations: list[tuple[str, str]],
        references: list[str],
    ) -> str:
        """Create a comprehensive rephrased document with full context preservation."""

        # Build header with metadata
        header_parts = []

        if metadata.get("title"):
            header_parts.append(f"# {metadata['title']}")

        if metadata.get("authors"):
            authors = ", ".join(metadata["authors"])
            header_parts.append(f"\n**Authors:** {authors}")

        if metadata.get("year"):
            header_parts.append(f"**Year:** {metadata['year']}")

        if metadata.get("venue"):
            header_parts.append(f"**Venue:** {metadata['venue']}")

        if metadata.get("doi"):
            header_parts.append(f"**DOI:** {metadata['doi']}")

        header_parts.append("\n---\n")

        # Create comprehensive prompt for the entire document
        full_content = self._build_full_content(sections)

        prompt = f"""Create a comprehensive academic rephrase of this paper for Building Information Modeling (BIM) and scan-to-BIM research context. This rephrased version will serve as context for future LLM analysis and academic review articles.

CORE OBJECTIVE: Preserve 85-95% of the original content while improving clarity, flow, and BIM/scan-to-BIM contextualization.

CRITICAL PRESERVATION AREAS:
1. Research Gaps and Future Directions (preserve 95-100%):
   - Keep ALL mentions of unresolved challenges
   - Preserve every suggested future research direction
   - Maintain all limitations and their implications
   - Keep temporal markers and priority indications

2. Technical Content (preserve 90%):
   - All algorithms, methodologies, and systems
   - Every numerical result and comparison
   - Complete experimental setups and parameters
   - Full system architectures and workflows

3. Academic Discourse (preserve 85%):
   - Theoretical frameworks and contributions
   - Literature review insights and comparisons
   - Discussion of implications and significance
   - Critical analysis and interpretations

REPHRASING APPROACH:
1. Structure:
   - Maintain clear section organization
   - Use descriptive headings and subheadings
   - Ensure smooth transitions between sections
   - Create cohesive narrative flow

2. Academic Style:
   - Write in formal, scholarly prose
   - Use complete paragraphs rather than bullet lists
   - Maintain objective, evidence-based tone
   - Include appropriate hedging for uncertain claims

3. BIM/Scan-to-BIM Integration:
   - Connect UAV/drone capabilities to building inspection
   - Relate computer vision techniques to point cloud processing
   - Link semantic understanding to BIM object classification
   - Draw parallels to as-built documentation workflows
   - Highlight applications in construction monitoring

4. Citation Handling:
   - Preserve ALL citations as inline (Author, Year) format
   - Maintain citation context and clustering
   - Keep direct quotes with proper attribution
   - Ensure all claims remain properly supported

5. Enhanced Clarity:
   - Define technical terms within context
   - Expand acronyms on first use
   - Clarify complex relationships
   - Add transitional phrases for better flow

Paper Content:
{full_content}

Original Citations: {len(citations)} inline citations
Original References: {len(references)} references

Create the rephrased document maintaining academic rigor while enhancing readability and BIM/scan-to-BIM relevance. Include ALL sections from the original paper:"""

        # Process with AI
        self._apply_rate_limit()

        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
                rephrased_content = response.content[0].text
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
                rephrased_content = response.choices[0].message.content

            # Combine header, rephrased content, and references
            final_parts = [
                "\n".join(header_parts),
                rephrased_content,
                "\n\n## References\n",
            ]

            # Add formatted references
            for ref in references:
                final_parts.append(f"\n{ref}")

            return "\n".join(final_parts)

        except Exception as e:
            print(f"Error in comprehensive rephrase: {e}")
            # Fallback to section-by-section processing
            return self.rephrase_for_bim_context(sections, metadata)

    def _build_full_content(self, sections: list[dict[str, Any]]) -> str:
        """Build the full content from sections."""
        parts = []
        for section in sections:
            parts.append(f"## {section['title']}\n\n{section['content']}\n")
        return "\n".join(parts)
