from __future__ import annotations

from datetime import date

import pandas as pd

import production_profitability_validation as ppv
from research.boundary import PRODUCTION_BOUNDARY
from research.sample_identity import DuplicateSampleError, sample_id


def test_frozen_strategy_identity_unchanged():
    freeze = ppv.freeze_snapshot()
    assert freeze["strategy"] == "observable_footprint_v1"
    assert freeze["strategy_status"] == "FROZEN"
    assert freeze["weights_status"] == "FROZEN"
    assert PRODUCTION_BOUNDARY["auto_weight_change"] == "OFF"
    assert PRODUCTION_BOUNDARY["broker"] == "NO_BROKER"
    assert PRODUCTION_BOUNDARY["live_order"] == "NO_LIVE_ORDER"


def test_current_ticket_score_uses_frozen_formula():
    assert ppv.current_ticket_score(0.80, 0.20) == 0.75 * 0.80 + 0.25 * 0.20
    assert ppv.current_ticket_score(0.40, None) == 0.75 * 0.40


def test_horizon_metrics_use_loss_only_average_loss():
    metrics = ppv.horizon_metrics([0.10, -0.05, 0.00, 0.02, -0.15])
    assert metrics["sample_count"] == 5
    assert metrics["wins"] == 2
    assert metrics["losses"] == 2
    assert metrics["flats"] == 1
    assert abs(metrics["avg_loss"] - ((-0.05 + -0.15) / 2)) < 1e-12
    assert metrics["avg_loss"] < 0
    expected_pf = (0.10 + 0.02) / abs(-0.05 + -0.15)
    assert abs(metrics["profit_factor"] - expected_pf) < 1e-12
    win_rate = 2 / 5
    loss_rate = 2 / 5
    expectancy = win_rate * ((0.10 + 0.02) / 2) + loss_rate * ((-0.05 + -0.15) / 2)
    assert abs(metrics["expectancy"] - expectancy) < 1e-12


def test_sample_identity_rejects_duplicates():
    first = sample_id(ticket_id=12, replay_horizon=1, replay_date="2026-08-18")
    second = sample_id(ticket_id=12, replay_horizon=1, replay_date="2026-08-18")
    assert first == second
    seen = {first: True}
    assert second in seen
    try:
        raise DuplicateSampleError(second)
    except DuplicateSampleError as exc:
        assert str(exc) == second


def test_version_bucket_does_not_promote_legacy():
    current = ppv.classify_version(
        {
            "strategy_version": "observable_footprint_v1",
            "version_status": "VERSIONED",
            "git_commit": ppv.CURRENT_GIT_COMMIT,
            "research_run_id": 146,
        }
    )
    reconstructed = ppv.classify_version(
        {
            "strategy_version": None,
            "version_status": "RECONSTRUCTED_FROM_DATABASE",
            "git_commit": "37693ec16f8ebbffdd29d758fa48ec458023b93b",
            "research_run_id": 143,
        }
    )
    unknown = ppv.classify_version(
        {
            "strategy_version": None,
            "version_status": None,
            "git_commit": None,
            "research_run_id": None,
        }
    )
    assert current == "CURRENT_VERSION"
    assert reconstructed == "LEGACY_VERSION"
    assert unknown == "UNKNOWN_VERSION"


def test_walk_forward_splits_recent_holdout():
    days = [date(2026, 6, 1) + __import__("datetime").timedelta(days=i) for i in range(10)]
    periods = ppv.split_periods(days)
    assert periods["holdout"]
    assert periods["holdout"][-1] == days[-1]
    assert max(periods["train"]) < min(periods["holdout"])


def test_cost_friction_is_subtracted_not_optimized():
    net = ppv.apply_friction([0.01, -0.01], 25)
    assert abs(net[0] - (0.01 - 0.0025)) < 1e-12
    assert abs(net[1] - (-0.01 - 0.0025)) < 1e-12


