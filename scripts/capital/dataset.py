"""Versioned Capital Behavior V3 dataset assembly and temporal eligibility.

This module is deliberately a projection layer. V2 remains the owner of
evidence, state, intent, control, and rule path inference. Dataset samples
copy those as-of outputs and keep future labels in a separate outcome object.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable, Mapping


DATASET_VERSION = "capital_dataset_v1"
FEATURE_VERSION = "capital_features_v2"
LABEL_VERSION = "capital_label_v1"
CAPITAL_MODEL_VERSION = "capital_behavior_v2"
STATE_MODEL_VERSION = "rule_state_v2"
INTENT_MODEL_VERSION = "rule_intent_v2"
PATH_MODEL_VERSION = "rule_path_v2"
CALIBRATION_VERSION = "calibration_v1"

VALID_REASONS = {"VALID"}
SPLITS = ("TRAIN", "VALIDATION", "TEST")

FEATURE_COLUMNS = (
    "upward_pressure", "downward_pressure", "selling_activity",
    "price_damage", "expected_price_damage", "damage_efficiency",
    "absorption", "absorption_efficiency", "absorption_persistence",
    "absorption_failure", "demand_persistence", "supply_exhaustion",
    "markup", "distribution", "crowding", "trap",
    "price_response_efficiency", "upside_control_efficiency",
    "downside_control_efficiency", "control_asymmetry", "control_collapse",
)


def _finite(value: Any) -> float | int | None:
    if value is None or isinstance(value, bool):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def _clean(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clean(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        return _finite(value)
    if isinstance(value, (date,)):
        return value.isoformat()
    return value


def canonical_json(value: Any) -> str:
    """Return stable JSON used for replay fingerprints and artifact output."""
    return json.dumps(_clean(value), ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _nested(snapshot: Mapping[str, Any], key: str, fallback: str) -> dict[str, Any]:
    value = snapshot.get(key)
    if value is None:
        value = snapshot.get(fallback)
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            value = {}
    return dict(value) if isinstance(value, Mapping) else {}


def _evidence_values(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    evidence = _nested(snapshot, "evidence", "evidence_json")
    if isinstance(evidence.get("evidence"), Mapping):
        evidence = dict(evidence["evidence"])
    result: dict[str, Any] = {}
    for key, value in evidence.items():
        if isinstance(value, Mapping):
            result[key] = _finite(value.get("value"))
        else:
            result[key] = _finite(value)
    return result


def _state_payload(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    state = _nested(snapshot, "state", "inferred_state")
    if not state and snapshot.get("capital_state") is not None:
        state = {key: snapshot.get(key) for key in (
            "capital_state", "previous_capital_state", "state_transition",
            "state_duration", "state_confidence", "state_reason",
            "transition_probabilities", "late_state_risk", "state_age_score",
        )}
    return _clean(state)


def _intent_payload(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    intent = _nested(snapshot, "intent", "inferred_intent")
    if not intent and snapshot.get("capital_intent") is not None:
        intent = {key: snapshot.get(key) for key in (
            "capital_intent", "intent_probability", "intent_confidence",
            "intent_probabilities", "intent_alternatives", "expected_direction",
            "intent_transition", "continuation_condition", "invalidation_condition",
        )}
    return _clean(intent)


def _path_payload(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    path = _nested(snapshot, "path", "predicted_path")
    if not path and snapshot.get("path_type") is not None:
        path = {key: snapshot.get(key) for key in (
            "path_type", "predicted_path", "t1_probability", "t3_probability",
            "t5_probability", "path_confidence", "paths", "path_distribution",
            "path_sequence", "path_invalidation",
        )}
    return _clean(path)


def _path_distribution(path: Mapping[str, Any], horizon: int) -> dict[str, Any]:
    direct = path.get(f"path_distribution_t{horizon}")
    if isinstance(direct, Mapping):
        return _clean(direct)
    paths = path.get("paths")
    if isinstance(paths, Mapping) and isinstance(paths.get(f"t{horizon}"), Mapping):
        return _clean(paths[f"t{horizon}"])
    return {}


def _lineage(snapshot: Mapping[str, Any], lineage: Mapping[str, Any] | None) -> dict[str, Any]:
    supplied = dict(lineage or snapshot.get("source_lineage") or {})
    return _clean(supplied)


def _eligibility_reason(
    snapshot: Mapping[str, Any],
    outcome: Mapping[str, Any] | None,
    lineage: Mapping[str, Any],
) -> str:
    if not snapshot.get("research_run_id"):
        return "MISSING_LINEAGE"
    if not lineage or lineage.get("status") in {"INVALID", "UNAVAILABLE_HISTORICAL"}:
        return "SOURCE_INVALID"
    for key in ("data_version", "model_version", "feature_version"):
        if not snapshot.get(key):
            return "VERSION_INVALID"
    if snapshot.get("data_gap") is True:
        return "DATA_GAP"
    required_outcomes = ("return_1d", "return_3d", "return_5d", "return_10d")
    if not outcome or any(outcome.get(key) is None for key in required_outcomes):
        return "INSUFFICIENT_FORWARD_DATA"
    return "VALID"


def assemble_dataset_sample(
    snapshot: Mapping[str, Any],
    *,
    outcome: Mapping[str, Any] | None = None,
    lineage: Mapping[str, Any] | None = None,
    split: str | None = None,
) -> dict[str, Any]:
    """Build one stable sample from one as-of V2 snapshot.

    ``outcome`` is intentionally supplied separately. It is never read from
    the feature/evidence layer and therefore cannot silently leak into input.
    """
    evidence = _evidence_values(snapshot)
    features = _nested(snapshot, "features", "derived_features")
    control = _nested(snapshot, "control", "control")
    state = _state_payload(snapshot)
    intent = _intent_payload(snapshot)
    path = _path_payload(snapshot)
    lineage_payload = _lineage(snapshot, lineage)
    clean_outcome = _clean(dict(outcome or {}))
    reason = _eligibility_reason(snapshot, clean_outcome, lineage_payload)
    requested_split = split.upper() if isinstance(split, str) else None
    if requested_split not in SPLITS:
        requested_split = None
    eligible = reason in VALID_REASONS
    sample = {
        "symbol": str(snapshot.get("symbol") or "").upper(),
        "as_of_date": str(snapshot.get("as_of_date") or ""),
        "research_run_id": snapshot.get("research_run_id"),
        "data_version": str(snapshot.get("data_version") or ""),
        "model_version": str(snapshot.get("model_version") or CAPITAL_MODEL_VERSION),
        "feature_version": str(snapshot.get("feature_version") or FEATURE_VERSION),
        "label_version": LABEL_VERSION if clean_outcome else None,
        "capital_model_version": str(snapshot.get("capital_model_version") or snapshot.get("model_version") or CAPITAL_MODEL_VERSION),
        "state_model_version": str(snapshot.get("state_model_version") or STATE_MODEL_VERSION),
        "intent_model_version": str(snapshot.get("intent_model_version") or INTENT_MODEL_VERSION),
        "path_model_version": str(snapshot.get("path_model_version") or PATH_MODEL_VERSION),
        "calibration_version": str(snapshot.get("calibration_version") or CALIBRATION_VERSION),
        "price": _finite(snapshot.get("price") or features.get("price") or features.get("close")),
        "volume": _finite(snapshot.get("volume") or features.get("volume")),
        "liquidity": _finite(snapshot.get("liquidity") or features.get("liquidity_proxy")),
        **{key: evidence.get(key) for key in FEATURE_COLUMNS},
        "price_response_efficiency": _finite(control.get("price_response_efficiency") or control.get("price_control_score") or snapshot.get("price_control_score")),
        "upside_control_efficiency": _finite(control.get("upside_control_efficiency") or snapshot.get("upside_control_efficiency")),
        "downside_control_efficiency": _finite(control.get("downside_control_efficiency") or snapshot.get("downside_control_efficiency")),
        "control_asymmetry": _finite(control.get("control_asymmetry") or snapshot.get("control_asymmetry")),
        "control_collapse": _finite(control.get("control_collapse_score") or snapshot.get("control_collapse_score")),
        "capital_state": state.get("capital_state") or snapshot.get("capital_state"),
        "capital_state_confidence": _finite(state.get("state_confidence") or snapshot.get("capital_state_confidence")),
        "capital_intent": intent.get("capital_intent") or snapshot.get("capital_intent"),
        "intent_probability": _finite(intent.get("intent_probability") or snapshot.get("intent_probability")),
        "capital_strength": _finite(snapshot.get("capital_strength") or snapshot.get("capital_score")),
        "capital_quality": _finite(snapshot.get("capital_quality")),
        "path_distribution_t1": _path_distribution(path, 1),
        "path_distribution_t3": _path_distribution(path, 3),
        "path_distribution_t5": _path_distribution(path, 5),
        "observed_inputs": _clean({
            key: snapshot.get(key) for key in ("symbol", "as_of_date", "price", "volume", "liquidity")
            if snapshot.get(key) is not None
        }),
        "derived_features": _clean(features),
        "inferred_state": state,
        "inferred_intent": intent,
        "predicted_path": path,
        "future_outcome": clean_outcome,
        "source_lineage": lineage_payload,
        "eligible_for_training": eligible and requested_split == "TRAIN",
        "eligible_for_validation": eligible and requested_split == "VALIDATION",
        "eligible_for_test": eligible and requested_split == "TEST",
        "eligibility_reason": reason,
        "dataset_split": requested_split,
        "dataset_version": DATASET_VERSION,
    }
    return _clean(sample)


@dataclass(frozen=True)
class TemporalSplit:
    train_dates: tuple[date, ...]
    validation_dates: tuple[date, ...]
    test_dates: tuple[date, ...]
    embargo_dates: tuple[date, ...]


def _date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def purged_temporal_split(
    dates: Iterable[date | str],
    *,
    train_ratio: float = 0.60,
    validation_ratio: float = 0.20,
    horizon_days: int = 10,
    embargo_days: int | None = None,
) -> TemporalSplit:
    """Split dates chronologically without crossing future-label boundaries.

    A sample dated ``d`` owns a forward label window through
    ``d + horizon_days``.  Dates at the end of TRAIN/VALIDATION whose label
    window reaches the next partition are purged.  An optional embargo also
    removes dates immediately after each boundary.  Calendar days are used
    deliberately as a conservative approximation; callers may pass the
    actual maximum forward-label horizon.
    """
    unique = sorted({_date(item) for item in dates})
    if not unique:
        return TemporalSplit((), (), (), ())
    if not 0 < train_ratio < 1 or not 0 < validation_ratio < 1 or train_ratio + validation_ratio >= 1:
        raise ValueError("train_ratio and validation_ratio must leave a positive test partition")
    embargo = max(0, int(horizon_days if embargo_days is None else embargo_days))
    train_end = max(1, int(len(unique) * train_ratio))
    validation_end = max(train_end + 1, int(len(unique) * (train_ratio + validation_ratio)))
    validation_end = min(validation_end, len(unique))
    train = unique[:train_end]
    validation = unique[train_end:validation_end]
    test = unique[validation_end:]
    purged_set: set[date] = set()
    if train and validation:
        validation_start = validation[0]
        purged_set.update(
            day for day in train
            if day + timedelta(days=horizon_days) >= validation_start
        )
    if validation and test:
        test_start = test[0]
        purged_set.update(
            day for day in validation
            if day + timedelta(days=horizon_days) >= test_start
        )

    embargo_set: set[date] = set()
    if validation:
        embargo_set.update(
            day for day in validation
            if day <= train[-1] + timedelta(days=embargo)
        )
    if test and validation:
        embargo_set.update(
            day for day in test
            if day <= validation[-1] + timedelta(days=embargo)
        )

    excluded = purged_set | embargo_set
    train = [day for day in train if day not in excluded]
    validation = [day for day in validation if day not in excluded]
    test = [day for day in test if day not in excluded]
    return TemporalSplit(tuple(train), tuple(validation), tuple(test), tuple(sorted(excluded)))


def assign_split(sample_date: date | str, split: TemporalSplit) -> str | None:
    day = _date(sample_date)
    if day in split.train_dates:
        return "TRAIN"
    if day in split.validation_dates:
        return "VALIDATION"
    if day in split.test_dates:
        return "TEST"
    return None


def temporal_split_assignments(
    rows: Iterable[Mapping[str, Any]],
    *,
    train_ratio: float = 0.60,
    validation_ratio: float = 0.20,
    horizon_days: int = 10,
    embargo_days: int | None = None,
) -> dict[Any, str]:
    """Return deterministic split assignments for valid persisted samples.

    IDs are kept separate from dates so duplicate symbols on one trading day
    receive the same chronological partition. Ineligible rows are excluded.
    """
    valid_rows = [row for row in rows if row.get("eligibility_reason") == "VALID"]
    split = purged_temporal_split(
        [row.get("as_of_date") for row in valid_rows if row.get("as_of_date")],
        train_ratio=train_ratio,
        validation_ratio=validation_ratio,
        horizon_days=horizon_days,
        embargo_days=embargo_days,
    )
    assignments: dict[Any, str] = {}
    for row in valid_rows:
        sample_id = row.get("id")
        partition = assign_split(row.get("as_of_date"), split)
        if sample_id is not None and partition:
            assignments[sample_id] = partition
    return assignments


def dataset_stats(samples: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(samples)
    valid = [row for row in rows if row.get("eligibility_reason") in VALID_REASONS]
    return {
        "total_samples": len(rows),
        "valid_samples": len(valid),
        "train_samples": sum(bool(row.get("eligible_for_training")) for row in rows),
        "validation_samples": sum(bool(row.get("eligible_for_validation")) for row in rows),
        "test_samples": sum(bool(row.get("eligible_for_test")) for row in rows),
        "trading_days": len({row.get("as_of_date") for row in rows if row.get("as_of_date")}),
        "symbols": len({row.get("symbol") for row in rows if row.get("symbol")}),
        "label_versions": sorted({row.get("label_version") for row in rows if row.get("label_version")}),
        "model_versions": sorted({row.get("model_version") for row in rows if row.get("model_version")}),
    }


def prediction_error_types(sample: Mapping[str, Any], outcome: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Classify deterministic discrepancies between a prediction and outcome."""
    errors: list[dict[str, Any]] = []
    predicted_state = sample.get("capital_state")
    actual_state = outcome.get("state_after_3d") or outcome.get("state_after_1d")
    predicted_intent = sample.get("capital_intent")
    actual_intent = outcome.get("actual_intent_proxy") or outcome.get("intent_after_3d")
    predicted_path = (_nested(sample, "predicted_path", "predicted_path").get("path_type")
                      or sample.get("path_type"))
    actual_path = outcome.get("actual_path") or outcome.get("path_after_3d")
    if predicted_state and actual_state and predicted_state != actual_state:
        errors.append({"error_type": "STATE_FALSE_POSITIVE", "error_magnitude": 1.0})
    if outcome.get("transition_label") and predicted_state and not str(outcome["transition_label"]).startswith(f"{predicted_state}->"):
        errors.append({"error_type": "TRANSITION_MISSED", "error_magnitude": 1.0})
    if predicted_intent and actual_intent and predicted_intent not in {actual_intent, "UNCERTAIN"}:
        errors.append({"error_type": "INTENT_WRONG", "error_magnitude": 1.0})
    if predicted_path and actual_path and predicted_path != actual_path:
        errors.append({"error_type": "PATH_WRONG", "error_magnitude": 1.0})
    if _finite(sample.get("distribution")) is not None and float(sample.get("distribution") or 0.0) >= 0.7 and actual_path not in {"DISTRIBUTION", "TRAP"}:
        errors.append({"error_type": "DISTRIBUTION_MISSED", "error_magnitude": float(sample.get("distribution") or 0.0)})
    if _finite(sample.get("trap")) is not None and float(sample.get("trap") or 0.0) >= 0.7 and actual_path != "TRAP":
        errors.append({"error_type": "TRAP_MISSED", "error_magnitude": float(sample.get("trap") or 0.0)})
    confidence = _finite(sample.get("capital_state_confidence"))
    if confidence is not None and actual_state and predicted_state != actual_state:
        if confidence >= 0.8:
            errors.append({"error_type": "CONFIDENCE_OVERSTATED", "error_magnitude": float(confidence)})
        elif confidence <= 0.5:
            errors.append({"error_type": "CONFIDENCE_UNDERSTATED", "error_magnitude": float(1.0 - confidence)})
    return errors
