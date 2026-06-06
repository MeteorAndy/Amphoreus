"""Tests for the verbatim-repeat diagnostic (review finding: copy-pasted clauses)."""
from __future__ import annotations

from app.services.narrative.post_processor import PostProcessor


def test_detects_repeated_clause_inside_sentences():
    # "像干涸的血迹" recurs inside two different sentences across chapters.
    text = (
        "封面上的灼痕暗红，像干涸的血迹，触目惊心。\n\n"
        "契约墙上的字迹斑驳，像干涸的血迹，无人擦拭。\n\n"
        "他抬起头望向远方的云海。"
    )
    reps = dict(PostProcessor.find_repeated_fragments(text, min_len=4))
    assert reps.get("像干涸的血迹") == 2


def test_no_false_positive_on_unique_prose():
    text = "晨光照进图书馆。\n\n苏婉清翻开一本旧书，指尖拂过泛黄的纸页。"
    assert PostProcessor.find_repeated_fragments(text, min_len=6) == []


def test_sorted_most_repeated_first():
    text = "甲句子内容。甲句子内容。甲句子内容。乙的句子。乙的句子。"
    reps = PostProcessor.find_repeated_fragments(text, min_len=4)
    assert reps[0][0] == "甲句子内容" and reps[0][1] == 3
    assert reps[1][1] == 2


def test_min_len_filters_short_fragments():
    # Short connective fragments below min_len must not be reported.
    text = "他说，好的，他说，好的。"
    assert all(len(s) >= 8 for s, _ in PostProcessor.find_repeated_fragments(text, min_len=8))
