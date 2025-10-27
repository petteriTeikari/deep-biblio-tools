"""Citation Quality MCP Server.

Provides comprehensive citation quality auditing tools for academic manuscripts.
Integrates with existing UnifiedCitationExtractor and CitationManager components.
"""

import asyncio
import json
import logging
from typing import Any

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    EmbeddedResource,
    ImageContent,
    TextContent,
    Tool,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server instance
server = Server("citation-quality")


# Tool definitions
AUDIT_MARKDOWN_CITATIONS = Tool(
    name="audit_markdown_citations",
    description=(
        "Comprehensive audit of all citations in a markdown file. "
        "Checks citation URLs, validates against Zotero, verifies metadata, "
        "and optionally checks link health. Returns detailed issues and recommendations."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the markdown file to audit",
            },
            "zotero_collection": {
                "type": "string",
                "description": "Zotero collection name (defaults to ZOTERO_COLLECTION env var)",
                "default": None,
            },
            "check_link_health": {
                "type": "boolean",
                "description": "Whether to check if HTTP links are reachable",
                "default": False,
            },
            "validate_metadata": {
                "type": "boolean",
                "description": "Whether to validate metadata against Zotero",
                "default": True,
            },
        },
        "required": ["file_path"],
    },
)

CHECK_CITATION_URL_QUALITY = Tool(
    name="check_citation_url_quality",
    description=(
        "Validate a single citation URL to determine if it points to a proper "
        "academic paper or a problematic source (project page, personal site, etc.). "
        "Returns validation status and suggestions for better URLs."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to validate"},
            "citation_text": {
                "type": "string",
                "description": "The citation text (e.g., 'Author et al., 2024')",
            },
        },
        "required": ["url", "citation_text"],
    },
)

VERIFY_ZOTERO_MATCH = Tool(
    name="verify_zotero_match",
    description=(
        "Check if a citation exists in Zotero and validate its metadata. "
        "Returns Better BibTeX key and validates author names and year."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The citation URL"},
            "citation_text": {
                "type": "string",
                "description": "The citation text (e.g., 'Cao et al., 2024')",
            },
            "collection": {
                "type": "string",
                "description": "Zotero collection name",
                "default": None,
            },
        },
        "required": ["url", "citation_text"],
    },
)

CHECK_LINK_HEALTH = Tool(
    name="check_link_health",
    description=(
        "Verify that HTTP(S) links are reachable. "
        "Performs HEAD requests to check status codes."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of URLs to check",
            }
        },
        "required": ["urls"],
    },
)

VALIDATE_BIBTEX_KEYS = Tool(
    name="validate_bibtex_keys",
    description=(
        "Check if BibTeX keys match Better BibTeX format from Zotero. "
        "Identifies citations using generated short keys instead of proper keys."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "citations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "current_key": {"type": "string"},
                    },
                    "required": ["url", "current_key"],
                },
                "description": "List of citations with their current BibTeX keys",
            },
            "collection": {
                "type": "string",
                "description": "Zotero collection name",
                "default": None,
            },
        },
        "required": ["citations"],
    },
)


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List all available citation quality tools."""
    return [
        AUDIT_MARKDOWN_CITATIONS,
        CHECK_CITATION_URL_QUALITY,
        VERIFY_ZOTERO_MATCH,
        CHECK_LINK_HEALTH,
        VALIDATE_BIBTEX_KEYS,
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool execution requests."""
    if arguments is None:
        arguments = {}

    try:
        if name == "audit_markdown_citations":
            from mcp_servers.citation_quality.tools.audit import (
                audit_markdown_citations,
            )

            result = await audit_markdown_citations(**arguments)

        elif name == "check_citation_url_quality":
            from mcp_servers.citation_quality.tools.url_quality import (
                check_citation_url_quality,
            )

            result = await check_citation_url_quality(**arguments)

        elif name == "verify_zotero_match":
            from mcp_servers.citation_quality.tools.zotero_match import (
                verify_zotero_match,
            )

            result = await verify_zotero_match(**arguments)

        elif name == "check_link_health":
            from mcp_servers.citation_quality.tools.link_health import (
                check_link_health,
            )

            result = await check_link_health(**arguments)

        elif name == "validate_bibtex_keys":
            from mcp_servers.citation_quality.tools.bibtex_keys import (
                validate_bibtex_keys,
            )

            result = await validate_bibtex_keys(**arguments)

        else:
            raise ValueError(f"Unknown tool: {name}")

        # Return result as JSON text content
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.exception(f"Error executing tool {name}")
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": str(e), "tool": name}, indent=2),
            )
        ]


async def main():
    """Run the MCP server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="citation-quality",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
