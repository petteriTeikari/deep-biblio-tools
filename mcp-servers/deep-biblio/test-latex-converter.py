#!/usr/bin/env python3
"""Test the markdown-to-LaTeX converter with regex-free codebase."""

from pathlib import Path

from loguru import logger

from src.converters import MarkdownToLatexConverter

# Configure paths
MANUSCRIPT_PATH = Path(
    "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/paper-manuscripts/mcp-review/mcp-draft-refined-v3.md"
)
OUTPUT_DIR = Path(
    "/Users/petteri/Dropbox/LABs/open-mode/github/dpp-fashion/mcp-servers/deep-biblio/test_output"
)

logger.info("=" * 80)
logger.info("TESTING LATEX CONVERTER (REGEX-FREE CODEBASE)")
logger.info("=" * 80)

# Read markdown
logger.info(f"Reading manuscript: {MANUSCRIPT_PATH}")
with open(MANUSCRIPT_PATH, encoding="utf-8") as f:
    markdown_content = f.read()

logger.info(
    f"Manuscript size: {len(markdown_content)} characters ({len(markdown_content) / 1024:.1f} KB)"
)

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Convert
logger.info("Converting to LaTeX...")
converter = MarkdownToLatexConverter(
    output_dir=OUTPUT_DIR,
    use_cache=False,
)

# Perform conversion
result = converter.convert(
    markdown_content=markdown_content, output_filename="mcp-draft-refined-v3.tex"
)

# Check output
tex_file = OUTPUT_DIR / "mcp-draft-refined-v3.tex"
if tex_file.exists():
    tex_size = tex_file.stat().st_size
    logger.success(f"[PASS] LaTeX file generated: {tex_file}")
    logger.success(f"   Size: {tex_size} bytes ({tex_size / 1024:.1f} KB)")

    # Check for preamble leak
    with open(tex_file, encoding="utf-8") as f:
        tex_content = f.read()

    # Find document body
    begin_doc = tex_content.find(r"\begin{document}")
    if begin_doc != -1:
        body = tex_content[
            begin_doc : begin_doc + 2000
        ]  # Check first 2000 chars of body
        preamble_commands = [
            r"\usepackage",
            r"\documentclass",
            r"\setcounter",
            r"\ifPDFTeX",
        ]

        leaked = []
        for cmd in preamble_commands:
            if cmd in body:
                leaked.append(cmd)

        if leaked:
            logger.error(f"[FAIL] PREAMBLE LEAK DETECTED: {leaked}")
        else:
            logger.success("[PASS] No preamble commands found in document body")

    # Compare with expected size
    markdown_size_kb = len(markdown_content) / 1024
    tex_size_kb = tex_size / 1024
    ratio = tex_size_kb / markdown_size_kb

    logger.info("\n[STATS] SIZE COMPARISON:")
    logger.info(f"   Markdown: {markdown_size_kb:.1f} KB")
    logger.info(f"   LaTeX: {tex_size_kb:.1f} KB")
    logger.info(f"   Ratio: {ratio:.1f}x")

    if tex_size_kb > 500:
        logger.warning(
            f"[WARNING]  LaTeX file is large ({tex_size_kb:.1f} KB > 500 KB)"
        )
    else:
        logger.success("[PASS] LaTeX file size is reasonable")
else:
    logger.error(f"[FAIL] LaTeX file not generated at {tex_file}")

logger.info("\n" + "=" * 80)
logger.info("TEST COMPLETE")
logger.info("=" * 80)
