"""Capital advantage decay and reversal diagnostics from adjacent snapshots."""
from __future__ import annotations

from typing import Any, Mapping

from .features import clamp


def _value(row: Mapping[str, Any], key: str) -> float:
    try:
        return float(row.get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _direction(row: Mapping[str, Any]) -> str:
    asymmetry = _value(row, "control_asymmetry")
    pressure = _value(row, "upward_pressure") - _value(row, "downward_pressure")
    score = asymmetry if asymmetry else pressure
    return "LONG" if score > 0.08 else "SHORT" if score < -0.08 else "NEUTRAL"


def capital_advantage_decay(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    components = {
        "pressure_decay": clamp((_value(previous, "upward_pressure") - _value(current, "upward_pressure")) + (_value(current, "downward_pressure") - _value(previous, "downward_pressure"))),
        "control_decay": clamp(_value(previous, "price_response_efficiency") - _value(current, "price_response_efficiency")),
        "persistence_decay": clamp(_value(previous, "demand_persistence") - _value(current, "demand_persistence")),
        "absorption_failure": clamp(_value(current, "absorption_failure")),
        "distribution_rise": clamp(_value(current, "distribution") - _value(previous, "distribution")),
        "crowding_rise": clamp(_value(current, "crowding") - _value(previous, "crowding")),
    }
    score = clamp(sum(components.values()) / len(components))
    return {"status": "RESEARCH_ONLY", "capital_advantage_decay_score": round(score, 6), "components": {key: round(value, 6) for key, value in components.items()}}


def detect_reversal(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    from_direction = _direction(previous)
    to_direction = _direction(current)
    decay = capital_advantage_decay(previous, current)
    transition_evidence = {
        "pressure_change": round((_value(current, "upward_pressure") - _value(current, "downward_pressure")) - (_value(previous, "upward_pressure") - _value(previous, "downward_pressure")), 6),
        "control_asymmetry_change": round(_value(current, "control_asymmetry") - _value(previous, "control_asymmetry"), 6),
        "state_transition": f"{previous.get('capital_state', 'UNKNOWN')}->{current.get('capital_state', 'UNKNOWN')}",
    }
    probability = clamp(
        0.45 * (1.0 if from_direction != to_direction and to_direction != "NEUTRAL" else 0.0)
        + 0.30 * decay["capital_advantage_decay_score"]
        + 0.15 * abs(transition_evidence["pressure_change"])
        + 0.10 * abs(transition_evidence["control_asymmetry_change"])
    )
    return {
        "status": "RESEARCH_ONLY",
        "from_direction": from_direction,
        "to_direction": to_direction,
        "reversal_probability": round(probability, 6),
        "transition_evidence": transition_evidence,
        "capital_advantage_decay": decay,
    }
