from __future__ import annotations

from datetime import datetime

from market_calendar import BEIJING_TZ, CALENDAR
from research.boundary import validate
from research.contracts import independent_scores
from research.memory import portfolio_concentration
from research.metric_semantics import risk_manager_recommendation
from research.temporal import classify_bar, daily_bar_gate
from research_panel import run_full_research_panel
from us_profit_ticket_pipeline import quote_cross_check


def test_legacy_panel_cannot_bypass_research_os():
    research = run_full_research_panel(
        "NVDA",
        {"prior_20d_momentum": 0.12, "five_day_acceleration": 0.01, "relative_strength_vs_equal_weight": 0.02, "volume_confirmation_ratio": 0.4},
        {"status": "missing", "relevance_score": 0.0},
        {"status": "missing", "relevance_score": 0.0},
        {},
    )
    assert research["canonical_owner"] == "scripts.research"
    assert research["compatibility_adapter"] is True


def test_unknown_risk_is_not_green_or_proceed():
    assert risk_manager_recommendation(insufficient=True, known_blocked=False, known_elevated=False, known_clean=False) == "NEED_MORE_EVIDENCE"


def test_realtime_and_intraday_are_not_daily():
    assert daily_bar_gate(classify_bar(bar_type="SNAPSHOT", is_complete=False)) is False
    assert daily_bar_gate(classify_bar(bar_type="INTRADAY_PARTIAL", is_complete=False)) is False
    assert daily_bar_gate(classify_bar(bar_type="DAILY_COMPLETE", is_complete=True)) is True


def test_monday_maps_to_friday_and_cross_check_requires_same_session():
    monday = datetime(2026, 9, 7, 5, tzinfo=BEIJING_TZ)
    assert CALENDAR.previous_completed_session(monday).isoformat() == "2026-09-04"
    result = quote_cross_check(100.0, {"prev_close": 100.0, "latest_price": 100.0})
    assert result["data_source_mismatch_reason"] == "CROSS_CHECK_NOT_COMPARABLE"


def test_composite_coverage_and_missing_weight_not_zero():
    scores = independent_scores({"score": 0.9}, None, None, {"score": 0.8})
    assert scores["coverage"] == 0.5
    assert scores["readiness"] == "PARTIAL"
    incomplete = portfolio_concentration(["NVDA", "MSFT"], {"NVDA": 0.4})
    assert incomplete["concentration_status"] == "INCOMPLETE"
    assert incomplete["top3_concentration"] == "UNKNOWN"


def test_research_output_must_pass_boundary_validate():
    payload = validate({"produces_pick": False, "allow_trade": False, "classification": "RESEARCH_ONLY"})
    assert payload["status"] == "RESEARCH_ONLY"
    assert payload["ranking_owner"] == "observable_footprint_v1"
