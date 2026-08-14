from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from us_profit_ticket_pipeline import build_forward_tracking_rows, build_summary_md, quote_cross_check
from xiaomei_scheduler import BEIJING_TZ, PIPELINE_SCHEDULE_DAYS, closed_us_session_date, is_trading_day


def _candidate_row() -> dict:
    return {
        "ticket_rank": 1,
        "symbol": "NVDA",
        "company_name": "NVIDIA Corp",
        "company_name_source": "eastmoney_us",
        "market_data_source": "Yahoo Finance historical kline + EastMoney US realtime quote",
        "kline_source": "Yahoo Finance historical kline",
        "quote_source": "EastMoney US realtime/delayed quote + kline",
        "quote_source_status": "ok",
        "quote_cross_check_basis": "prev_close",
        "quote_cross_check_price": 140.0,
        "quote_cross_check_gap_pct": 0.0,
        "data_source_mismatch": False,
        "data_source_mismatch_reason": "ok",
        "latest_price": 141.2,
        "prev_close": 140.0,
        "intraday_pct_chg": 0.00857,
        "raw_market_score": 0.8,
        "market_score": 0.82,
        "market_rule_flags": "",
        "ticket_score": 1.08,
        "catalyst_score": 0.21,
        "research_only": True,
        "allow_trade": False,
        "auto_order": False,
        "no_broker_api": True,
        "narrative_status": "found_relevant",
        "business_status": "found_relevant",
        "evidence_gate_status": "CANDIDATE_FOR_PAPER_REVIEW",
        "classification": "CANDIDATE_FOR_PAPER_REVIEW",
        "narrative_top_title": "NVIDIA guidance raises AI demand catalyst",
        "business_top_title": "Cloud customer orders expand",
        "narrative_topic": "NVDA NVIDIA stock catalyst earnings news",
        "business_topic": "NVDA NVIDIA orders demand backlog guidance revenue customer contract",
        "narrative_ranked_candidate_count": 2,
        "business_ranked_candidate_count": 2,
        "narrative_returncode": 0,
        "business_returncode": 0,
        "evidence_gap_reason": "paper_review_gate_passed",
        "quality_check": {"quality_verdict": "MODERATE", "overall_quality_score": 0.55, "scores": {"roe": 0.8}},
        "risk_checklist": {"risk_verdict": "CLEAN", "red_count": 0, "yellow_count": 0, "checks": {"liquidity": {"flag": "GREEN", "detail": "amount=100000000"}}},
        "research_panel": {"panel_verdict": "NEUTRAL", "positive_signals": 2, "negative_signals": 0, "agents": {"news_analyst": {"summary": "Relevant news catalysts found"}}},
        "supply_chain_map": {"supply_chain_summary": "AI/cloud themes identified", "themes_found": ["AI", "cloud"]},
        "replay_hypothesis": {"hypothesis": "research observation only"},
        "market_rank": 1,
        "prior_20d_momentum": 0.12,
        "five_day_acceleration": 0.02,
        "volume_confirmation_ratio": 0.3,
        "relative_strength_vs_equal_weight": 0.05,
    }


def test_quote_cross_check_flags_large_source_mismatch():
    result = quote_cross_check(100.0, {"prev_close": 102.0, "latest_price": 103.0})

    assert result["quote_cross_check_basis"] == "prev_close"
    assert round(result["quote_cross_check_gap_pct"], 4) == 0.02
    assert result["data_source_mismatch"] is True
    assert result["data_source_mismatch_reason"] == "DATA_SOURCE_MISMATCH"


def test_build_forward_tracking_rows_uses_adj_close_as_split_aware_entry_price():
    row = _candidate_row()
    row["symbol"] = "KLAC"
    row["close"] = 2263.169921875
    row["adj_close"] = 213.563995
    row["as_of_date"] = "2026-06-10"

    tracking_rows = build_forward_tracking_rows([row], "2026-06-10-open")

    assert tracking_rows[0]["as_of_close"] == 213.563995
    assert tracking_rows[0]["as_of_adj_close"] == 213.563995


def test_summary_ticket_card_is_research_only_without_ashare_or_order_terms():
    row = _candidate_row()
    package = {
        "market_summary": {
            "as_of_date": "2026-06-13",
            "market_data_source": "Yahoo Finance historical kline + EastMoney US realtime quote",
            "kline_source": "Yahoo Finance historical kline",
            "quote_source": "EastMoney US realtime/delayed quote + kline",
            "equal_weight_20d_benchmark": 0.03,
            "market_feature_medians": {
                "prior_20d_momentum": 0.04,
                "five_day_acceleration": 0.01,
                "volume_confirmation_ratio": 0.1,
                "relative_strength_vs_equal_weight": 0.0,
            },
            "market_feature_spreads": {"market_score_p90": 0.8},
        },
        "top_candidates": [row],
        "candidate_rows": [row],
        "market_rows": [row],
        "source_config": {"source_name": "explicit"},
        "source_mode": "live",
        "selected_universe_key": "explicit",
        "source_universe_total_symbols": 1,
        "source_universe_included_symbols": 1,
        "period_used": "3mo",
        "final_classification": "CANDIDATE_FOR_PAPER_REVIEW",
        "paper_review_count": 1,
        "market_watchlist_count": 0,
        "artifact_paths": {
            "summary": "summary.md",
            "metrics": "metrics.json",
            "candidates": "candidates.csv",
            "forward_tracking": "tracking.csv",
            "runtime_context": "runtime.json",
            "runtime_ledger": "runtime.jsonl",
        },
        "forward_tracking_rows": [],
    }

    summary = build_summary_md(package, "2026-06-13")

    assert "research_only=true" in summary
    assert "allow_trade=false" in summary
    assert "auto_order=false" in summary
    assert "no_broker_api=true" in summary
    assert "kline_source: Yahoo Finance historical kline" in summary
    assert "quote_source: EastMoney US realtime/delayed quote + kline" in summary
    assert "data_source_mismatch_threshold" in summary
    assert "Catalyst Summary" in summary
    for forbidden in ["涨停", "连板", "龙虎榜", "place_order", "append_ledger"]:
        assert forbidden not in summary


def test_post_close_beijing_time_maps_to_prior_us_session():
    post_close = datetime(2026, 8, 8, 5, tzinfo=BEIJING_TZ)

    assert closed_us_session_date(post_close) == date(2026, 8, 7)
    assert is_trading_day(closed_us_session_date(post_close)) is True
    assert PIPELINE_SCHEDULE_DAYS == "tue-sat"


def test_post_close_pipeline_skips_us_market_holidays():
    post_close_after_independence_day = datetime(2026, 7, 4, 5, tzinfo=BEIJING_TZ)

    assert closed_us_session_date(post_close_after_independence_day) == date(2026, 7, 3)
    assert is_trading_day(closed_us_session_date(post_close_after_independence_day)) is False
