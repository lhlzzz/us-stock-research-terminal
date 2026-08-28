"""Evidence-scored inferred capital intents for Capital Behavior V2."""
from __future__ import annotations

from typing import Any

from .features import clamp


INTENT_CANDIDATES = (
    "WAIT", "ACCUMULATE", "BUILD", "PUSH_HIGHER", "DEFEND_PRICE",
    "ABSORB_SUPPLY", "REACCELERATE", "DISTRIBUTE", "REDUCE_RISK",
    "PRESS_LOWER", "COVER_SHORT", "TEST_SUPPLY", "TEST_DEMAND",
    "PROBE_BREAKOUT", "PROTECT_SUPPORT", "FORCE_COVER",
    "EXIT_GRADUALLY", "EXIT_AGGRESSIVELY",
)

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
    "UNKNOWN": "WAIT",
}


def _softmax(scores: dict[str, float]) -> dict[str, float]:
    positive = {key: max(0.001, float(value)) for key, value in scores.items()}
    total = sum(positive.values())
    values = {key: round(value / total, 6) for key, value in positive.items()}
    if values:
        largest = max(values, key=values.get)
        values[largest] = round(values[largest] + 1.0 - sum(values.values()), 6)
    return values


def infer_capital_intent(
    state: dict[str, Any],
    evidence: dict[str, Any],
    control: dict[str, Any] | None = None,
    previous_intent: str | None = None,
) -> dict[str, Any]:
    """Score competing inferred behaviors; never asserts actual intent."""
    name = str(state.get("capital_state", "UNKNOWN"))
    values = {key: float(item.get("value", 0.0)) for key, item in evidence["evidence"].items()}
    control = control or {}
    asymmetry = float(control.get("control_asymmetry", 0.0))
    quality = clamp(control.get("capital_quality", 0.5))
    base = {
        "WAIT": 0.20 + 0.35 * values.get("trap", 0.0) + 0.20 * (1.0 - values.get("demand_persistence", 0.0)),
        "ACCUMULATE": 0.45 * values.get("accumulation", 0.0) + 0.25 * values.get("absorption", 0.0) + 0.15 * quality,
        "BUILD": 0.45 * values.get("markup", 0.0) + 0.30 * values.get("demand_persistence", 0.0) + 0.15 * max(asymmetry, 0),
        "PUSH_HIGHER": 0.50 * values.get("upward_pressure", 0.0) + 0.30 * values.get("demand_persistence", 0.0) + 0.20 * max(asymmetry, 0),
        "DEFEND_PRICE": 0.45 * values.get("support_retention", 0.0) + 0.35 * values.get("price_damage", 0.0) + 0.20 * values.get("upward_pressure", 0.0),
        "ABSORB_SUPPLY": 0.45 * values.get("absorption", 0.0) + 0.25 * values.get("damage_efficiency", 0.0) + 0.20 * values.get("selling_activity", 0.0) + 0.10 * values.get("support_retention", 0.0),
        "REACCELERATE": 0.45 * values.get("upward_pressure", 0.0) + 0.25 * values.get("recovery_after_pressure", 0.0) + 0.20 * values.get("price_impact", 0.0),
        "DISTRIBUTE": 0.55 * values.get("distribution", 0.0) + 0.25 * values.get("crowding", 0.0) + 0.20 * values.get("absorption_failure", 0.0),
        "REDUCE_RISK": 0.45 * values.get("distribution", 0.0) + 0.30 * values.get("crowding", 0.0) + 0.20 * values.get("trap", 0.0),
        "PRESS_LOWER": 0.55 * values.get("downward_pressure", 0.0) + 0.25 * values.get("price_damage", 0.0) + 0.20 * (1.0 - values.get("support_retention", 0.0)),
        "COVER_SHORT": 0.50 * values.get("recovery_after_pressure", 0.0) + 0.25 * (1.0 - values.get("downward_pressure", 0.0)) + 0.20 * values.get("upward_pressure", 0.0),
        "TEST_SUPPLY": 0.40 * values.get("selling_activity", 0.0) + 0.30 * values.get("damage_efficiency", 0.0) + 0.20 * values.get("support_retention", 0.0),
        "TEST_DEMAND": 0.40 * values.get("upward_pressure", 0.0) + 0.30 * values.get("price_impact", 0.0) + 0.20 * values.get("recovery_after_pressure", 0.0),
        "PROBE_BREAKOUT": 0.45 * values.get("markup", 0.0) + 0.30 * values.get("price_impact", 0.0) + 0.15 * max(asymmetry, 0),
        "PROTECT_SUPPORT": 0.50 * values.get("support_retention", 0.0) + 0.25 * values.get("absorption", 0.0) + 0.15 * values.get("recovery_after_pressure", 0.0),
        "FORCE_COVER": 0.50 * values.get("upward_pressure", 0.0) + 0.25 * values.get("recovery_after_pressure", 0.0) + 0.15 * max(asymmetry, 0),
        "EXIT_GRADUALLY": 0.50 * values.get("distribution", 0.0) + 0.25 * (1.0 - values.get("price_damage", 0.0)) + 0.15 * values.get("crowding", 0.0),
        "EXIT_AGGRESSIVELY": 0.50 * values.get("absorption_failure", 0.0) + 0.30 * values.get("price_damage", 0.0) + 0.15 * values.get("distribution", 0.0),
    }
    for intent in INTENT_CANDIDATES:
        if intent != "WAIT":
            base[intent] = max(base[intent], 0.001)
    probabilities = _softmax(base)
    ranked = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
    top_intent, top_probability = ranked[0]
    second_probability = ranked[1][1] if len(ranked) > 1 else 0.0
    selected = top_intent if top_probability - second_probability >= 0.05 and top_probability >= 0.12 else "UNCERTAIN"
    direction = "LONG" if asymmetry > 0.08 else "SHORT" if asymmetry < -0.08 else "NEUTRAL"
    return {
        "capital_intent": selected,
        "intent_probability": round(top_probability, 6),
        "intent_confidence": round(clamp(top_probability * float(state.get("state_confidence", 0.0)) + 0.20 * (top_probability - second_probability)), 6),
        "intent_probabilities": probabilities,
        "intent_alternatives": [
            {"intent": intent, "probability": probability}
            for intent, probability in ranked[1:4]
        ],
        "intent_semantic": "INFERRED",
        "expected_direction": direction,
        "previous_intent": previous_intent,
        "current_intent": selected,
        "intent_transition": f"{previous_intent}->{selected}" if previous_intent and previous_intent != selected else "HOLD",
        "continuation_condition": "pressure persists and response efficiency remains stable",
        "invalidation_condition": "pressure reverses, control collapses, or support fails",
    }
