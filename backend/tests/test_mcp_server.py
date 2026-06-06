"""TDD tests for MCP Server.

These tests are written BEFORE the implementation (RED phase).
They define the expected behavior of the MCP tool interface.
"""
from __future__ import annotations

import asyncio
import pytest
from mcp.types import ListToolsRequest


@pytest.mark.asyncio
async def test_mcp_server_imports():
    """MCP server module should be importable."""
    from mcp_server import create_mcp_server
    assert create_mcp_server is not None


@pytest.mark.asyncio
async def test_mcp_server_has_generate_story_tool():
    """MCP server should expose generate_story tool."""
    from mcp_server import create_mcp_server
    server = create_mcp_server()
    handler = server.request_handlers[ListToolsRequest]
    result = await handler(ListToolsRequest(method="tools/list"))
    tool_names = [t.name for t in result.root.tools]
    assert "generate_story" in tool_names


@pytest.mark.asyncio
async def test_mcp_server_has_individual_tools():
    """MCP server should expose individual pipeline stage tools."""
    from mcp_server import create_mcp_server
    server = create_mcp_server()
    handler = server.request_handlers[ListToolsRequest]
    result = await handler(ListToolsRequest(method="tools/list"))
    tool_names = [t.name for t in result.root.tools]
    assert "build_world" in tool_names
    assert "generate_characters" in tool_names
    assert "create_plot" in tool_names
    assert "run_scenes" in tool_names
    assert "write_narrative" in tool_names


@pytest.mark.asyncio
async def test_mcp_generate_story_requires_seed_idea():
    """generate_story tool should require seed_idea parameter."""
    from mcp_server import create_mcp_server
    server = create_mcp_server()
    handler = server.request_handlers[ListToolsRequest]
    result = await handler(ListToolsRequest(method="tools/list"))
    gen_tool = next(t for t in result.root.tools if t.name == "generate_story")
    schema = gen_tool.inputSchema
    assert "seed_idea" in schema.get("required", [])
