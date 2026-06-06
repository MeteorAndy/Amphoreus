"""Tests for the deterministic cliche / AI-flavor scanner (zero-LLM, pure)."""
from __future__ import annotations

from app.services.narrative.cliche_scanner import (
    ClicheHit,
    ClicheReport,
    scan,
)

_ALLOWED_SEVERITIES = {"critical", "warning", "info"}


def test_clean_zh_prose_scores_near_zero():
    text = (
        "晨光斜斜地落在书桌上，照亮了摊开的笔记本。她拿起笔，"
        "在纸上写下今天要做的事：去市场买菜，给母亲打电话，"
        "把院子里的落叶扫干净。窗外有麻雀在叫，声音清脆。"
        "她合上本子，起身去厨房烧水，准备煮一壶热茶。"
        "水开了，茶香慢慢弥漫开来，整个屋子都暖了起来。"
    ) * 1
    report = scan(text)
    assert report.ai_flavor_score < 1.0
    assert report.hits == []


def test_severity_weighting_monotonic():
    pad = "天" * 300
    text_info = "他挑了挑眉。" + pad
    text_warning = "他勾了勾嘴角。" + pad
    text_critical = "他心中一紧。" + pad
    s_info = scan(text_info).ai_flavor_score
    s_warning = scan(text_warning).ai_flavor_score
    s_critical = scan(text_critical).ai_flavor_score
    assert s_critical > s_warning > s_info
    text_2crit = "他心中一紧，随后空气仿佛凝固。" + pad
    assert scan(text_2crit).ai_flavor_score > s_critical


def test_empty_string_safe():
    report = scan("")
    assert report.ai_flavor_score == 0.0
    assert report.hits == []


def test_whitespace_only_safe():
    report = scan("   \n\n  ")
    assert report.ai_flavor_score == 0.0
    assert report.hits == []


def test_hit_fields_populated():
    report = scan("他嘴角勾起，心中一紧。A shiver ran down her spine.")
    assert report.hits
    for h in report.hits:
        assert isinstance(h, ClicheHit)
        assert h.name
        assert h.severity in _ALLOWED_SEVERITIES
        assert h.category
        assert h.span_excerpt
        assert isinstance(h.replacement_hint, str) and h.replacement_hint


def test_cliche_dense_zh_scores_high_and_lists_hits():
    text = (
        "他嘴角勾起，眸光一闪，露出不易察觉的冷笑。"
        "她深吸一口气，空气仿佛凝固，心中一紧。"
    )
    report = scan(text)
    assert report.ai_flavor_score > 20.0
    assert len(report.hits) >= 5
    names = {h.name for h in report.hits}
    assert "mouth_corner_curl" in names
    assert "eye_light" in names
    assert "imperceptible" in names
    assert "deep_breath" in names
    assert "air_freeze" in names
    assert "heart_tighten" in names


def test_english_cliches_detected():
    text = (
        "A shiver ran down her spine. She couldn't help but stare. "
        "Little did they know what waited ahead. Her heart skipped a beat."
    )
    report = scan(text)
    assert len(report.hits) >= 4
    names = {h.name for h in report.hits}
    assert "shiver_spine" in names
    assert "couldnt_help_but" in names
    assert "little_did_know" in names
    assert "heart_skipped" in names
    assert all(h.category in {"en_cliche", "narrator_intrusion"} for h in report.hits)


def test_span_excerpt_bounds():
    text = "无关前缀。" * 5 + "他嘴角勾起。" + "无关后缀。" * 5
    report = scan(text)
    curl = [h for h in report.hits if h.name == "mouth_corner_curl"]
    assert curl
    for h in curl:
        assert "嘴角勾起" in h.span_excerpt
        assert len(h.span_excerpt) <= 60


def test_score_capped_at_100():
    text = "心中一紧空气仿佛凝固嘴角勾起不易察觉的"
    report = scan(text)
    assert report.ai_flavor_score == 100.0


def test_scan_is_pure_deterministic():
    text = "他嘴角勾起，眸光一闪，心中一紧。仿佛仿佛仿佛。"
    r1 = scan(text)
    r2 = scan(text)
    assert r1.ai_flavor_score == r2.ai_flavor_score
    assert [h.name for h in r1.hits] == [h.name for h in r2.hits]


def test_overuse_rules_threshold():
    single = scan("夜色仿佛潮水。" + "字" * 100)
    assert "fangfu_overuse" not in {h.name for h in single.hits}
    triple = scan("仿佛潮水，仿佛云烟，仿佛旧梦。" + "字" * 100)
    assert "fangfu_overuse" in {h.name for h in triple.hits}


def test_to_dict_shape():
    report = scan("他心中一紧。")
    d = report.to_dict()
    assert "hits" in d and "ai_flavor_score" in d
    assert isinstance(d["hits"], list)
    if d["hits"]:
        assert "name" in d["hits"][0]


def test_clean_en_prose_scores_near_zero():
    text = (
        "The kettle clicked off and she poured the water slowly, "
        "watching steam rise from the cup. Outside, a delivery truck "
        "rolled past and a neighbor waved from across the street. "
        "She carried the tea to the desk, opened her laptop, and "
        "began typing the report she had promised to finish by noon."
    )
    report = scan(text)
    assert report.ai_flavor_score < 1.0
    assert report.hits == []
