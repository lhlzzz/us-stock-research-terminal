"""Deterministic historical analogue retrieval without future-feature leakage."""
from __future__ import annotations

import math
import hashlib
from typing import Any, Iterable, Mapping


SIMILARITY_FIELDS = (
    "capital_state", "upward_pressure", "downward_pressure", "absorption",
    "control_asymmetry", "demand_persistence", "distribution", "crowding",
    "regime", "liquidity_bucket",
)


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _field(sample: Mapping[str, Any], field: str) -> Any:
    value = sample.get(field)
    if value is not None:
        return value
    derived = sample.get("derived_features")
    if isinstance(derived, Mapping):
        return derived.get(field)
    return None


def _vector(sample: Mapping[str, Any]) -> list[float]:
    result = []
    for field in SIMILARITY_FIELDS:
        if field in {"capital_state", "regime", "liquidity_bucket"}:
            digest = hashlib.sha256(str(_field(sample, field) or "UNKNOWN").encode("utf-8")).hexdigest()
            result.append(float(int(digest[:8], 16) % 1000) / 1000.0)
        else:
            result.append(_number(_field(sample, field)))
    return result


def similarity(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    """Return bounded inverse distance using as-of fields only."""
    a, b = _vector(left), _vector(right)
    distance = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / max(1, len(a)))
    return round(1.0 / (1.0 + distance), 6)


def retrieve_similar_cases(
    current: Mapping[str, Any],
    historical: Iterable[Mapping[str, Any]],
    *,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Return stable nearest cases; outcomes are output context, never inputs."""
    current_key = (str(current.get("symbol")), str(current.get("as_of_date")))
    candidates = []
    for row in historical:
        if row.get("eligibility_reason") not in {None, "VALID"}:
            continue
        if (str(row.get("symbol")), str(row.get("as_of_date"))) == current_key:
            continue
        score = similarity(current, row)
        candidates.append({
            "symbol": row.get("symbol"),
            "as_of_date": row.get("as_of_date"),
            "capital_state": row.get("capital_state"),
            "similarity": score,
            "future_outcome": row.get("future_outcome") or {},
        })
    candidates.sort(key=lambda row: (-row["similarity"], str(row.get("symbol")), str(row.get("as_of_date"))))
    return candidates[:max(0, int(top_k))]


def analogue_outcome_distribution(cases: Iterable[Mapping[str, Any]], *, horizon: int = 3) -> dict[str, Any]:
    rows = [case for case in cases if isinstance(case.get("future_outcome"), Mapping)]
    values = [str(case["future_outcome"].get(f"path_after_{horizon}d")) for case in rows if case["future_outcome"].get(f"path_after_{horizon}d")]
    counts = {value: values.count(value) for value in sorted(set(values))}
    total = len(values)
    return {
        "status": "RESEARCH_ONLY" if total else "NOT_READY",
        "sample_count": total,
        "horizon": horizon,
        "probabilities": {key: round(value / total, 6) for key, value in counts.items()} if total else {},
    }


def classify_case(sample: Mapping[str, Any]) -> str | None:
    """Classify a complete public-data case, including deterministic counterexamples."""
    outcome = sample.get("future_outcome") or {}
    if not isinstance(outcome, Mapping) or outcome.get("return_3d") is None:
        return None
    state = str(sample.get("capital_state") or "")
    path = str(outcome.get("path_after_3d") or outcome.get("actual_path") or "")
    if state in {"ACCUMULATION", "EARLY_BUILD"} and path in {"BREAKDOWN", "TRAP"}:
        return "FALSE_ACCUMULATION"
    if state == "PULLBACK_ABSORPTION" and path in {"BREAKDOWN", "TRAP"}:
        return "FALSE_ABSORPTION"
    if state in {"ACTIVE_MARKUP", "SECONDARY_MARKUP"} and path in {"DISTRIBUTION", "BREAKDOWN", "TRAP"}:
        return "DISTRIBUTION_AFTER_MOMENTUM"
    if path == "TRAP":
        return "TRAP_AFTER_VOLUME_SPIKE"
    if state in {"ACTIVE_MARKUP", "LATE_MARKUP"} and path == "BREAKDOWN":
        return "CONTROL_COLLAPSE"
    return None
