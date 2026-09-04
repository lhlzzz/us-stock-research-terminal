"""Independent future-price outcomes. Not V2 state/intent labels."""
from __future__ import annotations

import math
from datetime import date
from typing import Any, Iterable, Mapping

import pandas as pd


HORIZONS = (1, 3, 5, 10)


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _normalize(frame: pd.DataFrame) -> pd.DataFrame:
    bars = frame.copy()
    if "date" not in bars.columns and "trade_date" in bars.columns:
        bars = bars.rename(columns={"trade_date": "date"})
    if "date" in bars.columns:
        bars["date"] = pd.to_datetime(bars["date"])
        bars = bars.set_index("date")
    bars = bars.sort_index()
    bars = bars[~bars.index.duplicated(keep="last")]
    return bars


def independent_price_outcomes(
    frame: pd.DataFrame | None,
    *,
    as_of_date: date | str,
    benchmark: pd.DataFrame | None = None,
    sector: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """T+h returns, MFE/MAE, drawdown, relative returns from future bars only."""
    if frame is None or getattr(frame, "empty", True):
        return {"available": False, "as_of_date": str(as_of_date), "label_kind": "INDEPENDENT_PRICE"}
    bars = _normalize(frame)
    cutoff = pd.Timestamp(as_of_date)
    prior = bars.loc[bars.index <= cutoff]
    future = bars.loc[bars.index > cutoff]
    if prior.empty:
        return {"available": False, "as_of_date": str(as_of_date), "label_kind": "INDEPENDENT_PRICE"}
    entry = _finite(prior.iloc[-1]["close"])
    if not entry or entry <= 0:
        return {"available": False, "as_of_date": str(as_of_date), "label_kind": "INDEPENDENT_PRICE"}
    outcome: dict[str, Any] = {
        "available": True,
        "as_of_date": str(pd.Timestamp(as_of_date).date()),
        "label_kind": "INDEPENDENT_PRICE",
        "entry_close": round(entry, 6),
    }
    for horizon in HORIZONS:
        if len(future) < horizon:
            outcome[f"return_{horizon}d"] = None
            continue
        close = _finite(future.iloc[horizon - 1]["close"])
        outcome[f"return_{horizon}d"] = None if close is None else round(close / entry - 1.0, 6)
    window = future.iloc[: max((h for h in HORIZONS if len(future) >= h), default=0)] if not future.empty else future
    if window.empty:
        outcome.update({"mfe": None, "mae": None, "max_drawdown": None, "volatility": None, "gap_risk": None})
    else:
        highs = window["high"].astype(float) / entry - 1.0
        lows = window["low"].astype(float) / entry - 1.0
        closes = window["close"].astype(float)
        outcome["mfe"] = round(float(highs.max()), 6)
        outcome["mae"] = round(float(lows.min()), 6)
        outcome["max_drawdown"] = round(float(lows.min()), 6)
        rets = closes.pct_change().dropna()
        outcome["volatility"] = round(float(rets.std()), 6) if len(rets) else None
        if "open" in prior.columns:
            last_close = entry
            first_open = _finite(window.iloc[0]["open"]) if "open" in window.columns else None
            outcome["gap_risk"] = None if first_open is None else round(first_open / last_close - 1.0, 6)
        else:
            outcome["gap_risk"] = None

    def _relative(other: pd.DataFrame | None, name: str) -> None:
        if other is None or getattr(other, "empty", True):
            outcome[name] = None
            return
        bench = _normalize(other)
        future_b = bench.loc[bench.index > cutoff]
        prior_b = bench.loc[bench.index <= cutoff]
        if prior_b.empty or future_b.empty or len(future) < 5 or len(future_b) < 5:
            outcome[name] = None
            return
        entry_b = _finite(prior_b.iloc[-1]["close"])
        close_b = _finite(future_b.iloc[4]["close"])
        close_s = _finite(future.iloc[4]["close"])
        if not entry_b or not close_b or not close_s:
            outcome[name] = None
            return
        outcome[name] = round((close_s / entry - 1.0) - (close_b / entry_b - 1.0), 6)

    _relative(benchmark, "benchmark_relative_return")
    _relative(sector, "sector_relative_return")
    return outcome


def completed_horizon_returns(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Completed-only long-form tracking. Conflicts invalidate the sample."""
    collected: dict[int, list[float]] = {horizon: [] for horizon in HORIZONS}
    conflicts = []
    for row in rows:
        if str(row.get("check_status") or "").lower() != "completed":
            continue
        horizon = int(row.get("horizon_days") or 0)
        value = _finite(row.get("forward_return"))
        if horizon in HORIZONS and value is not None:
            collected[horizon].append(value)
        for key, mapped in ((f"return_{h}d", h) for h in HORIZONS):
            wide = _finite(row.get(key))
            if wide is not None:
                collected[mapped].append(wide)
    outcome = {f"return_{horizon}d": None for horizon in HORIZONS}
    for horizon, values in collected.items():
        unique: list[float] = []
        for value in values:
            if not any(abs(value - seen) < 1e-12 for seen in unique):
                unique.append(value)
        if len(unique) > 1:
            conflicts.append({"horizon": horizon, "values": unique})
        elif unique:
            outcome[f"return_{horizon}d"] = unique[0]
    outcome["outcome_conflict"] = bool(conflicts)
    outcome["outcome_conflicts"] = conflicts
    outcome["complete"] = all(outcome[f"return_{h}d"] is not None for h in HORIZONS) and not conflicts
    return outcome
