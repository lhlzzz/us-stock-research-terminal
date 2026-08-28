"""Deterministic OHLCV feature preparation for the Capital Brain."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ("close", "high", "low", "volume")


def clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return low
    if not np.isfinite(number):
        return low
    return float(min(high, max(low, number)))


def normalize_ohlcv(frame: pd.DataFrame | None) -> pd.DataFrame:
    """Return a de-duplicated, ascending OHLCV frame without forward filling."""
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    aliases = {
        "date": "date",
        "Date": "date",
        "open": "open",
        "Open": "open",
        "high": "high",
        "High": "high",
        "low": "low",
        "Low": "low",
        "close": "close",
        "Close": "close",
        "volume": "volume",
        "Volume": "volume",
    }
    selected = frame.rename(columns={key: aliases[key] for key in frame.columns if key in aliases}).copy()
    if "date" in selected:
        selected["date"] = pd.to_datetime(selected["date"], errors="coerce")
        selected = selected.dropna(subset=["date"]).sort_values("date").drop_duplicates("date", keep="last")
        selected = selected.set_index("date")
    elif not isinstance(selected.index, pd.DatetimeIndex):
        selected.index = pd.to_datetime(selected.index, errors="coerce")
        selected = selected.loc[selected.index.notna()]
    for column in ("open", "high", "low", "close", "volume"):
        if column not in selected:
            selected[column] = np.nan
        selected[column] = pd.to_numeric(selected[column], errors="coerce")
    selected = selected.replace([np.inf, -np.inf], np.nan).sort_index()
    valid_prices = selected[list(REQUIRED_COLUMNS[:-1])].notna().all(axis=1) & (selected["close"] > 0)
    return selected.loc[valid_prices]


def availability(frame: pd.DataFrame, minimum_rows: int = 20) -> tuple[bool, str]:
    if len(frame) < minimum_rows:
        return False, "INSUFFICIENT_HISTORY"
    if frame["volume"].iloc[-20:].fillna(0).sum() <= 0:
        return False, "ZERO_OR_MISSING_VOLUME"
    return True, "AVAILABLE"


def _safe_ratio(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return 0.0
    return float(numerator / denominator)


def build_feature_set(
    frame: pd.DataFrame | None,
    relative_strength: float | None = None,
) -> dict[str, float | int | bool | str]:
    """Build only features observable at the final row of ``frame``."""
    bars = normalize_ohlcv(frame)
    ready, availability_status = availability(bars)
    result: dict[str, float | int | bool | str] = {
        "row_count": int(len(bars)),
        "available": ready,
        "availability": availability_status,
        "relative_strength": float(relative_strength) if relative_strength is not None and np.isfinite(relative_strength) else 0.0,
    }
    if bars.empty:
        return result

    close = bars["close"]
    high = bars["high"]
    low = bars["low"]
    volume = bars["volume"].fillna(0)
    returns = close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    ranges = (high - low).replace(0, np.nan)
    close_position = ((close - low) / ranges).replace([np.inf, -np.inf], np.nan).fillna(0.5)
    baseline20 = volume.rolling(20, min_periods=5).median()
    volume_ratio = _safe_ratio(float(volume.iloc[-1]), float(baseline20.iloc[-1]))
    volume_mean20 = volume.rolling(20, min_periods=5).mean()
    volume_std20 = volume.rolling(20, min_periods=5).std(ddof=0)
    volume_z = _safe_ratio(float(volume.iloc[-1] - volume_mean20.iloc[-1]), float(volume_std20.iloc[-1]))
    up_volume = volume.where(returns > 0, 0.0).rolling(10, min_periods=3).sum()
    down_volume = volume.where(returns < 0, 0.0).abs().rolling(10, min_periods=3).sum()
    recent = returns.iloc[-10:]
    downside_volume_recent = volume.where(returns < 0, 0.0).iloc[-5:].mean()
    downside_volume_prior = volume.where(returns < 0, 0.0).iloc[-10:-5].mean()
    pullback = close.rolling(5, min_periods=3).max() / close - 1.0
    max_drawdown_5 = float(pullback.iloc[-5:].max()) if len(pullback) >= 5 else 0.0
    prior_drawdown_5 = float(pullback.iloc[-10:-5].max()) if len(pullback) >= 10 else max_drawdown_5
    high_20 = close.rolling(20, min_periods=5).max()
    failed_breakdown = bool(close.iloc[-1] >= close.iloc[-3:].min() and close.iloc[-1] > low.iloc[-3:].min())
    result.update(
        {
            "return_1d": float(returns.iloc[-1]),
            "return_3d": float(close.iloc[-1] / close.iloc[-4] - 1.0) if len(close) >= 4 else 0.0,
            "return_5d": float(close.iloc[-1] / close.iloc[-6] - 1.0) if len(close) >= 6 else 0.0,
            "return_10d": float(close.iloc[-1] / close.iloc[-11] - 1.0) if len(close) >= 11 else 0.0,
            "return_20d": float(close.iloc[-1] / close.iloc[-21] - 1.0) if len(close) >= 21 else 0.0,
            "volume_vs_baseline": volume_ratio,
            "volume_zscore": volume_z,
            "up_volume_ratio": _safe_ratio(float(up_volume.iloc[-1]), float(up_volume.iloc[-1] + down_volume.iloc[-1])),
            "down_volume_ratio": _safe_ratio(float(down_volume.iloc[-1]), float(up_volume.iloc[-1] + down_volume.iloc[-1])),
            "volume_persistence": float((volume.iloc[-5:] > baseline20.iloc[-5:]).mean()),
            "volume_acceleration": _safe_ratio(float(volume.iloc[-5:].mean()), float(volume.iloc[-10:-5].mean())),
            "volume_concentration": _safe_ratio(float(volume.iloc[-1]), float(volume.iloc[-5:].sum())),
            "close_position": float(close_position.iloc[-1]),
            "close_position_5d": float(close_position.iloc[-5:].mean()),
            "range_decay": _safe_ratio(float((high - low).iloc[-5:].mean()), float((high - low).iloc[-10:-5].mean())),
            "downside_volume_decay": _safe_ratio(float(downside_volume_recent), float(downside_volume_prior)),
            "higher_low": float(low.iloc[-1] > low.iloc[-5:].min()) if len(low) >= 5 else 0.0,
            "failed_breakdown": float(failed_breakdown),
            "recovery_speed": float((returns.iloc[-3:] > 0).mean()),
            "pullback_resilience": clamp(1.0 - max(0.0, max_drawdown_5) / max(0.01, prior_drawdown_5)),
            "price_progress": clamp(_safe_ratio(float(close.iloc[-1] - close.iloc[-5]), float((high - low).iloc[-5:].sum())), -1.0, 1.0),
            "distance_from_20d_high": _safe_ratio(float(close.iloc[-1]), float(high_20.iloc[-1])) - 1.0,
            "recent_positive_days": float((recent > 0).mean()),
            "recent_negative_days": float((recent < 0).mean()),
            "flat_price": bool(abs(float(returns.iloc[-5:].sum())) < 0.002),
        }
    )
    return result


def build_intraday_feature_set(
    daily_context: dict[str, Any],
    quote: dict[str, Any],
) -> dict[str, Any]:
    """Derive session-only evidence without treating a quote as a daily bar."""
    price = float(quote.get("latest_price") or 0.0)
    prev_close = float(quote.get("prev_close") or 0.0)
    high = float(quote.get("high") or price)
    low = float(quote.get("low") or price)
    volume = float(quote.get("volume") or 0.0)
    pct_change = price / prev_close - 1.0 if prev_close > 0 else 0.0
    range_position = _safe_ratio(price - low, high - low) if high > low else 0.5
    daily_volume_pressure = clamp(daily_context.get("volume_pressure", 0.0))
    daily_demand = clamp(daily_context.get("demand_persistence_score", 0.0))
    return {
        "available": bool(price > 0 and prev_close > 0),
        "availability": "AVAILABLE" if price > 0 and prev_close > 0 else "MISSING_QUOTE_FIELDS",
        "price": price,
        "prev_close": prev_close,
        "volume": volume,
        "pct_change": pct_change,
        "range_position": clamp(range_position),
        "session_momentum": clamp((pct_change + 0.02) / 0.06),
        "session_downside": clamp((-pct_change + 0.02) / 0.06),
        "daily_volume_pressure": daily_volume_pressure,
        "daily_demand_persistence": daily_demand,
        "quote_semantic": "OBSERVED",
    }
