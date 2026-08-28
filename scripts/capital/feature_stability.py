"""Feature stability diagnostics for public-data Capital Behavior samples."""
from __future__ import annotations

import math
from typing import Any, Iterable, Mapping

import numpy as np


NOT_READY = "NOT_READY"


def _rank(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = np.arange(1, len(values) + 1, dtype=float)
    return ranks


def _corr(left: np.ndarray, right: np.ndarray) -> float | None:
    if len(left) < 2 or np.std(left) == 0 or np.std(right) == 0:
        return None
    return float(np.corrcoef(left, right)[0, 1])


def _mutual_information(values: np.ndarray, returns: np.ndarray, bins: int = 5) -> float:
    edges = np.unique(np.quantile(values, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    x = np.clip(np.digitize(values, edges[1:-1]), 0, len(edges) - 2)
    y = returns > 0
    total = len(values)
    mi = 0.0
    for xi in range(int(x.max()) + 1):
        for yi in (False, True):
            joint = np.sum((x == xi) & (y == yi)) / total
            if joint == 0:
                continue
            px = np.sum(x == xi) / total
            py = np.sum(y == yi) / total
            mi += joint * math.log(joint / (px * py))
    return mi


def feature_stability(
    rows: Iterable[Mapping[str, Any]],
    *,
    features: Iterable[str],
    return_key: str = "return_3d",
    min_samples: int = 30,
    buckets: int = 5,
) -> dict[str, Any]:
    data = list(rows)
    result: dict[str, Any] = {"status": NOT_READY, "sample_count": 0, "features": {}}
    for feature in features:
        pairs = []
        for row in data:
            try:
                value = float(row.get(feature))
                outcome = float(row.get(return_key))
            except (TypeError, ValueError):
                continue
            if math.isfinite(value) and math.isfinite(outcome):
                pairs.append((value, outcome))
        if len(pairs) < min_samples:
            continue
        values = np.asarray([pair[0] for pair in pairs], dtype=float)
        returns = np.asarray([pair[1] for pair in pairs], dtype=float)
        rank_ic = _corr(_rank(values), _rank(returns))
        ic = _corr(values, returns)
        bucket_ids = np.clip(np.digitize(values, np.quantile(values, np.linspace(0, 1, buckets + 1))[1:-1]), 0, buckets - 1)
        bucket_means = [float(np.mean(returns[bucket_ids == bucket])) for bucket in range(buckets) if np.any(bucket_ids == bucket)]
        monotonicity = _corr(np.arange(len(bucket_means), dtype=float), np.asarray(bucket_means)) if len(bucket_means) > 1 else None
        result["features"][feature] = {
            "sample_count": len(pairs),
            "ic": round(ic, 6) if ic is not None else None,
            "rank_ic": round(rank_ic, 6) if rank_ic is not None else None,
            "mutual_information": round(_mutual_information(values, returns), 6),
            "sign_stability": round(float(np.mean(np.sign(values) == np.sign(np.mean(values)))), 6),
            "bucket_monotonicity": round(monotonicity, 6) if monotonicity is not None else None,
            "bucket_means": [round(value, 6) for value in bucket_means],
        }
    result["sample_count"] = len(data)
    if result["features"]:
        result["status"] = "RESEARCH_ONLY"
    return result
