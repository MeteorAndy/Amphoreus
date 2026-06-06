"""Regression tests for LLMClient retry + error classification.

Covers the two failure modes that previously hung generation:
- timeouts misclassified as UNKNOWN (not retried) because "Request timed out."
  does not contain the substring "timeout";
- 5xx / Cloudflare 524 misclassified as UNKNOWN (not retried) because only
  401/403/402/429 had explicit branches.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

from app.core.llm_client import LLMClient, LLMError, LLMErrorCode


def _status_exc(cls, code: int, msg: str = "err"):
    req = httpx.Request("POST", "http://x")
    resp = httpx.Response(code, request=req)
    return cls(msg, response=resp, body=None)


def _client() -> LLMClient:
    with patch("app.core.llm_client.AsyncOpenAI"), patch(
        "app.core.llm_client.get_settings"
    ) as gs:
        gs.return_value = MagicMock(
            deepseek_api_key_effective="k",
            deepseek_base_url="http://x",
            deepseek_model="m",
            deepseek_timeout=120.0,
            deepseek_max_retries=3,
        )
        return LLMClient()


# ── Classification: the core regression ──────────────────────────────

@pytest.mark.parametrize("exc, expected, retryable", [
    (APITimeoutError(request=httpx.Request("POST", "http://x")), LLMErrorCode.NETWORK_ERROR, True),
    (_status_exc(InternalServerError, 524), LLMErrorCode.NETWORK_ERROR, True),
    (_status_exc(InternalServerError, 503), LLMErrorCode.NETWORK_ERROR, True),
    (_status_exc(InternalServerError, 500), LLMErrorCode.NETWORK_ERROR, True),
    (_status_exc(RateLimitError, 429), LLMErrorCode.RATE_LIMITED, True),
    (_status_exc(AuthenticationError, 401), LLMErrorCode.AUTH_ERROR, False),
    (_status_exc(InternalServerError, 402), LLMErrorCode.QUOTA_EXHAUSTED, False),
])
def test_classify_error(exc, expected, retryable):
    code = LLMClient._classify_error(exc)
    assert code == expected
    assert LLMError(code, "x", exc).is_retryable is retryable


def test_timeout_message_no_longer_misclassified():
    # "Request timed out." lacks the substring "timeout" — the original bug.
    exc = APITimeoutError(request=httpx.Request("POST", "http://x"))
    assert "timeout" not in str(exc).lower()
    assert LLMClient._classify_error(exc) == LLMErrorCode.NETWORK_ERROR


def test_sdk_retries_disabled():
    # LLMClient owns retry policy; the SDK layer must be off (max_retries=0).
    with patch("app.core.llm_client.AsyncOpenAI") as mk, patch(
        "app.core.llm_client.get_settings"
    ) as gs:
        gs.return_value = MagicMock(
            deepseek_api_key_effective="k", deepseek_base_url="http://x",
            deepseek_model="m", deepseek_timeout=99.0, deepseek_max_retries=3,
        )
        LLMClient()
        assert mk.call_args.kwargs["max_retries"] == 0
        # Timeout must be a per-component httpx.Timeout, NOT a bare float — a bare
        # float collapses connect (SDK default 5s) to the full read window.
        to = mk.call_args.kwargs["timeout"]
        assert isinstance(to, httpx.Timeout)
        assert to.read == 99.0
        assert to.connect == 5.0  # short connect preserved


def test_connect_timeout_capped_when_total_is_tiny():
    # If deepseek_timeout < 5s, connect must not exceed it.
    with patch("app.core.llm_client.AsyncOpenAI") as mk, patch(
        "app.core.llm_client.get_settings"
    ) as gs:
        gs.return_value = MagicMock(
            deepseek_api_key_effective="k", deepseek_base_url="http://x",
            deepseek_model="m", deepseek_timeout=2.0, deepseek_max_retries=3,
        )
        LLMClient()
        to = mk.call_args.kwargs["timeout"]
        assert to.connect == 2.0 and to.read == 2.0


# ── chat() retry behavior ────────────────────────────────────────────

def _ok_response(text="hi"):
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.mark.asyncio
async def test_chat_retries_then_succeeds():
    c = _client()
    c._client.chat.completions.create = AsyncMock(side_effect=[
        _status_exc(InternalServerError, 524),
        _ok_response("recovered"),
    ])
    with patch("asyncio.sleep", new=AsyncMock()) as slp:
        out = await c.chat([{"role": "user", "content": "x"}])
    assert out == "recovered"
    assert c._client.chat.completions.create.call_count == 2
    slp.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_does_not_retry_auth():
    c = _client()
    c._client.chat.completions.create = AsyncMock(
        side_effect=_status_exc(AuthenticationError, 401))
    with patch("asyncio.sleep", new=AsyncMock()):
        with pytest.raises(LLMError) as ei:
            await c.chat([{"role": "user", "content": "x"}])
    assert ei.value.code == LLMErrorCode.AUTH_ERROR
    assert c._client.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_chat_exhausts_retries_and_raises():
    c = _client()
    c._client.chat.completions.create = AsyncMock(
        side_effect=_status_exc(InternalServerError, 503))
    with patch("asyncio.sleep", new=AsyncMock()) as slp:
        with pytest.raises(LLMError) as ei:
            await c.chat([{"role": "user", "content": "x"}])
    assert ei.value.code == LLMErrorCode.NETWORK_ERROR
    assert c._client.chat.completions.create.call_count == 3  # max_retries
    assert slp.await_count == 2  # sleeps between, not after last


@pytest.mark.asyncio
async def test_backoff_is_capped_at_30s():
    c = _client()
    c._max_retries = 10
    c._client.chat.completions.create = AsyncMock(
        side_effect=_status_exc(InternalServerError, 503))
    delays = []
    async def fake_sleep(d): delays.append(d)
    with patch("asyncio.sleep", new=fake_sleep):
        with pytest.raises(LLMError):
            await c.chat([{"role": "user", "content": "x"}])
    assert max(delays) <= 30.0
    assert delays[:4] == [2.0, 4.0, 8.0, 16.0]


# ── chat_stream() hardening ──────────────────────────────────────────

class _FakeStream:
    """Async-iterable stream whose chunks may include a hang sentinel."""

    def __init__(self, chunks):
        self._chunks = list(chunks)
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i >= len(self._chunks):
            raise StopAsyncIteration
        item = self._chunks[self._i]
        self._i += 1
        if item == "__HANG__":
            await asyncio.sleep(3600)  # never resolves within the test timeout
        return item


def _chunk(text):
    delta = MagicMock()
    delta.content = text
    choice = MagicMock()
    choice.delta = delta
    c = MagicMock()
    c.choices = [choice]
    return c


@pytest.mark.asyncio
async def test_chat_stream_yields_content():
    c = _client()
    c._client.chat.completions.create = AsyncMock(
        return_value=_FakeStream([_chunk("Hello "), _chunk("world")]))
    out = "".join([x async for x in c.chat_stream([{"role": "user", "content": "x"}])])
    assert out == "Hello world"


@pytest.mark.asyncio
async def test_chat_stream_retries_connect():
    c = _client()
    c._client.chat.completions.create = AsyncMock(side_effect=[
        _status_exc(InternalServerError, 524),
        _FakeStream([_chunk("ok")]),
    ])
    with patch("asyncio.sleep", new=AsyncMock()):
        out = "".join([x async for x in c.chat_stream([{"role": "user", "content": "x"}])])
    assert out == "ok"
    assert c._client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_chat_stream_idle_timeout_raises():
    # The "卡住一半" regression: a stream that stalls mid-output must not hang.
    c = _client()
    c._timeout = 0.05
    c._client.chat.completions.create = AsyncMock(
        return_value=_FakeStream([_chunk("partial "), "__HANG__"]))
    got = []
    with pytest.raises(LLMError) as ei:
        async for x in c.chat_stream([{"role": "user", "content": "x"}]):
            got.append(x)
    assert ei.value.code == LLMErrorCode.NETWORK_ERROR
    assert got == ["partial "]  # yielded what it had, then raised instead of hanging


# ── chat_json() parse-retry (the pipeline-crash regression) ──────────

@pytest.mark.asyncio
async def test_chat_json_recovers_on_reask():
    c = _client()
    c.chat = AsyncMock(side_effect=["not json at all", '{"stage": "rules"}'])
    out = await c.chat_json([{"role": "user", "content": "x"}])
    assert out == {"stage": "rules"}
    assert c.chat.await_count == 2


@pytest.mark.asyncio
async def test_chat_json_persistent_bad_raises_llmerror_not_valueerror():
    # Regression: a stochastic unparseable response must NOT escape as a bare
    # ValueError (which the orchestrator's `except LLMError` cannot catch and
    # which crashed the whole pipeline mid-run).
    c = _client()
    c.chat = AsyncMock(return_value="never valid json")
    with pytest.raises(LLMError) as ei:
        await c.chat_json([{"role": "user", "content": "x"}])
    assert ei.value.code == LLMErrorCode.PARSE_ERROR
    assert ei.value.is_retryable is False
    assert c.chat.await_count == 3  # max_retries re-asks


@pytest.mark.asyncio
async def test_chat_json_first_try_clean():
    c = _client()
    c.chat = AsyncMock(return_value='```json\n{"a": 1}\n```')
    out = await c.chat_json([{"role": "user", "content": "x"}])
    assert out == {"a": 1}
    assert c.chat.await_count == 1


@pytest.mark.asyncio
async def test_chat_json_propagates_network_error():
    # A network failure inside chat_json must bubble up as NETWORK_ERROR, not be
    # swallowed by the parse-retry loop or relabelled PARSE_ERROR.
    c = _client()
    c.chat = AsyncMock(side_effect=LLMError(LLMErrorCode.NETWORK_ERROR, "boom"))
    with pytest.raises(LLMError) as ei:
        await c.chat_json([{"role": "user", "content": "x"}])
    assert ei.value.code == LLMErrorCode.NETWORK_ERROR
    assert c.chat.await_count == 1  # not re-asked; propagated immediately


