"""Competing, horizon-specific price-path inference."""
from __future__ import annotations

from typing import Any

from .features import clamp


PATHS = (
    "UP_CONTINUATION",
    "PULLBACK_CONTINUE",
    "ACCELERATION",
    "SIDEWAYS",
    "DISTRIBUTION",
    "BREAKDOWN",
    "TRAP",
)

PATH_BY_STATE = {
    "ACCUMULATION": "SIDEWAYS",
    "EARLY_BUILD": "UP_CONTINUATION",
    "ACTIVE_MARKUP": "UP_CONTINUATION",
    "PULLBACK_ABSORPTION": "PULLBACK_CONTINUE",
    "SECONDARY_MARKUP": "ACCELERATION",
    "LATE_MARKUP": "DISTRIBUTION",
    "DISTRIBUTION": "DISTRIBUTION",
    "MARKDOWN": "BREAKDOWN",
    "SHORT_BUILD": "BREAKDOWN",
    "SHORT_PRESSURE": "BREAKDOWN",
    "SHORT_COVER": "UP_CONTINUATION",
    "TRAP": "TRAP",
}


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    scores = {key: max(0.001, float(value)) for key, value in scores.items()}
    total = sum(scores.values())
    result = {key: round(value / total, 6) for key, value in scores.items()}
    largest = max(result, key=result.get)
    result[largest] = round(result[largest] + 1.0 - sum(result.values()), 6)
    return result


def _distribution(values: dict[str, float], features: dict[str, Any], horizon: int) -> dict[str, float]:
    up = values.get("upward_pressure", 0.0)
    down = values.get("downward_pressure", 0.0)
    persistence = values.get("demand_persistence", 0.0)
    distribution = values.get("distribution", 0.0)
    trap = values.get("trap", 0.0)
    absorption = values.get("absorption", 0.0)
    control = clamp(features.get("price_control_efficiency", 0.5))
    horizon_bias = {1: 0.05, 3: 0.0, 5: -0.04}[horizon]
    return {
        "UP_CONTINUATION": 0.25 + 0.30 * up + 0.20 * persistence + horizon_bias,
        "PULLBACK_CONTINUE": 0.18 + 0.28 * absorption + 0.18 * values.get("damage_efficiency", 0.0) + 0.08 * persistence,
        "ACCELERATION": 0.12 + 0.30 * up + 0.22 * control + 0.10 * values.get("price_impact", 0.0) + horizon_bias,
        "SIDEWAYS": 0.15 + 0.25 * (1.0 - abs(up - down)) + 0.18 * (1.0 - control),
        "DISTRIBUTION": 0.08 + 0.45 * distribution + 0.20 * values.get("crowding", 0.0) + (0.05 if horizon >= 3 else 0.0),
        "BREAKDOWN": 0.06 + 0.42 * down + 0.25 * values.get("price_damage", 0.0) + (0.06 if horizon >= 3 else 0.0),
        "TRAP": 0.04 + 0.45 * trap + 0.15 * (1.0 - persistence),
    }


def infer_price_path(
    state: dict[str, Any],
    intent: dict[str, Any],
    evidence: dict[str, Any],
    control: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return competing path distributions for T+1, T+3, and T+5."""
    del intent
    values = {key: float(item.get("value", 0.0)) for key, item in evidence["evidence"].items()}
    features = dict(evidence.get("features", {}))
    if control:
        features.update(control)
    distributions = {
        f"t{horizon}": _normalize(_distribution(values, features, horizon))
        for horizon in (1, 3, 5)
    }
    t1 = distributions["t1"]
    predicted = max(t1, key=t1.get)
    state_name = str(state.get("capital_state", "UNKNOWN"))
    sequence = {
        "PULLBACK_CONTINUE": ["PULLBACK", "HOLD", "CONTINUE"],
        "UP_CONTINUATION": ["CONTINUE"],
        "ACCELERATION": ["BREAKOUT", "ACCELERATE"],
        "DISTRIBUTION": ["SPIKE", "DISTRIBUTE"],
        "BREAKDOWN": ["FAIL_SUPPORT", "MARKDOWN"],
        "TRAP": ["BREAKOUT_OR_SPIKE", "REVERSE"],
    }.get(predicted, ["RANGE", "HOLD"])
    invalidation = {
        "PULLBACK_CONTINUE": ["absorption collapse", "support failure", "downside pressure acceleration"],
        "UP_CONTINUATION": ["control collapse", "distribution acceleration"],
        "ACCELERATION": ["failed breakout", "crowding with weak response"],
        "SIDEWAYS": ["persistent directional pressure"],
        "DISTRIBUTION": ["renewed demand with improving control"],
        "BREAKDOWN": ["support recovery", "failed downside continuation"],
        "TRAP": ["confirmation of price acceptance"],
    }[predicted]
    return {
        "path_type": predicted,
        "predicted_path": predicted,
        "path_distribution_t1": distributions["t1"],
        "path_distribution_t3": distributions["t3"],
        "path_distribution_t5": distributions["t5"],
        "paths": distributions,
        "t1_probability": t1[predicted],
        "t3_probability": distributions["t3"].get(predicted, 0.0),
        "t5_probability": distributions["t5"].get(predicted, 0.0),
        "path_confidence": round(clamp(max(t1.values()) * float(state.get("state_confidence", 0.0))), 6),
        "path_sequence": sequence,
        "path_invalidation": invalidation,
        "path_semantic": "PREDICTED",
        "state_context": state_name,
    }