def test_price_mismatch_is_audited_not_a_hard_exclusion():
    trading_day = date(2026, 8, 18)
    mismatch = ppv.classify_sample_exclusion(
        output_date=trading_day,
        as_of_date=trading_day,
        check_status="completed",
        forward_return=0.01,
        as_of_close=100.0,
        kline_close=104.0,
        kline_adj_close=None,
        is_trading_day=True,
    )
    assert mismatch["exclude"] is False
    assert mismatch["hard"] == []
    assert "price_basis_mismatch" in mismatch["audit"]

    future = ppv.classify_sample_exclusion(
        output_date=date(2026, 6, 1),
        as_of_date=date(2026, 7, 25),
        check_status="completed",
        forward_return=0.01,
        as_of_close=100.0,
        kline_close=None,
        kline_adj_close=None,
        is_trading_day=True,
    )
    assert future["exclude"] is True
    assert "future_data_detected" in future["hard"]


def test_full_pool_requires_scored_candidates_not_factor_rows_alone():
    assert ppv.classify_pool_status(80, 3) == "SELECTED_TICKET_ONLY"
    assert ppv.classify_pool_status(80, 24) == "FULL_POOL"
    assert ppv.classify_pool_status(10, 24) == "SELECTED_TICKET_ONLY"


def _positive_metrics(n: int = 40) -> dict:
    return {
        "sample_count": n,
        "expectancy": 0.01,
        "avg_return": 0.01,
        "profit_factor": 1.5,
        "win_rate": 0.55,
    }


def _negative_metrics(n: int = 40) -> dict:
    return {
        "sample_count": n,
        "expectancy": -0.01,
        "avg_return": -0.01,
        "profit_factor": 0.7,
        "win_rate": 0.45,
    }


def test_verdict_does_not_use_legacy_plus_175():
    payload = {
        "anomalies": {
            "exclusion_rate": 0.1,
            "future_data_detected": 0,
            "duplicate_sample": 0,
            "price_basis_mismatch": 0,
            "mixed_price_basis_in_returns": 0,
            "adj_close_available": 10,
        },
        "realized": {"by_horizon": {"1": _negative_metrics()}},
        "reconstructed": {
            "full_pool_days": 40,
            "top1_t1": _negative_metrics(20),
        },
        "walk_forward": {"holdout": _negative_metrics(8)},
        "cost_sensitivity": {
            "reconstructed_top1_t1": {
                "25": _negative_metrics(),
                "50": _negative_metrics(),
            }
        },
        "version_counts": {"CURRENT_VERSION": 9},
    }
    verdict = ppv.decide_verdict(payload)
    assert verdict["profitability"] in {"NOT_PROFITABLE", "WEAK_EDGE"}
    assert verdict["profitability"] != "PROFITABLE"
    assert verdict["profitability_validated"] == "NO"


def test_historical_future_asof_does_not_invalidate_asof_reconstruction():
    payload = {
        "anomalies": {
            "exclusion_rate": 0.59,
            "future_data_detected": 218,
            "duplicate_sample": 0,
            "price_basis_mismatch": 276,
            "mixed_price_basis_in_returns": 0,
            "adj_close_available": 0,
        },
        "realized": {"by_horizon": {"1": _negative_metrics(121)}},
        "reconstructed": {
            "full_pool_days": 40,
            "top1_t1": _negative_metrics(40),
        },
        "walk_forward": {"holdout": _negative_metrics(8)},
        "cost_sensitivity": {
            "reconstructed_top1_t1": {
                "25": _negative_metrics(40),
                "50": _negative_metrics(40),
            }
        },
        "version_counts": {"CURRENT_VERSION": 9},
    }
    verdict = ppv.decide_verdict(payload)
    assert verdict["profitability"] == "NOT_PROFITABLE"
    assert verdict["profitability_validated"] == "NO"
    assert "historical_realized_future_data_detected" in verdict["reasons"]
    assert "asof_price_basis_unadjusted_close" in verdict["reasons"]
    assert "future_data_detected" not in verdict["reasons"]
    assert "adjusted_close_unavailable" not in verdict["reasons"]


