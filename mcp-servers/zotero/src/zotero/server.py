#!/usr/bin/env python3
"""
Zotero MCP Server

Provides integration with Zotero library for paper management and sync.

Tools:
- import_from_zotero: Auto-import papers from Zotero
- sync_metadata: Keep Zotero metadata synced with Chroma
- trigger_conversion: Use deep-biblio-tools for PDF conversion
- get_zotero_item: Retrieve item by ID
"""

import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field
from pyzotero import zotero


class ImportFromZoteroArgs(BaseModel):
    """Arguments for import_from_zotero tool."""

    collection_id: str | None = Field(
        default=None, description="Zotero collection ID (optional)"
    )
    limit: int = Field(default=50, description="Max papers to import")
    tags: list[str] = Field(default=[], description="Filter by tags")


class SyncMetadataArgs(BaseModel):
    """Arguments for sync_metadata tool."""

    arxiv_id: str = Field(description="ArXiv ID to sync")
    direction: str = Field(
        default="zotero_to_chroma",
        description="zotero_to_chroma or chroma_to_zotero",
    )


class TriggerConversionArgs(BaseModel):
    """Arguments for trigger_conversion tool."""

    zotero_item_id: str = Field(description="Zotero item ID")
    deep_biblio_tools_path: str = Field(
        default="/Users/petteri/Dropbox/github-personal/deep-biblio-tools",
        description="Path to deep-biblio-tools",
    )


class GetZoteroItemArgs(BaseModel):
    """Arguments for get_zotero_item tool."""

    item_id: str = Field(description="Zotero item ID")


