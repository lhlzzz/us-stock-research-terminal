"""Typed research claims. UNKNOWN is never promoted to a fact."""
from __future__ import annotations

from typing import Any, Mapping


SEMANTICS = ("OBSERVED", "DERIVED", "INFERRED", "UNKNOWN")
SOURCE_TYPES = (
    "public_quote",
    "public_ohlcv",
    "ticket",
    "forward_tracking",
    "obsidian",
    "skill",
    "capital_brain",
    "statistical_brain",
    "personal_portfolio",
    "market_research",
)


def claim(
    value: Any,
    *,
    semantic: str,
    source: str,
    source_type: str,
    effective_date: str | None = None,
    as_of_date: str | None = None,
    confidence: float | None = None,
    evidence_refs: list[str] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Build one auditable claim. Missing evidence stays UNKNOWN."""
    label = str(semantic or "UNKNOWN").upper()
    if label not in SEMANTICS:
        label = "UNKNOWN"
    if value is None or value == "" or label == "UNKNOWN":
        return {
            "value": None if label == "UNKNOWN" else value,
            "semantic": "UNKNOWN" if value is None or value == "" else label,
            "source": source,
            "source_type": source_type,
            "effective_date": effective_date,
            "as_of_date": as_of_date,
            "confidence": None if value is None or value == "" else confidence,
            "evidence_refs": list(evidence_refs or []),
            "reason": reason or ("no evidence" if value is None or value == "" else None),
        }
    return {
        "value": value,
        "semantic": label,
        "source": source,
        "source_type": source_type,
        "effective_date": effective_date,
        "as_of_date": as_of_date,
        "confidence": confidence,
        "evidence_refs": list(evidence_refs or []),
        "reason": reason,
    }


class Claim(dict):
    """Compatibility wrapper around :func:`claim`."""


def unknown(source: str, source_type: str, *, reason: str = "no evidence", **kwargs: Any) -> dict[str, Any]:
    return claim(None, semantic="UNKNOWN", source=source, source_type=source_type, reason=reason, **kwargs)


def observed_number(value: Any) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def provenance(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source": item.get("source"),
        "source_type": item.get("source_type"),
        "effective_date": item.get("effective_date"),
        "as_of_date": item.get("as_of_date"),
        "confidence": item.get("confidence"),
        "evidence_refs": list(item.get("evidence_refs") or []),
        "semantic": item.get("semantic") or "UNKNOWN",
    }
