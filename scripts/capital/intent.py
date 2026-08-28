"""Inferred intent from an inferred state and observable evidence."""
from __future__ import annotations

from typing import Any


INTENT_BY_STATE = {
    "ACCUMULATION": "ACCUMULATE",
    "EARLY_BUILD": "BUILD",
    "ACTIVE_MARKUP": "PUSH_HIGHER",
    "PULLBACK_ABSORPTION": "ABSORB_SUPPLY",
    "SECONDARY_MARKUP": "REACCELERATE",
    "LATE_MARKUP": "REDUCE_RISK",
    "DISTRIBUTION": "DISTRIBUTE",
    "MARKDOWN": "PRESS_LOWER",
    "SHORT_BUILD": "PRESS_LOWER",
    "SHORT_PRESSURE": "PRESS_LOWER",
    "SHORT_COVER": "COVER_SHORT",
    "EXIT": "REDUCE_RISK",
    "TRAP": "WAIT",
    "NEUTRAL": "WAIT",
    "UNKNOWN": "UNKNOWN",
}


def infer_capital_intent(state: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    """Intent is explicitly inferred rather than represented as observed fact."""
    name = str(state.get("capital_state", "UNKNOWN"))
    intent = INTENT_BY_STATE.get(name, "UNKNOWN")
    values = {key: float(item.get("value", 0.0)) for key, item in evidence["evidence"].items()}
    supporting = max(
        values.get("demand_persistence", 0.0),
        values.get("supply_exhaustion", 0.0),
        values.get("distribution", 0.0),
        values.get("downward_pressure", 0.0),
    )
    confidence = min(float(state.get("state_confidence", 0.0)), supporting)
    direction = "LONG" if name in {"ACCUMULATION", "EARLY_BUILD", "ACTIVE_MARKUP", "PULLBACK_ABSORPTION", "SECONDARY_MARKUP"} else "SHORT" if name in {"MARKDOWN", "SHORT_BUILD", "SHORT_PRESSURE"} else "NEUTRAL"
    condition = (
        "demand persistence and price acceptance remain intact"
        if direction == "LONG"
        else "downside pressure remains persistent"
        if direction == "SHORT"
        else "no actionable observable pressure"
    )
    invalidation = (
        "downside volume expansion, relative-strength breakdown, or support failure"
        if direction == "LONG"
        else "upside recovery with expanding demand and failed downside continuation"
        if direction == "SHORT"
        else "fresh persistent price-volume evidence"
    )
    return {
        "capital_intent": intent,
        "intent_confidence": round(confidence, 6),
        "intent_semantic": "INFERRED",
        "expected_direction": direction,
        "continuation_condition": condition,
        "invalidation_condition": invalidation,
    }
