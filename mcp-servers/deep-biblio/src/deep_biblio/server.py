"""MCP server for deep-biblio-tools integration.

This server provides tools for:
- Extracting metadata from PDFs and academic papers
- Converting HTML papers to markdown
- Validating and correcting citations
- Processing bibliographic information
- Converting markdown to LaTeX
- Parsing BibTeX files
"""

import sys
from pathlib import Path
from typing import Any

from loguru import logger
from mcp.server import Server
from mcp.types import TextContent, Tool

# Add deep-biblio-tools to path AFTER standard imports
# Note: deep-biblio-tools uses 'src' as the package name, so we add the parent dir
DEEP_BIBLIO_PATH = Path("/Users/petteri/Dropbox/github-personal/deep-biblio-tools")
if str(DEEP_BIBLIO_PATH) not in sys.path:
    sys.path.insert(0, str(DEEP_BIBLIO_PATH))

# Import deep-biblio-tools modules
MODULES_AVAILABLE = {
    "pdf_parser": False,
    "html_parser": False,
    "arxiv_parser": False,
    "bibtex_parser": False,
    "markdown_parser": False,
    "latex_converter": False,
}

try:
    from src.utils.pdf_parser import PDFParser, is_pdf_url

    MODULES_AVAILABLE["pdf_parser"] = True
except ImportError as e:
    logger.warning(f"PDF parser not available: {e}")

try:
    from src.parsers.extract_complete_paper import parse_sciencedirect_html
    from src.parsers.extract_sciencedirect_paper import (
        extract_full_content as extract_sciencedirect_content,
    )

    MODULES_AVAILABLE["html_parser"] = True
except ImportError as e:
    logger.warning(f"HTML parser not available: {e}")

try:
    from src.parsers.extract_arxiv_paper import (
        extract_full_content as extract_arxiv_content,
    )

    MODULES_AVAILABLE["arxiv_parser"] = True
except ImportError as e:
    logger.warning(f"arXiv parser not available: {e}")

try:
    from src.parsers.bibtex_parser import BibtexParser

    MODULES_AVAILABLE["bibtex_parser"] = True
except ImportError as e:
    logger.warning(f"BibTeX parser not available: {e}")

try:
    from src.parsers.markdown_parser import MarkdownParser

    MODULES_AVAILABLE["markdown_parser"] = True
except ImportError as e:
    logger.warning(f"Markdown parser not available: {e}")

try:
    from src.converters.md_to_latex.converter import MarkdownToLatexConverter

    MODULES_AVAILABLE["latex_converter"] = True
except ImportError as e:
    logger.warning(f"LaTeX converter not available: {e}")

DEEP_BIBLIO_AVAILABLE = any(MODULES_AVAILABLE.values())