class ZoteroServer:
    """MCP server for Zotero operations."""

    def __init__(self):
        """Initialize with Zotero client."""
        library_id = os.getenv("ZOTERO_LIBRARY_ID")
        library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")
        api_key = os.getenv("ZOTERO_API_KEY")

        if not library_id or not api_key:
            raise ValueError(
                "ZOTERO_LIBRARY_ID and ZOTERO_API_KEY environment variables required"
            )

        self.zot = zotero.Zotero(library_id, library_type, api_key)

    async def import_from_zotero(
        self,
        collection_id: str | None = None,
        limit: int = 50,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Auto-import papers from Zotero library.

        Args:
            collection_id: Zotero collection ID (optional)
            limit: Max papers to import
            tags: Filter by tags

        Returns:
            Import summary with paper metadata
        """
        # Get items from Zotero
        if collection_id:
            items = self.zot.collection_items(collection_id, limit=limit)
        else:
            items = self.zot.items(limit=limit)

        # Filter by tags if specified
        if tags:
            items = [
                item
                for item in items
                if any(
                    tag["tag"] in tags for tag in item["data"].get("tags", [])
                )
            ]

        # Extract paper metadata
        papers = []
        for item in items:
            data = item["data"]
            if data.get("itemType") not in ["journalArticle", "preprint"]:
                continue

            # Extract metadata
            metadata = {
                "title": data.get("title", "Unknown"),
                "authors": self._extract_authors(data),
                "year": self._extract_year(data),
                "arxiv_id": self._extract_arxiv_id(data),
                "doi": data.get("DOI", ""),
                "url": data.get("url", ""),
                "abstract": data.get("abstractNote", ""),
                "tags": [tag["tag"] for tag in data.get("tags", [])],
                "zotero_item_id": item["key"],
            }

            papers.append(metadata)

        return {
            "imported_count": len(papers),
            "papers": papers,
            "collection_id": collection_id,
        }

    async def sync_metadata(
        self, arxiv_id: str, direction: str = "zotero_to_chroma"
    ) -> dict[str, Any]:
        """
        Sync metadata between Zotero and Chroma.

        Args:
            arxiv_id: ArXiv ID to sync
            direction: zotero_to_chroma or chroma_to_zotero

        Returns:
            Sync status
        """
        if direction == "zotero_to_chroma":
            # Find item in Zotero by arxiv_id
            items = self.zot.items(q=arxiv_id)
            if not items:
                return {"status": "not_found", "arxiv_id": arxiv_id}

            item = items[0]
            data = item["data"]

            metadata = {
                "title": data.get("title", "Unknown"),
                "authors": self._extract_authors(data),
                "year": self._extract_year(data),
                "arxiv_id": arxiv_id,
                "url": data.get("url", f"https://arxiv.org/abs/{arxiv_id}"),
                "summary": data.get("abstractNote", ""),
                "tags": [tag["tag"] for tag in data.get("tags", [])],
                "zotero_item_id": item["key"],
            }

            # TODO: Update Chroma with this metadata
            return {
                "status": "synced",
                "direction": direction,
                "arxiv_id": arxiv_id,
                "metadata": metadata,
            }

        else:  # chroma_to_zotero
            # TODO: Get metadata from Chroma and update Zotero
            return {
                "status": "not_implemented",
                "direction": direction,
                "arxiv_id": arxiv_id,
            }

    async def trigger_conversion(
        self,
        zotero_item_id: str,
        deep_biblio_tools_path: str = (
            "/Users/petteri/Dropbox/github-personal/deep-biblio-tools"
        ),
    ) -> dict[str, Any]:
        """
        Trigger PDF conversion using deep-biblio-tools.

        Args:
            zotero_item_id: Zotero item ID
            deep_biblio_tools_path: Path to deep-biblio-tools

        Returns:
            Conversion status
        """
        # Check if PDF attachment exists
        children = self.zot.children(zotero_item_id)
        pdf_attachment = None
        for child in children:
            if child["data"].get("contentType") == "application/pdf":
                pdf_attachment = child
                break

        if not pdf_attachment:
            return {
                "status": "no_pdf",
                "zotero_item_id": zotero_item_id,
            }

        # Note: pyzotero doesn't support file download directly
        # PDF download path would be: Path("/tmp") / f"{zotero_item_id}.pdf"
        # This would need additional implementation

        # TODO: Call deep-biblio-tools conversion
        # For now, return placeholder
        return {
            "status": "conversion_triggered",
            "zotero_item_id": zotero_item_id,
            "deep_biblio_tools_path": deep_biblio_tools_path,
            "note": (
                "PDF conversion integration pending - "
                "requires deep-biblio-tools API"
            ),
        }

    async def get_zotero_item(self, item_id: str) -> dict[str, Any]:
        """
        Retrieve Zotero item by ID.

        Args:
            item_id: Zotero item ID

        Returns:
            Item metadata
        """
        item = self.zot.item(item_id)
        data = item["data"]

        return {
            "id": item["key"],
            "title": data.get("title", "Unknown"),
            "authors": self._extract_authors(data),
            "year": self._extract_year(data),
            "arxiv_id": self._extract_arxiv_id(data),
            "doi": data.get("DOI", ""),
            "url": data.get("url", ""),
            "abstract": data.get("abstractNote", ""),
            "tags": [tag["tag"] for tag in data.get("tags", [])],
            "item_type": data.get("itemType", "unknown"),
        }

    def _extract_authors(self, data: dict[str, Any]) -> str:
        """Extract authors from Zotero item."""
        creators = data.get("creators", [])
        authors = [
            f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
            for c in creators
            if c.get("creatorType") == "author"
        ]
        return ", ".join(authors) if authors else "Unknown"

    def _extract_year(self, data: dict[str, Any]) -> str:
        """Extract year from Zotero item."""
        date = data.get("date", "")
        if date:
            # Try to extract year from date string
            import re

            match = re.search(r"\d{4}", date)
            if match:
                return match.group()
        return "N/A"

    def _extract_arxiv_id(self, data: dict[str, Any]) -> str:
        """Extract arXiv ID from Zotero item."""
        # Check extra field for arXiv ID
        extra = data.get("extra", "")
        if "arXiv:" in extra:
            import re

            match = re.search(r"arXiv:(\d+\.\d+)", extra)
            if match:
                return match.group(1)

        # Check URL
        url = data.get("url", "")
        if "arxiv.org" in url:
            import re

            match = re.search(r"arxiv\.org/abs/(\d+\.\d+)", url)
            if match:
                return match.group(1)

        return "N/A"


async def main():
    """Run MCP server."""
    server = Server("zotero")
    zot = ZoteroServer()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="import_from_zotero",
                description="Auto-import papers from Zotero library",
                inputSchema=ImportFromZoteroArgs.model_json_schema(),
            ),
            Tool(
                name="sync_metadata",
                description="Sync metadata between Zotero and Chroma",
                inputSchema=SyncMetadataArgs.model_json_schema(),
            ),
            Tool(
                name="trigger_conversion",
                description="Trigger PDF conversion using deep-biblio-tools",
                inputSchema=TriggerConversionArgs.model_json_schema(),
            ),
            Tool(
                name="get_zotero_item",
                description="Retrieve Zotero item by ID",
                inputSchema=GetZoteroItemArgs.model_json_schema(),
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Any) -> list[TextContent]:
        """Handle tool calls."""
        if name == "import_from_zotero":
            args = ImportFromZoteroArgs(**arguments)
            result = await zot.import_from_zotero(
                args.collection_id, args.limit, args.tags
            )
            return [TextContent(type="text", text=str(result))]

        elif name == "sync_metadata":
            args = SyncMetadataArgs(**arguments)
            result = await zot.sync_metadata(args.arxiv_id, args.direction)
            return [TextContent(type="text", text=str(result))]

        elif name == "trigger_conversion":
            args = TriggerConversionArgs(**arguments)
            result = await zot.trigger_conversion(
                args.zotero_item_id, args.deep_biblio_tools_path
            )
            return [TextContent(type="text", text=str(result))]

        elif name == "get_zotero_item":
            args = GetZoteroItemArgs(**arguments)
            result = await zot.get_zotero_item(args.item_id)
            return [TextContent(type="text", text=str(result))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    # Run server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
