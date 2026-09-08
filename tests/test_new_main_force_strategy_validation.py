from __future__ import annotations

from datetime import date

import pandas as pd

import new_main_force_strategy_validation as nmf
from research.boundary import PRODUCTION_BOUNDARY


def test_identity_lock_is_capital_behavior_v2_not_observable_footprint():
    lock = nmf.identity_lock()
    assert lock["NEW_STRATEGY_ID"] == "capital_behavior_v2"
    assert lock["NEW_STRATEGY_VERSION"] == "capital_behavior_v2"
    assert lock["NEW_STRATEGY_STATUS"] == "UNVALIDATED_NO_FIXED_CHAIN"
    assert "0.55*capital_strength" in lock["NEW_STRATEGY_FORMULA"]
    assert lock["NEW_RANKING_KEY"].startswith("capital_behavior_score")
    assert PRODUCTION_BOUNDARY["strategy"] == "observable_footprint_v1"
    assert nmf.PRODUCTION_RANKING_OWNER == "observable_footprint_v1"
    assert nmf.NEW_STRATEGY_ID != PRODUCTION_BOUNDARY["strategy"]


def test_fingerprint_covers_capital_source_files():
    payload = nmf.fingerprint_payload()
    for rel in nmf.SOURCE_FILES:
        assert rel in payload["source_sha256"]
        assert len(payload["source_sha256"][rel]) == 64
    assert payload["fingerprint_sha256"]
    assert payload["do_not_mutate_during_replay"] is True


def test_quality_filter_rejects_missing_as_of_bar():
    history = pd.DataFrame(
        {
            "trade_date": [date(2026, 7, 1), date(2026, 7, 2)],
            "close": [10.0, 11.0],
            "volume": [1_000_000, 1_000_000],
        }
    )
    missing = nmf.quality_filter_asof_symbol(history, date(2026, 7, 3))
    assert missing["include"] is False
    assert "not_in_as_of_session" in missing["reasons"]


def test_score_symbol_does_not_use_future_bars():
    rows = []
    for i in range(40):
        day = pd.Timestamp("2026-01-02") + pd.Timedelta(days=i)
        close = 10.0 + i * 0.1
        rows.append(
            {
                "trade_date": day.date(),
                "open": close,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close,
                "volume": 2_000_000,
            }
        )
    history = pd.DataFrame(rows)
    as_of = history["trade_date"].iloc[25]
    scored = nmf.score_symbol(
        history,
        as_of,
        relative_strength=0.01,
        regime_alignment=0.5,
        previous_state=None,
        previous_duration=0,
    )
    assert scored["available"] is True
    assert scored["statistical_score_forced_zero"] == 0.0
    assert scored["model_version"] == "capital_behavior_v2"
    later = history[history["trade_date"] > as_of]
    assert not later.empty
    # Future close path is unused: as-of score must ignore later prices.
    mutated = history.copy()
    mutated.loc[mutated["trade_date"] > as_of, "close"] = 999.0
    rescore = nmf.score_symbol(
        mutated,
        as_of,
        relative_strength=0.01,
        regime_alignment=0.5,
        previous_state=None,
        previous_duration=0,
    )
    assert rescore["capital_behavior_score"] == scored["capital_behavior_score"]


def test_verdict_labels_are_closed_set():
    payload = {
        "strategy": {"top1": {"1": {"sample_count": 10, "expectancy": 0.01, "avg_return": 0.01, "profit_factor": 1.2}}},
        "walk_forward": {"holdout": {"sample_count": 3, "avg_return": 0.01, "profit_factor": 1.2}},
        "cost_stress": {"10": {"avg_return": 0.01}, "25": {"avg_return": 0.01}},
        "ranking": {"1": {"Top1": 0.01, "Top20pct": 0.01, "Bottom20pct": 0.0}},
        "baselines": {
            "equal_weight": {"1": {"avg_return": 0.0}},
            "random_top1": {"1": {"avg_return": 0.0}},
        },
        "coverage": {"full_asof_days": 40, "future_data_in_features": False},
    }
    verdict = nmf.decide_verdict(payload)
    assert verdict["NEW_MAIN_FORCE_STRATEGY_PROFITABILITY"] in {
        "VALIDATED",
        "NOT_VALIDATED",
        "DATA_INVALID",
        "INSUFFICIENT_SAMPLE",
    }
    assert verdict["NEW_MAIN_FORCE_STRATEGY_PROFITABILITY"] == "INSUFFICIENT_SAMPLE"


def test_horizon_metrics_drops_nan():
    metrics = nmf.horizon_metrics([0.10, float("nan"), None, -0.05])
    assert metrics["sample_count"] == 2
    assert abs(metrics["avg_return"] - 0.025) < 1e-12


def test_horizon_metrics_match_required_fields():
    metrics = nmf.horizon_metrics([0.10, -0.05, 0.00, 0.02, -0.15])
    assert metrics["sample_count"] == 5
    assert metrics["wins"] == 2
    assert metrics["losses"] == 2
    assert abs(metrics["avg_loss"] - ((-0.05 + -0.15) / 2)) < 1e-12
    assert "best_trade" in metrics and "worst_trade" in metrics
    assert metrics["best_trade"] == 0.10
    assert metrics["worst_trade"] == -0.15
