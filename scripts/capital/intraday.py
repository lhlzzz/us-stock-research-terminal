"""Fresh public-quote Capital Brain evidence for the paper strategy."""
from __future__ import annotations

from typing import Any

from .features import build_intraday_feature_set, clamp


def build_intraday_capital_assessment(
    daily_context: dict[str, Any],
    quote: dict[str, Any],
) -> dict[str, Any]:
    """Keep daily and intraday state separate and explicitly labeled."""
    features = build_intraday_feature_set(daily_context, quote)
    if not features["available"]:
        return {
            "availability": features["availability"],
            "features": features,
            "intraday_capital_state": "UNKNOWN",
            "intraday_intent": "UNKNOWN",
            "intraday_strength": 0.0,
            "intraday_distribution_risk": 0.0,
            "intraday_trap_risk": 0.0,
            "semantic": {"quote": "OBSERVED", "assessment": "INFERRED"},
        }

    momentum = float(features["session_momentum"])
    downside = float(features["session_downside"])
    range_position = float(features["range_position"])
    daily_state = str(daily_context.get("capital_state") or "UNKNOWN")
    daily_distribution = clamp(
        daily_context.get("distribution_probability", daily_context.get("distribution_risk", daily_context.get("distribution_score", 0.0)))
    )
    daily_trap = clamp(
        daily_context.get("trap_probability", daily_context.get("trap_risk", daily_context.get("trap_score", 0.0)))
    )
    daily_strength = clamp(daily_context.get("capital_strength", 0.0))
    daily_quality = clamp(daily_context.get("capital_quality", 0.0))
    strength = clamp(
        0.35 * momentum
        + 0.20 * range_position
        + 0.20 * daily_strength
        + 0.05 * daily_quality
        + 0.20 * float(features["daily_demand_persistence"])
    )
    distribution = clamp(
        0.55 * daily_distribution
        + 0.25 * (1.0 - range_position)
        + 0.20 * downside
    )
    trap = clamp(0.60 * daily_trap + 0.25 * downside + 0.15 * (1.0 - range_position))
    if distribution >= 0.70 or trap >= 0.70:
        state, intent = "TRAP", "WAIT"
    elif daily_state in {"ACTIVE_MARKUP", "SECONDARY_MARKUP"} and downside >= 0.55:
        state, intent = "PULLBACK_ABSORPTION", "ABSORB_SUPPLY"
    elif strength >= 0.62 and momentum >= downside:
        state, intent = "ACTIVE_MARKUP", "PUSH_HIGHER"
    elif downside >= 0.62:
        state, intent = "SHORT_PRESSURE", "PRESS_LOWER"
    else:
        state, intent = "NEUTRAL", "WAIT"
    return {
        "availability": "AVAILABLE",
        "features": features,
        "intraday_capital_state": state,
        "intraday_intent": intent,
        "intraday_strength": round(strength, 6),
        "intraday_distribution_risk": round(distribution, 6),
        "intraday_trap_risk": round(trap, 6),
        "daily_capital_state": daily_state,
        "daily_capital_intent": daily_context.get("capital_intent") or "UNKNOWN",
        "daily_path": daily_context.get("path_type") or "UNKNOWN",
        "daily_path_distribution": daily_context.get("path_distribution") or {},
        "daily_capital_quality": round(daily_quality, 6),
        "daily_distribution_probability": round(daily_distribution, 6),
        "daily_trap_probability": round(daily_trap, 6),
        "semantic": {"quote": "OBSERVED", "assessment": "INFERRED"},
    }
