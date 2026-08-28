"""Price-response efficiency derived from observable activity and price moves."""
from __future__ import annotations

import math
from typing import Any

from .features import clamp


def _response_efficiency(response: float, activity: float) -> float:
    """Return bounded response per unit of directional activity."""
    if not math.isfinite(response) or not math.isfinite(activity) or activity <= 0.02:
        return 0.0
    return clamp(response / activity)


def build_price_control(evidence: dict[str, Any]) -> dict[str, float | str | dict[str, Any]]:
    """Measure how effectively activity produced directional price response."""
    values = {key: float(item.get("value", 0.0)) for key, item in evidence["evidence"].items()}
    features = evidence.get("features", {})
    up_activity = clamp(features.get("upside_activity", values.get("upward_pressure", 0.0)))
    down_activity = clamp(features.get("downside_activity", values.get("downward_pressure", 0.0)))
    up_response = clamp(features.get("upside_response", values.get("upward_pressure", 0.0)))
    down_response = clamp(features.get("downside_response", values.get("downward_pressure", 0.0)))
    volatility = clamp(features.get("volatility_20d", 0.0))
    liquidity = clamp(features.get("liquidity_proxy", 0.0))
    normalization = 0.65 + 0.20 * volatility + 0.15 * (1.0 - liquidity)
    upside = _response_efficiency(up_response / normalization, up_activity)
    downside = _response_efficiency(down_response / normalization, down_activity)
    asymmetry = upside - downside
    direction = "LONG" if asymmetry > 0.08 else "SHORT" if asymmetry < -0.08 else "NEUTRAL"
    prior = clamp(features.get("prior_control_efficiency", 0.5))
    current = max(upside, downside)
    collapse = clamp((prior - current) / max(prior, 0.05))
    regime = "HIGH" if current >= 0.70 else "MEDIUM" if current >= 0.40 else "LOW"
    if abs(asymmetry) >= 0.18 and abs(float(features.get("pressure_change", 0.0))) >= 0.15:
        regime = "SHIFTING"
    return {
        "price_control_score": round(current, 6),
        "price_response_efficiency": round(current, 6),
        "upside_control_efficiency": round(upside, 6),
        "downside_control_efficiency": round(downside, 6),
        "control_asymmetry": round(asymmetry, 6),
        "control_regime": regime,
        "control_collapse_score": round(collapse, 6),
        "dominant_direction": direction,
        "dominant_pressure": round(max(values.get("upward_pressure", 0.0), values.get("downward_pressure", 0.0)), 6),
    }