# Initialize server
app = Server("deep-biblio")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    tools = [
        Tool(
            name="status",
            description="Check status and available modules in deep-biblio-tools",
            inputSchema={"type": "object", "properties": {}},
        )
    ]

    # PDF extraction tools
    if MODULES_AVAILABLE["pdf_parser"]:
        tools.extend(
            [
                Tool(
                    name="extract_pdf_metadata",
                    description=(
                        "Extract bibliographic metadata from a PDF URL. "
                        "Returns title, authors, year, publisher extracted from PDF."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL to the PDF file",
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "Request timeout (seconds, default: 15)",
                                "default": 15,
                            },
                        },
                        "required": ["url"],
                    },
                ),
                Tool(
                    name="check_pdf_url",
                    description="Check if a URL points to a PDF file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to check"}
                        },
                        "required": ["url"],
                    },
                ),
            ]
        )

    # HTML paper extraction tools
    if MODULES_AVAILABLE["html_parser"]:
        tools.append(
            Tool(
                name="extract_html_paper",
                description=(
                    "Extract paper content from HTML (ScienceDirect, etc.). "
                    "Converts HTML to structured markdown."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "html_path": {
                            "type": "string",
                            "description": "Path to HTML file",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Optional path for markdown output",
                        },
                    },
                    "required": ["html_path"],
                },
            )
        )

    # arXiv paper extraction
    if MODULES_AVAILABLE["arxiv_parser"]:
        tools.append(
            Tool(
                name="extract_arxiv_paper",
                description=(
                    "Extract paper from arXiv HTML. "
                    "Handles arXiv-specific HTML structure."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "html_path": {
                            "type": "string",
                            "description": "Path to arXiv HTML file",
                        }
                    },
                    "required": ["html_path"],
                },
            )
        )

    # BibTeX parsing
    if MODULES_AVAILABLE["bibtex_parser"]:
        tools.extend(
            [
                Tool(
                    name="parse_bibtex",
                    description=(
                        "Parse BibTeX file and return structured entries. "
                        "Useful for citation processing and validation."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "bibtex_path": {
                                "type": "string",
                                "description": "Path to BibTeX file",
                            }
                        },
                        "required": ["bibtex_path"],
                    },
                ),
                Tool(
                    name="validate_bibtex",
                    description=(
                        "Validate BibTeX entries for completeness "
                        "and correct formatting"
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "bibtex_path": {
                                "type": "string",
                                "description": "Path to BibTeX file",
                            }
                        },
                        "required": ["bibtex_path"],
                    },
                ),
            ]
        )

    # Markdown parsing
    if MODULES_AVAILABLE["markdown_parser"]:
        tools.append(
            Tool(
                name="parse_markdown",
                description=(
                    "Parse markdown file into structured format. "
                    "Extracts headings, citations, and content structure."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "markdown_path": {
                            "type": "string",
                            "description": "Path to markdown file",
                        }
                    },
                    "required": ["markdown_path"],
                },
            )
        )

    # LaTeX conversion
    if MODULES_AVAILABLE["latex_converter"]:
        tools.append(
            Tool(
                name="convert_markdown_to_latex",
                description=(
                    "Convert academic markdown to arXiv-ready LaTeX. "
                    "Generates proper citations, BibTeX, and formatting."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "markdown_path": {
                            "type": "string",
                            "description": "Path to markdown file",
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Output directory for LaTeX files",
                        },
                        "single_column": {
                            "type": "boolean",
                            "description": "Use single-column layout (default: false)",
                            "default": False,
                        },
                        "author": {
                            "type": "string",
                            "description": "Author name for the paper",
                        },
                    },
                    "required": ["markdown_path", "output_dir"],
                },
            )
        )

    # Manuscript-to-arXiv tool (always available)
    tools.append(
        Tool(
            name="manuscript_to_arxiv",
            description=(
                "Complete pipeline: markdown → arXiv-ready LaTeX with Zotero citations. "
                "Extracts citations, matches against Zotero JSON, generates BibTeX with "
                "DOI/arXiv permalinks, reports missing citations, converts to LaTeX."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "markdown_path": {
                        "type": "string",
                        "description": "Path to markdown manuscript",
                    },
                    "zotero_json_path": {
                        "type": "string",
                        "description": "Path to Zotero CSL JSON export",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Output directory for LaTeX + BibTeX files",
                    },
                    "author": {
                        "type": "string",
                        "description": "Author name for the paper",
                    },
                    "single_column": {
                        "type": "boolean",
                        "description": "Use single-column layout (default: false)",
                        "default": False,
                    },
                },
                "required": [
                    "markdown_path",
                    "zotero_json_path",
                    "output_dir",
                    "author",
                ],
            },
        )
    )

    return tools


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    if name == "status":
        # Format status report
        result = ["## deep-biblio-tools MCP Server Status\n"]
        result.append(f"**Path**: {DEEP_BIBLIO_PATH}")
        result.append(
            f"**Overall Status**: {'[PASS] Available' if DEEP_BIBLIO_AVAILABLE else '[FAIL] Not Available'}\n"
        )
        result.append("### Module Status:")
        for module, available in MODULES_AVAILABLE.items():
            status_icon = "[PASS]" if available else "[FAIL]"
            result.append(f"- {status_icon} **{module}**: {available}")

        return [TextContent(type="text", text="\n".join(result))]

    # Check if required module is available for the requested tool
    required_module = None
    if name in ["extract_pdf_metadata", "check_pdf_url"]:
        required_module = "pdf_parser"
    elif name == "extract_html_paper":
        required_module = "html_parser"
    elif name == "extract_arxiv_paper":
        required_module = "arxiv_parser"
    elif name in ["parse_bibtex", "validate_bibtex"]:
        required_module = "bibtex_parser"
    elif name == "parse_markdown":
        required_module = "markdown_parser"
    elif name == "convert_markdown_to_latex":
        required_module = "latex_converter"

    if required_module and not MODULES_AVAILABLE.get(required_module, False):
        return [
            TextContent(
                type="text",
                text=f"[FAIL] Module '{required_module}' not available for tool '{name}'",
            )
        ]

    # PDF tools
    if name == "extract_pdf_metadata":
        url = arguments["url"]
        timeout = arguments.get("timeout", 15)

        logger.info(f"Extracting metadata from PDF: {url}")

        try:
            parser = PDFParser(timeout=timeout)
            metadata = parser.extract_pdf_info(url)

            if metadata:
                # Format metadata as readable text
                result = ["[PASS] Successfully extracted PDF metadata:\n"]

                if "title" in metadata:
                    result.append(f"[FILE] Title: {metadata['title']}")
                if "authors" in metadata:
                    authors_str = ", ".join(metadata["authors"])
                    result.append(f"[USER] Authors: {authors_str}")
                if "year" in metadata:
                    result.append(f" Year: {metadata['year']}")
                if "publisher" in metadata:
                    result.append(f" Publisher: {metadata['publisher']}")
                if "source_url" in metadata:
                    result.append(f"[LINK] Source: {metadata['source_url']}")

                # Add raw metadata as JSON
                result.append("\n[CLIPBOARD] Raw metadata (JSON):")
                import json

                result.append(json.dumps(metadata, indent=2))

                return [TextContent(type="text", text="\n".join(result))]
            else:
                return [
                    TextContent(
                        type="text",
                        text=(
                            f"[WARNING]  Could not extract metadata from PDF: {url}\n"
                            "This could be due to:\n"
                            "- PDF is behind authentication\n"
                            "- PDF format is not parseable\n"
                            "- Network connectivity issues"
                        ),
                    )
                ]

        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"[FAIL] Error extracting PDF metadata: {str(e)}",
                )
            ]

    elif name == "check_pdf_url":
        url = arguments["url"]
        is_pdf = is_pdf_url(url)

        return [
            TextContent(
                type="text",
                text=(
                    f"{'[PASS]' if is_pdf else '[FAIL]'} URL "
                    f"{'is' if is_pdf else 'is not'} a PDF: {url}"
                ),
            )
        ]

    # HTML paper extraction
    elif name == "extract_html_paper":
        html_path = Path(arguments["html_path"])
        output_path = arguments.get("output_path")

        try:
            logger.info(f"Extracting paper from HTML: {html_path}")

            # Try different HTML extraction methods
            if "sciencedirect" in str(html_path).lower():
                content = extract_sciencedirect_content(str(html_path))
            else:
                content = parse_sciencedirect_html(str(html_path))

            if output_path:
                output_path = Path(output_path)
                output_path.write_text(content)
                return [
                    TextContent(
                        type="text",
                        text=f"[PASS] Extracted paper to: {output_path}\n\nLength: {len(content)} characters",
                    )
                ]
            else:
                return [
                    TextContent(
                        type="text",
                        text=f"[PASS] Extracted paper:\n\n{content[:1000]}...",
                    )
                ]

        except Exception as e:
            logger.error(f"Error extracting HTML paper: {e}")
            return [
                TextContent(
                    type="text", text=f"[FAIL] Error extracting HTML paper: {str(e)}"
                )
            ]

    # arXiv paper extraction
    elif name == "extract_arxiv_paper":
        html_path = Path(arguments["html_path"])

        try:
            logger.info(f"Extracting arXiv paper from: {html_path}")
            content = extract_arxiv_content(str(html_path))

            return [
                TextContent(
                    type="text",
                    text=f"[PASS] Extracted arXiv paper:\n\n{content[:1000]}...",
                )
            ]

        except Exception as e:
            logger.error(f"Error extracting arXiv paper: {e}")
            return [
                TextContent(
                    type="text", text=f"[FAIL] Error extracting arXiv paper: {str(e)}"
                )
            ]

    # BibTeX parsing
    elif name == "parse_bibtex":
        bibtex_path = Path(arguments["bibtex_path"])

        try:
            logger.info(f"Parsing BibTeX file: {bibtex_path}")
            parser = BibtexParser()
            entries = parser.parse_file(str(bibtex_path))

            result = [f"[PASS] Parsed {len(entries)} BibTeX entries:\n"]
            for i, entry in enumerate(entries[:10], 1):  # Show first 10
                entry_type = getattr(entry, "entry_type", "unknown")
                cite_key = getattr(entry, "cite_key", "no_key")
                title = getattr(entry, "title", "No title")
                result.append(f"{i}. [{entry_type}] {cite_key}: {title[:50]}...")

            if len(entries) > 10:
                result.append(f"\n... and {len(entries) - 10} more entries")

            # Add JSON representation
            result.append("\n[CLIPBOARD] Raw data available for processing")

            return [TextContent(type="text", text="\n".join(result))]

        except Exception as e:
            logger.error(f"Error parsing BibTeX: {e}")
            return [
                TextContent(type="text", text=f"[FAIL] Error parsing BibTeX: {str(e)}")
            ]

    elif name == "validate_bibtex":
        bibtex_path = Path(arguments["bibtex_path"])

        try:
            logger.info(f"Validating BibTeX file: {bibtex_path}")
            parser = BibtexParser()
            entries = parser.parse_file(str(bibtex_path))

            # Basic validation
            issues = []
            for entry in entries:
                cite_key = getattr(entry, "cite_key", None)
                if not cite_key:
                    issues.append("Entry missing cite key")

                title = getattr(entry, "title", None)
                if not title:
                    issues.append(f"{cite_key}: Missing title")

                author = getattr(entry, "author", None)
                if not author:
                    issues.append(f"{cite_key}: Missing author")

                year = getattr(entry, "year", None)
                if not year:
                    issues.append(f"{cite_key}: Missing year")

            if issues:
                return [
                    TextContent(
                        type="text",
                        text=f"[WARNING]  Found {len(issues)} validation issues:\n"
                        + "\n".join(f"- {issue}" for issue in issues[:20]),
                    )
                ]
            else:
                return [
                    TextContent(
                        type="text",
                        text=f"[PASS] All {len(entries)} BibTeX entries are valid!",
                    )
                ]

        except Exception as e:
            logger.error(f"Error validating BibTeX: {e}")
            return [
                TextContent(
                    type="text", text=f"[FAIL] Error validating BibTeX: {str(e)}"
                )
            ]

    # Markdown parsing
    elif name == "parse_markdown":
        markdown_path = Path(arguments["markdown_path"])

        try:
            logger.info(f"Parsing markdown file: {markdown_path}")
            parser = MarkdownParser()
            doc = parser.parse_file(str(markdown_path))

            result = ["[PASS] Parsed markdown document:\n"]
            result.append(f"[FILE] Title: {getattr(doc, 'title', 'No title')}")
            result.append(f"[INFO] Sections: {len(getattr(doc, 'sections', []))}")
            result.append(f"[DOCS] Citations: {len(getattr(doc, 'citations', []))}")

            # Show section structure
            sections = getattr(doc, "sections", [])
            if sections:
                result.append("\n## Document Structure:")
                for section in sections[:5]:
                    level = getattr(section, "level", 1)
                    title = getattr(section, "title", "Untitled")
                    result.append(f"{'  ' * (level - 1)}- {title}")

            return [TextContent(type="text", text="\n".join(result))]

        except Exception as e:
            logger.error(f"Error parsing markdown: {e}")
            return [
                TextContent(
                    type="text", text=f"[FAIL] Error parsing markdown: {str(e)}"
                )
            ]

    # LaTeX conversion
    elif name == "convert_markdown_to_latex":
        markdown_path = Path(arguments["markdown_path"])
        output_dir = Path(arguments["output_dir"])
        single_column = arguments.get("single_column", False)
        author = arguments.get("author", "Anonymous")

        try:
            logger.info(f"Converting {markdown_path} to LaTeX")
            output_dir.mkdir(parents=True, exist_ok=True)

            converter = MarkdownToLatexConverter(
                markdown_file=str(markdown_path),
                output_dir=str(output_dir),
                single_column=single_column,
                author=author,
            )

            converter.convert()

            # List generated files
            generated_files = list(output_dir.glob("*"))
            result = [f"[PASS] Successfully converted to LaTeX in: {output_dir}\n"]
            result.append("Generated files:")
            for file in generated_files:
                result.append(f"- {file.name}")

            return [TextContent(type="text", text="\n".join(result))]

        except Exception as e:
            logger.error(f"Error converting to LaTeX: {e}")
            return [
                TextContent(
                    type="text", text=f"[FAIL] Error converting to LaTeX: {str(e)}"
                )
            ]

    # Manuscript-to-arXiv converter
    elif name == "manuscript_to_arxiv":
        from deep_biblio.arxiv_converter import create_arxiv_package

        markdown_path = Path(arguments["markdown_path"])
        zotero_json_path = Path(arguments["zotero_json_path"])
        output_dir = Path(arguments["output_dir"])
        author = arguments["author"]
        single_column = arguments.get("single_column", False)

        try:
            logger.info(f"Converting {markdown_path.name} to arXiv package")

            result = create_arxiv_package(
                markdown_path=markdown_path,
                zotero_json_path=zotero_json_path,
                output_dir=output_dir,
                author=author,
                single_column=single_column,
            )

            # Format result
            output = [
                "[PASS] Manuscript-to-arXiv conversion complete!\n",
                f"**Manuscript**: {markdown_path.name}",
                f"**Output**: {output_dir}\n",
                "### Citation Matching:",
                f"- [PASS] **Matched**: {result['matched_count']}/{result['total_citations']} citations",
                f"- {'[FAIL]' if result['missing_count'] > 0 else '[PASS]'} **Missing**: {result['missing_count']} citations\n",
            ]

            # Report missing citations
            if result["missing_count"] > 0:
                output.append(
                    "### [WARNING]  Missing Citations (not found in Zotero):\n"
                )
                for i, cite in enumerate(result["missing_citations"], 1):
                    output.append(
                        f"{i}. **{cite['author']}, {cite['year']}**\n"
                        f"   - URL: {cite['url']}\n"
                        f"   - Line: {cite['line_number']}"
                    )
                output.append(
                    "\n**Action Required**: Add these citations to Zotero or "
                    "create manual BibTeX entries"
                )

            # Report generated files
            output.append("\n### Generated Files:")
            output.append(f"- [FILE] BibTeX: `{result['bibtex_path']}`")

            # Warnings
            if result.get("warnings"):
                output.append("\n### [WARNING]  Warnings:")
                for warn in result["warnings"]:
                    output.append(f"- {warn}")

            return [TextContent(type="text", text="\n".join(output))]

        except Exception as e:
            logger.error(f"Error in manuscript-to-arxiv: {e}", exc_info=True)
            return [
                TextContent(
                    type="text",
                    text=f"[FAIL] Error converting manuscript to arXiv: {str(e)}",
                )
            ]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


def main() -> None:
    """Main entry point for the MCP server."""
    import asyncio

    logger.info("Starting deep-biblio MCP server...")
    logger.info(f"Deep-biblio-tools path: {DEEP_BIBLIO_PATH}")
    logger.info(f"Deep-biblio-tools available: {DEEP_BIBLIO_AVAILABLE}")

    asyncio.run(app.run())


if __name__ == "__main__":
    main()
