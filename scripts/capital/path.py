"""Predicted path inference from the inferred state."""
from __future__ import annotations

from typing import Any

from .features import clamp


PATH_BY_STATE = {
    "ACCUMULATION": "SIDEWAYS_ACCUMULATION",
    "EARLY_BUILD": "CONTINUE_UP",
    "ACTIVE_MARKUP": "CONTINUE_UP",
    "PULLBACK_ABSORPTION": "PULLBACK_THEN_CONTINUE",
    "SECONDARY_MARKUP": "ACCELERATE_UP",
    "LATE_MARKUP": "LATE_MARKUP",
    "DISTRIBUTION": "DISTRIBUTION",
    "MARKDOWN": "BREAKDOWN",
    "SHORT_BUILD": "BREAKDOWN",
    "SHORT_PRESSURE": "BREAKDOWN",
    "SHORT_COVER": "SHORT_COVER_RALLY",
    "TRAP": "TRAP",
}


def infer_price_path(state: dict[str, Any], intent: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    name = str(state.get("capital_state", "UNKNOWN"))
    path_type = PATH_BY_STATE.get(name, "UNKNOWN")
    values = {key: float(item.get("value", 0.0)) for key, item in evidence["evidence"].items()}
    strength = max(values.get("demand_persistence", 0.0), values.get("downward_pressure", 0.0))
    risk = max(values.get("distribution", 0.0), values.get("trap", 0.0))
    if path_type in {"CONTINUE_UP", "ACCELERATE_UP", "PULLBACK_THEN_CONTINUE", "SIDEWAYS_ACCUMULATION"}:
        base = clamp(0.48 + 0.40 * strength - 0.24 * risk)
    elif path_type in {"DISTRIBUTION", "BREAKDOWN", "TRAP"}:
        base = clamp(0.48 + 0.36 * risk + 0.24 * values.get("downward_pressure", 0.0))
    else:
        base = 0.5
    confidence = clamp(float(state.get("state_confidence", 0.0)) * (1.0 - 0.25 * abs(base - 0.5)))
    return {
        "path_type": path_type,
        "t1_probability": round(clamp(base), 6),
        "t3_probability": round(clamp(base + (strength - risk) * 0.08), 6),
        "t5_probability": round(clamp(base + (strength - risk) * 0.03), 6),
        "path_confidence": round(confidence, 6),
        "path_semantic": "PREDICTED",
        "predicted_path": path_type,
    }
