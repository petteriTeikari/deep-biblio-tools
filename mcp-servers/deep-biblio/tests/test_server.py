"""Tests for deep-biblio MCP server."""

import sys
from pathlib import Path

import pytest

# Add server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from deep_biblio.server import (
    DEEP_BIBLIO_AVAILABLE,
    MODULES_AVAILABLE,
    app,
    call_tool,
    list_tools,
)


def test_server_initialization():
    """Test that server initializes correctly."""
    assert app is not None
    assert app.name == "deep-biblio"


def test_modules_status():
    """Test that module availability is tracked."""
    assert isinstance(MODULES_AVAILABLE, dict)
    assert "pdf_parser" in MODULES_AVAILABLE
    assert "html_parser" in MODULES_AVAILABLE
    assert "bibtex_parser" in MODULES_AVAILABLE


def test_deep_biblio_available():
    """Test that at least one module is available."""
    # If deep-biblio-tools is properly installed, at least one module should work
    if DEEP_BIBLIO_AVAILABLE:
        assert any(MODULES_AVAILABLE.values())
    else:
        pytest.skip("deep-biblio-tools not available")


@pytest.mark.asyncio
async def test_list_tools():
    """Test that tools are listed correctly."""
    tools = await list_tools()

    assert len(tools) > 0
    assert any(tool.name == "status" for tool in tools)

    # If modules are available, check for their tools
    if MODULES_AVAILABLE.get("pdf_parser"):
        assert any(tool.name == "extract_pdf_metadata" for tool in tools)
        assert any(tool.name == "check_pdf_url" for tool in tools)


@pytest.mark.asyncio
async def test_status_tool():
    """Test the status tool."""
    result = await call_tool("status", {})

    assert len(result) == 1
    assert "deep-biblio-tools" in result[0].text
    assert "Module Status" in result[0].text


@pytest.mark.asyncio
async def test_check_pdf_url():
    """Test PDF URL checking."""
    if not MODULES_AVAILABLE.get("pdf_parser"):
        pytest.skip("pdf_parser module not available")

    # Test positive case
    result = await call_tool("check_pdf_url", {"url": "https://example.com/paper.pdf"})
    assert len(result) == 1
    assert "PDF" in result[0].text

    # Test negative case
    result = await call_tool("check_pdf_url", {"url": "https://example.com/paper.html"})
    assert len(result) == 1
    assert "not" in result[0].text.lower()


@pytest.mark.asyncio
async def test_unknown_tool():
    """Test handling of unknown tool."""
    result = await call_tool("nonexistent_tool", {})

    assert len(result) == 1
    assert "Unknown tool" in result[0].text


@pytest.mark.asyncio
async def test_tool_schemas():
    """Test that all tools have valid schemas."""
    tools = await list_tools()

    for tool in tools:
        # Check required fields
        assert tool.name
        assert tool.description
        assert tool.inputSchema

        # Check schema structure
        schema = tool.inputSchema
        assert schema["type"] == "object"
        assert "properties" in schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
