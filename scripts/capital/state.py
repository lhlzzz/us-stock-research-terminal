"""Continuous inferred capital-state machine for Capital Behavior V2."""
from __future__ import annotations

from enum import Enum
from typing import Any

from .features import clamp


class CapitalState(str, Enum):
    UNKNOWN = "UNKNOWN"
    NEUTRAL = "NEUTRAL"
    ACCUMULATION = "ACCUMULATION"
    EARLY_BUILD = "EARLY_BUILD"
    ACTIVE_MARKUP = "ACTIVE_MARKUP"
    PULLBACK_ABSORPTION = "PULLBACK_ABSORPTION"
    SECONDARY_MARKUP = "SECONDARY_MARKUP"
    LATE_MARKUP = "LATE_MARKUP"
    DISTRIBUTION = "DISTRIBUTION"
    MARKDOWN = "MARKDOWN"
    SHORT_BUILD = "SHORT_BUILD"
    SHORT_PRESSURE = "SHORT_PRESSURE"
    SHORT_COVER = "SHORT_COVER"
    EXIT = "EXIT"
    TRAP = "TRAP"


_NEXT = {
    CapitalState.UNKNOWN: {CapitalState.NEUTRAL, CapitalState.ACCUMULATION, CapitalState.SHORT_BUILD},
    CapitalState.NEUTRAL: {CapitalState.ACCUMULATION, CapitalState.EARLY_BUILD, CapitalState.SHORT_BUILD, CapitalState.SHORT_PRESSURE},
    CapitalState.ACCUMULATION: {CapitalState.EARLY_BUILD, CapitalState.ACTIVE_MARKUP, CapitalState.NEUTRAL},
    CapitalState.EARLY_BUILD: {CapitalState.ACTIVE_MARKUP, CapitalState.PULLBACK_ABSORPTION, CapitalState.NEUTRAL},
    CapitalState.ACTIVE_MARKUP: {CapitalState.PULLBACK_ABSORPTION, CapitalState.SECONDARY_MARKUP, CapitalState.LATE_MARKUP, CapitalState.DISTRIBUTION},
    CapitalState.PULLBACK_ABSORPTION: {CapitalState.SECONDARY_MARKUP, CapitalState.ACTIVE_MARKUP, CapitalState.DISTRIBUTION},
    CapitalState.SECONDARY_MARKUP: {CapitalState.LATE_MARKUP, CapitalState.DISTRIBUTION, CapitalState.PULLBACK_ABSORPTION},
    CapitalState.LATE_MARKUP: {CapitalState.DISTRIBUTION, CapitalState.EXIT, CapitalState.TRAP},
    CapitalState.DISTRIBUTION: {CapitalState.MARKDOWN, CapitalState.EXIT, CapitalState.TRAP},
    CapitalState.MARKDOWN: {CapitalState.SHORT_PRESSURE, CapitalState.SHORT_COVER, CapitalState.NEUTRAL},
    CapitalState.SHORT_BUILD: {CapitalState.SHORT_PRESSURE, CapitalState.SHORT_COVER, CapitalState.NEUTRAL},
    CapitalState.SHORT_PRESSURE: {CapitalState.SHORT_COVER, CapitalState.MARKDOWN, CapitalState.EXIT},
    CapitalState.SHORT_COVER: {CapitalState.NEUTRAL, CapitalState.ACCUMULATION, CapitalState.EARLY_BUILD},
    CapitalState.EXIT: {CapitalState.NEUTRAL, CapitalState.MARKDOWN},
    CapitalState.TRAP: {CapitalState.DISTRIBUTION, CapitalState.MARKDOWN, CapitalState.NEUTRAL},
}


