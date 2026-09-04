"""Single legal entry for automatic weight changes.

Optimizer, self-evolve, calibration, regime adaptation, and factor
tuning must call :func:`request_weight_change`. Direct writes to
``scoring_config`` / weight artifacts are not a legal auto path.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping

from .boundary import (
    PRODUCTION_BOUNDARY,
    WeightMutationBlocked,
    assert_weight_mutation_allowed,
    learning_cannot_auto_weight,
    strategy_is_frozen,
    weights_are_frozen,
)
from .stability import (
    CONFIRMATION_PERIODS,
    KEEP_PREVIOUS_WEIGHT,
    MIN_SAMPLES,
    MIN_TRADING_DAYS,
    weight_change_guard,
)

__all__ = [
    "KEEP_PREVIOUS_WEIGHT",
    "PROPOSAL_ONLY",
    "request_weight_change",
    "audit_records",
    "WeightMutationBlocked",
]

MIN_FACTOR_COVERAGE = 0.75
MAX_AVERAGE_LOSS = -0.05
UPDATE_WEIGHT = "UPDATE_WEIGHT"
PROPOSAL_ONLY = "PROPOSAL_ONLY"

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
    """Validate then optionally persist. Failed guards never write.

    Frozen strategy / frozen weights never persist. Callers may still
    receive a PROPOSAL_ONLY record. Direct persist callbacks are not a
    legal production mutation path.
    """
    reasons: list[str] = []
    frozen = strategy_is_frozen() or weights_are_frozen()
    if frozen:
        reasons.append("strategy_frozen")
        reasons.append("weights_frozen")
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

    if frozen:
        keep = True
        applied = previous if not isinstance(previous, Mapping) else dict(previous or {})
        action = KEEP_PREVIOUS_WEIGHT
    else:
        action = KEEP_PREVIOUS_WEIGHT if keep else UPDATE_WEIGHT
    persisted = False
    persist_result = None
    production_apply = False
    if action == UPDATE_WEIGHT and persist is not None:
        try:
            assert_weight_mutation_allowed(source=source)
        except WeightMutationBlocked as exc:
            keep = True
            action = KEEP_PREVIOUS_WEIGHT
            applied = previous if not isinstance(previous, Mapping) else dict(previous or {})
            reasons.append("weight_mutation_blocked")
            reasons.append(str(exc))
        else:
            persist_result = persist()
            persisted = True
            production_apply = True
    if frozen and persist is not None:
        reasons.append("proposal_only_frozen")
    record = {
        "status": PROPOSAL_ONLY if frozen or not persisted else "PRODUCTION_WEIGHT",
        "source": source,
        "key": key,
        "action": action,
        "decision": KEEP_PREVIOUS_WEIGHT if keep else UPDATE_WEIGHT,
        "current_weight": previous if not isinstance(previous, Mapping) else dict(previous or {}),
        "proposed_weight": proposed if not isinstance(proposed, Mapping) else dict(proposed or {}),
        "previous": previous if not isinstance(previous, Mapping) else dict(previous),
        "proposed": proposed if not isinstance(proposed, Mapping) else dict(proposed),
        "applied": applied,
        "persisted": persisted,
        "production_apply": production_apply,
        "strategy_status": PRODUCTION_BOUNDARY["strategy_status"],
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
