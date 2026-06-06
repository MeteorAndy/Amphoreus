"""Tests for T1-②: convergence hourglass phase directives."""

from __future__ import annotations

from app.services.narrative.novel_writer import _render_phase_directive as r


def test_short_story_skips_phase():
    assert r(1, 1, True) == ""
    assert r(1, 2, True) == ""


def test_four_phases_zh():
    assert "开篇" in r(1, 10, True)
    assert "发展" in r(5, 10, True)
    assert "收束" in r(8, 10, True)
    assert "终局" in r(10, 10, True)


def test_four_phases_en():
    assert "OPENING" in r(1, 10, False)
    assert "DEVELOPMENT" in r(5, 10, False)
    assert "CONVERGENCE" in r(8, 10, False)
    assert "FINALE" in r(10, 10, False)


def test_boundary_transitions():
    # 4-chapter book (25% per chapter): ch1=open, ch2-3=dev, ch4=fin
    assert "开篇" in r(1, 4, True)
    assert "发展" in r(2, 4, True)
    assert "发展" in r(3, 4, True)  # 0.75 is the dev boundary
    assert "终局" in r(4, 4, True)

    # 12-chapter: ch8 (0.67)=dev, ch10 (0.83)=conv, ch11 (0.92)=fin
    assert "收束" in r(10, 12, True)
    assert "终局" in r(11, 12, True)
