"""Deterministic observable behavior archetypes for Capital Behavior V3."""
from __future__ import annotations

from typing import Any, Mapping


ARCHETYPES = (
    "EARLY_ACCUMULATION", "HEALTHY_BUILD", "ACTIVE_MARKUP",
    "PULLBACK_ABSORPTION", "LATE_MARKUP", "DISTRIBUTION_RISK",
    "BREAKDOWN_PRESSURE", "SHORT_COVER", "TRAP",
)


def _value(sample: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(sample.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def score_archetypes(sample: Mapping[str, Any]) -> dict[str, float]:
    state = str(sample.get("capital_state") or "UNKNOWN")
    absorption = _value(sample, "absorption")
    persistence = _value(sample, "demand_persistence")
    exhaustion = _value(sample, "supply_exhaustion")
    markup = _value(sample, "markup")
    distribution = _value(sample, "distribution")
    crowding = _value(sample, "crowding")
    trap = _value(sample, "trap")
    down = _value(sample, "downward_pressure")
    control = _value(sample, "control_asymmetry", _value(sample, "price_response_efficiency"))
    scores = {
        "EARLY_ACCUMULATION": 0.35 * absorption + 0.35 * exhaustion + 0.20 * (1.0 - crowding) + 0.10 * (1.0 - markup),
        "HEALTHY_BUILD": 0.35 * persistence + 0.25 * markup + 0.20 * max(0.0, control) + 0.20 * (1.0 - distribution),
        "ACTIVE_MARKUP": 0.40 * markup + 0.25 * persistence + 0.20 * max(0.0, control) + 0.15 * (1.0 - distribution),
        "PULLBACK_ABSORPTION": 0.40 * absorption + 0.25 * _value(sample, "absorption_persistence") + 0.20 * _value(sample, "damage_efficiency") + 0.15 * _value(sample, "support_retention"),
        "LATE_MARKUP": 0.40 * markup + 0.30 * crowding + 0.20 * distribution + 0.10 * persistence,
        "DISTRIBUTION_RISK": 0.45 * distribution + 0.25 * crowding + 0.20 * _value(sample, "absorption_failure") + 0.10 * max(0.0, -control),
        "BREAKDOWN_PRESSURE": 0.45 * down + 0.25 * _value(sample, "price_damage") + 0.20 * (1.0 - _value(sample, "demand_persistence")) + 0.10 * max(0.0, -control),
        "SHORT_COVER": 0.45 * _value(sample, "recovery_after_pressure") + 0.25 * down + 0.20 * max(0.0, control) + 0.10 * (1.0 - distribution),
        "TRAP": 0.55 * trap + 0.25 * distribution + 0.20 * (1.0 - persistence),
    }
    if state == "PULLBACK_ABSORPTION":
        scores["PULLBACK_ABSORPTION"] += 0.10
    if state in {"DISTRIBUTION", "LATE_MARKUP"}:
        scores["DISTRIBUTION_RISK"] += 0.10
    return {key: round(max(0.0, min(1.0, value)), 6) for key, value in sorted(scores.items())}


def classify_archetype(sample: Mapping[str, Any]) -> dict[str, Any]:
    scores = score_archetypes(sample)
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    primary, primary_score = ranked[0]
    return {
        "status": "RESEARCH_ONLY",
        "primary": primary,
        "score": primary_score,
        "scores": dict(ranked),
        "semantic": "OBSERVABLE_BEHAVIOR_PATTERN",
    }
