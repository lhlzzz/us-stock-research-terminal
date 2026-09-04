from __future__ import annotations

from research_panel import build_replay_hypothesis, build_risk_checklist, run_full_research_panel


def test_legacy_panel_cannot_bypass_research_os():
    research = run_full_research_panel(
        "NVDA",
        {"prior_20d_momentum": 0.12, "five_day_acceleration": 0.01, "relative_strength_vs_equal_weight": 0.02, "volume_confirmation_ratio": 0.4},
        {"status": "missing", "relevance_score": 0.0},
        {"status": "missing", "relevance_score": 0.0},
        {"roe": 0.23, "pe_ttm": 18, "dividend_yield": 0.02},
    )
    assert research["canonical_owner"] == "scripts.research"
    assert research["compatibility_adapter"] is True
    assert research["research_panel"]["method"] == "DETERMINISTIC_PANEL_RULE"
    assert research["research_panel"]["not_multi_agent_vote"] is True


def test_heuristic_confidence_is_not_calibrated_probability():
    panel = {"panel_verdict": "BULLISH_CONSENSUS"}
    quality = {"overall_quality_score": 0.7}
    replay = build_replay_hypothesis("NVDA", {"prior_20d_momentum": 0.12, "five_day_acceleration": 0.0}, panel, quality)
    assert replay["status"] == "UNCALIBRATED_HYPOTHESIS"
    assert replay["heuristic_confidence"] is not None
    assert "prediction_confidence" not in replay
    assert replay["historically_calibrated_probability"] is None
    assert replay["model_probability"] is None


def test_unknown_risk_is_not_green():
    risk = build_risk_checklist("NVDA", {"status": "missing"}, {"status": "missing"}, {}, {})
    assert risk["checks"]["short_interest"]["status"] == "UNKNOWN"
    assert risk["checks"]["short_interest"]["flag"] == "GRAY"
    assert risk["recommendation"] == "NEED_MORE_EVIDENCE"
