"""Calibration interfaces for research-only capital probabilities."""
from __future__ import annotations

import math
from typing import Any, Iterable


UNAVAILABLE_STATUS = "UNAVAILABLE_NO_FIXED_CHAIN"


def _finite_pairs(predicted: Iterable[float], actual: Iterable[float]) -> list[tuple[float, float]]:
    pairs = []
    for probability, outcome in zip(predicted, actual):
        try:
            probability = float(probability)
            outcome = float(outcome)
        except (TypeError, ValueError):
            continue
        if math.isfinite(probability) and math.isfinite(outcome):
            pairs.append((min(1.0, max(0.0, probability)), min(1.0, max(0.0, outcome))))
    return pairs


def brier_score(predicted: Iterable[float], actual: Iterable[float]) -> dict[str, Any]:
    pairs = _finite_pairs(predicted, actual)
    if not pairs:
        return {"status": UNAVAILABLE_STATUS, "sample_count": 0, "value": None}
    return {"status": "RESEARCH_ONLY", "sample_count": len(pairs), "value": round(sum((p - y) ** 2 for p, y in pairs) / len(pairs), 6)}


def log_loss(predicted: Iterable[float], actual: Iterable[float], epsilon: float = 1e-15) -> dict[str, Any]:
    pairs = _finite_pairs(predicted, actual)
    if not pairs:
        return {"status": UNAVAILABLE_STATUS, "sample_count": 0, "value": None}
    value = -sum(y * math.log(max(epsilon, p)) + (1.0 - y) * math.log(max(epsilon, 1.0 - p)) for p, y in pairs) / len(pairs)
    return {"status": "RESEARCH_ONLY", "sample_count": len(pairs), "value": round(value, 6)}


def calibration_curve(
    predicted: Iterable[float],
    actual: Iterable[float],
    bins: int = 10,
) -> dict[str, Any]:
    pairs = _finite_pairs(predicted, actual)
    if not pairs:
        return {"status": UNAVAILABLE_STATUS, "sample_count": 0, "bins": []}
    bins = max(1, int(bins))
    groups = []
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        cohort = [(p, y) for p, y in pairs if lower <= p < upper or (index == bins - 1 and p <= upper)]
        if cohort:
            groups.append({
                "lower": round(lower, 6),
                "upper": round(upper, 6),
                "sample_count": len(cohort),
                "predicted_mean": round(sum(p for p, _ in cohort) / len(cohort), 6),
                "actual_rate": round(sum(y for _, y in cohort) / len(cohort), 6),
            })
    return {"status": "RESEARCH_ONLY", "sample_count": len(pairs), "bins": groups}


def evaluate_calibration(predicted: Iterable[float], actual: Iterable[float]) -> dict[str, Any]:
    """Return honest metrics; zero samples never become fabricated precision."""
    return {
        "status": UNAVAILABLE_STATUS if not _finite_pairs(predicted, actual) else "RESEARCH_ONLY",
        "brier_score": brier_score(predicted, actual),
        "log_loss": log_loss(predicted, actual),
        "calibration_curve": calibration_curve(predicted, actual),
    }
