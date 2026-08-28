"""Research evaluation metrics for Capital Behavior V3."""
from __future__ import annotations

import math
from collections import Counter
from statistics import median
from typing import Any, Iterable, Mapping


NOT_READY = "NOT_READY"


def _usable_pairs(actual: Iterable[Any], predicted: Iterable[Any]) -> list[tuple[str, str]]:
    return [(str(a), str(p)) for a, p in zip(actual, predicted) if a is not None and p is not None]


def classification_metrics(actual: Iterable[Any], predicted: Iterable[Any], *, min_samples: int = 1) -> dict[str, Any]:
    pairs = _usable_pairs(actual, predicted)
    if len(pairs) < min_samples:
        return {"status": NOT_READY, "sample_count": len(pairs), "accuracy": None, "macro_f1": None, "per_class": {}, "confusion_matrix": {}}
    labels = sorted({label for pair in pairs for label in pair})
    matrix = {actual_label: {predicted_label: 0 for predicted_label in labels} for actual_label in labels}
    for actual_label, predicted_label in pairs:
        matrix[actual_label][predicted_label] += 1
    per_class = {}
    f1_values = []
    for label in labels:
        tp = matrix[label][label]
        fp = sum(matrix[other][label] for other in labels if other != label)
        fn = sum(matrix[label][other] for other in labels if other != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1_values.append(f1)
        per_class[label] = {"precision": round(precision, 6), "recall": round(recall, 6), "f1": round(f1, 6), "support": tp + fn}
    return {
        "status": "RESEARCH_ONLY",
        "sample_count": len(pairs),
        "accuracy": round(sum(a == p for a, p in pairs) / len(pairs), 6),
        "macro_f1": round(sum(f1_values) / len(f1_values), 6) if f1_values else None,
        "per_class": per_class,
        "confusion_matrix": matrix,
    }


def multiclass_brier(probabilities: Iterable[Mapping[str, float]], actual: Iterable[Any], *, min_samples: int = 1) -> dict[str, Any]:
    rows = [(dict(probs), str(label)) for probs, label in zip(probabilities, actual) if label is not None]
    if len(rows) < min_samples:
        return {"status": NOT_READY, "sample_count": len(rows), "value": None}
    labels = sorted({label for probs, actual_label in rows for label in set(probs) | {actual_label}})
    value = sum(sum((float(probs.get(label, 0.0)) - float(label == actual_label)) ** 2 for label in labels) for probs, actual_label in rows) / len(rows)
    return {"status": "RESEARCH_ONLY", "sample_count": len(rows), "value": round(value, 6)}


def multiclass_log_loss(probabilities: Iterable[Mapping[str, float]], actual: Iterable[Any], *, epsilon: float = 1e-15, min_samples: int = 1) -> dict[str, Any]:
    rows = [(dict(probs), str(label)) for probs, label in zip(probabilities, actual) if label is not None]
    if len(rows) < min_samples:
        return {"status": NOT_READY, "sample_count": len(rows), "value": None}
    value = -sum(math.log(max(epsilon, min(1.0, float(probs.get(label, 0.0))))) for probs, label in rows) / len(rows)
    return {"status": "RESEARCH_ONLY", "sample_count": len(rows), "value": round(value, 6)}


def calibration_error(probabilities: Iterable[Mapping[str, float]], actual: Iterable[Any], *, bins: int = 10, min_samples: int = 1) -> dict[str, Any]:
    rows = []
    for probs, label in zip(probabilities, actual):
        if label is None or not probs:
            continue
        best = max(probs, key=probs.get)
        confidence = min(1.0, max(0.0, float(probs[best])))
        rows.append((confidence, float(str(label) == str(best))))
    if len(rows) < min_samples:
        return {"status": NOT_READY, "sample_count": len(rows), "value": None, "reliability": []}
    reliability = []
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        bucket = [row for row in rows if (lower <= row[0] < upper) or (index == bins - 1 and row[0] <= upper)]
        if not bucket:
            continue
        avg_confidence = sum(row[0] for row in bucket) / len(bucket)
        accuracy = sum(row[1] for row in bucket) / len(bucket)
        reliability.append({"lower": lower, "upper": upper, "sample_count": len(bucket), "confidence": round(avg_confidence, 6), "accuracy": round(accuracy, 6)})
    value = sum(abs(item["confidence"] - item["accuracy"]) * item["sample_count"] for item in reliability) / len(rows)
    return {"status": "RESEARCH_ONLY", "sample_count": len(rows), "value": round(value, 6), "reliability": reliability}


def economic_metrics(returns: Iterable[float], *, mfe: Iterable[float] | None = None, mae: Iterable[float] | None = None, min_samples: int = 1) -> dict[str, Any]:
    values = [float(value) for value in returns if value is not None and math.isfinite(float(value))]
    mfe_values = [float(value) for value in mfe if value is not None and math.isfinite(float(value))] if mfe is not None else []
    mae_values = [float(value) for value in mae if value is not None and math.isfinite(float(value))] if mae is not None else []
    if len(values) < min_samples:
        return {"status": NOT_READY, "sample_count": len(values), "average_return": None, "median_return": None, "profit_factor": None, "mfe": None, "mae": None, "tail_loss": None}
    gains = sum(value for value in values if value > 0)
    losses = sum(value for value in values if value < 0)
    return {
        "status": "RESEARCH_ONLY",
        "sample_count": len(values),
        "average_return": round(sum(values) / len(values), 6),
        "median_return": round(median(values), 6),
        "profit_factor": round(gains / abs(losses), 6) if losses else None,
        "mfe": round(sum(mfe_values) / len(mfe_values), 6) if mfe_values else None,
        "mae": round(sum(mae_values) / len(mae_values), 6) if mae_values else None,
        "tail_loss": round(min(values), 6),
    }


def evaluate_predictions(
    *,
    actual_state: Iterable[Any],
    predicted_state: Iterable[Any],
    actual_path: Iterable[Any],
    predicted_path: Iterable[Any],
    path_probabilities: Iterable[Mapping[str, float]],
    returns: Iterable[float],
    min_samples: int = 30,
) -> dict[str, Any]:
    actual_state = list(actual_state)
    predicted_state = list(predicted_state)
    actual_path = list(actual_path)
    predicted_path = list(predicted_path)
    path_probabilities = list(path_probabilities)
    returns = list(returns)
    state = classification_metrics(actual_state, predicted_state, min_samples=min_samples)
    path = classification_metrics(actual_path, predicted_path, min_samples=min_samples)
    return {
        "status": "RESEARCH_ONLY" if state["status"] == "RESEARCH_ONLY" and path["status"] == "RESEARCH_ONLY" else NOT_READY,
        "state": state,
        "path": path,
        "path_brier": multiclass_brier(path_probabilities, actual_path, min_samples=min_samples),
        "path_log_loss": multiclass_log_loss(path_probabilities, actual_path, min_samples=min_samples),
        "path_calibration": calibration_error(path_probabilities, actual_path, min_samples=min_samples),
        "economic": economic_metrics(returns, min_samples=min_samples),
        "production_action": "NO_PRODUCTION_WEIGHT_CHANGE",
    }


def evaluate_model_drift(
    *,
    actual_state: Iterable[Any],
    predicted_state: Iterable[Any],
    actual_path: Iterable[Any],
    predicted_path: Iterable[Any],
    path_probabilities: Iterable[Mapping[str, float]],
    distribution_warning: Iterable[bool] | None = None,
    distribution_actual: Iterable[bool] | None = None,
    min_samples: int = 30,
    model_version: str = "capital_empirical_baseline_v1",
    window_start: Any = None,
    window_end: Any = None,
) -> dict[str, Any]:
    """Return a bounded, research-only drift record.

    Drift is diagnostic only.  Insufficient samples never become a healthy
    model and no value from this function changes production weights.
    """
    actual_state = list(actual_state)
    predicted_state = list(predicted_state)
    actual_path = list(actual_path)
    predicted_path = list(predicted_path)
    path_probabilities = list(path_probabilities)
    states = classification_metrics(actual_state, predicted_state, min_samples=min_samples)
    paths = classification_metrics(actual_path, predicted_path, min_samples=min_samples)
    calibration = calibration_error(path_probabilities, actual_path, min_samples=min_samples)
    warning_precision = None
    warnings = list(distribution_warning or [])
    actual_distribution = list(distribution_actual or [])
    if warnings and len(warnings) == len(actual_distribution):
        warned = [actual for warning, actual in zip(warnings, actual_distribution) if warning]
        warning_precision = sum(bool(value) for value in warned) / len(warned) if warned else None
    ready = states["status"] == "RESEARCH_ONLY" and paths["status"] == "RESEARCH_ONLY"
    return {
        "model_version": model_version,
        "window_start": str(window_start) if window_start is not None else None,
        "window_end": str(window_end) if window_end is not None else None,
        "status": "RESEARCH_ONLY" if ready else NOT_READY,
        "state_accuracy": states.get("accuracy"),
        "path_accuracy": paths.get("accuracy"),
        "calibration_error": calibration.get("value"),
        "distribution_warning_precision": round(warning_precision, 6) if warning_precision is not None else None,
        "metrics": {"state": states, "path": paths, "path_calibration": calibration},
        "production_action": "NO_PRODUCTION_WEIGHT_CHANGE",
    }