def test_no_full_asof_panel_is_data_invalid():
    payload = {
        "anomalies": {
            "exclusion_rate": 0.1,
            "future_data_detected": 0,
            "duplicate_sample": 0,
            "price_basis_mismatch": 0,
            "mixed_price_basis_in_returns": 0,
            "adj_close_available": 0,
        },
        "realized": {"by_horizon": {"1": _positive_metrics()}},
        "reconstructed": {
            "full_pool_days": 0,
            "top1_t1": {"sample_count": 0, "expectancy": None, "avg_return": None, "profit_factor": None},
        },
        "walk_forward": {"holdout": _positive_metrics(8)},
        "cost_sensitivity": {"reconstructed_top1_t1": {"25": _positive_metrics(), "50": _positive_metrics()}},
        "version_counts": {"CURRENT_VERSION": 9},
    }
    verdict = ppv.decide_verdict(payload)
    assert verdict["profitability"] == "DATA_INVALID"
    assert verdict["profitability_validated"] == "NO"
    assert "no_full_asof_panel_days" in verdict["reasons"]


def test_quality_filter_requires_same_day_bar_and_floors():
    as_of = date(2026, 6, 1)
    short = pd.DataFrame(
        {
            "trade_date": [as_of],
            "close": [10.0],
            "volume": [1_000_000],
            "adj_close": [None],
        }
    )
    decision = ppv.quality_filter_asof_symbol(short, as_of)
    assert decision["include"] is False
    assert "history_days_short" in decision["reasons"]

    missing_session = pd.DataFrame(
        {
            "trade_date": [date(2026, 5, 29)],
            "close": [10.0],
            "volume": [2_000_000],
            "adj_close": [None],
        }
    )
    skipped = ppv.quality_filter_asof_symbol(missing_session, as_of)
    assert skipped["include"] is False
    assert "not_in_as_of_session" in skipped["reasons"]

    history = pd.DataFrame(
        {
            "trade_date": [date(2025, 8, 1) + __import__("datetime").timedelta(days=i) for i in range(220)]
            + [as_of],
            "close": [10.0] * 221,
            "volume": [1_000_000] * 221,
            "adj_close": [None] * 221,
        }
    )
    ok = ppv.quality_filter_asof_symbol(history, as_of)
    assert ok["include"] is True


def test_classify_asof_pool_status_uses_quality_filtered_count():
    assert ppv.classify_asof_pool_status(19) == "INCOMPLETE_ASOF_PANEL"
    assert ppv.classify_asof_pool_status(20) == "FULL_ASOF_PANEL"
    assert ppv.classify_asof_pool_status(73) == "FULL_ASOF_PANEL"


def test_asof_ranking_uses_frozen_formula_with_catalyst_zero():
    assert ppv.current_ticket_score(0.80, 0.0) == 0.75 * 0.80
    assert ppv.ASOF_CATALYST_POLICY == "unavailable_as_of_equals_zero"


def test_asof_session_return_uses_calendar_due_date_not_next_available_bar():
    as_of = date(2026, 6, 1)
    history = pd.DataFrame(
        {
            "trade_date": [as_of, date(2026, 6, 3), date(2026, 6, 4)],
            "close": [100.0, 110.0, 102.0],
        }
    )
    outcome = ppv.asof_session_return(history, as_of, 1)
    assert outcome["return"] is None
    assert outcome["source"] == "missing_future_price"


def test_period_metrics_accepts_asof_date():
    samples = [
        {"as_of_date": date(2026, 6, 1), "t1": 0.02},
        {"as_of_date": date(2026, 6, 2), "t1": -0.01},
        {"output_date": date(2026, 6, 1), "t1": 0.50},
    ]
    metrics = ppv.period_metrics(samples, [date(2026, 6, 1)], "t1")
    assert metrics["sample_count"] == 2
    assert abs(metrics["avg_return"] - 0.26) < 1e-12
