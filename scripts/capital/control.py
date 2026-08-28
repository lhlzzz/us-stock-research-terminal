"""Price-response efficiency derived from observable activity and price moves."""
from __future__ import annotations

from typing import Any

from .features import clamp


def build_price_control(evidence: dict[str, Any]) -> dict[str, float | str]:
    values = {key: float(item.get("value", 0.0)) for key, item in evidence["evidence"].items()}
    features = evidence.get("features", {})
    impact = values["price_impact"]
    upward = values["upward_pressure"]
    downward = values["downward_pressure"]
    volume = values["volume_pressure"]
    upside = clamp(0.55 * upward + 0.30 * impact + 0.15 * float(features.get("close_position_5d", 0.5)))
    downside = clamp(0.55 * downward + 0.30 * impact + 0.15 * (1.0 - float(features.get("close_position_5d", 0.5))))
    control = clamp(max(upside, downside) * (1.0 - 0.20 * volume + 0.20))
    direction = "LONG" if upside - downside > 0.08 else "SHORT" if downside - upside > 0.08 else "NEUTRAL"
    return {
        "price_control_score": round(control, 6),
        "upside_control_efficiency": round(upside, 6),
        "downside_control_efficiency": round(downside, 6),
        "dominant_direction": direction,
        "dominant_pressure": round(max(upside, downside), 6),
    }
