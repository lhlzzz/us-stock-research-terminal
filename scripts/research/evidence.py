"""Typed research claims. UNKNOWN is never promoted to a fact."""
from __future__ import annotations

from typing import Any, Mapping


SEMANTICS = ("OBSERVED", "DERIVED", "INFERRED", "UNKNOWN")
CLAIM_KINDS = ("FACT", "DERIVED", "INFERRED", "PREDICTED")
EVIDENCE_LEVELS = (
    "LEVEL_1",
    "LEVEL_2",
    "LEVEL_3",
    "LEVEL_4",
    "LEVEL_5",
    "LEVEL_6",
)
EVIDENCE_HIERARCHY = {
    "LEVEL_1": "Primary filings / company disclosure",
    "LEVEL_2": "Official company materials / transcripts",
    "LEVEL_3": "Regulatory / authoritative data",
    "LEVEL_4": "High-quality financial/news sources",
    "LEVEL_5": "Social / community",
    "LEVEL_6": "Model inference",
}
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
    "sec_filing",
    "earnings",
)


def evidence_level(source_type: str | None, *, filing: bool = False, transcript: bool = False, social: bool = False, inferred: bool = False) -> str:
    if filing or source_type == "sec_filing":
        return "LEVEL_1"
    if transcript or source_type == "earnings":
        return "LEVEL_2"
    if source_type in {"forward_tracking", "ticket"}:
        return "LEVEL_3"
    if source_type in {"public_quote", "public_ohlcv", "capital_brain"}:
        return "LEVEL_4"
    if social or source_type == "obsidian":
        return "LEVEL_5"
    if inferred or source_type in {"skill", "statistical_brain"}:
        return "LEVEL_6"
    return "LEVEL_6"


def claim_kind(semantic: str) -> str:
    label = str(semantic or "UNKNOWN").upper()
    if label in {"OBSERVED"}:
        return "FACT"
    if label == "DERIVED":
        return "DERIVED"
    if label == "INFERRED":
        return "INFERRED"
    if label == "PREDICTED":
        return "PREDICTED"
    return "INFERRED" if label != "UNKNOWN" else "INFERRED"


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
    level: str | None = None,
    kind: str | None = None,
) -> dict[str, Any]:
    """Build one auditable claim. Missing evidence stays UNKNOWN."""
    label = str(semantic or "UNKNOWN").upper()
    if label == "PREDICTED":
        kind = "PREDICTED"
        label = "INFERRED"
    if label not in SEMANTICS:
        label = "UNKNOWN"
    resolved_level = level if level in EVIDENCE_LEVELS else evidence_level(source_type, inferred=label in {"INFERRED", "UNKNOWN"})
    resolved_kind = kind if kind in CLAIM_KINDS else claim_kind(label)
    if value is None or value == "" or label == "UNKNOWN":
        return {
            "value": None if label == "UNKNOWN" else value,
            "semantic": "UNKNOWN" if value is None or value == "" else label,
            "kind": resolved_kind,
            "level": resolved_level,
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
        "kind": resolved_kind,
        "level": resolved_level,
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
