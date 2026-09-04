"""Factor stability and weight-change guard. Does not write production weights."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from .boundary import PRODUCTION_BOUNDARY

FACTOR_STATUSES = ("STABLE", "DEGRADING", "UNSTABLE", "REVERSED", "INSUFFICIENT_DATA")
KEEP_PREVIOUS_WEIGHT = "KEEP_PREVIOUS_WEIGHT"

MIN_SAMPLES = 20
MIN_TRADING_DAYS = 10
MAX_PERIOD_CHANGE = 0.10
CONFIRMATION_PERIODS = 2


def _sign(value: float | None) -> int:
    if value is None:
        return 0
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def factor_stability(row: Mapping[str, Any] | None = None) -> dict[str, Any]:
    row = dict(row or {})
    current = row.get("current_ic")
    r30 = row.get("rolling_30d_ic")
    r60 = row.get("rolling_60d_ic")
    r120 = row.get("rolling_120d_ic")
    regime = row.get("regime_ic")
    coverage = row.get("coverage")
    samples = int(row.get("sample_count") or 0)
    signs = [_sign(value) for value in (current, r30, r60, r120) if value is not None]
    sign_stability = None
    if signs:
        sign_stability = round(sum(1 for item in signs if item == signs[0]) / len(signs), 4)
    if samples < MIN_SAMPLES or current is None:
        status = "INSUFFICIENT_DATA"
    elif current is not None and r30 is not None and _sign(current) != _sign(r30) and _sign(r30) != 0:
        status = "REVERSED"
    elif sign_stability is not None and sign_stability < 0.5:
        status = "UNSTABLE"
    elif r30 is not None and current is not None and abs(current) + 1e-9 < abs(r30) * 0.5:
        status = "DEGRADING"
    else:
        status = "STABLE"
    return {
        "factor": row.get("factor"),
        "current_ic": current,
        "rolling_30d_ic": r30,
        "rolling_60d_ic": r60,
        "rolling_120d_ic": r120,
        "walk_forward_ic": row.get("walk_forward_ic"),
        "regime_ic": regime,
        "sector_ic": row.get("sector_ic"),
        "stability_score": sign_stability,
        "sign_stability": sign_stability,
        "coverage": coverage,
        "sample_count": samples,
        "factor_status": status,
        "does_not_write_production_weights": True,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def weight_change_guard(
    previous: float | None,
    proposed: float | None,
    *,
    sample_count: int = 0,
    trading_days: int = 0,
    sign_stability: float | None = None,
    confirmations: int = 0,
    max_period_change: float = MAX_PERIOD_CHANGE,
) -> dict[str, Any]:
    reasons = []
    if sample_count < MIN_SAMPLES:
        reasons.append("min_samples")
    if trading_days < MIN_TRADING_DAYS:
        reasons.append("min_trading_days")
    if sign_stability is not None and sign_stability < 0.6:
        reasons.append("sign_stability")
    if confirmations < CONFIRMATION_PERIODS:
        reasons.append("confirmation")
    if previous is not None and proposed is not None and abs(proposed - previous) > max_period_change:
        reasons.append("max_period_change")
    keep = bool(reasons) or previous is None or proposed is None
    return {
        "action": KEEP_PREVIOUS_WEIGHT if keep else "UPDATE_WEIGHT",
        "previous": previous,
        "proposed": None if keep else proposed,
        "applied": previous if keep else proposed,
        "reasons": reasons,
        "min_samples": MIN_SAMPLES,
        "min_trading_days": MIN_TRADING_DAYS,
        "max_period_change": max_period_change,
        "confirmation_periods": CONFIRMATION_PERIODS,
        "does_not_write_production_weights": True,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def stability_table(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [factor_stability(row) for row in rows]
