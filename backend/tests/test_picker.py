"""Tests for the option picker (fallback path + pure logic)."""

from __future__ import annotations

import pytest

from app.cli import picker
from app.cli.picker import PickResult, _build_rows, _decode_escape_seq, _resolve, pick


def _labels(rows):
    return [r[2] for r in rows]


def test_build_rows_suggestions_plus_custom_and_auto():
    rows = _build_rows(["a", "b"], True, True, "CUSTOM", "AUTO")
    assert [r[0] for r in rows] == ["suggestion", "suggestion", "custom", "auto"]
    assert _labels(rows) == ["a", "b", "CUSTOM", "AUTO"]


def test_build_rows_no_custom_no_auto():
    rows = _build_rows(["a"], False, False, None, None)
    assert [r[0] for r in rows] == ["suggestion"]


def test_resolve_suggestion_returns_value_and_index():
    rows = [("suggestion", "x", "x"), ("auto", "", "AUTO")]
    res = _resolve(rows, 0)
    assert res == PickResult("suggestion", "x", 0)


def test_resolve_auto():
    rows = [("suggestion", "x", "x"), ("auto", "", "AUTO")]
    assert _resolve(rows, 1) == PickResult("auto", "", -1)


def test_decode_escape_seq_arrows():
    assert _decode_escape_seq("[A") == "up"
    assert _decode_escape_seq("[B") == "down"


def test_decode_escape_seq_unknown_returns_none():
    # Left/Right/Home/End/F-keys must be ignored (None), not abort the session.
    for seq in ("[C", "[D", "[H", "[F", "OP", "[3"):
        assert _decode_escape_seq(seq) is None


def test_pick_fallback_selects_numbered_suggestion(monkeypatch):
    monkeypatch.setattr(picker, "_is_interactive", lambda: False)
    monkeypatch.setattr(picker.Prompt, "ask", staticmethod(lambda *a, **k: "2"))
    res = pick("q", ["first", "second", "third"])
    assert res == PickResult("suggestion", "second", 1)


def test_pick_fallback_enter_uses_default(monkeypatch):
    monkeypatch.setattr(picker, "_is_interactive", lambda: False)
    monkeypatch.setattr(picker.Prompt, "ask", staticmethod(lambda *a, **k: k.get("default", "")))
    res = pick("q", ["first", "second"])
    assert res == PickResult("suggestion", "first", 0)


def test_pick_fallback_prose_is_custom(monkeypatch):
    monkeypatch.setattr(picker, "_is_interactive", lambda: False)
    monkeypatch.setattr(picker.Prompt, "ask", staticmethod(lambda *a, **k: "my own answer"))
    res = pick("q", ["a", "b"])
    assert res.kind == "custom"
    assert res.value == "my own answer"


def test_pick_fallback_auto_row(monkeypatch):
    monkeypatch.setattr(picker, "_is_interactive", lambda: False)
    # 2 suggestions + custom(3) + auto(4); pick the auto row
    monkeypatch.setattr(picker.Prompt, "ask", staticmethod(lambda *a, **k: "4"))
    res = pick("q", ["a", "b"], allow_auto=True)
    assert res.kind == "auto"


def test_pick_empty_suggestions_still_offers_custom(monkeypatch):
    monkeypatch.setattr(picker, "_is_interactive", lambda: False)
    monkeypatch.setattr(picker.Prompt, "ask", staticmethod(lambda *a, **k: "typed"))
    res = pick("q", [])
    assert res.kind == "custom"
    assert res.value == "typed"


def test_pick_custom_row_then_text(monkeypatch):
    monkeypatch.setattr(picker, "_is_interactive", lambda: False)
    calls = iter(["3", "hand typed"])  # choose custom row, then provide text
    monkeypatch.setattr(picker.Prompt, "ask", staticmethod(lambda *a, **k: next(calls)))
    res = pick("q", ["a", "b"])
    assert res == PickResult("custom", "hand typed", -1)