def _candidate(values: dict[str, float], features: dict[str, Any]) -> tuple[CapitalState, str, float]:
    upward, downward = values["upward_pressure"], values["downward_pressure"]
    accumulation, absorption = values["accumulation"], values["absorption"]
    markup, distribution, trap = values["markup"], values["distribution"], values["trap"]
    crowding = values["crowding"]
    ret5 = float(features.get("return_5d", 0.0))
    ret20 = float(features.get("return_20d", 0.0))
    failure = values.get("absorption_failure", 0.0)
    if trap >= 0.68:
        return CapitalState.TRAP, "public-volume-price rejection pattern", trap
    if distribution >= 0.66 and crowding >= 0.45:
        return CapitalState.DISTRIBUTION, "high activity with weak price progress", distribution
    if failure >= 0.68 and distribution >= 0.45:
        return CapitalState.DISTRIBUTION, "absorption failed as price damage expanded", failure
    if downward >= 0.68 and ret20 < -0.04:
        return CapitalState.SHORT_PRESSURE, "persistent downside price pressure", downward
    if downward >= 0.56 and ret5 < -0.02:
        return CapitalState.SHORT_BUILD, "downside pressure building", downward
    if absorption >= 0.62 and ret5 <= 0.02 and upward >= downward:
        return CapitalState.PULLBACK_ABSORPTION, "activity absorbed with recovery support", absorption
    if accumulation >= 0.65 and ret20 <= 0.08:
        return CapitalState.ACCUMULATION, "stabilization, absorption, and supply exhaustion", accumulation
    if markup >= 0.70 and ret20 >= 0.15 and (distribution >= 0.52 or crowding >= 0.70):
        return CapitalState.LATE_MARKUP, "extended markup with crowding or distribution risk", markup
    if markup >= 0.66 and ret20 >= 0.10:
        return CapitalState.ACTIVE_MARKUP, "persistent upside pressure and price acceptance", markup
    if markup >= 0.58 and ret5 > 0:
        return CapitalState.EARLY_BUILD, "early upside pressure with demand persistence", markup
    if downward >= 0.55 and ret5 < 0:
        return CapitalState.MARKDOWN, "downside pressure exceeds demand", downward
    if upward >= 0.55 and ret5 > 0:
        return CapitalState.SECONDARY_MARKUP, "renewed upside pressure", upward
    return CapitalState.NEUTRAL, "no dominant observable pressure", max(upward, downward)


def _state_scores(values: dict[str, float], features: dict[str, Any]) -> dict[CapitalState, float]:
    up, down = values["upward_pressure"], values["downward_pressure"]
    return {
        CapitalState.NEUTRAL: clamp(1.0 - abs(up - down)),
        CapitalState.ACCUMULATION: clamp(0.45 * values["accumulation"] + 0.30 * values["absorption"] + 0.25 * values["supply_exhaustion"]),
        CapitalState.EARLY_BUILD: clamp(0.55 * values["markup"] + 0.25 * values["demand_persistence"] + 0.20 * clamp((float(features.get("return_5d", 0.0)) + 0.02) / 0.06)),
        CapitalState.ACTIVE_MARKUP: clamp(0.45 * values["markup"] + 0.35 * values["demand_persistence"] + 0.20 * values["upward_pressure"]),
        CapitalState.PULLBACK_ABSORPTION: clamp(0.45 * values["absorption"] + 0.25 * values["damage_efficiency"] + 0.20 * values["support_retention"] + 0.10 * up),
        CapitalState.SECONDARY_MARKUP: clamp(0.55 * values["upward_pressure"] + 0.25 * values["price_impact"] + 0.20 * values["demand_persistence"]),
        CapitalState.LATE_MARKUP: clamp(0.45 * values["markup"] + 0.35 * values["crowding"] + 0.20 * values["distribution"]),
        CapitalState.DISTRIBUTION: clamp(0.45 * values["distribution"] + 0.25 * values["crowding"] + 0.20 * values.get("absorption_failure", 0.0) + 0.10 * down),
        CapitalState.MARKDOWN: clamp(0.55 * down + 0.25 * values["price_impact"] + 0.20 * (1.0 - values["demand_persistence"])),
        CapitalState.SHORT_BUILD: clamp(0.55 * down + 0.25 * values["price_damage"] + 0.20 * (1.0 - values["support_retention"])),
        CapitalState.SHORT_PRESSURE: clamp(0.60 * down + 0.25 * values["price_damage"] + 0.15 * (1.0 - values["support_retention"])),
        CapitalState.SHORT_COVER: clamp(0.45 * values["recovery_after_pressure"] + 0.30 * (1.0 - down) + 0.25 * values["upward_pressure"]),
        CapitalState.EXIT: clamp(0.60 * values["distribution"] + 0.20 * values["crowding"] + 0.20 * values.get("absorption_failure", 0.0)),
        CapitalState.TRAP: values["trap"],
    }


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, score) for score in scores.values())
    if total <= 0:
        return {key: 0.0 for key in scores}
    return {key: round(max(0.0, value) / total, 6) for key, value in scores.items()}


