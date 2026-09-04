from __future__ import annotations

from research.metric_semantics import risk_manager_recommendation
from us_profit_ticket_pipeline import build_candidate_record


def test_unknown_risk_does_not_proceed():
    assert risk_manager_recommendation(known_blocked=False, known_elevated=False, known_clean=False, insufficient=True) == "NEED_MORE_EVIDENCE"
    assert risk_manager_recommendation(known_blocked=False, known_elevated=False, known_clean=True, insufficient=False) == "PROCEED"


def test_rss_does_not_automatically_pass_gate(monkeypatch):
    import us_profit_ticket_pipeline as ticket_pipeline

    monkeypatch.setattr(ticket_pipeline, "SKIP_LAST30DAYS", False)
    monkeypatch.setattr(
        ticket_pipeline,
        "resolve_company_profile",
        lambda symbol: {
            "symbol": symbol,
            "company_name": "NVIDIA Corp",
            "company_query_name": "NVIDIA",
            "company_name_source": "fixture",
            "provider_profile": {
                "symbol": symbol,
                "latest_price": 100.0,
                "prev_close": 100.0,
                "prev_close_session": "2026-09-03",
                "quote_session": "2026-09-03",
            },
        },
    )
    monkeypatch.setattr(
        ticket_pipeline,
        "run_full_research_panel",
        lambda *_args: {
            "risk_checklist": {"risk_verdict": "UNKNOWN", "recommendation": "NEED_MORE_EVIDENCE"},
            "quality_check": {"quality_verdict": "MODERATE"},
            "research_panel": {"panel_verdict": "MIXED"},
            "supply_chain_map": {},
            "replay_hypothesis": {},
        },
    )
    monkeypatch.setattr(
        ticket_pipeline,
        "run_last30days_topic",
        lambda topic: {
            "topic": topic,
            "returncode": 0,
            "payload": {
                "items_by_source": {"yahoo_finance_rss": [{"title": "NVDA headline"}]},
                "ranked_candidates": [{
                    "title": "NVDA guidance",
                    "source": "yahoo_finance_rss",
                    "final_score": 0.9,
                    "freshness": 0.9,
                    "source_quality": 0.4,
                    "primary_source": False,
                }],
                "clusters": [],
                "artifacts": {"resolved": {"entity": "NVDA"}},
            },
        },
    )
    monkeypatch.setattr(ticket_pipeline, "candidate_enhanced_urls", lambda symbol: {"quote_detail": symbol, "news_detail": symbol, "company_detail": symbol})
    monkeypatch.setattr(ticket_pipeline, "information_coverage_audit", lambda symbol: {"symbol": symbol})
    monkeypatch.setattr(
        ticket_pipeline,
        "score_evidence_item",
        lambda item, company_profile, focus: {
            "title": item["title"],
            "snippet": "",
            "relevance_type": "relevant",
            "relevance_score": 0.95,
            "relevance_reason": "matched",
            "matched_term": "NVDA",
        },
    )
    row = {
        "symbol": "NVDA",
        "close": 100.0,
        "adj_close": 100.0,
        "volume": 1_000_000.0,
        "market_score": 0.9,
        "market_rank": 1,
        "prior_20d_momentum": 0.12,
        "five_day_acceleration": 0.02,
        "relative_strength_vs_equal_weight": 0.05,
        "volume_confirmation_ratio": 0.4,
        "confirmation_score": 1.0,
        "reversal_signal": 0,
        "intraday_momentum": 0.01,
        "blowoff_risk": "",
        "capital_score": 0.0,
        "statistical_score": 0.0,
        "combined_score": 0.0,
        "large_participant_footprint_score": 0.0,
        "raw_market_score": 0.9,
        "market_rule_flags": "",
        "market_rule_adjustment": 0.0,
        "median_dollar_volume_20d": 2_000_000.0,
        "closing_strength_5d": 0.8,
        "volume_weighted_momentum": 0.1,
        "volume_trend_20d": 1.0,
        "prior_5d_momentum": 0.08,
        "blended_score": 0.9,
        "footprint_factor_coverage": 1.0,
        "footprint_factor_contributions": {},
        "market_participation_score": 0.7,
        "breakout_score": 0.8,
    }
    record = build_candidate_record(row, __import__("pandas").Timestamp("2026-09-03"), market_cutoff=5)
    assert record["research_gate"]["rss_cannot_auto_pass"] is True
    assert record["research_gate"]["weak_rss"] is True
    assert record["research_gate"]["research_evidence"] is False
    assert record["classification"] != "CANDIDATE_FOR_PAPER_REVIEW"
