from datetime import datetime, timedelta
from pathlib import Path
import sys

from zoneinfo import ZoneInfo

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from realtime_runner import (
    MAX_QUOTE_AGE_SECONDS,
    borrow_state,
    evaluate_short_model,
    is_us_regular_session,
    quote_is_fresh,
    score_intraday_quote,
    score_intraday_short_quote,
)


ET = ZoneInfo("America/New_York")


def test_regular_session_uses_new_york_market_hours():
    assert is_us_regular_session(datetime(2026, 8, 17, 9, 30, tzinfo=ET))
    assert is_us_regular_session(datetime(2026, 8, 17, 15, 59, tzinfo=ET))
    assert not is_us_regular_session(datetime(2026, 8, 17, 9, 29, tzinfo=ET))
    assert not is_us_regular_session(datetime(2026, 8, 17, 16, 0, tzinfo=ET))
    assert not is_us_regular_session(datetime(2026, 8, 16, 11, 0, tzinfo=ET))


def test_quote_freshness_requires_a_recent_provider_timestamp():
    now = datetime(2026, 8, 17, 10, 0, tzinfo=ET)
    fresh = {"as_of": (now - timedelta(seconds=MAX_QUOTE_AGE_SECONDS)).isoformat()}
    stale = {"as_of": (now - timedelta(seconds=MAX_QUOTE_AGE_SECONDS + 1)).isoformat()}

    assert quote_is_fresh(fresh, now)
    assert not quote_is_fresh(stale, now)
    assert not quote_is_fresh({}, now)


def test_intraday_score_uses_completed_context_and_quote_range_only():
    score, components = score_intraday_quote(
        {"final_score": 0.8},
        {
            "latest_price": 103.0,
            "prev_close": 100.0,
            "high": 104.0,
            "low": 100.0,
        },
    )

    assert 0.0 < score <= 1.0
    assert components["daily_context"] == 0.8
    assert components["pct_change"] == 0.03
    assert components["range_position"] == 0.75


def test_short_score_is_independent_and_requires_explicit_borrow_evidence():
    score, components = score_intraday_short_quote(
        {"final_score": 0.2},
        {
            "latest_price": 96.0,
            "prev_close": 100.0,
            "high": 101.0,
            "low": 95.0,
        },
    )

    assert score > 0.0
    assert components["pct_change"] == -0.04
    assert borrow_state({})["reason"] == "UNAVAILABLE_NO_BORROW_SOURCE"
    assert borrow_state({"borrow_available": True, "borrow_rate_daily": 0.001}) == {
        "available": True,
        "rate_daily": 0.001,
        "reason": "OBSERVED",
    }


def test_short_model_is_audited_but_cannot_open_a_position():
    now = datetime(2026, 8, 17, 10, 0, tzinfo=ET)
    decision, status, reason, score, components = evaluate_short_model(
        {"final_score": 0.2},
        {
            "as_of": now.isoformat(),
            "latest_price": 96.0,
            "prev_close": 100.0,
            "high": 101.0,
            "low": 95.0,
            "borrow_available": True,
            "borrow_rate_daily": 0.001,
        },
        now,
    )

    assert decision == "PAPER_SHORT_REJECTED"
    assert status == "UNVALIDATED_PAPER_SHORT"
    assert reason == "short_model_requires_completed_sample_gate"
    assert score is not None
    assert components["borrow"]["available"] is True
