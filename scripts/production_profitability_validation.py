#!/usr/bin/env python3
"""Read-only profitability validation for frozen observable_footprint_v1.

Does not modify tickets, forward_tracking, weights, scoring, or strategy.
Owner of production ranking remains scripts/us_profit_ticket_pipeline.py.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
from sqlalchemy import text

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from db.engine import engine  # noqa: E402
from market_calendar import CALENDAR  # noqa: E402
from market_regime import classify_market_regime, get_regime_thresholds  # noqa: E402
from research.boundary import (  # noqa: E402
    PRODUCTION_BOUNDARY,
    RANKING_KEY,
    freeze_snapshot,
    strategy_is_frozen,
    weights_are_frozen,
)
from research.sample_identity import sample_id  # noqa: E402

STRATEGY = "observable_footprint_v1"
CURRENT_GIT_COMMIT = "bedb58e1f15ddc8d26b5860359e2bbd3640990c1"
TICKET_SCORE_MARKET_WEIGHT = 0.75
TICKET_SCORE_CATALYST_WEIGHT = 0.25
MIN_TICKET_SCORE = 0.3
HORIZONS = (1, 3, 5, 10)
FOOTPRINT_STOCK_WEIGHT = 0.85
FOOTPRINT_MARKET_WEIGHT = 0.15
COST_BPS = (0, 10, 25, 50)
MIN_FULL_POOL = 20
MIN_INDEPENDENT_SAMPLES = 30
HIGH_EXCLUSION_RATE = 0.40
SCORE_MATCH_ABS = 0.02
PRICE_MISMATCH_REL_THRESHOLD = 0.01
MIN_HISTORY_DAYS = 200
MIN_PRICE = 5.0
MIN_MEDIAN_DOLLAR_VOLUME = 5_000_000.0
ASOF_LOOKBACK_BARS = 40
ASOF_UNIVERSE_SOURCE = "daily_klines_as_of_membership"
ASOF_CATALYST_POLICY = "unavailable_as_of_equals_zero"
INDEX_UNIVERSE_STATUS = "DATA_GAP_NO_TRUE_HISTORICAL_MEMBERSHIP"
LEGACY_REFERENCE = {
    "source": "research/historical-backtest-report.md",
    "generated": "2026-06-18",
    "total_trades": 672,
    "win_rate": 0.569,
    "avg_return": 0.0175,
    "median_return": 0.0075,
    "profit_factor": 1.92,
    "note": "LEGACY_REFERENCE only. Not CURRENT observable_footprint_v1.",
}
OUTPUT_DIR = ROOT / "research" / "production-profitability"


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text_value = str(value)[:10]
    try:
        return date.fromisoformat(text_value)
    except ValueError:
        return None


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return number
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def readonly_query(sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params or {}).mappings().all()
        return [dict(row) for row in rows]


def percentile_rank(series: pd.Series) -> pd.Series:
    if series.dropna().empty:
        return pd.Series(index=series.index, dtype=float)
    return series.rank(pct=True, na_option="keep")


def classify_version(row: Mapping[str, Any]) -> str:
    strategy_version = str(row.get("strategy_version") or "").strip()
    version_status = str(row.get("version_status") or "").strip()
    git_commit = str(row.get("git_commit") or "").strip()
    if (
        strategy_version == STRATEGY
        and version_status == "VERSIONED"
        and git_commit == CURRENT_GIT_COMMIT
    ):
        return "CURRENT_VERSION"
    if strategy_version and strategy_version != STRATEGY:
        return "LEGACY_VERSION"
    if version_status in {"RECONSTRUCTED_FROM_DATABASE", "UNAVAILABLE_HISTORICAL"}:
        return "LEGACY_VERSION"
    if row.get("research_run_id") in (None, "") and not strategy_version:
        return "UNKNOWN_VERSION"
    if strategy_version == STRATEGY:
        return "CURRENT_VERSION"
    return "LEGACY_VERSION"


def current_ticket_score(market_score: float | None, catalyst_score: float | None) -> float | None:
    if market_score is None:
        return None
    catalyst = 0.0 if catalyst_score is None else catalyst_score
    return TICKET_SCORE_MARKET_WEIGHT * float(market_score) + TICKET_SCORE_CATALYST_WEIGHT * float(catalyst)


def classify_pool_status(factor_count: int, scored_candidate_count: int) -> str:
    """Persisted-candidate reconstruction is SELECTED_TICKET_ONLY unless both
    factor rows and stored catalyst scores cover a full same-day pool.

    This path cannot prove CURRENT STRATEGY EDGE. As-of kline replay uses
    classify_asof_pool_status instead.
    """
    if factor_count >= MIN_FULL_POOL and scored_candidate_count >= MIN_FULL_POOL:
        return "FULL_POOL"
    return "SELECTED_TICKET_ONLY"


def classify_asof_pool_status(included_count: int) -> str:
    """FULL_ASOF_PANEL = as-of quality-filtered kline universe, not index membership."""
    if included_count >= MIN_FULL_POOL:
        return "FULL_ASOF_PANEL"
    return "INCOMPLETE_ASOF_PANEL"


def classify_sample_exclusion(
    *,
    output_date: date | None,
    as_of_date: date | None,
    check_status: str | None,
    forward_return: float | None,
    as_of_close: float | None,
    kline_close: float | None,
    kline_adj_close: float | None,
    is_trading_day: bool,
) -> dict[str, Any]:
    """Hard exclusions drop a sample. Price-basis mismatch is audited, not mixed.

    Returns stay on forward_tracking as_of_close → due_close. A kline disagreement
    does not rewrite the return and does not silently drop an internally consistent
    tracking row.
    """
    hard: list[str] = []
    audit: list[str] = []
    if as_of_date and output_date and as_of_date > output_date:
        hard.append("future_data_detected")
    if output_date is None or not is_trading_day:
        hard.append("invalid_date")
    if check_status != "completed" or forward_return is None:
        hard.append("missing_future_price")
    reference = kline_adj_close if kline_adj_close is not None else kline_close
    if reference is not None and as_of_close is not None:
        relative = abs(reference - as_of_close) / max(abs(as_of_close), 1e-9)
        if relative > PRICE_MISMATCH_REL_THRESHOLD:
            audit.append("price_basis_mismatch")
    return {
        "hard": hard,
        "audit": audit,
        "exclude": bool(hard),
    }


def quality_filter_asof_symbol(
    history: pd.DataFrame,
    as_of: date,
    *,
    min_history_days: int = MIN_HISTORY_DAYS,
    min_price: float = MIN_PRICE,
    min_median_dollar_volume: float = MIN_MEDIAN_DOLLAR_VOLUME,
) -> dict[str, Any]:
    visible = history[history["trade_date"] <= as_of].sort_values("trade_date")
    if visible.empty:
        return {"include": False, "reasons": ["no_as_of_bar"], "history_days": 0}
    last = visible.iloc[-1]
    if last["trade_date"] != as_of:
        return {
            "include": False,
            "reasons": ["not_in_as_of_session"],
            "history_days": int(len(visible)),
        }
    last_close = _as_float(last["close"])
    dollar = visible["close"] * visible["volume"]
    median_dollar = float(dollar.dropna().median()) if dollar.notna().any() else None
    reasons: list[str] = []
    if len(visible) < min_history_days:
        reasons.append("history_days_short")
    if last_close is None or last_close < min_price:
        reasons.append("price_floor")
    if median_dollar is None or median_dollar < min_median_dollar_volume:
        reasons.append("median_dollar_volume")
    return {
        "include": not reasons,
        "reasons": reasons,
        "history_days": int(len(visible)),
        "last_close": last_close,
        "median_dollar_volume": median_dollar,
        "adj_close_available": last.get("adj_close") is not None,
    }


def asof_session_return(history: pd.DataFrame, as_of: date, horizon: int) -> dict[str, Any]:
    ordered = history.sort_values("trade_date")
    as_of_rows = ordered[ordered["trade_date"] == as_of]
    if as_of_rows.empty:
        return {"return": None, "source": "missing_as_of_bar"}
    due = CALENDAR.add_trading_days(as_of, horizon)
    due_rows = ordered[ordered["trade_date"] == due]
    if due_rows.empty:
        return {"return": None, "source": "missing_future_price"}
    entry = _as_float(as_of_rows.iloc[0]["close"])
    exit_px = _as_float(due_rows.iloc[0]["close"])
    if entry is None or exit_px is None or entry <= 0:
        return {"return": None, "source": "missing_future_price"}
    return {
        "return": exit_px / entry - 1.0,
        "source": "kline_close_unadjusted",
        "due_date": due,
        "as_of_close": entry,
        "due_close": exit_px,
    }


def replay_asof_universe_day(as_of: date, bars: pd.DataFrame) -> dict[str, Any]:
    """Replay frozen observable_footprint_v1 on the as-of kline panel.

    Universe = names with a complete as-of bar that pass production quality
    floors. Catalyst is unavailable as-of, so catalyst_score = 0. Intraday
    quotes are not used. Feedback penalties are not used. Capital Brain does
    not alter ranking.
    """
    if bars.empty:
        return {"as_of_date": as_of, "status": "missing_klines", "pool_status": "INCOMPLETE_ASOF_PANEL", "rows": []}
    visible = bars[bars["trade_date"] <= as_of].copy()
    if visible.empty:
        return {"as_of_date": as_of, "status": "no_visible_bars", "pool_status": "INCOMPLETE_ASOF_PANEL", "rows": []}
    included: list[str] = []
    excluded: dict[str, Any] = {}
    for symbol, history in visible.groupby("symbol", sort=True):
        decision = quality_filter_asof_symbol(history, as_of)
        if decision["include"]:
            included.append(str(symbol))
        else:
            excluded[str(symbol)] = decision
    pool_status = classify_asof_pool_status(len(included))
    if len(included) < 10:
        return {
            "as_of_date": as_of,
            "status": "incomplete_universe",
            "pool_status": pool_status,
            "included_count": len(included),
            "excluded_count": len(excluded),
            "universe_source": ASOF_UNIVERSE_SOURCE,
            "index_universe_status": INDEX_UNIVERSE_STATUS,
            "catalyst_policy": ASOF_CATALYST_POLICY,
            "rows": [],
        }

    close_map: dict[str, pd.Series] = {}
    high_map: dict[str, pd.Series] = {}
    low_map: dict[str, pd.Series] = {}
    volume_map: dict[str, pd.Series] = {}
    for symbol in included:
        history = visible[visible["symbol"] == symbol].sort_values("trade_date")
        series_index = pd.DatetimeIndex(pd.to_datetime(history["trade_date"]))
        close_map[symbol] = pd.Series(history["close"].to_numpy(), index=series_index, dtype=float)
        high_map[symbol] = pd.Series(history["high"].to_numpy(), index=series_index, dtype=float)
        low_map[symbol] = pd.Series(history["low"].to_numpy(), index=series_index, dtype=float)
        volume_map[symbol] = pd.Series(history["volume"].to_numpy(), index=series_index, dtype=float)
    close_panel = pd.DataFrame(close_map).sort_index()
    high_panel = pd.DataFrame(high_map).reindex(close_panel.index)
    low_panel = pd.DataFrame(low_map).reindex(close_panel.index)
    volume_panel = pd.DataFrame(volume_map).reindex(close_panel.index)
    window = close_panel.tail(ASOF_LOOKBACK_BARS + 5)
    if as_of not in {idx.date() for idx in window.index}:
        return {
            "as_of_date": as_of,
            "status": "as_of_not_in_panel",
            "pool_status": pool_status,
            "rows": [],
        }
    as_of_ts = pd.Timestamp(as_of)
    prior_5d = window / window.shift(5) - 1.0
    prior_20d = window / window.shift(20) - 1.0
    five_day_acceleration = prior_5d - prior_20d
    dollar_volume = window * volume_panel.reindex(window.index)
    avg_dollar_volume_5d = dollar_volume.rolling(5, min_periods=5).mean()
    median_dollar_volume_20d = dollar_volume.rolling(20, min_periods=20).median()
    volume_confirmation = avg_dollar_volume_5d / median_dollar_volume_20d.replace(0, np.nan) - 1.0
    daily_range = high_panel.reindex(window.index) - low_panel.reindex(window.index)
    closing_strength = (window - low_panel.reindex(window.index)) / daily_range.replace(0, np.nan)
    closing_strength_5d = closing_strength.rolling(5, min_periods=5).mean()
    prior_5d_volume = volume_panel.reindex(window.index).rolling(5, min_periods=5).mean()
    prior_20d_volume = volume_panel.reindex(window.index).rolling(20, min_periods=20).mean()
    volume_trend = prior_5d_volume / prior_20d_volume.replace(0, np.nan)
    volume_weighted_momentum = prior_20d * volume_trend
    equal_weight_20d = float(prior_20d.loc[as_of_ts].dropna().mean()) if as_of_ts in prior_20d.index else 0.0
    relative_strength = prior_20d.loc[as_of_ts] - equal_weight_20d
    daily_returns = window.pct_change()
    rsi_14 = daily_returns.rolling(14, min_periods=14).apply(
        lambda x: 100.0 - 100.0 / (1.0 + x[x > 0].sum() / max(1e-9, abs(x[x < 0].sum()))),
        raw=True,
    )
    regime = classify_market_regime(window, included)
    thresholds = get_regime_thresholds(regime.name)
    frame = pd.DataFrame(
        {
            "symbol": included,
            "close": window.loc[as_of_ts].reindex(included).values,
            "prior_5d_momentum": prior_5d.loc[as_of_ts].reindex(included).values,
            "prior_20d_momentum": prior_20d.loc[as_of_ts].reindex(included).values,
            "five_day_acceleration": five_day_acceleration.loc[as_of_ts].reindex(included).values,
            "relative_strength_vs_equal_weight": relative_strength.reindex(included).values,
            "volume_confirmation_ratio": volume_confirmation.loc[as_of_ts].reindex(included).values,
            "median_dollar_volume_20d": median_dollar_volume_20d.loc[as_of_ts].reindex(included).values,
            "closing_strength_5d": closing_strength_5d.loc[as_of_ts].reindex(included).values,
            "volume_weighted_momentum": volume_weighted_momentum.loc[as_of_ts].reindex(included).values,
            "volume_trend_20d": volume_trend.loc[as_of_ts].reindex(included).values,
            "rsi_14": rsi_14.loc[as_of_ts].reindex(included).values,
        }
    ).set_index("symbol")
    strong_mom = frame["prior_20d_momentum"] > 0.05
    high_vol = frame["volume_confirmation_ratio"] > 0.2
    frame["breakout_score"] = np.where(
        strong_mom & high_vol,
        np.minimum(1.0, frame["prior_20d_momentum"] * 3.0 + frame["volume_confirmation_ratio"] * 0.5),
        0.0,
    )
    scores = pd.DataFrame(index=frame.index)
    scores["relative_volume_expansion"] = percentile_rank(frame["volume_trend_20d"])
    scores["volume_price_alignment"] = np.select(
        [
            frame["volume_trend_20d"].notna() & frame["prior_20d_momentum"].notna()
            & (frame["volume_trend_20d"] > 1.0) & (frame["prior_20d_momentum"] > 0),
            frame["volume_trend_20d"].notna() & frame["prior_20d_momentum"].notna()
            & ((frame["volume_trend_20d"] > 1.0) | (frame["prior_20d_momentum"] > 0)),
            frame["volume_trend_20d"].notna() & frame["prior_20d_momentum"].notna(),
        ],
        [1.0, 0.5, 0.0],
        default=np.nan,
    )
    scores["close_strength"] = frame["closing_strength_5d"].clip(0, 1)
    scores["breakout_acceptance"] = frame["breakout_score"].clip(0, 1)
    scores["liquidity_quality"] = percentile_rank(frame["median_dollar_volume_20d"])
    scores["relative_strength"] = percentile_rank(frame["relative_strength_vs_equal_weight"])
    coverage = scores.notna().mean(axis=1)
    structured = scores.mean(axis=1, skipna=True) * coverage
    participation = min(1.0, max(0.0, (float(regime.breadth) + float(regime.advance_ratio)) / 200.0))
    blended = structured * FOOTPRINT_STOCK_WEIGHT + participation * FOOTPRINT_MARKET_WEIGHT
    exhaustion_adj = np.where(
        frame["five_day_acceleration"] < thresholds.exhaustion_threshold,
        thresholds.exhaustion_adjustment,
        0.0,
    )
    risk_penalty = (
        np.where(frame["five_day_acceleration"] < thresholds.exhaustion_threshold * 1.5, 0.08, 0.0)
        + np.where(frame["five_day_acceleration"] < thresholds.accel_hard_block_threshold, 0.10, 0.0)
        + np.where(frame["volume_confirmation_ratio"] < 0.0, 0.03, 0.0)
        + np.where(frame["volume_weighted_momentum"] < 0.0, 0.03, 0.0)
        + np.where(
            (frame["volume_confirmation_ratio"] > thresholds.blowoff_volume_threshold)
            & (frame["closing_strength_5d"] < thresholds.blowoff_closing_threshold)
            & (frame["five_day_acceleration"] < thresholds.blowoff_accel_threshold),
            0.15,
            0.0,
        )
        + np.where(frame["closing_strength_5d"] < 0.3, 0.05, 0.0)
        + np.where(frame["five_day_acceleration"] < thresholds.accel_hard_block_threshold * 1.5, 0.12, 0.0)
        + np.where(frame["rsi_14"] > 75, 0.06, 0.0)
    )
    frame["recomputed_market_score"] = blended + exhaustion_adj - risk_penalty
    frame["persisted_catalyst_score"] = 0.0
    frame["recomputed_ticket_score"] = [
        current_ticket_score(market, 0.0) for market in frame["recomputed_market_score"]
    ]
    ranked = frame.reset_index().sort_values(
        by=["recomputed_ticket_score", "recomputed_market_score", "volume_confirmation_ratio"],
        ascending=False,
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)
    ranked["recomputed_rank"] = np.arange(1, len(ranked) + 1)
    eligible = ranked[
        ranked["recomputed_ticket_score"].notna()
        & (ranked["recomputed_ticket_score"] >= MIN_TICKET_SCORE)
    ].copy()
    rows = eligible.to_dict(orient="records")
    histories = {symbol: bars[bars["symbol"] == symbol] for symbol in included}
    for row in rows:
        row["as_of_date"] = as_of
        row["pool_status"] = pool_status
        row["regime"] = regime.name
        row["universe_source"] = ASOF_UNIVERSE_SOURCE
        row["catalyst_policy"] = ASOF_CATALYST_POLICY
        history = histories.get(row["symbol"])
        for horizon in HORIZONS:
            outcome = asof_session_return(history, as_of, horizon) if history is not None else {
                "return": None,
                "source": "missing_future_price",
            }
            row[f"t{horizon}"] = outcome.get("return")
            row[f"t{horizon}_source"] = outcome.get("source")
    return {
        "as_of_date": as_of,
        "status": "ok",
        "pool_status": pool_status,
        "included_count": len(included),
        "excluded_count": len(excluded),
        "eligible_size": int(len(eligible)),
        "universe_source": ASOF_UNIVERSE_SOURCE,
        "index_universe_status": INDEX_UNIVERSE_STATUS,
        "catalyst_policy": ASOF_CATALYST_POLICY,
        "price_basis": "kline_close_unadjusted",
        "regime": regime.name,
        "breadth": regime.breadth,
        "advance_ratio": regime.advance_ratio,
        "rows": rows,
        "top1": rows[0] if rows else None,
        "top3": rows[:3],
    }


def consecutive_counts(flags: list[bool]) -> tuple[int, int]:
    max_true = max_false = run_true = run_false = 0
    for flag in flags:
        if flag:
            run_true += 1
            run_false = 0
        else:
            run_false += 1
            run_true = 0
        max_true = max(max_true, run_true)
        max_false = max(max_false, run_false)
    return max_true, max_false


def horizon_metrics(returns: list[float]) -> dict[str, Any]:
    values = [float(item) for item in returns if item is not None]
    sample_count = len(values)
    if sample_count == 0:
        return {
            "sample_count": 0,
            "wins": 0,
            "losses": 0,
            "flats": 0,
            "win_rate": None,
            "avg_return": None,
            "median_return": None,
            "best_return": None,
            "worst_return": None,
            "avg_win": None,
            "avg_loss": None,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "profit_factor": None,
            "expectancy": None,
            "std_return": None,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
        }
    wins = [item for item in values if item > 0]
    losses = [item for item in values if item < 0]
    flats = sample_count - len(wins) - len(losses)
    win_rate = len(wins) / sample_count
    loss_rate = len(losses) / sample_count
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    gross_profit = float(sum(wins))
    gross_loss = float(sum(losses))
    if gross_loss == 0 and gross_profit > 0:
        profit_factor = float("inf")
    elif gross_loss == 0:
        profit_factor = None
    else:
        profit_factor = gross_profit / abs(gross_loss)
    expectancy = win_rate * avg_win + loss_rate * avg_loss
    max_wins, max_losses = consecutive_counts([item > 0 for item in values])
    return {
        "sample_count": sample_count,
        "wins": len(wins),
        "losses": len(losses),
        "flats": flats,
        "win_rate": win_rate,
        "avg_return": float(np.mean(values)),
        "median_return": float(np.median(values)),
        "best_return": float(max(values)),
        "worst_return": float(min(values)),
        "avg_win": avg_win if wins else None,
        "avg_loss": avg_loss if losses else None,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "std_return": float(np.std(values, ddof=1)) if sample_count > 1 else 0.0,
        "max_consecutive_wins": max_wins,
        "max_consecutive_losses": max_losses,
    }


def apply_friction(returns: list[float], bps: int) -> list[float]:
    friction = bps / 10000.0
    return [item - friction for item in returns]


def load_tickets() -> list[dict[str, Any]]:
    rows = readonly_query(
        """
        SELECT
            t.id AS ticket_id,
            t.symbol,
            t.output_date,
            t.as_of_date,
            t.ticket_rank,
            t.market_score,
            t.catalyst_score,
            t.ticket_score,
            t.classification,
            t.run_name,
            t.research_run_id,
            t.created_at,
            rr.git_commit,
            rr.config->>'strategy_version' AS strategy_version,
            rr.config->>'version_status' AS version_status,
            rr.config->>'data_as_of' AS data_as_of,
            rr.finished_at
        FROM tickets t
        LEFT JOIN research_runs rr ON rr.run_id = t.research_run_id
        ORDER BY t.output_date, t.ticket_rank NULLS LAST, t.id
        """
    )
    for row in rows:
        row["output_date"] = _as_date(row.get("output_date"))
        row["as_of_date"] = _as_date(row.get("as_of_date"))
        row["market_score"] = _as_float(row.get("market_score"))
        row["catalyst_score"] = _as_float(row.get("catalyst_score"))
        row["ticket_score"] = _as_float(row.get("ticket_score"))
        row["ticket_rank"] = int(row["ticket_rank"]) if row.get("ticket_rank") is not None else None
        row["version_bucket"] = classify_version(row)
    return rows


def load_forward_tracking() -> list[dict[str, Any]]:
    rows = readonly_query(
        """
        SELECT
            ft.id,
            ft.ticket_id,
            ft.symbol,
            ft.output_date,
            ft.as_of_date,
            ft.horizon_days,
            ft.due_date,
            ft.as_of_close,
            ft.due_close,
            ft.forward_return,
            ft.check_status,
            ft.track_key
        FROM forward_tracking ft
        ORDER BY ft.output_date, ft.ticket_id, ft.horizon_days, ft.id
        """
    )
    for row in rows:
        row["output_date"] = _as_date(row.get("output_date"))
        row["as_of_date"] = _as_date(row.get("as_of_date"))
        row["due_date"] = _as_date(row.get("due_date"))
        row["horizon_days"] = int(row["horizon_days"]) if row.get("horizon_days") is not None else None
        row["as_of_close"] = _as_float(row.get("as_of_close"))
        row["due_close"] = _as_float(row.get("due_close"))
        row["forward_return"] = _as_float(row.get("forward_return"))
        row["ticket_id"] = int(row["ticket_id"]) if row.get("ticket_id") is not None else None
    return rows


def load_factor_snapshots() -> list[dict[str, Any]]:
    rows = readonly_query(
        """
        SELECT
            trade_date, symbol,
            prior_5d_momentum, prior_20d_momentum, five_day_acceleration,
            relative_strength, volume_weighted_momentum, rsi_14,
            momentum_quality, breakout_score, reversal_quality,
            volume_confirmation, closing_strength_5d, dollar_volume_20d,
            market_score, structured_score, blended_score, regime
        FROM factor_snapshots
        ORDER BY trade_date, symbol
        """
    )
    for row in rows:
        row["trade_date"] = _as_date(row.get("trade_date"))
        for key in (
            "prior_5d_momentum",
            "prior_20d_momentum",
            "five_day_acceleration",
            "relative_strength",
            "volume_weighted_momentum",
            "rsi_14",
            "momentum_quality",
            "breakout_score",
            "reversal_quality",
            "volume_confirmation",
            "closing_strength_5d",
            "dollar_volume_20d",
            "market_score",
            "structured_score",
            "blended_score",
        ):
            row[key] = _as_float(row.get(key))
    return rows


def load_daily_candidates() -> list[dict[str, Any]]:
    rows = readonly_query(
        """
        SELECT
            trade_date, symbol, rank, is_official_pick,
            market_score, catalyst_score, ticket_score,
            factor_snapshot, ranking_basis
        FROM daily_candidates
        ORDER BY trade_date, rank NULLS LAST, symbol
        """
    )
    for row in rows:
        row["trade_date"] = _as_date(row.get("trade_date"))
        row["rank"] = int(row["rank"]) if row.get("rank") is not None else None
        row["market_score"] = _as_float(row.get("market_score"))
        row["catalyst_score"] = _as_float(row.get("catalyst_score"))
        row["ticket_score"] = _as_float(row.get("ticket_score"))
    return rows


def load_market_snapshots() -> dict[date, dict[str, Any]]:
    rows = readonly_query(
        """
        SELECT trade_date, regime, breadth, momentum, volatility,
               advance_ratio, universe_count
        FROM market_snapshots
        ORDER BY trade_date
        """
    )
    out: dict[date, dict[str, Any]] = {}
    for row in rows:
        day = _as_date(row.get("trade_date"))
        if day is None:
            continue
        out[day] = {
            "regime": row.get("regime"),
            "breadth": _as_float(row.get("breadth")),
            "momentum": _as_float(row.get("momentum")),
            "volatility": _as_float(row.get("volatility")),
            "advance_ratio": _as_float(row.get("advance_ratio")),
            "universe_count": int(row["universe_count"]) if row.get("universe_count") is not None else None,
        }
    return out


def load_kline_bars() -> pd.DataFrame:
    rows = readonly_query(
        """
        SELECT symbol, trade_date, open, high, low, close, adj_close, volume
        FROM daily_klines
        ORDER BY symbol, trade_date
        """
    )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(
            columns=["symbol", "trade_date", "open", "high", "low", "close", "adj_close", "volume"]
        )
    frame["trade_date"] = frame["trade_date"].map(_as_date)
    for key in ("open", "high", "low", "close", "adj_close", "volume"):
        frame[key] = frame[key].map(_as_float)
    frame["symbol"] = frame["symbol"].astype(str)
    return frame.dropna(subset=["trade_date", "symbol", "close"])


def load_kline_index() -> dict[tuple[str, date], dict[str, float | None]]:
    rows = readonly_query(
        """
        SELECT symbol, trade_date, close, adj_close
        FROM daily_klines
        WHERE trade_date >= DATE '2026-04-01'
        """
    )
    index: dict[tuple[str, date], dict[str, float | None]] = {}
    for row in rows:
        day = _as_date(row.get("trade_date"))
        symbol = str(row.get("symbol") or "")
        if not day or not symbol:
            continue
        index[(symbol, day)] = {
            "close": _as_float(row.get("close")),
            "adj_close": _as_float(row.get("adj_close")),
        }
    return index


def load_obsidian_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    json_dir = ROOT / "research" / "knowledge-assets"
    if json_dir.exists():
        for path in sorted(json_dir.glob("*_knowledge.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            output_date = _as_date(payload.get("trade_date") or path.name[:10])
            returns = payload.get("returns") or {}
            for ticket in payload.get("tickets") or []:
                symbol = str(ticket.get("symbol") or "").upper()
                outcome = returns.get(symbol) or {}
                records.append(
                    {
                        "source": f"knowledge-assets/{path.name}",
                        "output_date": output_date,
                        "symbol": symbol,
                        "ticket_score": _as_float(ticket.get("ticket_score")),
                        "market_score": _as_float(ticket.get("market_score")),
                        "catalyst_score": _as_float(ticket.get("catalyst_score")),
                        "classification": ticket.get("classification"),
                        "t1": _as_float(outcome.get("forward_1d")),
                        "t3": _as_float(outcome.get("forward_3d")),
                        "t5": _as_float(outcome.get("forward_5d")),
                        "t10": _as_float(outcome.get("forward_10d")),
                    }
                )
    ka_rows = readonly_query(
        """
        SELECT source_path, title, content
        FROM knowledge_assets
        WHERE title ILIKE '%知识资产%' OR content ILIKE '%Score%'
        ORDER BY id
        """
    )
    ticket_re = re.compile(
        r"###\s+([A-Z.]{1,10})\s*\n-\s+\*\*Score\*\*:\s+([0-9.]+)\s+\(market=([0-9.]+),\s+catalyst=([0-9.]+)\)",
        re.MULTILINE,
    )
    date_re = re.compile(r"(20\d{2}-\d{2}-\d{2})")
    for row in ka_rows:
        path = str(row.get("source_path") or "")
        if "shenlin" in path or "指针" in str(row.get("title") or ""):
            continue
        content = str(row.get("content") or "")
        found_date = date_re.search(path) or date_re.search(str(row.get("title") or ""))
        output_date = _as_date(found_date.group(1)) if found_date else None
        for match in ticket_re.finditer(content):
            records.append(
                {
                    "source": path,
                    "output_date": output_date,
                    "symbol": match.group(1).upper(),
                    "ticket_score": _as_float(match.group(2)),
                    "market_score": _as_float(match.group(3)),
                    "catalyst_score": _as_float(match.group(4)),
                    "classification": None,
                    "t1": None,
                    "t3": None,
                    "t5": None,
                    "t10": None,
                }
            )
    return records


def audit_ticket_ledger(tickets: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [row["ticket_id"] for row in tickets]
    date_symbol = [(row["output_date"], row["symbol"]) for row in tickets]
    dup_ids = [key for key, count in Counter(ids).items() if count > 1]
    dup_date_symbol = [key for key, count in Counter(date_symbol).items() if count > 1]
    future_asof = [
        row for row in tickets
        if row.get("as_of_date") and row.get("output_date") and row["as_of_date"] > row["output_date"]
    ]
    invalid_dates = [
        row for row in tickets
        if row.get("output_date") is None or not CALENDAR.is_trading_day(row["output_date"])
    ]
    missing_score = [row for row in tickets if row.get("ticket_score") is None]
    return {
        "total_tickets": len(tickets),
        "unique_ticket_ids": len(set(ids)),
        "unique_output_dates": len({row["output_date"] for row in tickets}),
        "unique_symbols": len({row["symbol"] for row in tickets}),
        "duplicate_ticket_ids": len(dup_ids),
        "duplicate_ticket_date_symbol": len(dup_date_symbol),
        "duplicate_date_symbol_pairs": [
            {"output_date": key[0].isoformat() if key[0] else None, "symbol": key[1], "count": count}
            for key, count in Counter(date_symbol).items()
            if count > 1
        ],
        "future_asof_count": len(future_asof),
        "invalid_output_date_count": len(invalid_dates),
        "missing_ticket_score": len(missing_score),
        "version_counts": dict(Counter(row["version_bucket"] for row in tickets)),
        "audit": "DUPLICATE_DATE_SYMBOL_AUDITED" if dup_date_symbol else "NO_DATE_SYMBOL_DUPLICATES",
    }


def reconstruct_day(
    day: date,
    factor_rows: list[dict[str, Any]],
    candidate_by_symbol: dict[str, dict[str, Any]],
    snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    frame = pd.DataFrame(factor_rows)
    if frame.empty:
        return {"as_of_date": day, "status": "missing_factor_snapshot", "rows": []}
    frame = frame.copy()
    frame["symbol"] = frame["symbol"].astype(str)
    prior_20d = frame["prior_20d_momentum"]
    volume_trend = np.where(
        prior_20d.notna() & (prior_20d.abs() > 1e-9) & frame["volume_weighted_momentum"].notna(),
        frame["volume_weighted_momentum"] / prior_20d,
        np.nan,
    )
    frame["volume_trend_20d"] = volume_trend
    scores = pd.DataFrame(index=frame.index)
    scores["relative_volume_expansion"] = percentile_rank(pd.Series(volume_trend, index=frame.index))
    scores["volume_price_alignment"] = np.select(
        [
            pd.notna(volume_trend) & prior_20d.notna() & (volume_trend > 1.0) & (prior_20d > 0),
            pd.notna(volume_trend) & prior_20d.notna() & ((volume_trend > 1.0) | (prior_20d > 0)),
            pd.notna(volume_trend) & prior_20d.notna(),
        ],
        [1.0, 0.5, 0.0],
        default=np.nan,
    )
    scores["close_strength"] = frame["closing_strength_5d"].clip(0, 1)
    scores["breakout_acceptance"] = frame["breakout_score"].clip(0, 1)
    scores["liquidity_quality"] = percentile_rank(frame["dollar_volume_20d"])
    scores["relative_strength"] = percentile_rank(frame["relative_strength"])
    coverage = scores.notna().mean(axis=1)
    structured = scores.mean(axis=1, skipna=True) * coverage
    breadth = float((prior_20d.dropna() > 0).mean() * 100) if prior_20d.notna().any() else 50.0
    advance = 50.0
    if snapshot and snapshot.get("advance_ratio") is not None:
        advance = float(snapshot["advance_ratio"])
        if advance <= 1:
            advance *= 100
    if snapshot and snapshot.get("breadth") is not None:
        breadth = float(snapshot["breadth"])
        if breadth <= 1:
            breadth *= 100
    participation = min(1.0, max(0.0, (breadth + advance) / 200.0))
    if snapshot and snapshot.get("regime"):
        regime_name = str(snapshot["regime"])
    elif frame["regime"].notna().any():
        regime_name = str(frame["regime"].dropna().mode().iloc[0])
    else:
        regime_name = "balanced"
    thresholds = get_regime_thresholds(regime_name)
    blended = structured * FOOTPRINT_STOCK_WEIGHT + participation * FOOTPRINT_MARKET_WEIGHT
    exhaustion_adj = np.where(
        frame["five_day_acceleration"] < thresholds.exhaustion_threshold,
        thresholds.exhaustion_adjustment,
        0.0,
    )
    risk_penalty = (
        np.where(frame["five_day_acceleration"] < thresholds.exhaustion_threshold * 1.5, 0.08, 0.0)
        + np.where(frame["five_day_acceleration"] < thresholds.accel_hard_block_threshold, 0.10, 0.0)
        + np.where(frame["volume_confirmation"] < 0.0, 0.03, 0.0)
        + np.where(frame["volume_weighted_momentum"] < 0.0, 0.03, 0.0)
        + np.where(
            (frame["volume_confirmation"] > thresholds.blowoff_volume_threshold)
            & (frame["closing_strength_5d"] < thresholds.blowoff_closing_threshold)
            & (frame["five_day_acceleration"] < thresholds.blowoff_accel_threshold),
            0.15,
            0.0,
        )
        + np.where(frame["closing_strength_5d"] < 0.3, 0.05, 0.0)
        + np.where(frame["five_day_acceleration"] < thresholds.accel_hard_block_threshold * 1.5, 0.12, 0.0)
        + np.where(frame["rsi_14"] > 75, 0.06, 0.0)
    )
    recomputed_market = blended + exhaustion_adj - risk_penalty
    frame["recomputed_market_score"] = recomputed_market
    frame["volume_confirmation_ratio"] = frame["volume_confirmation"]
    catalyst = []
    persisted_ticket_score = []
    for symbol in frame["symbol"]:
        candidate = candidate_by_symbol.get(symbol, {})
        catalyst.append(_as_float(candidate.get("catalyst_score")))
        persisted_ticket_score.append(_as_float(candidate.get("ticket_score")))
    frame["persisted_catalyst_score"] = catalyst
    frame["persisted_ticket_score"] = persisted_ticket_score
    frame["recomputed_ticket_score"] = [
        current_ticket_score(market, cat)
        for market, cat in zip(frame["recomputed_market_score"], frame["persisted_catalyst_score"])
    ]
    scored_mask = frame["persisted_catalyst_score"].notna()
    scored_candidate_count = int(scored_mask.sum())
    rank_frame = frame.loc[scored_mask].copy()
    ranked = rank_frame.sort_values(
        by=["recomputed_ticket_score", "recomputed_market_score", "volume_confirmation_ratio"],
        ascending=False,
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)
    ranked["recomputed_rank"] = np.arange(1, len(ranked) + 1)
    eligible = ranked[
        ranked["recomputed_ticket_score"].notna()
        & (ranked["recomputed_ticket_score"] >= MIN_TICKET_SCORE)
    ].copy()
    pool_status = classify_pool_status(len(frame), scored_candidate_count)
    rows = eligible.to_dict(orient="records")
    for row in rows:
        row["as_of_date"] = day
        row["pool_status"] = pool_status
        row["regime"] = regime_name
    return {
        "as_of_date": day,
        "status": "ok",
        "pool_status": pool_status,
        "pool_size": int(len(frame)),
        "scored_candidate_count": scored_candidate_count,
        "eligible_size": int(len(eligible)),
        "regime": regime_name,
        "rows": rows,
        "top1": rows[0] if rows else None,
        "top3": rows[:3],
    }


def attach_returns(
    symbol: str,
    as_of: date,
    tracking_by_key: dict[tuple[str, date, int], dict[str, Any]],
    klines: dict[tuple[str, date], dict[str, float | None]],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for horizon in HORIZONS:
        track = tracking_by_key.get((symbol, as_of, horizon))
        if track and track.get("check_status") == "completed" and track.get("forward_return") is not None:
            out[f"t{horizon}"] = track["forward_return"]
            out[f"t{horizon}_source"] = "forward_tracking"
            continue
        due = CALENDAR.add_trading_days(as_of, horizon)
        entry = klines.get((symbol, as_of), {})
        exit_bar = klines.get((symbol, due), {})
        if entry.get("adj_close") is not None and exit_bar.get("adj_close") is not None:
            if entry["adj_close"] > 0:
                out[f"t{horizon}"] = exit_bar["adj_close"] / entry["adj_close"] - 1.0
                out[f"t{horizon}_source"] = "adj_close"
                continue
        out[f"t{horizon}"] = None
        out[f"t{horizon}_source"] = "missing_future_price"
    return out


def split_periods(dates: list[date]) -> dict[str, list[date]]:
    unique = sorted({day for day in dates if day is not None})
    if not unique:
        return {"train": [], "validation": [], "holdout": []}
    n = len(unique)
    train_end = max(1, int(n * 0.60))
    valid_end = max(train_end + 1, int(n * 0.80)) if n >= 5 else train_end
    if n < 5:
        return {"train": unique[: max(1, n - 1)], "validation": [], "holdout": unique[-1:]}
    return {
        "train": unique[:train_end],
        "validation": unique[train_end:valid_end],
        "holdout": unique[valid_end:],
    }


def period_metrics(samples: list[dict[str, Any]], dates: list[date], field: str = "t1") -> dict[str, Any]:
    wanted = set(dates)
    values = [
        row[field]
        for row in samples
        if (row.get("output_date") or row.get("as_of_date")) in wanted and row.get(field) is not None
    ]
    metrics = horizon_metrics(values)
    metrics["dates"] = [day.isoformat() for day in dates]
    return metrics


def equity_from_daily(returns_by_day: list[tuple[date, float]]) -> dict[str, Any]:
    if not returns_by_day:
        return {
            "cumulative_return": None,
            "max_drawdown": None,
            "max_drawdown_duration": None,
            "volatility": None,
            "win_days": 0,
            "loss_days": 0,
            "points": [],
        }
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    dd_start = None
    max_dd_duration = 0
    points = []
    for day, ret in sorted(returns_by_day, key=lambda item: item[0]):
        equity *= 1.0 + ret
        if equity > peak:
            peak = equity
            dd_start = None
        drawdown = equity / peak - 1.0
        if drawdown < max_dd:
            max_dd = drawdown
        if drawdown < 0:
            dd_start = dd_start or day
            duration = (day - dd_start).days if dd_start else 0
            max_dd_duration = max(max_dd_duration, duration)
        points.append({"date": day.isoformat(), "daily_return": ret, "equity": equity, "drawdown": drawdown})
    daily = [ret for _, ret in returns_by_day]
    return {
        "cumulative_return": equity - 1.0,
        "max_drawdown": max_dd,
        "max_drawdown_duration": max_dd_duration,
        "volatility": float(np.std(daily, ddof=1)) if len(daily) > 1 else 0.0,
        "win_days": sum(1 for ret in daily if ret > 0),
        "loss_days": sum(1 for ret in daily if ret < 0),
        "points": points,
    }


def correlation(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    return float(np.corrcoef(xs, ys)[0, 1])


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    rx = pd.Series(xs).rank().tolist()
    ry = pd.Series(ys).rank().tolist()
    return correlation(rx, ry)


def pass_fail(metrics: dict[str, Any] | None) -> str:
    if not metrics or metrics.get("sample_count", 0) == 0:
        return "FAIL"
    expectancy = metrics.get("expectancy")
    avg_return = metrics.get("avg_return")
    profit_factor = metrics.get("profit_factor")
    if expectancy is None or avg_return is None or profit_factor is None:
        return "FAIL"
    if expectancy > 0 and avg_return > 0 and profit_factor > 1:
        return "PASS"
    return "FAIL"


def decide_verdict(payload: dict[str, Any]) -> dict[str, Any]:
    """CURRENT STRATEGY uses as-of Top1. Historical tickets are a separate gate.

    Historical future-asof, unadjusted close, and historical exclusion rate do
    not invalidate the as-of reconstruction. They are labeled, not mixed into
    as-of returns.
    """
    anomalies = payload["anomalies"]
    realized_t1 = (payload.get("realized") or {}).get("by_horizon", {}).get("1") or {}
    reconstructed = payload.get("reconstructed") or {}
    reconstructed_t1 = reconstructed.get("top1_t1") or {}
    recent = (payload.get("walk_forward") or {}).get("holdout") or {}
    cost = (payload.get("cost_sensitivity") or {}).get("reconstructed_top1_t1") or {}
    asof_full_days = int(reconstructed.get("full_pool_days") or 0)
    mixed_returns = anomalies.get("mixed_price_basis_in_returns", 0)
    duplicate_samples = anomalies.get("duplicate_sample", 0)
    historical_future_leak = anomalies.get("future_data_detected", 0)
    exclusion_rate = anomalies.get("exclusion_rate") or 0.0
    reasons: list[str] = []
    if duplicate_samples > 0:
        reasons.append("duplicate_sample")
    if mixed_returns > 0:
        reasons.append("mixed_price_basis_in_returns")
    if asof_full_days == 0:
        reasons.append("no_full_asof_panel_days")
    if historical_future_leak > 0:
        reasons.append("historical_realized_future_data_detected")
    if anomalies.get("adj_close_available", 0) == 0:
        reasons.append("asof_price_basis_unadjusted_close")
    if anomalies.get("price_basis_mismatch", 0) > 0:
        reasons.append("price_basis_mismatch_audited_not_used_in_returns")
    if exclusion_rate >= HIGH_EXCLUSION_RATE:
        reasons.append("historical_realized_high_exclusion_rate")
    data_invalid = bool(duplicate_samples > 0 or mixed_returns > 0 or asof_full_days == 0)
    if data_invalid:
        return {
            "profitability": "DATA_INVALID",
            "profitability_validated": "NO",
            "reasons": reasons,
        }
    t1_pos = (
        (reconstructed_t1.get("sample_count") or 0) >= MIN_INDEPENDENT_SAMPLES
        and (reconstructed_t1.get("expectancy") or 0) > 0
        and (reconstructed_t1.get("avg_return") or 0) > 0
        and (reconstructed_t1.get("profit_factor") or 0) > 1
    )
    recent_pos = (
        (recent.get("sample_count") or 0) > 0
        and (recent.get("expectancy") or 0) > 0
        and (recent.get("avg_return") or 0) > 0
    )
    cost_25 = pass_fail(cost.get("25")) == "PASS"
    cost_50 = pass_fail(cost.get("50")) == "PASS"
    realized_pos = (
        (realized_t1.get("sample_count") or 0) >= MIN_INDEPENDENT_SAMPLES
        and (realized_t1.get("expectancy") or 0) > 0
        and (realized_t1.get("avg_return") or 0) > 0
        and (realized_t1.get("profit_factor") or 0) > 1
    )
    audit_only = {
        "historical_realized_future_data_detected",
        "asof_price_basis_unadjusted_close",
        "price_basis_mismatch_audited_not_used_in_returns",
        "historical_realized_high_exclusion_rate",
    }
    remaining_blockers = [item for item in reasons if item not in audit_only]
    if t1_pos and recent_pos and cost_25 and cost_50 and realized_pos and not remaining_blockers:
        return {
            "profitability": "PROFITABLE",
            "profitability_validated": "YES",
            "reasons": ["all_profitability_gates_passed"],
        }
    if (
        (reconstructed_t1.get("expectancy") or 0) <= 0
        or (reconstructed_t1.get("avg_return") or 0) <= 0
        or (reconstructed_t1.get("profit_factor") or 1) <= 1
        or (reconstructed_t1.get("sample_count") or 0) < MIN_INDEPENDENT_SAMPLES
        or not recent_pos
    ):
        return {
            "profitability": "NOT_PROFITABLE",
            "profitability_validated": "NO",
            "reasons": reasons
            + [
                f"reconstructed_t1_expectancy={reconstructed_t1.get('expectancy')}",
                f"reconstructed_t1_profit_factor={reconstructed_t1.get('profit_factor')}",
                f"reconstructed_t1_n={reconstructed_t1.get('sample_count')}",
                f"recent_pos={recent_pos}",
                f"realized_t1_expectancy={realized_t1.get('expectancy')}",
            ],
        }
    return {
        "profitability": "WEAK_EDGE",
        "profitability_validated": "NO",
        "reasons": reasons + ["edge_exists_but_not_stable_under_gates"],
    }


def fmt_pct(value: float | None, signed: bool = False) -> str:
    if value is None:
        return "n/a"
    if signed:
        return f"{value * 100:+.2f}%"
    return f"{value * 100:.2f}%"


def fmt_num(value: float | None) -> str:
    if value is None:
        return "n/a"
    if math.isinf(value):
        return "inf"
    return f"{value:.2f}"


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = {}
            for key in fieldnames:
                value = row.get(key)
                if isinstance(value, date):
                    value = value.isoformat()
                elif isinstance(value, float):
                    value = "" if math.isnan(value) else f"{value:.10g}"
                out[key] = value if value is not None else ""
            writer.writerow(out)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_ready(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_report(summary: dict[str, Any]) -> str:
    realized = summary["realized"]["by_horizon"]
    recon = summary["reconstructed"]
    rec = summary["reconciliation"]
    verdict = summary["verdict"]
    t1 = realized.get("1") or {}
    realized_equity = summary.get("equity_historical_realized_top1") or {}
    lines = [
        "====================================================",
        "XIAOMEI CURRENT STRATEGY PROFITABILITY VALIDATION",
        "====================================================",
        "",
        "Strategy:",
        STRATEGY,
        "",
        "Strategy Status:",
        PRODUCTION_BOUNDARY["strategy_status"],
        "",
        "Historical Tickets:",
        str(summary["ledger"]["total_tickets"]),
        "",
        "Unique Tickets:",
        str(summary["ledger"]["unique_ticket_ids"]),
        "",
        "Valid T+1 Samples:",
        str((t1.get("sample_count") if t1 else 0) or 0),
        "",
    ]
    for horizon in HORIZONS:
        metrics = realized.get(str(horizon)) or {}
        lines.extend(
            [
                "----------------------------------------------------",
                f"T+{horizon}",
                "----------------------------------------------------",
                "",
                "Win Rate:",
                fmt_pct(metrics.get("win_rate")),
                "",
                "Average Return:",
                fmt_pct(metrics.get("avg_return"), signed=True),
                "",
                "Median Return:",
                fmt_pct(metrics.get("median_return"), signed=True),
                "",
                "Profit Factor:",
                fmt_num(metrics.get("profit_factor")),
                "",
                "Expectancy:",
                fmt_pct(metrics.get("expectancy"), signed=True),
                "",
            ]
        )
        if horizon == 1:
            lines.extend(
                [
                    "Max Drawdown (historical realized Top1):",
                    fmt_pct(realized_equity.get("max_drawdown"), signed=True),
                    "",
                ]
            )
    top1 = recon.get("top1_t1") or {}
    top3 = recon.get("top3_t1") or {}
    selected_top1 = ((recon.get("by_horizon") or {}).get("1") or {}).get("selected_ticket_only") or {}
    holdout = summary["walk_forward"]["holdout"]
    cost = summary["cost_sensitivity"].get("reconstructed_top1_t1") or summary["cost_sensitivity"].get("realized_t1") or {}
    lines.extend(
        [
            "----------------------------------------------------",
            "CURRENT STRATEGY RECONSTRUCTION",
            "----------------------------------------------------",
            "",
            "Universe source:",
            str(recon.get("universe_source") or ASOF_UNIVERSE_SOURCE),
            "",
            "Index membership:",
            str(recon.get("index_universe_status") or INDEX_UNIVERSE_STATUS),
            "",
            "Catalyst policy:",
            str(recon.get("catalyst_policy") or ASOF_CATALYST_POLICY),
            "",
            "FULL_ASOF_PANEL days:",
            str(recon.get("full_pool_days", 0)),
            "",
            "SELECTED_TICKET_ONLY days:",
            str(recon.get("selected_ticket_only_days", 0)),
            "",
            "Price basis:",
            str(recon.get("price_basis") or "kline_close_unadjusted"),
            "",
            "Top 1:",
            f"{fmt_pct(top1.get('win_rate'))} win",
            f"{fmt_pct(top1.get('avg_return'), signed=True)} avg",
            "",
            "Top 3:",
            f"{fmt_pct(top3.get('win_rate'))} win",
            f"{fmt_pct(top3.get('avg_return'), signed=True)} avg",
            "",
            "Max Drawdown (as-of Top1):",
            fmt_pct((summary.get("equity") or {}).get("max_drawdown"), signed=True),
            "",
            "Top 1 SELECTED_TICKET_ONLY:",
            f"{fmt_pct(selected_top1.get('win_rate'))} win",
            f"{fmt_pct(selected_top1.get('avg_return'), signed=True)} avg",
            "NOTE: past selected names only; not CURRENT STRATEGY EDGE",
            "",
            "Recent Holdout:",
            f"{fmt_pct(holdout.get('win_rate'))} win",
            f"{fmt_pct(holdout.get('avg_return'), signed=True)} avg",
            "",
            "----------------------------------------------------",
            "COST STRESS",
            "----------------------------------------------------",
            "",
        ]
    )
    for bps in COST_BPS:
        lines.extend([f"{bps} bps:", pass_fail(cost.get(str(bps))), ""])
    lines.extend(
        [
            "----------------------------------------------------",
            "RECONCILIATION",
            "----------------------------------------------------",
            "",
            "DB ↔ Obsidian:",
            fmt_pct(rec.get("db_obsidian_match_rate")),
            "",
            "Historical ↔ Current Strategy:",
            fmt_pct(rec.get("score_reconciliation_rate")),
            "",
            "----------------------------------------------------",
            "FINAL",
            "----------------------------------------------------",
            "",
            "PROFITABILITY:",
            verdict["profitability"],
            "",
            "PROFITABILITY_VALIDATED:",
            verdict["profitability_validated"],
            "",
            "PRODUCTION STRATEGY:",
            STRATEGY,
            "",
            "STRATEGY CHANGE:",
            "NONE",
            "",
            "WEIGHT CHANGE:",
            "NONE",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    freeze = freeze_snapshot()
    if freeze["strategy"] != STRATEGY or not strategy_is_frozen() or not weights_are_frozen():
        raise RuntimeError("production strategy/weights are not frozen; refusing to validate")

    tickets = load_tickets()
    tracking = load_forward_tracking()
    factors = load_factor_snapshots()
    candidates = load_daily_candidates()
    snapshots = load_market_snapshots()
    kline_bars = load_kline_bars()
    klines = {
        (str(row["symbol"]), row["trade_date"]): {
            "close": row["close"],
            "adj_close": row["adj_close"],
        }
        for row in kline_bars.to_dict(orient="records")
        if row.get("trade_date") is not None
    }
    obsidian = load_obsidian_records()
    ledger = audit_ticket_ledger(tickets)
    tickets_by_id = {row["ticket_id"]: row for row in tickets}

    anomalies: dict[str, int] = {
        "missing_future_price": 0,
        "duplicate_ticket": ledger["duplicate_ticket_ids"],
        "duplicate_ticket_date_symbol": ledger["duplicate_ticket_date_symbol"],
        "duplicate_sample": 0,
        "future_data_detected": ledger["future_asof_count"],
        "invalid_date": ledger["invalid_output_date_count"],
        "price_basis_mismatch": 0,
        "missing_factor_snapshot": 0,
        "missing_ticket_score": ledger["missing_ticket_score"],
        "unknown_strategy_version": ledger["version_counts"].get("UNKNOWN_VERSION", 0),
        "adj_close_available": 0,
        "kline_close_available": 0,
        "mixed_price_basis_in_returns": 0,
        "return_price_basis": "forward_tracking_as_of_close_to_due_close",
        "asof_universe_source": ASOF_UNIVERSE_SOURCE,
        "index_universe_status": INDEX_UNIVERSE_STATUS,
        "asof_catalyst_policy": ASOF_CATALYST_POLICY,
    }

    for meta in klines.values():
        if meta.get("adj_close") is not None:
            anomalies["adj_close_available"] += 1
        if meta.get("close") is not None:
            anomalies["kline_close_available"] += 1

    tracking_by_ticket_horizon: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    tracking_by_symbol_asof_h: dict[tuple[str, date, int], dict[str, Any]] = {}
    for row in tracking:
        if row.get("ticket_id") is not None and row.get("horizon_days") is not None:
            tracking_by_ticket_horizon[(row["ticket_id"], row["horizon_days"])].append(row)
        if row.get("symbol") and row.get("as_of_date") and row.get("horizon_days") is not None:
            key = (row["symbol"], row["as_of_date"], row["horizon_days"])
            tracking_by_symbol_asof_h[key] = row

    sample_seen: dict[str, dict[str, Any]] = {}
    realized_samples: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for row in tracking:
        ticket = tickets_by_id.get(row.get("ticket_id"))
        if ticket is None:
            excluded.append({"reason": "missing_ticket", "tracking_id": row.get("id")})
            continue
        replay_date = row.get("as_of_date") or ticket.get("as_of_date") or ticket.get("output_date")
        try:
            identity = sample_id(
                ticket_id=ticket["ticket_id"],
                replay_horizon=row["horizon_days"],
                replay_date=replay_date,
            )
        except ValueError:
            excluded.append({"reason": "invalid_sample_identity", "ticket_id": ticket["ticket_id"]})
            continue
        if identity in sample_seen:
            anomalies["duplicate_sample"] += 1
            excluded.append({"reason": "duplicate_sample", "sample_id": identity})
            continue
        sample_seen[identity] = row
        kline_entry = klines.get((row["symbol"], row["as_of_date"] or ticket["as_of_date"])) or {}
        decision = classify_sample_exclusion(
            output_date=ticket["output_date"],
            as_of_date=ticket["as_of_date"],
            check_status=row.get("check_status"),
            forward_return=row.get("forward_return"),
            as_of_close=row.get("as_of_close"),
            kline_close=kline_entry.get("close"),
            kline_adj_close=kline_entry.get("adj_close"),
            is_trading_day=bool(ticket["output_date"] and CALENDAR.is_trading_day(ticket["output_date"])),
        )
        if "missing_future_price" in decision["hard"]:
            anomalies["missing_future_price"] += 1
        if "price_basis_mismatch" in decision["audit"]:
            anomalies["price_basis_mismatch"] += 1
        reasons = decision["hard"] + decision["audit"]
        sample = {
            "sample_id": identity,
            "ticket_id": ticket["ticket_id"],
            "symbol": ticket["symbol"],
            "output_date": ticket["output_date"],
            "as_of_date": ticket["as_of_date"],
            "horizon": row["horizon_days"],
            "ticket_rank": ticket["ticket_rank"],
            "ticket_score": ticket["ticket_score"],
            "market_score": ticket["market_score"],
            "catalyst_score": ticket["catalyst_score"],
            "classification": ticket["classification"],
            "version_bucket": ticket["version_bucket"],
            "strategy_version": ticket.get("strategy_version"),
            "forward_return": row.get("forward_return"),
            "as_of_close": row.get("as_of_close"),
            "due_close": row.get("due_close"),
            "check_status": row.get("check_status"),
            "exclusion_reasons": reasons,
            "hard_exclusion_reasons": decision["hard"],
            "audit_reasons": decision["audit"],
        }
        if decision["exclude"]:
            excluded.append(sample)
        else:
            realized_samples.append(sample)

    usable = len(realized_samples)
    excluded_count = len(excluded)
    anomalies["usable_sample_count"] = usable
    anomalies["excluded_sample_count"] = excluded_count
    anomalies["exclusion_rate"] = excluded_count / max(1, usable + excluded_count)

    realized_by_horizon: dict[str, dict[str, Any]] = {}
    for horizon in HORIZONS:
        values = [
            row["forward_return"]
            for row in realized_samples
            if row["horizon"] == horizon and row["forward_return"] is not None
        ]
        realized_by_horizon[str(horizon)] = horizon_metrics(values)

    current_realized = [
        row for row in realized_samples if row["version_bucket"] == "CURRENT_VERSION"
    ]
    current_by_horizon = {
        str(horizon): horizon_metrics(
            [row["forward_return"] for row in current_realized if row["horizon"] == horizon]
        )
        for horizon in HORIZONS
    }

    t1_realized = [row for row in realized_samples if row["horizon"] == 1]
    t1_dates = [row["output_date"] for row in t1_realized if row.get("output_date")]
    periods = split_periods(t1_dates)
    walk_forward = {
        name: period_metrics(t1_realized, dates, "forward_return")
        for name, dates in periods.items()
    }
    walk_forward["holdout"] = walk_forward.get("holdout") or horizon_metrics([])

    official_top1_by_day: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for row in t1_realized:
        if row.get("ticket_rank") == 1 and row.get("output_date"):
            official_top1_by_day[row["output_date"]].append(row)
    daily_returns: list[tuple[date, float]] = []
    for day, rows in sorted(official_top1_by_day.items()):
        chosen = sorted(rows, key=lambda item: (item["ticket_id"], item["symbol"]))[0]
        if chosen.get("forward_return") is None:
            continue
        daily_returns.append((day, chosen["forward_return"]))
    equity = equity_from_daily(daily_returns)

    cost_realized = {
        str(bps): horizon_metrics(apply_friction([row["forward_return"] for row in t1_realized], bps))
        for bps in COST_BPS
    }

    monthly: dict[str, list[float]] = defaultdict(list)
    weekly: dict[str, list[float]] = defaultdict(list)
    for row in t1_realized:
        day = row["output_date"]
        monthly[day.strftime("%Y-%m")].append(row["forward_return"])
        weekly[f"{day.isocalendar().year}-W{day.isocalendar().week:02d}"].append(row["forward_return"])

    def period_table(groups: dict[str, list[float]]) -> dict[str, Any]:
        rows = []
        for key in sorted(groups):
            metrics = horizon_metrics(groups[key])
            rows.append({"period": key, **metrics})
        profitable = sum(1 for row in rows if (row.get("avg_return") or 0) > 0)
        signs = [(row.get("avg_return") or 0) > 0 for row in rows]
        _, max_neg = consecutive_counts(signs)
        return {
            "rows": rows,
            "profitable_ratio": profitable / max(1, len(rows)),
            "max_consecutive_negative_periods": max_neg,
        }

    by_period = {"month": period_table(monthly), "week": period_table(weekly)}

    factors_by_day: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for row in factors:
        if row.get("trade_date"):
            factors_by_day[row["trade_date"]].append(row)
    candidates_by_day: dict[date, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in candidates:
        if row.get("trade_date") and row.get("symbol"):
            candidates_by_day[row["trade_date"]][row["symbol"]] = row
    tickets_by_day_symbol: dict[tuple[date, str], dict[str, Any]] = {}
    for row in tickets:
        if row.get("output_date") and row.get("symbol"):
            tickets_by_day_symbol[(row["output_date"], row["symbol"])] = row

    reconstructed_days = []
    reconstructed_rows = []
    for day, day_factors in sorted(factors_by_day.items()):
        candidate_map = dict(candidates_by_day.get(day, {}))
        for row in tickets:
            if row.get("output_date") == day:
                candidate_map.setdefault(
                    row["symbol"],
                    {
                        "catalyst_score": row.get("catalyst_score"),
                        "ticket_score": row.get("ticket_score"),
                        "market_score": row.get("market_score"),
                    },
                )
        if not day_factors:
            anomalies["missing_factor_snapshot"] += 1
            continue
        reconstructed = reconstruct_day(day, day_factors, candidate_map, snapshots.get(day))
        reconstructed_days.append(reconstructed)
        for row in reconstructed.get("rows") or []:
            returns = attach_returns(row["symbol"], day, tracking_by_symbol_asof_h, klines)
            item = {
                "as_of_date": day,
                "symbol": row["symbol"],
                "recomputed_ticket_score": _as_float(row.get("recomputed_ticket_score")),
                "recomputed_market_score": _as_float(row.get("recomputed_market_score")),
                "persisted_catalyst_score": _as_float(row.get("persisted_catalyst_score")),
                "historical_ticket_score": _as_float(row.get("persisted_ticket_score") or row.get("market_score")),
                "historical_market_score": _as_float(row.get("market_score")),
                "recomputed_rank": int(row["recomputed_rank"]),
                "volume_confirmation_ratio": _as_float(row.get("volume_confirmation_ratio")),
                "pool_status": reconstructed["pool_status"],
                "pool_size": reconstructed["pool_size"],
                "scored_candidate_count": reconstructed.get("scored_candidate_count"),
                **returns,
            }
            hist = tickets_by_day_symbol.get((day, row["symbol"]))
            if hist:
                item["historical_ticket_score"] = hist.get("ticket_score")
                item["historical_rank"] = hist.get("ticket_rank")
                item["ticket_id"] = hist.get("ticket_id")
            reconstructed_rows.append(item)

    full_pool_rows = [row for row in reconstructed_rows if row.get("pool_status") == "FULL_POOL"]
    selected_only_days = sum(1 for day in reconstructed_days if day.get("pool_status") == "SELECTED_TICKET_ONLY")

    def slice_metrics(rows: list[dict[str, Any]], predicate, field: str) -> dict[str, Any]:
        values = [row[field] for row in rows if predicate(row) and row.get(field) is not None]
        return horizon_metrics(values)

    asof_days: list[dict[str, Any]] = []
    asof_rows: list[dict[str, Any]] = []
    asof_dates = sorted({day for day in kline_bars["trade_date"].dropna().unique() if day >= date(2026, 5, 26)})
    for day in asof_dates:
        replayed = replay_asof_universe_day(day, kline_bars)
        asof_days.append(replayed)
        for row in replayed.get("rows") or []:
            asof_rows.append(
                {
                    "as_of_date": day,
                    "symbol": row["symbol"],
                    "recomputed_rank": int(row["recomputed_rank"]),
                    "recomputed_ticket_score": _as_float(row.get("recomputed_ticket_score")),
                    "recomputed_market_score": _as_float(row.get("recomputed_market_score")),
                    "persisted_catalyst_score": 0.0,
                    "volume_confirmation_ratio": _as_float(row.get("volume_confirmation_ratio")),
                    "pool_status": replayed["pool_status"],
                    "pool_size": replayed.get("included_count"),
                    "universe_source": ASOF_UNIVERSE_SOURCE,
                    "catalyst_policy": ASOF_CATALYST_POLICY,
                    "t1": row.get("t1"),
                    "t3": row.get("t3"),
                    "t5": row.get("t5"),
                    "t10": row.get("t10"),
                    "t1_source": row.get("t1_source"),
                    "t3_source": row.get("t3_source"),
                    "t5_source": row.get("t5_source"),
                    "t10_source": row.get("t10_source"),
                }
            )
    asof_full_rows = [row for row in asof_rows if row.get("pool_status") == "FULL_ASOF_PANEL"]
    asof_top1 = [row for row in asof_full_rows if row.get("recomputed_rank") == 1]
    asof_t1_dates = [row["as_of_date"] for row in asof_top1 if row.get("t1") is not None]
    asof_periods = split_periods(asof_t1_dates)
    asof_walk = {
        name: period_metrics(asof_top1, dates, "t1")
        for name, dates in asof_periods.items()
    }
    asof_walk["holdout"] = asof_walk.get("holdout") or horizon_metrics([])
    asof_daily_returns = [
        (row["as_of_date"], row["t1"])
        for row in asof_top1
        if row.get("t1") is not None and row.get("as_of_date")
    ]
    asof_equity = equity_from_daily(asof_daily_returns)
    asof_ew = []
    asof_by_day = defaultdict(list)
    for row in asof_full_rows:
        if row.get("t1") is not None:
            asof_by_day[row["as_of_date"]].append(row["t1"])
    for day, values in sorted(asof_by_day.items()):
        if values:
            asof_ew.append(float(np.mean(values)))
    asof_monthly: dict[str, list[float]] = defaultdict(list)
    asof_weekly: dict[str, list[float]] = defaultdict(list)
    for row in asof_top1:
        day = row.get("as_of_date")
        if day is None or row.get("t1") is None:
            continue
        asof_monthly[day.strftime("%Y-%m")].append(row["t1"])
        asof_weekly[f"{day.isocalendar().year}-W{day.isocalendar().week:02d}"].append(row["t1"])
    asof_by_period = {"month": period_table(asof_monthly), "week": period_table(asof_weekly)}

    reconstructed_metrics = {
        "label": "CURRENT STRATEGY RECONSTRUCTED RESULT",
        "universe_source": ASOF_UNIVERSE_SOURCE,
        "index_universe_status": INDEX_UNIVERSE_STATUS,
        "catalyst_policy": ASOF_CATALYST_POLICY,
        "price_basis": "kline_close_unadjusted",
        "pool_days": len(asof_days),
        "full_pool_days": sum(1 for day in asof_days if day.get("pool_status") == "FULL_ASOF_PANEL"),
        "selected_ticket_only_days": selected_only_days,
        "incomplete_asof_days": sum(1 for day in asof_days if day.get("pool_status") != "FULL_ASOF_PANEL"),
        "top1_t1": slice_metrics(asof_full_rows, lambda row: row.get("recomputed_rank") == 1, "t1"),
        "top3_t1": slice_metrics(asof_full_rows, lambda row: (row.get("recomputed_rank") or 99) <= 3, "t1"),
        "top1_all_pools_t1": slice_metrics(asof_rows, lambda row: row.get("recomputed_rank") == 1, "t1"),
        "top3_all_pools_t1": slice_metrics(asof_rows, lambda row: (row.get("recomputed_rank") or 99) <= 3, "t1"),
        "persisted_candidate_reconstruction": {
            "pool_days": len(reconstructed_days),
            "full_pool_days": sum(1 for day in reconstructed_days if day.get("pool_status") == "FULL_POOL"),
            "selected_ticket_only_days": selected_only_days,
            "note": "Persisted tickets/candidates only. Not CURRENT STRATEGY EDGE.",
        },
        "note": (
            "CURRENT STRATEGY reconstruction uses the as-of kline panel as the "
            "tradable universe. nasdaq100/sp500 membership history is DATA_GAP. "
            "Catalyst evidence is unavailable as-of, so catalyst_score=0. "
            "This is frozen observable_footprint_v1 with missing catalyst, not a new strategy."
        ),
    }
    reconstructed_by_horizon = {}
    for horizon in HORIZONS:
        field = f"t{horizon}"
        reconstructed_by_horizon[str(horizon)] = {
            "top1_full_pool": slice_metrics(asof_full_rows, lambda row: row.get("recomputed_rank") == 1, field),
            "top3_full_pool": slice_metrics(asof_full_rows, lambda row: (row.get("recomputed_rank") or 99) <= 3, field),
            "selected_ticket_only": slice_metrics(
                [row for row in reconstructed_rows if row.get("pool_status") == "SELECTED_TICKET_ONLY"],
                lambda row: row.get("recomputed_rank") == 1,
                field,
            ),
        }

    score_pairs = [
        (row["historical_ticket_score"], row["recomputed_ticket_score"])
        for row in reconstructed_rows
        if row.get("historical_ticket_score") is not None and row.get("recomputed_ticket_score") is not None
    ]
    rank_pairs = [
        (row.get("historical_rank"), row.get("recomputed_rank"))
        for row in reconstructed_rows
        if row.get("historical_rank") is not None and row.get("recomputed_rank") is not None
    ]
    by_day_hist = defaultdict(list)
    by_day_recomputed = defaultdict(list)
    for row in tickets:
        if row.get("output_date") and row.get("ticket_rank") is not None:
            by_day_hist[row["output_date"]].append(row)
    for row in reconstructed_rows:
        by_day_recomputed[row["as_of_date"]].append(row)

    def top_set(rows: list[dict[str, Any]], key: str, n: int) -> set[str]:
        ordered = sorted(
            [row for row in rows if row.get(key) is not None],
            key=lambda item: item[key],
        )
        return {row["symbol"] for row in ordered[:n]}

    overlap_days = sorted(set(by_day_hist) & set(by_day_recomputed))
    top1_same = []
    top3_overlap = []
    top5_overlap = []
    for day in overlap_days:
        hist_top1 = top_set(by_day_hist[day], "ticket_rank", 1)
        rec_top1 = top_set(by_day_recomputed[day], "recomputed_rank", 1)
        hist_top3 = top_set(by_day_hist[day], "ticket_rank", 3)
        rec_top3 = top_set(by_day_recomputed[day], "recomputed_rank", 3)
        hist_top5 = top_set(by_day_hist[day], "ticket_rank", 5)
        rec_top5 = top_set(by_day_recomputed[day], "recomputed_rank", 5)
        top1_same.append(1.0 if hist_top1 and hist_top1 == rec_top1 else 0.0)
        top3_overlap.append(len(hist_top3 & rec_top3) / max(1, len(hist_top3 | rec_top3)))
        top5_overlap.append(len(hist_top5 & rec_top5) / max(1, len(hist_top5 | rec_top5)))
    ranking_consistency = {
        "score_correlation": correlation([a for a, _ in score_pairs], [b for _, b in score_pairs]),
        "rank_correlation": spearman(
            [float(a) for a, _ in rank_pairs],
            [float(b) for _, b in rank_pairs],
        ),
        "top1_same_rate": float(np.mean(top1_same)) if top1_same else None,
        "top3_overlap": float(np.mean(top3_overlap)) if top3_overlap else None,
        "top5_overlap": float(np.mean(top5_overlap)) if top5_overlap else None,
        "compared_days": len(overlap_days),
        "compared_score_pairs": len(score_pairs),
    }

    def bucket_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        ranked_days = defaultdict(list)
        for row in rows:
            ranked_days[row["as_of_date"]].append(row)
        buckets = {
            "Top 1": [],
            "Top 3": [],
            "Top 5": [],
            "Top 10%": [],
            "Top 20%": [],
            "Bottom 20%": [],
        }
        for day, day_rows in ranked_days.items():
            ordered = sorted(
                [row for row in day_rows if row.get("recomputed_ticket_score") is not None],
                key=lambda item: item["recomputed_ticket_score"],
                reverse=True,
            )
            n = len(ordered)
            if n == 0:
                continue
            for row in ordered[:1]:
                buckets["Top 1"].append(row)
            for row in ordered[:3]:
                buckets["Top 3"].append(row)
            for row in ordered[:5]:
                buckets["Top 5"].append(row)
            for row in ordered[: max(1, int(math.ceil(n * 0.10)))]:
                buckets["Top 10%"].append(row)
            for row in ordered[: max(1, int(math.ceil(n * 0.20)))]:
                buckets["Top 20%"].append(row)
            for row in ordered[max(0, int(math.floor(n * 0.80))):]:
                buckets["Bottom 20%"].append(row)
        out = {}
        for name, bucket in buckets.items():
            out[name] = {
                "t1": horizon_metrics([row["t1"] for row in bucket if row.get("t1") is not None]),
                "t3": horizon_metrics([row["t3"] for row in bucket if row.get("t3") is not None]),
                "count_rows": len(bucket),
            }
        top1_avg = (out["Top 1"]["t1"] or {}).get("avg_return")
        top5_avg = (out["Top 5"]["t1"] or {}).get("avg_return")
        bottom_avg = (out["Bottom 20%"]["t1"] or {}).get("avg_return")
        out["diagnostics"] = {
            "top1_lt_top5": bool(top1_avg is not None and top5_avg is not None and top1_avg < top5_avg),
            "high_not_better_than_low": bool(
                top1_avg is not None and bottom_avg is not None and top1_avg <= bottom_avg
            ),
        }
        return out

    score_buckets = bucket_rows(asof_full_rows)
    if not asof_full_rows:
        score_buckets["note"] = (
            "No FULL_ASOF_PANEL days. Score buckets were not computed from SELECTED_TICKET_ONLY."
        )

    obsidian_keys = {(row["output_date"], row["symbol"]) for row in obsidian if row.get("output_date") and row.get("symbol")}
    db_keys = {(row["output_date"], row["symbol"]) for row in tickets if row.get("output_date")}
    both = db_keys & obsidian_keys
    score_mismatch = 0
    return_mismatch = 0
    date_mismatch = 0
    obsidian_by_key: dict[tuple[date, str], dict[str, Any]] = {}
    for row in obsidian:
        if row.get("output_date") and row.get("symbol"):
            obsidian_by_key[(row["output_date"], row["symbol"])] = row
    for key in both:
        db_row = tickets_by_day_symbol.get(key)
        ob_row = obsidian_by_key.get(key)
        if not db_row or not ob_row:
            continue
        if db_row.get("ticket_score") is not None and ob_row.get("ticket_score") is not None:
            if abs(db_row["ticket_score"] - ob_row["ticket_score"]) > SCORE_MATCH_ABS:
                score_mismatch += 1
        t1_track = tracking_by_symbol_asof_h.get((key[1], db_row.get("as_of_date") or key[0], 1))
        if t1_track and t1_track.get("forward_return") is not None and ob_row.get("t1") is not None:
            if abs(t1_track["forward_return"] - ob_row["t1"]) > 0.0005:
                return_mismatch += 1
    recon_status = {
        "db_only": len(db_keys - obsidian_keys),
        "obsidian_only": len(obsidian_keys - db_keys),
        "both_match": max(0, len(both) - score_mismatch - return_mismatch),
        "score_mismatch": score_mismatch,
        "return_mismatch": return_mismatch,
        "date_mismatch": date_mismatch,
        "duplicate": ledger["duplicate_ticket_date_symbol"],
        "db_obsidian_match_rate": (len(both) / max(1, len(db_keys | obsidian_keys))),
        "history_reconciliation_rate": (len(both) / max(1, len(db_keys))),
        "return_reconciliation_rate": 1.0 - (return_mismatch / max(1, len(both))),
        "score_reconciliation_rate": 1.0 - (score_mismatch / max(1, len(score_pairs) or len(both))),
    }
    if score_pairs:
        close_matches = sum(1 for hist, rec in score_pairs if abs(hist - rec) <= SCORE_MATCH_ABS)
        recon_status["score_reconciliation_rate"] = close_matches / len(score_pairs)

    matrix_rows = []
    for ticket in tickets:
        rec_match = next(
            (
                row
                for row in reconstructed_rows
                if row.get("as_of_date") == ticket.get("output_date") and row.get("symbol") == ticket.get("symbol")
            ),
            None,
        )
        tmap = {
            horizon: next(
                (
                    sample["forward_return"]
                    for sample in realized_samples
                    if sample["ticket_id"] == ticket["ticket_id"] and sample["horizon"] == horizon
                ),
                None,
            )
            for horizon in HORIZONS
        }
        ob_row = obsidian_by_key.get((ticket["output_date"], ticket["symbol"]))
        recomputed_score = rec_match["recomputed_ticket_score"] if rec_match else None
        delta = None
        if ticket.get("ticket_score") is not None and recomputed_score is not None:
            delta = recomputed_score - ticket["ticket_score"]
        match_status = "db_only"
        if ob_row and rec_match:
            match_status = "both_match"
        elif ob_row:
            match_status = "obsidian_and_db"
        elif rec_match:
            match_status = "reconstructed"
        if ticket["as_of_date"] and ticket["output_date"] and ticket["as_of_date"] > ticket["output_date"]:
            match_status = "future_data_detected"
        matrix_rows.append(
            {
                "ticket_id": ticket["ticket_id"],
                "symbol": ticket["symbol"],
                "output_date": ticket["output_date"],
                "historical_score": ticket.get("ticket_score"),
                "recomputed_score": recomputed_score,
                "score_delta": delta,
                "historical_rank": ticket.get("ticket_rank"),
                "recomputed_rank": rec_match.get("recomputed_rank") if rec_match else None,
                "T1": tmap[1],
                "T3": tmap[3],
                "T5": tmap[5],
                "T10": tmap[10],
                "DB_result": tmap[1],
                "Obsidian_result": ob_row.get("t1") if ob_row else None,
                "match_status": match_status,
                "version_bucket": ticket["version_bucket"],
            }
        )

    ew_returns = []
    by_day_all = defaultdict(list)
    for row in t1_realized:
        by_day_all[row["output_date"]].append(row["forward_return"])
    for day, values in sorted(by_day_all.items()):
        if values:
            ew_returns.append(float(np.mean(values)))
    equal_weight_ref = horizon_metrics(ew_returns)

    recon_top1_returns = [
        row["t1"]
        for row in asof_full_rows
        if row.get("recomputed_rank") == 1 and row.get("t1") is not None
    ]
    cost_recon = {
        str(bps): horizon_metrics(apply_friction(recon_top1_returns, bps))
        for bps in COST_BPS
    }

    payload = {
        "strategy": STRATEGY,
        "strategy_status": PRODUCTION_BOUNDARY["strategy_status"],
        "weights_status": PRODUCTION_BOUNDARY["weights_status"],
        "ranking_key": list(RANKING_KEY),
        "formula": {
            "ticket_score": "0.75 * market_score + 0.25 * catalyst_score",
            "ranking": list(RANKING_KEY),
            "official_selection": "Top 1 after MIN_TICKET_SCORE filter, top_k=3 persisted",
        },
        "legacy_reference": LEGACY_REFERENCE,
        "ledger": ledger,
        "version_counts": ledger["version_counts"],
        "anomalies": anomalies,
        "realized": {
            "label": "LIVE/HISTORICAL REALIZED RESULT",
            "by_horizon": realized_by_horizon,
            "current_version_by_horizon": current_by_horizon,
            "valid_t1_samples": realized_by_horizon.get("1", {}).get("sample_count", 0),
        },
        "reconstructed": {
            "label": "CURRENT STRATEGY RECONSTRUCTED RESULT",
            **reconstructed_metrics,
            "by_horizon": reconstructed_by_horizon,
        },
        "walk_forward": asof_walk,
        "walk_forward_historical_realized": walk_forward,
        "cost_sensitivity": {
            "realized_t1": cost_realized,
            "reconstructed_top1_t1": cost_recon,
        },
        "equity": {k: v for k, v in asof_equity.items() if k != "points"},
        "equity_historical_realized_top1": {k: v for k, v in equity.items() if k != "points"},
        "benchmark": {
            "equal_weight_same_day_tickets_t1": equal_weight_ref,
            "equal_weight_asof_panel_t1": horizon_metrics(asof_ew),
            "spy": "UNAVAILABLE_NO_SPY_SERIES",
        },
        "ranking_consistency": ranking_consistency,
        "reconciliation": recon_status,
        "score_buckets": score_buckets,
        "by_period": {
            "month": {
                "profitable_month_ratio": asof_by_period["month"]["profitable_ratio"],
                "max_consecutive_negative_periods": asof_by_period["month"]["max_consecutive_negative_periods"],
                "rows": asof_by_period["month"]["rows"],
            },
            "week": {
                "profitable_week_ratio": asof_by_period["week"]["profitable_ratio"],
                "max_consecutive_negative_periods": asof_by_period["week"]["max_consecutive_negative_periods"],
                "rows": asof_by_period["week"]["rows"],
            },
        },
        "by_period_historical_realized": {
            "month": {
                "profitable_month_ratio": by_period["month"]["profitable_ratio"],
                "max_consecutive_negative_periods": by_period["month"]["max_consecutive_negative_periods"],
                "rows": by_period["month"]["rows"],
            },
            "week": {
                "profitable_week_ratio": by_period["week"]["profitable_ratio"],
                "max_consecutive_negative_periods": by_period["week"]["max_consecutive_negative_periods"],
                "rows": by_period["week"]["rows"],
            },
        },
    }
    payload["verdict"] = decide_verdict(payload)
    payload["questions"] = {
        "1_valid_samples": payload["realized"]["valid_t1_samples"],
        "2_t1_win_rate": (realized_by_horizon.get("1") or {}).get("win_rate"),
        "3_t1_avg_return": (realized_by_horizon.get("1") or {}).get("avg_return"),
        "4_t1_profit_factor": (realized_by_horizon.get("1") or {}).get("profit_factor"),
        "5_t1_expectancy": (realized_by_horizon.get("1") or {}).get("expectancy"),
        "6_top1_profitable": pass_fail(reconstructed_metrics.get("top1_t1")) == "PASS",
        "7_recent_profitable": pass_fail(asof_walk.get("holdout")) == "PASS",
        "8_cost_25bps_pass": pass_fail(cost_recon.get("25")) == "PASS",
        "9_history_current_score_agreement": recon_status.get("score_reconciliation_rate"),
        "10_final": payload["verdict"]["profitability"],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(
        OUTPUT_DIR / "historical_ticket_reconciliation.csv",
        matrix_rows,
        [
            "ticket_id",
            "symbol",
            "output_date",
            "historical_score",
            "recomputed_score",
            "score_delta",
            "historical_rank",
            "recomputed_rank",
            "T1",
            "T3",
            "T5",
            "T10",
            "DB_result",
            "Obsidian_result",
            "match_status",
            "version_bucket",
        ],
    )
    write_csv(
        OUTPUT_DIR / "current_strategy_replay.csv",
        asof_rows,
        [
            "as_of_date",
            "symbol",
            "recomputed_rank",
            "recomputed_ticket_score",
            "recomputed_market_score",
            "persisted_catalyst_score",
            "pool_status",
            "pool_size",
            "universe_source",
            "catalyst_policy",
            "t1",
            "t3",
            "t5",
            "t10",
            "t1_source",
        ],
    )
    write_csv(
        OUTPUT_DIR / "equity_curve.csv",
        asof_equity.get("points") or [],
        ["date", "daily_return", "equity", "drawdown"],
    )
    write_json(OUTPUT_DIR / "profitability_metrics.json", payload["realized"])
    write_json(OUTPUT_DIR / "profitability_by_horizon.json", {
        "realized": realized_by_horizon,
        "current_version": current_by_horizon,
        "reconstructed": reconstructed_by_horizon,
        "legacy_reference": LEGACY_REFERENCE,
    })
    write_json(OUTPUT_DIR / "profitability_by_score_bucket.json", score_buckets)
    write_json(OUTPUT_DIR / "profitability_by_period.json", payload["by_period"])
    write_json(OUTPUT_DIR / "cost_sensitivity.json", payload["cost_sensitivity"])
    report_text = build_report(payload)
    (OUTPUT_DIR / "production_profitability_report.md").write_text(
        "# Production Profitability Report\n\n"
        "READ ONLY validation of frozen `observable_footprint_v1`.\n\n"
        "## Distinctions\n\n"
        f"- LEGACY BACKTEST RESULT: {LEGACY_REFERENCE['win_rate']:.1%} / {LEGACY_REFERENCE['avg_return']:+.2%} "
        f"({LEGACY_REFERENCE['total_trades']} trades, {LEGACY_REFERENCE['source']})\n"
        f"- LIVE/HISTORICAL REALIZED RESULT T+1: {fmt_pct((realized_by_horizon.get('1') or {}).get('win_rate'))} / "
        f"{fmt_pct((realized_by_horizon.get('1') or {}).get('avg_return'), signed=True)}\n"
        f"- CURRENT STRATEGY RECONSTRUCTED Top1 T+1 (FULL_ASOF_PANEL): {fmt_pct((reconstructed_metrics.get('top1_t1') or {}).get('win_rate'))} / "
        f"{fmt_pct((reconstructed_metrics.get('top1_t1') or {}).get('avg_return'), signed=True)} "
        f"(full_pool_days={reconstructed_metrics.get('full_pool_days', 0)}; universe={ASOF_UNIVERSE_SOURCE}; catalyst={ASOF_CATALYST_POLICY})\n"
        f"- INDEX MEMBERSHIP: {INDEX_UNIVERSE_STATUS}\n"
        f"- SELECTED_TICKET_ONLY Top1 T+1: {fmt_pct((((reconstructed_by_horizon.get('1') or {}).get('selected_ticket_only') or {}).get('win_rate')))} / "
        f"{fmt_pct((((reconstructed_by_horizon.get('1') or {}).get('selected_ticket_only') or {}).get('avg_return')), signed=True)} "
        f"(cannot prove CURRENT STRATEGY EDGE)\n"
        f"- RECENT HOLDOUT T+1: {fmt_pct((asof_walk.get('holdout') or {}).get('win_rate'))} / "
        f"{fmt_pct((asof_walk.get('holdout') or {}).get('avg_return'), signed=True)}\n\n"
        "## Anomalies\n\n"
        + "\n".join(f"- {key}: {value}" for key, value in anomalies.items())
        + "\n\n## Verdict reasons\n\n"
        + "\n".join(f"- {item}" for item in payload["verdict"]["reasons"])
        + "\n\n```text\n"
        + report_text
        + "```\n",
        encoding="utf-8",
    )
    write_json(OUTPUT_DIR / "production_profitability_summary.json", {
        **payload,
        "equity_points_omitted": True,
        "strategy_change": "NONE",
        "weight_change": "NONE",
        "read_only": True,
    })
    print(report_text)
    return payload


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
