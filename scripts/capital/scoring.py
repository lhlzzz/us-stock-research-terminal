"""Capital Behavior V2 score, quality, risk, and decision contract."""
from __future__ import annotations

from typing import Any

from .control import build_price_control
from .evidence import build_capital_evidence
from .features import clamp
from .intent import infer_capital_intent
from .path import infer_price_path
from .state import transition_state


MODEL_VERSION = "capital_behavior_v2"
VALIDATION_STATUS = "UNVALIDATED_NO_FIXED_CHAIN"


def build_capital_assessment(
    frame,
    *,
    statistical_score: float | None = None,
    relative_strength: float | None = None,
    regime_alignment: float | None = None,
    previous_state: str | None = None,
    previous_duration: int = 0,
    previous_intent: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic V2 assessment from one as-of OHLCV frame."""
    evidence = build_capital_evidence(frame, relative_strength=relative_strength)
    values = {key: float(item.get("value", 0.0)) for key, item in evidence["evidence"].items()}
    control = build_price_control(evidence)
    state = transition_state(
        evidence,
        previous_state,
        previous_duration,
        previous_intent,
        control=control,
    )
    intent = infer_capital_intent(state, evidence, control, previous_intent)
    path = infer_price_path(state, intent, evidence, control)
    regime = clamp(regime_alignment if regime_alignment is not None else 0.5)
    state_confidence = clamp(state.get("state_confidence", 0.0))
    transition_confidence = clamp(state.get("transition_matrix", {}).get("transition_confidence", 0.0))
    direction = str(control["dominant_direction"])
    direction_pressure = values["upward_pressure"] if direction == "LONG" else values["downward_pressure"] if direction == "SHORT" else max(values["upward_pressure"], values["downward_pressure"])
    capital_strength = clamp(
        0.22 * direction_pressure
        + 0.16 * values["demand_persistence"]
        + 0.14 * values["selling_activity"]
        + 0.14 * values["absorption"]
        + 0.14 * float(control["price_response_efficiency"])
        + 0.10 * state_confidence
        + 0.10 * transition_confidence
        + 0.04 * regime
    )
    distribution_probability = clamp(
        0.45 * values["distribution"]
        + 0.20 * values["crowding"]
        + 0.20 * values["absorption_failure"]
        + 0.15 * float(control["control_collapse_score"])
    )
    trap_probability = clamp(0.55 * values["trap"] + 0.20 * values["distribution"] + 0.15 * (1.0 - state_confidence) + 0.10 * (1.0 - float(control["price_response_efficiency"])))
    capital_quality = clamp(
        0.28 * values["demand_persistence"]
        + 0.22 * values["absorption"]
        + 0.20 * float(control["price_response_efficiency"])
        + 0.15 * state_confidence
        + 0.15 * transition_confidence
        - 0.30 * distribution_probability
        - 0.20 * trap_probability
        - 0.15 * values["crowding"]
    )
    quality_label = "STRONG_BUT_DISTRIBUTING" if capital_strength >= 0.70 and capital_quality < 0.45 else "HEALTHY" if capital_quality >= 0.65 else "FRAGILE"
    statistical = clamp(statistical_score if statistical_score is not None else 0.0)
    combined = clamp(0.70 * statistical + 0.30 * capital_strength - 0.10 * distribution_probability - 0.08 * trap_probability)
    return {
        "model_version": MODEL_VERSION,
        "data_version": evidence.get("data_version", "PUBLIC_OHLCV_V2"),
        "validation_status": VALIDATION_STATUS,
        "evidence": evidence,
        "control": control,
        "state": state,
        "intent": intent,
        "path": path,
        "scores": {
            "statistical_score": round(statistical, 6),
            "capital_score": round(combined, 6),
            "combined_score": round(combined, 6),
            "capital_strength": round(capital_strength, 6),
            "capital_quality": round(capital_quality, 6),
            "quality_label": quality_label,
            "distribution_probability": round(distribution_probability, 6),
            "distribution_risk": round(distribution_probability, 6),
            "distribution_stage": "ACCELERATING" if distribution_probability >= 0.70 else "WARNING" if distribution_probability >= 0.45 else "LOW",
            "distribution_acceleration": round(clamp(values["distribution"] - values["absorption"]), 6),
            "distribution_transition_risk": round(clamp(distribution_probability + float(state.get("late_state_risk", 0.0)) * 0.25), 6),
            "trap_probability": round(trap_probability, 6),
            "trap_risk": round(trap_probability, 6),
            "dominant_direction": direction,
            "dominant_pressure": round(float(control["dominant_pressure"]), 6),
        },
        "decision": {
            "statistical_score": round(statistical, 6),
            "capital_score": round(combined, 6),
            "capital_strength": round(capital_strength, 6),
            "capital_quality": round(capital_quality, 6),
            "state": state["capital_state"],
            "intent": intent["capital_intent"],
            "path": path["path_type"],
            "path_probability": path["t1_probability"],
            "distribution_risk": round(distribution_probability, 6),
            "trap_risk": round(trap_probability, 6),
            "research_action": "AVOID" if quality_label == "STRONG_BUT_DISTRIBUTING" or trap_probability >= 0.70 else "WATCH" if capital_quality < 0.55 else "CONTINUE",
        },
    }
