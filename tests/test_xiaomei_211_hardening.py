from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from market_calendar import CALENDAR, BEIJING_TZ, closed_us_session_date, is_trading_day
from research.contracts import independent_scores
from research.fundamentals import company_fundamentals, earnings_intelligence, sec_filing
from research.industry import historical_universe_eligible, universe_as_of, universe_snapshot
from research.memory import portfolio_concentration, portfolio_context
from research.metric_semantics import decode_metric_value, normalize_metric, risk_manager_recommendation
from research.outcomes import independent_price_outcomes
from research.providers import GapSECDataProvider
from research.temporal import classify_bar, daily_bar_gate, historical_claim_eligible, temporal_record
from research_panel import build_quality_check, build_risk_checklist, build_replay_hypothesis, run_full_research_panel
from us_profit_ticket_pipeline import (
    _enrich_panels_with_realtime,
    bday_date,
    quote_cross_check,
)
from xiaomei_scheduler import closed_us_session_date as scheduler_closed_session


def test_legacy_panel_is_compatibility_adapter():
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
    assert research["replay_hypothesis"]["status"] == "UNCALIBRATED_HYPOTHESIS"
    assert research["replay_hypothesis"]["heuristic_confidence"] is not None
    assert "prediction_confidence" not in research["replay_hypothesis"]


def test_missing_risk_is_unknown_not_green():
    risk = build_risk_checklist(
        "NVDA",
        {"status": "missing"},
        {"status": "missing"},
        {},
        {"latest_price": None},
    )
    for name in ("short_interest", "dilution_risk", "debt_covenant", "earnings_quality", "insider_selling", "regulatory_risk", "concentration_risk"):
        assert risk["checks"][name]["status"] == "UNKNOWN"
        assert risk["checks"][name]["flag"] == "GRAY"
        assert risk["checks"][name]["risk_known"] is False
        assert risk["checks"][name]["value"] is None
    assert risk["recommendation"] == "NEED_MORE_EVIDENCE"
    assert risk["risk_verdict"] != "CLEAN"


def test_unknown_risk_does_not_proceed():
    assert risk_manager_recommendation(known_blocked=False, known_elevated=False, known_clean=False, insufficient=True) == "NEED_MORE_EVIDENCE"
    assert risk_manager_recommendation(known_blocked=False, known_elevated=False, known_clean=True, insufficient=False) == "PROCEED"


def test_quality_uses_metric_registry_not_raw_units():
    quality = build_quality_check("NVDA", {"roe": 0.23, "pe_ttm": 18, "dividend_yield": 0.02})
    assert quality["metric_registry"] == "research.metric_semantics.REGISTRY"
    assert 0 <= quality["scores"]["roe"] <= 1
    mixed = decode_metric_value(23, "percent_0_100")
    ratio = decode_metric_value(0.23, "ratio_0_1")
    assert mixed == pytest.approx(0.23)
    assert ratio == pytest.approx(0.23)
    assert normalize_metric("roe", 23) is None


def test_monday_beijing_maps_to_friday_session():
    monday = datetime(2026, 9, 7, 5, tzinfo=BEIJING_TZ)
    assert closed_us_session_date(monday) == date(2026, 9, 4)
    assert is_trading_day(date(2026, 9, 4)) is True
    session = CALENDAR.pipeline_session(monday)
    assert session["target_session"] == "2026-09-04"
    assert session["session_status"] == "COMPLETED"
    holiday = datetime(2026, 7, 4, 5, tzinfo=BEIJING_TZ)
    assert scheduler_closed_session(holiday) == date(2026, 7, 2)


def test_realtime_does_not_pollute_daily_bars():
    idx = pd.to_datetime(["2026-09-03"])
    close = pd.DataFrame({"NVDA": [100.0]}, index=idx)
    adj = close.copy()
    long_panel = pd.DataFrame({"date": ["2026-09-03"], "symbol": ["NVDA"], "Close": [100.0]})
    out_close, out_adj, out_long = _enrich_panels_with_realtime(close, adj, long_panel, ["NVDA"])
    assert list(out_close.index) == list(close.index)
    assert len(out_long) == 1
    bar = classify_bar(bar_type="INTRADAY_PARTIAL", is_complete=False)
    assert bar["usable_for_daily_factors"] is False
    assert daily_bar_gate(bar) is False
    assert classify_bar(bar_type="DAILY_COMPLETE", is_complete=True)["usable_for_daily_ranking"] is True


def test_historical_claim_as_of_contract():
    record = temporal_record(published_at="2026-01-01", effective_date="2026-01-02", retrieved_at="2026-09-01", as_of="2026-06-01")
    assert record["published_at_is_not_retrieved_at"] is True
    ok = historical_claim_eligible(record, as_of="2026-06-01")
    assert ok["eligible"] is True
    assert ok["retrieved_at_after_as_of_is_not_violation"] is True
    blocked = historical_claim_eligible({"published_at": "2026-07-01", "effective_date": "2026-07-01"}, as_of="2026-06-01")
    assert blocked["eligible"] is False


