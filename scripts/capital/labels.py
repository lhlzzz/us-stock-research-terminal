"""Deterministic post-hoc public-data outcome labels for Capital Behavior V3."""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

import pandas as pd

from .dataset import LABEL_VERSION
from .features import normalize_ohlcv
from .scoring import build_capital_assessment


HORIZONS = (1, 3, 5, 10)
PATH_LABELS = (
    "UP_CONTINUATION", "PULLBACK_CONTINUE", "ACCELERATION", "SIDEWAYS",
    "DISTRIBUTION", "BREAKDOWN", "TRAP", "OTHER",
)


def _bars_after(frame: pd.DataFrame, as_of_date: date | str) -> pd.DataFrame:
    bars = normalize_ohlcv(frame)
    cutoff = pd.Timestamp(as_of_date)
    return bars.loc[bars.index > cutoff]


def _return_at(bars: pd.DataFrame, entry: float, horizon: int) -> float | None:
    if len(bars) < horizon or entry <= 0:
        return None
    return round(float(bars.iloc[horizon - 1]["close"]) / entry - 1.0, 6)


def _path_label(bars: pd.DataFrame, entry: float, horizon: int) -> str | None:
    if len(bars) < horizon or entry <= 0:
        return None
    window = bars.iloc[:horizon]
    closes = window["close"].astype(float)
    lows = window["low"].astype(float)
    returns = closes / entry - 1.0
    final_return = float(returns.iloc[-1])
    max_gain = float(returns.max())
    min_return = float(returns.min())
    max_drawdown = float((lows / entry - 1.0).min())
    if max_gain >= 0.04 and final_return <= max_gain - 0.035 and final_return <= 0.01:
        return "TRAP" if final_return <= -0.02 else "DISTRIBUTION"
    if final_return <= -0.06 or max_drawdown <= -0.08:
        return "BREAKDOWN"
    if max_gain >= 0.08 and final_return >= 0.05 and min_return > -0.035:
        return "ACCELERATION"
    if final_return >= 0.03 and min_return > -0.035:
        return "UP_CONTINUATION"
    if final_return <= -0.02:
        return "PULLBACK_CONTINUE"
    span = float(closes.max() / closes.min() - 1.0) if closes.min() > 0 else 1.0
    if abs(final_return) < 0.02 and span < 0.05:
        return "SIDEWAYS"
    return "OTHER"


def _state_at(bars: pd.DataFrame, horizon: int) -> tuple[str | None, str | None]:
    if len(bars) < horizon:
        return None, None
    bounded = bars.iloc[:horizon]
    assessment = build_capital_assessment(bounded)
    state = assessment.get("state", {}).get("capital_state")
    intent = assessment.get("intent", {}).get("capital_intent")
    return state, intent


def label_future_outcomes(
    frame: pd.DataFrame,
    *,
    as_of_date: date | str,
    current_state: str | None = None,
) -> dict[str, Any]:
    """Label only bars strictly after ``as_of_date``.

    A missing horizon remains ``None``. The state and intent values are
    explicitly post-hoc public-data proxies, never institutional facts.
    """
    bounded = normalize_ohlcv(frame)
    prior = bounded.loc[bounded.index <= pd.Timestamp(as_of_date)]
    future = _bars_after(bounded, as_of_date)
    if prior.empty or future.empty:
        return {"label_version": LABEL_VERSION, "as_of_date": str(as_of_date), "available": False}
    entry = float(prior.iloc[-1]["close"])
    outcome: dict[str, Any] = {
        "label_version": LABEL_VERSION,
        "as_of_date": str(pd.Timestamp(as_of_date).date()),
        "available": True,
        "actual_intent_semantic": "POST_HOC_PUBLIC_DATA_INFERRED_PROXY",
    }
    for horizon in HORIZONS:
        # The state at T+h must use the complete as-of history plus exactly h
        # future bars, never bars beyond the label horizon.
        bounded_horizon = pd.concat([prior, future.iloc[:horizon]]).sort_index()
        if len(future) < horizon:
            state, intent = None, None
        else:
            state_assessment = build_capital_assessment(bounded_horizon)
            state = state_assessment.get("state", {}).get("capital_state")
            intent = state_assessment.get("intent", {}).get("capital_intent")
        return_value = _return_at(future, entry, horizon)
        path = _path_label(future, entry, horizon)
        outcome[f"return_{horizon}d"] = return_value
        outcome[f"state_after_{horizon}d"] = state
        outcome[f"path_after_{horizon}d"] = path
        outcome[f"intent_after_{horizon}d"] = intent
        outcome[f"transition_after_{horizon}d"] = (
            f"{current_state}->{state}" if current_state and state else None
        )
    outcome["actual_path"] = outcome.get("path_after_3d") or outcome.get("path_after_1d")
    outcome["actual_intent_proxy"] = outcome.get("intent_after_3d") or outcome.get("intent_after_1d")
    outcome["transition_label"] = outcome.get("transition_after_3d") or outcome.get("transition_after_1d")
    return outcome


def outcome_is_complete(outcome: Mapping[str, Any] | None) -> bool:
    return bool(outcome) and all(outcome.get(f"return_{horizon}d") is not None for horizon in HORIZONS)


def label_for_tracking_row(
    frame: pd.DataFrame,
    *,
    as_of_date: date | str,
    current_state: str | None = None,
) -> dict[str, Any]:
    """Compatibility adapter for the existing forward-tracking owner."""
    return label_future_outcomes(frame, as_of_date=as_of_date, current_state=current_state)
