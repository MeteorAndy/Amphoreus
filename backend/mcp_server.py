"""Amphoreus Story Engine — MCP Server.

Exposes the story generation pipeline as MCP tools for AI agent integration.
Run with: uv run mcp_server.py
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult

from app.core.config import get_settings
from app.core.i18n import Lang, set_lang
from app.core.llm_client import LLMClient
from app.services.memory import MemoryManager
from app.services.pipeline_orchestrator import (
    PipelineConfig,
    PipelineOrchestrator,
)


def _tool_schema(required: list[str], properties: dict) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def create_mcp_server() -> Server:
    server = Server("amphoreus-story-engine")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(
                name="generate_story",
                description=(
                    "Generate a complete novel or screenplay from a seed idea. "
                    "Runs the full pipeline: world building, characters, plot, "
                    "scenes, and narrative writing."
                ),
                inputSchema=_tool_schema(
                    required=["seed_idea"],
                    properties={
                        "seed_idea": {
                            "type": "string",
                            "description": "The core story idea (one sentence)",
                        },
                        "lang": {
                            "type": "string",
                            "enum": ["zh", "en"],
                            "default": "zh",
                        },
                        "character_count": {
                            "type": "integer",
                            "default": 5,
                        },
                        "narrative_structure": {
                            "type": "string",
                            "enum": ["three_act", "hero_journey", "save_the_cat", "qi_cheng_zhuan_he"],
                            "default": "three_act",
                        },
                        "output_format": {
                            "type": "string",
                            "enum": ["novel", "screenplay"],
                            "default": "novel",
                        },
                    },
                ),
            ),
            Tool(
                name="build_world",
                description="Build a world from a seed idea using self-play conversation.",
                inputSchema=_tool_schema(
                    required=["seed_idea"],
                    properties={
                        "seed_idea": {"type": "string"},
                        "lang": {"type": "string", "enum": ["zh", "en"], "default": "zh"},
                    },
                ),
            ),
            Tool(
                name="generate_characters",
                description="Generate characters for an existing world.",
                inputSchema=_tool_schema(
                    required=["session_id"],
                    properties={
                        "session_id": {"type": "string"},
                        "count": {"type": "integer", "default": 5},
                    },
                ),
            ),
            Tool(
                name="create_plot",
                description="Create a plot outline from world and characters.",
                inputSchema=_tool_schema(
                    required=["session_id"],
                    properties={
                        "session_id": {"type": "string"},
                        "structure": {"type": "string", "default": "three_act"},
                    },
                ),
            ),
            Tool(
                name="run_scenes",
                description="Execute all scenes from the plot outline.",
                inputSchema=_tool_schema(
                    required=["session_id"],
                    properties={
                        "session_id": {"type": "string"},
                        "max_rounds": {"type": "integer", "default": 15},
                    },
                ),
            ),
            Tool(
                name="write_narrative",
                description="Convert scene archives into a novel or screenplay.",
                inputSchema=_tool_schema(
                    required=["session_id"],
                    properties={
                        "session_id": {"type": "string"},
                        "format": {"type": "string", "enum": ["novel", "screenplay"], "default": "novel"},
                    },
                ),
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        args = arguments or {}

        if name == "generate_story":
            return await _run_full_pipeline(args)
        elif name == "build_world":
            return [TextContent(type="text", text=f"World building started for: {args.get('seed_idea', '')}")]
        elif name == "generate_characters":
            return [TextContent(type="text", text=f"Character generation for session: {args.get('session_id', '')}")]
        elif name == "create_plot":
            return [TextContent(type="text", text=f"Plot creation for session: {args.get('session_id', '')}")]
        elif name == "run_scenes":
            return [TextContent(type="text", text=f"Scene execution for session: {args.get('session_id', '')}")]
        elif name == "write_narrative":
            return [TextContent(type="text", text=f"Narrative writing for session: {args.get('session_id', '')}")]
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


async def _run_full_pipeline(args: dict[str, Any]) -> list[TextContent]:
    lang = args.get("lang", "zh")
    set_lang(Lang.ZH if lang == "zh" else Lang.EN)

    config = PipelineConfig(
        seed_idea=args["seed_idea"],
        lang=lang,
        character_count=args.get("character_count", 5),
        narrative_structure=args.get("narrative_structure", "three_act"),
        output_format=args.get("output_format", "novel"),
    )

    llm = LLMClient()
    settings = get_settings()
    memory = MemoryManager(settings)
    await memory.initialize()
    orchestrator = PipelineOrchestrator(llm, memory)

    final_text = ""
    session_id = ""
    async for event in orchestrator.run(config):
        session_id = event.session_id
        if event.stage == "writing" and event.type == "completed":
            final_text = event.data.get("output_text", "")

    if not final_text:
        final_text = f"Pipeline completed. Session: {session_id}"

    return [TextContent(type="text", text=final_text)]


async def main():
    server = create_mcp_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
