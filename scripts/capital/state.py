"""Continuous inferred capital-state machine."""
from __future__ import annotations

from enum import Enum
from typing import Any


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
    CapitalState.ACTIVE_MARKUP: {CapitalState.PULLBACK_ABSORPTION, CapitalState.SECONDARY_MARKUP, CapitalState.LATE_MARKUP},
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
    if trap >= 0.68:
        return CapitalState.TRAP, "public-volume-price rejection pattern", trap
    if distribution >= 0.66 and crowding >= 0.45:
        return CapitalState.DISTRIBUTION, "high activity with weak price progress", distribution
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


def transition_state(
    evidence: dict[str, Any],
    previous_state: str | CapitalState | None = None,
    previous_duration: int = 0,
) -> dict[str, Any]:
    """Apply a persistence gate before accepting non-adjacent transitions."""
    values = {key: float(item.get("value", 0.0)) for key, item in evidence["evidence"].items()}
    proposed, reason, strength = _candidate(values, evidence.get("features", {}))
    try:
        prior = CapitalState(previous_state or CapitalState.UNKNOWN)
    except ValueError:
        prior = CapitalState.UNKNOWN
    allowed = proposed == prior or proposed in _NEXT.get(prior, set())
    exceptional = strength >= 0.82 or proposed in {CapitalState.TRAP, CapitalState.SHORT_PRESSURE}
    state = proposed if allowed or exceptional or prior == CapitalState.UNKNOWN else prior
    transition = f"{prior.value}->{state.value}" if state != prior else "HOLD"
    duration = int(previous_duration) + 1 if state == prior else 1
    confidence = min(1.0, strength * float(evidence["evidence"]["upward_pressure"].get("confidence", 0.0)))
    if state != proposed:
        reason = f"continuity hold: proposed {proposed}; {reason}"
        confidence *= 0.75
    return {
        "capital_state": state.value,
        "previous_capital_state": prior.value,
        "state_transition": transition,
        "state_duration": duration,
        "state_confidence": round(confidence, 6),
        "state_reason": reason,
    }
