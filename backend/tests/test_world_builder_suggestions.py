"""Tests for world-builder suggestions and seed brainstorming."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.world_builder import WorldBuilder, _parse_suggestions


def _builder_with(chat_json_return):
    llm = AsyncMock()
    llm.chat_json = AsyncMock(return_value=chat_json_return)
    memory = MagicMock()
    memory.openviking = MagicMock()
    memory.openviking.write_entry = MagicMock()
    return WorldBuilder(llm, memory), llm


def test_parse_suggestions_filters_and_caps():
    assert _parse_suggestions(["a", "", "  b ", "c", "d", "e"], limit=4) == ["a", "b", "c", "d"]


def test_parse_suggestions_rejects_non_list():
    assert _parse_suggestions("nope") == []
    assert _parse_suggestions(None) == []
    assert _parse_suggestions([1, 2, {"x": 1}]) == []


@pytest.mark.asyncio
async def test_start_new_world_populates_suggestions():
    builder, _ = _builder_with({
        "stage": "rules",
        "next_question": "Q?",
        "suggestions": ["s1", "s2", "s3"],
        "extracted": {},
        "completeness": 0.2,
    })
    session = await builder.start_new_world("a seed")
    assert session.suggestions == ["s1", "s2", "s3"]
    assert session.next_question == "Q?"


@pytest.mark.asyncio
async def test_brainstorm_seed_ideas_returns_list():
    builder, _ = _builder_with({"ideas": ["idea one", "idea two"]})
    ideas = await builder.brainstorm_seed_ideas(count=4)
    assert ideas == ["idea one", "idea two"]


@pytest.mark.asyncio
async def test_brainstorm_seed_ideas_empty_on_failure():
    builder, llm = _builder_with({})
    llm.chat_json = AsyncMock(side_effect=RuntimeError("boom"))
    assert await builder.brainstorm_seed_ideas() == []