def transition_state(
    evidence: dict[str, Any],
    previous_state: str | CapitalState | None = None,
    previous_duration: int = 0,
    previous_intent: str | None = None,
    control: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply evidence persistence and continuity to a dynamic state matrix."""
    values = {key: float(item.get("value", 0.0)) for key, item in evidence["evidence"].items()}
    features = evidence.get("features", {})
    control = control or {}
    proposed, reason, strength = _candidate(values, features)
    try:
        prior = CapitalState(previous_state or CapitalState.UNKNOWN)
    except ValueError:
        prior = CapitalState.UNKNOWN
    raw_scores = _state_scores(values, features)
    probabilities = _normalize({state.value: score for state, score in raw_scores.items()})
    allowed = proposed == prior or proposed in _NEXT.get(prior, set())
    exceptional = strength >= 0.82 or proposed in {CapitalState.TRAP, CapitalState.SHORT_PRESSURE}
    state = proposed if allowed or exceptional or prior == CapitalState.UNKNOWN else prior
    transition = f"{prior.value}->{state.value}" if state != prior else "HOLD"
    duration = int(previous_duration) + 1 if state == prior else 1
    state_confidence = clamp(probabilities.get(state.value, 0.0) + 0.20 * strength)
    state_momentum = clamp(values.get("demand_persistence", 0.0) - values.get("distribution", 0.0) + 0.5)
    transition_acceleration = clamp(
        abs(float(features.get("pressure_change", 0.0)))
        + float(control.get("control_collapse_score", 0.0))
        + abs(float(values.get("absorption_failure", 0.0)))
    )
    expected_duration = {
        CapitalState.ACTIVE_MARKUP: 9,
        CapitalState.LATE_MARKUP: 5,
        CapitalState.DISTRIBUTION: 7,
    }.get(state, 8)
    duration_percentile = clamp(duration / max(expected_duration * 2.0, 1.0))
    late_state_risk = clamp(
        (duration / max(expected_duration, 1))
        * (0.55 if state in {CapitalState.ACTIVE_MARKUP, CapitalState.LATE_MARKUP, CapitalState.DISTRIBUTION} else 0.20)
        + 0.45 * values.get("distribution", 0.0)
    )
    targets = {state_name: probability for state_name, probability in probabilities.items() if state_name in {item.value for item in _NEXT.get(state, set())}}
    if state.value in probabilities:
        targets[state.value] = probabilities[state.value]
    target_total = sum(targets.values())
    transition_probabilities = _normalize(targets) if target_total else {state.value: 1.0}
    if state != proposed:
        reason = f"continuity hold: proposed {proposed.value}; {reason}"
        state_confidence *= 0.75
    return {
        "capital_state": state.value,
        "previous_capital_state": prior.value,
        "state_transition": transition,
        "state_duration": duration,
        "state_confidence": round(clamp(state_confidence), 6),
        "state_reason": reason,
        "state_momentum": round(state_momentum, 6),
        "transition_score": round(clamp(strength), 6),
        "transition_acceleration": round(transition_acceleration, 6),
        "evidence_persistence": round(
            clamp(
                0.5 * float(features.get("pressure_persistence", 0.0))
                + 0.5 * float(values.get("absorption_persistence", 0.0))
            ),
            6,
        ),
        "transition_probabilities": transition_probabilities,
        "transition_matrix": {
            "from_state": state.value,
            "probabilities": transition_probabilities,
            "supporting_evidence": [reason],
            "transition_confidence": round(clamp(state_confidence), 6),
        },
        "expected_duration": expected_duration,
        "duration_percentile": round(duration_percentile, 6),
        "late_state_risk": round(late_state_risk, 6),
        "state_age_score": round(duration_percentile, 6),
        "previous_intent": previous_intent,
    }
