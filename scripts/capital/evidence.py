"""Observable and derived capital-behavior evidence."""
from __future__ import annotations

from typing import Any

from .features import build_feature_set, clamp


MODEL_VERSION = "capital_behavior_v2"
DATA_VERSION = "PUBLIC_OHLCV_V2"
SOURCE = "PUBLIC_OHLCV"


def _evidence(
    value: float,
    confidence: float,
    available: bool,
    lookback: str,
    semantic: str = "DERIVED",
) -> dict[str, Any]:
    return {
        "value": round(clamp(value), 6),
        "confidence": round(clamp(confidence), 6),
        "availability": "AVAILABLE" if available else "UNAVAILABLE",
        "source": SOURCE,
        "lookback": lookback,
        "semantic": semantic,
    }


def build_capital_evidence(
    frame,
    *,
    relative_strength: float | None = None,
) -> dict[str, Any]:
    """Return public-data evidence, never a claim about participant identity."""
    f = build_feature_set(frame, relative_strength=relative_strength)
    available = bool(f.get("available"))
    confidence = min(1.0, float(f.get("row_count", 0)) / 40.0) if available else 0.0
    if not available:
        unavailable = _evidence(0.0, 0.0, False, "20d")
        return {
            "model_version": MODEL_VERSION,
            "data_version": DATA_VERSION,
            "availability": f["availability"],
            "features": f,
            "evidence": {name: dict(unavailable) for name in (
                "upward_pressure", "downward_pressure", "volume_pressure",
                "demand_persistence", "supply_exhaustion", "absorption",
                "accumulation", "markup", "distribution", "crowding",
                "trap", "price_impact", "selling_activity", "price_damage",
                "expected_price_damage", "damage_efficiency",
                "recovery_after_pressure", "support_retention",
                "absorption_persistence", "absorption_failure",
            )},
        }

    ret1 = float(f["return_1d"])
    ret5 = float(f["return_5d"])
    ret20 = float(f["return_20d"])
    volume_ratio = float(f["volume_vs_baseline"])
    volume_z = float(f["volume_zscore"])
    close_position = float(f["close_position_5d"])
    up_ratio = float(f["up_volume_ratio"])
    down_ratio = float(f["down_volume_ratio"])
    relative_raw = f.get("relative_strength")
    relative = clamp(0.5 + float(relative_raw) * 5.0) if relative_raw is not None else 0.0

    upward = clamp(
        0.24 * clamp((ret5 + 0.05) / 0.10)
        + 0.20 * clamp((ret20 + 0.10) / 0.20)
        + 0.18 * up_ratio
        + 0.18 * close_position
        + 0.20 * relative
    )
    downward = clamp(
        0.28 * clamp((-ret5 + 0.05) / 0.10)
        + 0.20 * clamp((-ret20 + 0.10) / 0.20)
        + 0.22 * down_ratio
        + 0.16 * (1.0 - close_position)
        + 0.14 * (1.0 - relative)
    )
    volume_pressure = clamp(
        0.50 * clamp((volume_ratio - 0.5) / 1.5)
        + 0.30 * clamp((volume_z + 1.0) / 4.0)
        + 0.20 * float(f["volume_persistence"])
    )
    demand_persistence = clamp(
        0.26 * float(f["recent_positive_days"])
        + 0.20 * clamp((ret5 + 0.05) / 0.10)
        + 0.16 * float(f["recovery_speed"])
        + 0.16 * float(f["pullback_resilience"])
        + 0.12 * relative
        + 0.10 * up_ratio
    )
    supply_exhaustion = clamp(
        0.28 * clamp(1.0 - float(f["downside_volume_decay"]))
        + 0.22 * clamp(1.0 - float(f["range_decay"]))
        + 0.18 * float(f["failed_breakdown"])
        + 0.16 * float(f["higher_low"])
        + 0.16 * float(f["recovery_speed"])
    )
    selling_activity = clamp(float(f["selling_activity"]))
    price_damage = clamp(float(f["price_damage"]))
    expected_damage = clamp(float(f["expected_price_damage"]))
    damage_efficiency = clamp(float(f["damage_efficiency"]))
    recovery_after_pressure = clamp(float(f["recovery_after_pressure"]))
    support_retention = clamp(float(f["support_retention"]))
    absorption_persistence = clamp(
        0.10 * float(f["absorption_persistence_1d"])
        + 0.20 * float(f["absorption_persistence_3d"])
        + 0.30 * float(f["absorption_persistence_5d"])
        + 0.40 * float(f["absorption_persistence_10d"])
    )
    # Activity is necessary; quiet stability is not absorption.
    absorption = clamp(
        selling_activity
        * (
            0.45 * damage_efficiency
            + 0.25 * recovery_after_pressure
            + 0.20 * support_retention
            + 0.10 * absorption_persistence
        )
    )
    absorption_failure = clamp(
        0.35 * selling_activity
        + 0.30 * price_damage
        + 0.20 * (1.0 - support_retention)
        + 0.15 * clamp(float(f["pressure_change"]) + 0.5)
        - 0.25 * damage_efficiency
    )
    accumulation = clamp(
        0.24 * absorption
        + 0.20 * supply_exhaustion
        + 0.20 * float(f["pullback_resilience"])
        + 0.18 * relative
        + 0.18 * clamp((ret5 + 0.03) / 0.08)
    )
    markup = clamp(
        0.30 * upward
        + 0.22 * demand_persistence
        + 0.16 * volume_pressure
        + 0.16 * relative
        + 0.16 * clamp((ret20 + 0.02) / 0.15)
    )
    poor_progress = clamp(1.0 - max(0.0, float(f["price_progress"])))
    late_extension = clamp((ret20 - 0.10) / 0.20)
    distribution = clamp(
        0.28 * volume_pressure * poor_progress
        + 0.22 * clamp((1.0 - close_position) * volume_ratio)
        + 0.20 * late_extension
        + 0.16 * clamp(1.0 - relative)
        + 0.14 * clamp(float(f["recent_negative_days"]) + down_ratio - 0.5)
    )
    crowding = clamp(
        0.28 * late_extension
        + 0.24 * volume_pressure
        + 0.20 * clamp(abs(ret1) / 0.08)
        + 0.16 * clamp(float(f["volume_concentration"]) * 4.0)
        + 0.12 * clamp(abs(volume_z) / 4.0)
    )
    trap = clamp(
        0.34 * distribution
        + 0.26 * clamp((volume_ratio - 1.0) / 2.0) * (1.0 - close_position)
        + 0.22 * clamp(-ret1 / 0.06)
        + 0.18 * clamp(1.0 - demand_persistence)
    )
    price_impact = clamp(
        0.50 * clamp(abs(ret1) / max(0.015, volume_ratio * 0.02))
        + 0.25 * clamp(abs(ret5) / max(0.04, volume_ratio * 0.05))
        + 0.25 * clamp(abs(float(f["price_progress"])))
    )
    evidence = {
        "upward_pressure": _evidence(upward, confidence, True, "5d/20d"),
        "downward_pressure": _evidence(downward, confidence, True, "5d/20d"),
        "volume_pressure": _evidence(volume_pressure, confidence, True, "20d"),
        "demand_persistence": _evidence(demand_persistence, confidence, True, "1d/3d/5d/10d/20d"),
        "supply_exhaustion": _evidence(supply_exhaustion, confidence, True, "5d/10d"),
        "absorption": _evidence(absorption, confidence * 0.85, True, "5d/10d"),
        "accumulation": _evidence(accumulation, confidence * 0.85, True, "5d/20d"),
        "markup": _evidence(markup, confidence, True, "5d/20d"),
        "distribution": _evidence(distribution, confidence * 0.85, True, "5d/20d"),
        "crowding": _evidence(crowding, confidence * 0.75, True, "1d/20d"),
        "trap": _evidence(trap, confidence * 0.75, True, "1d/5d"),
        "price_impact": _evidence(price_impact, confidence, True, "1d/5d"),
        "selling_activity": _evidence(selling_activity, confidence, True, "1d/5d/10d"),
        "price_damage": _evidence(price_damage, confidence, True, "1d/5d"),
        "expected_price_damage": _evidence(expected_damage, confidence, True, "5d/20d"),
        "damage_efficiency": _evidence(damage_efficiency, confidence * 0.9, True, "1d/5d/20d"),
        "recovery_after_pressure": _evidence(recovery_after_pressure, confidence, True, "3d"),
        "support_retention": _evidence(support_retention, confidence, True, "5d/10d"),
        "absorption_persistence": _evidence(absorption_persistence, confidence * 0.9, True, "1d/3d/5d/10d"),
        "absorption_failure": _evidence(absorption_failure, confidence * 0.9, True, "1d/5d/10d"),
    }
    return {
        "model_version": MODEL_VERSION,
        "data_version": DATA_VERSION,
        "availability": "AVAILABLE",
        "features": f,
        "evidence": evidence,
    }
