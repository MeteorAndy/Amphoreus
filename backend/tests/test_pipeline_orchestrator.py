"""TDD tests for PipelineOrchestrator.

Tests the core orchestration logic with mocked services.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.pipeline_orchestrator import (
    PipelineOrchestrator,
    PipelineConfig,
    PipelineEvent,
    PipelineStage,
)


@pytest.mark.asyncio
async def test_orchestrator_yields_events(mock_llm, mock_memory):
    """Orchestrator should yield PipelineEvent objects."""
    orch = PipelineOrchestrator(mock_llm, mock_memory)
    config = PipelineConfig(seed_idea="A robot uprising story")

    events = []
    with patch.object(orch, '_stage_world') as mock_world:
        mock_world.return_value = _async_gen([
            PipelineEvent(stage="world", type="started", progress=0.0, session_id="test"),
            PipelineEvent(stage="world", type="completed", progress=0.15, session_id="test"),
        ])
        async for event in orch.run(config):
            events.append(event)
            if len(events) >= 2:
                break

    assert len(events) >= 2
    assert all(isinstance(e, PipelineEvent) for e in events)


@pytest.mark.asyncio
async def test_orchestrator_progress_increases(mock_llm, mock_memory):
    """Progress should monotonically increase across events."""
    orch = PipelineOrchestrator(mock_llm, mock_memory)
    config = PipelineConfig(seed_idea="A robot uprising story")

    events = []
    with patch.object(orch, '_stage_world') as mock_world:
        mock_world.return_value = _async_gen([
            PipelineEvent(stage="world", type="started", progress=0.0, session_id="t"),
            PipelineEvent(stage="world", type="progress", progress=0.05, session_id="t"),
            PipelineEvent(stage="world", type="completed", progress=0.15, session_id="t"),
        ])
        async for event in orch.run(config):
            events.append(event)
            if len(events) >= 3:
                break

    progresses = [e.progress for e in events]
    assert progresses == sorted(progresses)


@pytest.mark.asyncio
async def test_config_defaults():
    """PipelineConfig should have sensible defaults."""
    config = PipelineConfig(seed_idea="test")
    assert config.lang == "zh"
    assert config.character_count == 5
    assert config.narrative_structure == "three_act"
    assert config.output_format == "novel"
    assert config.max_rounds_per_scene == 15
    assert config.auto_refine is True
    assert config.session_id is None


@pytest.mark.asyncio
async def test_pipeline_event_has_session_id(mock_llm, mock_memory):
    """Every event should carry a session_id for tracking."""
    orch = PipelineOrchestrator(mock_llm, mock_memory)
    config = PipelineConfig(seed_idea="test", session_id="my-session")

    with patch.object(orch, '_stage_world') as mock_world:
        mock_world.return_value = _async_gen([
            PipelineEvent(stage="world", type="started", progress=0.0, session_id="my-session"),
        ])
        async for event in orch.run(config):
            assert event.session_id == "my-session"
            break


async def _async_gen(items):
    for item in items:
        yield item
