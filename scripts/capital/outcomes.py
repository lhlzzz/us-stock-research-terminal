"""Public outcome facade for the deterministic Capital Behavior labels.

``labels.py`` owns the labeling rules.  This module is the stable result-level
API used by persistence and future callers, so outcome assembly is not copied
into backfill code.
"""
from __future__ import annotations

from typing import Any, Mapping

from .labels import label_future_outcomes, label_for_tracking_row, outcome_is_complete


def merge_outcomes(existing: Mapping[str, Any] | None, incoming: Mapping[str, Any] | None) -> dict[str, Any]:
    """Merge newly due horizons without overwriting known values with nulls."""
    merged = dict(existing or {})
    for key, value in (incoming or {}).items():
        if value is not None:
            merged[key] = value
    return merged


__all__ = [
    "label_future_outcomes",
    "label_for_tracking_row",
    "outcome_is_complete",
    "merge_outcomes",
]
