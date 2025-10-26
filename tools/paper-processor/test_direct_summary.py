#!/usr/bin/env python3
"""
Test direct summarization with explicit length requirements.
"""

from pathlib import Path

from anthropic import Anthropic

# Set up API
# API key should be provided via environment variable ANTHROPIC_API_KEY
client = Anthropic()  # Uses ANTHROPIC_API_KEY from environment

# Read the extracted content
extracted_file = Path(
    "/home/petteri/Dropbox/LABs/github-personal/papers/scan2bim/biblio/bim/extracted/2D–3D fusion approach for improved point cloud segmentation - ScienceDirect.md"
)
content = extracted_file.read_text(encoding="utf-8")
original_words = len(content.split())

print(f"Original content: {original_words} words")

# Target 15% compression (middle of 10-25% range)
target_words = int(original_words * 0.15)
print(f"Target summary: {target_words} words")

# Create a very explicit prompt
prompt = f"""I need you to create a comprehensive academic summary of exactly {target_words} words.

CRITICAL REQUIREMENTS:
1. The summary MUST be exactly {target_words} words (count them!)
2. This is approximately 15% of the original {original_words}-word paper
3. Include all major sections with substantial detail
4. Preserve technical details, methodologies, results, and conclusions

The paper to summarize:

{content}

IMPORTANT: Your response must be EXACTLY {target_words} words. Start with a title and then provide the summary. Count carefully and adjust your writing to meet this exact word count."""

# Call Claude
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=8000,
    temperature=0.3,
    messages=[{"role": "user", "content": prompt}],
)

summary = response.content[0].text
summary_words = len(summary.split())

print(f"\nGenerated summary: {summary_words} words")
print(f"Compression ratio: {(summary_words / original_words) * 100:.1f}%")
print(
    f"Target achieved: {'YES' if abs(summary_words - target_words) < 50 else 'NO'}"
)

# Save the test summary
output_file = Path("test_direct_summary.md")
output_file.write_text(summary, encoding="utf-8")
print(f"\nSummary saved to: {output_file}")

# Show first 500 chars
print("\nFirst 500 characters of summary:")
print(summary[:500] + "...")