def test_provider_requires_symbol_as_of():
    gap = GapSECDataProvider()
    filing = sec_filing({}, provider=gap)
    assert filing["status"] in {"DATA_GAP", "ERROR"}
    assert filing.get("reason") == "symbol required" or "ticker" in filing.get("data_gaps", [])
    filled = company_fundamentals({}, provider=gap, symbol="NVDA", as_of="2024-06-01")
    assert filled["symbol"] == "NVDA"
    assert filled["as_of"] == "2024-06-01"
    earnings = earnings_intelligence({}, provider=gap, symbol="NVDA", as_of="2024-06-01")
    assert earnings["status"] == "DATA_GAP"


def test_universe_as_of_survivorship():
    rows = [
        universe_snapshot(universe_name="CORE_UNIVERSE", symbol="OLD", effective_from="2023-01-01", effective_to="2024-12-31", source="fixture", source_url="https://example.test/2024"),
        universe_snapshot(universe_name="CORE_UNIVERSE", symbol="NEW", effective_from="2025-01-01", source="fixture", source_url="https://example.test/2026"),
        universe_snapshot(universe_name="CORE_UNIVERSE", symbol="KEPT", effective_from="2023-01-01", source="fixture", source_url="https://example.test/all"),
    ]
    assert "OLD" in universe_as_of(rows, as_of="2024-06-01")
    assert "NEW" not in universe_as_of(rows, as_of="2024-06-01")
    assert historical_universe_eligible("OLD", rows, as_of="2024-06-01") is True
    assert historical_universe_eligible("NEW", rows, as_of="2024-06-01") is False
    assert historical_universe_eligible("OLD", rows, as_of="2026-01-01") is False
    assert historical_universe_eligible("KEPT", rows, as_of="2026-01-01") is True


def test_quote_cross_check_same_session_only():
    missing_session = quote_cross_check(100.0, {"prev_close": 102.0, "latest_price": 103.0})
    assert missing_session["data_source_mismatch_reason"] == "CROSS_CHECK_NOT_COMPARABLE"
    mismatch = quote_cross_check(
        100.0,
        {"prev_close": 102.0, "latest_price": 103.0, "prev_close_session": "2026-09-03"},
        historical_session="2026-09-03",
        quote_session="2026-09-03",
        historical_symbol="NVDA",
        quote_symbol="NVDA",
        time_basis="close",
        quote_time_basis="prev_close",
    )
    assert mismatch["quote_cross_check_basis"] == "prev_close"
    assert round(mismatch["quote_cross_check_gap_pct"], 4) == 0.02
    incomparable = quote_cross_check(
        100.0,
        {"prev_close": 100.0, "latest_price": 100.0},
        historical_session="2026-09-03",
        quote_session="2026-09-04",
        historical_symbol="NVDA",
        quote_symbol="NVDA",
    )
    assert incomparable["data_source_mismatch_reason"] == "CROSS_CHECK_NOT_COMPARABLE"


def test_portfolio_already_owned_is_not_overweight():
    notes = [{"tickers": ["NVDA"], "kinds": ["position"], "note_kind": "holding", "effective_date": "2026-01-01", "position_weight": None}]
    context = portfolio_context(notes, as_of="2026-06-01", symbol="NVDA", historical=True)
    assert context["already_owned"] is True
    assert context["overweight"] is False
    assert context["already_owned_is_not_overweight"] is True
    incomplete = portfolio_concentration(["NVDA", "MSFT"], {"NVDA": 0.4})
    assert incomplete["concentration_status"] == "INCOMPLETE"
    assert incomplete["top3_concentration"] == "UNKNOWN"


def test_research_composite_exposes_coverage():
    scores = independent_scores({"score": 0.9}, None, None, {"score": 0.8})
    assert scores["score"] == pytest.approx(0.85)
    assert scores["coverage"] == 0.5
    assert scores["brain_count"] == 2
    assert scores["brain_total"] == 4
    assert scores["readiness"] == "PARTIAL"
    assert scores["not_fully_validated"] is True


def test_independent_outcomes_per_horizon():
    dates = pd.bdate_range("2026-01-02", periods=20)
    frame = pd.DataFrame({
        "date": dates,
        "open": 100,
        "high": 102,
        "low": 99,
        "close": [100 + i for i in range(20)],
    })
    outcome = independent_price_outcomes(frame, as_of_date=dates[9].date())
    assert outcome["horizons"][1]["complete"] is True
    assert outcome["MFE_T1"] is not None
    short = independent_price_outcomes(frame.iloc[:12], as_of_date=dates[9].date())
    assert short["horizons"][1]["complete"] is True
    assert short["horizons"][10]["complete"] is False
    assert short["return_10d"] is None
    assert short["missing_horizon_does_not_invalidate_available"] is True
    assert short["price_basis"] in {"RAW", "ADJUSTED"}


def test_forward_dates_use_us_market_calendar():
    # 2026-07-02 is Thursday; Friday 07-03 is Independence Day observed.
    assert bday_date(pd.Timestamp("2026-07-02"), 1) == "2026-07-06"


def test_pipeline_lock_exists():
    script = Path(__file__).resolve().parents[1] / "scripts" / "daily_pipeline.sh"
    text = script.read_text()
    assert "daily-pipeline.lock" in text
    assert "acquire_lock" in text
    assert "skip_if_completed" in text
    assert "step_status" in text
    assert "artifact_hash" in text
