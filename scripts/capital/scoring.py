"""Capital score and parallel unified decision."""
from __future__ import annotations

from typing import Any

from .control import build_price_control
from .evidence import build_capital_evidence
from .features import clamp
from .intent import infer_capital_intent
from .path import infer_price_path
from .state import transition_state


def build_capital_assessment(
    frame,
    *,
    statistical_score: float | None = None,
    relative_strength: float | None = None,
    regime_alignment: float | None = None,
    previous_state: str | None = None,
    previous_duration: int = 0,
) -> dict[str, Any]:
    """Build a fully structured parallel Capital Brain assessment."""
    evidence = build_capital_evidence(frame, relative_strength=relative_strength)
    values = {key: float(item["value"]) for key, item in evidence["evidence"].items()}
    control = build_price_control(evidence)
    state = transition_state(evidence, previous_state, previous_duration)
    intent = infer_capital_intent(state, evidence)
    path = infer_price_path(state, intent, evidence)
    demand_strength = values["upward_pressure"]
    regime = clamp(regime_alignment if regime_alignment is not None else 0.5)
    capital_score = clamp(
        0.18 * demand_strength
        + 0.14 * values["absorption"]
        + 0.14 * values["demand_persistence"]
        + 0.12 * float(control["price_control_score"])
        + 0.12 * values["supply_exhaustion"]
        + 0.10 * clamp(0.5 + float(evidence["features"].get("relative_strength", 0.0)) * 5.0)
        + 0.08 * values["volume_pressure"]
        + 0.12 * regime
        - 0.16 * values["distribution"]
        - 0.12 * values["trap"]
        - 0.06 * values["crowding"]
    )
    statistical = clamp(statistical_score if statistical_score is not None else 0.0)
    combined = clamp(0.70 * statistical + 0.30 * capital_score - 0.10 * values["distribution"] - 0.08 * values["trap"])
    return {
        "model_version": "capital_behavior_v1",
        "validation_status": "UNVALIDATED_NOT_READY",
        "evidence": evidence,
        "control": control,
        "state": state,
        "intent": intent,
        "path": path,
        "scores": {
            "statistical_score": round(statistical, 6),
            "capital_score": round(capital_score, 6),
            "combined_score": round(combined, 6),
            "capital_strength": round(float(control["dominant_pressure"]), 6),
            "distribution_risk": round(values["distribution"], 6),
            "trap_risk": round(values["trap"], 6),
        },
    }
