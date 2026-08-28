"""Research-only empirical Capital Behavior baselines.

The baseline is a deterministic conditional-frequency model. It is useful for
measuring whether recurring public-data patterns have predictive value, but it
does not mutate V2 rule outputs or production ranking.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping


NOT_READY = "NOT_READY"
RESEARCH_ONLY = "RESEARCH_ONLY"
MIN_SAMPLES = 30


def _label(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _read_nested(row: Mapping[str, Any], dotted_key: str) -> Any:
    value: Any = row
    for part in dotted_key.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def _normalize(counts: Mapping[str, int]) -> dict[str, float]:
    total = sum(max(0, int(value)) for value in counts.values())
    if total <= 0:
        return {}
    values = {str(key): round(max(0, int(value)) / total, 6) for key, value in sorted(counts.items())}
    if values:
        largest = max(values, key=values.get)
        values[largest] = round(values[largest] + 1.0 - sum(values.values()), 6)
    return values


def empirical_distribution(
    rows: Iterable[Mapping[str, Any]],
    *,
    condition_keys: tuple[str, ...],
    outcome_key: str,
    min_samples: int = MIN_SAMPLES,
) -> dict[str, Any]:
    """Estimate P(outcome | condition) using stable sorted frequency counts."""
    grouped: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    usable = 0
    for row in rows:
        outcome = _label(_read_nested(row, outcome_key))
        condition = tuple(_label(row.get(key)) or "UNKNOWN" for key in condition_keys)
        if outcome is None:
            continue
        grouped[condition][outcome] += 1
        usable += 1
    if usable < min_samples:
        return {
            "status": NOT_READY,
            "sample_count": usable,
            "min_samples": min_samples,
            "condition_keys": list(condition_keys),
            "outcome_key": outcome_key,
            "probabilities": {},
        }
    probabilities = {
        "|".join(condition): _normalize(counter)
        for condition, counter in sorted(grouped.items())
    }
    return {
        "status": RESEARCH_ONLY,
        "sample_count": usable,
        "min_samples": min_samples,
        "condition_keys": list(condition_keys),
        "outcome_key": outcome_key,
        "probabilities": probabilities,
    }


def fit_empirical_baseline(
    samples: Iterable[Mapping[str, Any]],
    *,
    min_samples: int = MIN_SAMPLES,
    split: str = "TRAIN",
) -> dict[str, Any]:
    """Fit conditionals from one chronological partition.

    Persisted datasets must provide ``dataset_split`` and are restricted to
    the requested partition, normally TRAIN.  Small in-memory callers that
    do not carry split metadata remain supported for deterministic unit tests
    and replay utilities.
    """
    requested_split = str(split or "TRAIN").upper()
    source_rows = [dict(row) for row in samples if row.get("eligibility_reason") == "VALID"]
    has_split_metadata = any("dataset_split" in row for row in source_rows)
    rows = [
        row for row in source_rows
        if not has_split_metadata or str(row.get("dataset_split") or "").upper() == requested_split
    ]
    result = {
        "model_version": "capital_empirical_baseline_v1",
        "status": NOT_READY,
        "sample_count": len(rows),
        "min_samples": min_samples,
        "fit_split": requested_split,
        "production_action": "NO_PRODUCTION_WEIGHT_CHANGE",
        "state_model": empirical_distribution(rows, condition_keys=("capital_state",), outcome_key="future_outcome.state_after_3d", min_samples=min_samples),
        "transition_model": empirical_distribution(rows, condition_keys=("capital_state",), outcome_key="future_outcome.transition_after_3d", min_samples=min_samples),
        "intent_model": empirical_distribution(rows, condition_keys=("capital_state",), outcome_key="future_outcome.intent_after_3d", min_samples=min_samples),
        "path_models": {
            f"t{horizon}": empirical_distribution(rows, condition_keys=("capital_state",), outcome_key=f"future_outcome.path_after_{horizon}d", min_samples=min_samples)
            for horizon in (1, 3, 5, 10)
        },
    }
    models = (
        result["state_model"], result["transition_model"], result["intent_model"], *result["path_models"].values()
    )
    if all(model.get("status") == RESEARCH_ONLY for model in models):
        result["status"] = RESEARCH_ONLY
    return result


def predict_empirical(
    model: Mapping[str, Any],
    sample: Mapping[str, Any],
    *,
    model_name: str = "state_model",
    horizon: int | None = None,
) -> dict[str, float]:
    """Return a deterministic empirical distribution or an empty NOT_READY result."""
    selected: Mapping[str, Any] = model.get(model_name, {}) if horizon is None else model.get("path_models", {}).get(f"t{horizon}", {})
    probabilities = selected.get("probabilities", {}) if isinstance(selected, Mapping) else {}
    condition = "|".join(_label(sample.get(key)) or "UNKNOWN" for key in selected.get("condition_keys", ("capital_state",)))
    values = probabilities.get(condition, {}) if isinstance(probabilities, Mapping) else {}
    return {str(key): float(value) for key, value in sorted(values.items())}


def hybrid_probability(
    rule_probability: Mapping[str, float],
    empirical_probability: Mapping[str, float],
    *,
    empirical_weight: float = 0.5,
) -> dict[str, Any]:
    """Combine probabilities only as an explicit research output."""
    if not empirical_probability:
        return {
            "status": NOT_READY,
            "rule_probability": dict(sorted(rule_probability.items())),
            "empirical_probability": {},
            "hybrid_probability": dict(sorted(rule_probability.items())),
        }
    weight = min(1.0, max(0.0, float(empirical_weight)))
    keys = sorted(set(rule_probability) | set(empirical_probability))
    hybrid = {
        key: (1.0 - weight) * float(rule_probability.get(key, 0.0)) + weight * float(empirical_probability.get(key, 0.0))
        for key in keys
    }
    normalized = _normalize({key: int(round(value * 1_000_000)) for key, value in hybrid.items()})
    return {
        "status": RESEARCH_ONLY,
        "rule_probability": dict(sorted((key, float(value)) for key, value in rule_probability.items())),
        "empirical_probability": dict(sorted((key, float(value)) for key, value in empirical_probability.items())),
        "hybrid_probability": normalized,
        "empirical_weight": weight,
    }
