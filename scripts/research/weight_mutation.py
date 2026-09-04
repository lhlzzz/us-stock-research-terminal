"""Single legal entry for automatic weight changes.

Optimizer, self-evolve, calibration, regime adaptation, and factor
tuning must call :func:`request_weight_change`. Direct writes to
``scoring_config`` / weight artifacts are not a legal auto path.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping

from .boundary import PRODUCTION_BOUNDARY, learning_cannot_auto_weight
from .stability import (
    CONFIRMATION_PERIODS,
    KEEP_PREVIOUS_WEIGHT,
    MIN_SAMPLES,
    MIN_TRADING_DAYS,
    weight_change_guard,
)

__all__ = ["KEEP_PREVIOUS_WEIGHT", "request_weight_change", "audit_records"]

MIN_FACTOR_COVERAGE = 0.75
MAX_AVERAGE_LOSS = -0.05
UPDATE_WEIGHT = "UPDATE_WEIGHT"

_AUDIT: list[dict[str, Any]] = []


def audit_records() -> list[dict[str, Any]]:
    return list(_AUDIT)


def request_weight_change(
    *,
    source: str,
    previous: float | Mapping[str, float] | None,
    proposed: float | Mapping[str, float] | None,
    persist: Callable[[], Any] | None = None,
    sample_count: int = 0,
    trading_days: int = 0,
    factor_coverage: float | None = None,
    confirmations: int = 0,
    sign_stability: float | None = None,
    average_loss: float | None = None,
    key: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Validate then optionally persist. Failed guards never write."""
    reasons: list[str] = []
    if learning_cannot_auto_weight(source):
        reasons.append("learning_cannot_auto_weight")
    if sample_count < MIN_SAMPLES:
        reasons.append("min_samples")
    if trading_days < MIN_TRADING_DAYS:
        reasons.append("min_trading_days")
    if factor_coverage is not None and factor_coverage < MIN_FACTOR_COVERAGE:
        reasons.append("factor_coverage")
    if confirmations < CONFIRMATION_PERIODS:
        reasons.append("confirmation")
    if average_loss is not None and average_loss < MAX_AVERAGE_LOSS:
        reasons.append("performance_guard")

    if isinstance(previous, Mapping) or isinstance(proposed, Mapping):
        prev_map = dict(previous or {})
        prop_map = dict(proposed or {})
        keys = sorted(set(prev_map) | set(prop_map))
        factor_reasons: dict[str, list[str]] = {}
        keep_any = bool(reasons)
        for factor in keys:
            guard = weight_change_guard(
                prev_map.get(factor),
                prop_map.get(factor),
                sample_count=sample_count,
                trading_days=trading_days,
                sign_stability=sign_stability,
                confirmations=confirmations,
            )
            factor_reasons[factor] = list(guard["reasons"])
            if guard["action"] == KEEP_PREVIOUS_WEIGHT:
                keep_any = True
                reasons.extend(item for item in guard["reasons"] if item not in reasons)
        keep = keep_any
        applied = prev_map if keep else prop_map
    else:
        guard = weight_change_guard(
            previous if previous is None else float(previous),
            proposed if proposed is None else float(proposed),
            sample_count=sample_count,
            trading_days=trading_days,
            sign_stability=sign_stability,
            confirmations=confirmations,
        )
        for item in guard["reasons"]:
            if item not in reasons:
                reasons.append(item)
        keep = bool(reasons) or guard["action"] == KEEP_PREVIOUS_WEIGHT
        applied = previous if keep else proposed
        factor_reasons = {str(key or "weight"): list(guard["reasons"])}

    action = KEEP_PREVIOUS_WEIGHT if keep else UPDATE_WEIGHT
    persisted = False
    persist_result = None
    if action == UPDATE_WEIGHT and persist is not None:
        persist_result = persist()
        persisted = True
    record = {
        "source": source,
        "key": key,
        "action": action,
        "previous": previous if not isinstance(previous, Mapping) else dict(previous),
        "proposed": proposed if not isinstance(proposed, Mapping) else dict(proposed),
        "applied": applied,
        "persisted": persisted,
        "reasons": reasons,
        "factor_reasons": factor_reasons,
        "sample_count": sample_count,
        "trading_days": trading_days,
        "factor_coverage": factor_coverage,
        "confirmations": confirmations,
        "reason": reason,
        "persist_result": persist_result,
        "at": datetime.utcnow().isoformat() + "Z",
        "production_boundary": PRODUCTION_BOUNDARY,
        "does_not_bypass_guard": True,
        "not_a_buy_sell": True,
    }
    _AUDIT.append(record)
    return record
