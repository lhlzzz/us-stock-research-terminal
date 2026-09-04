"""Typed research claims. UNKNOWN is never promoted to a fact."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Mapping


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


LEVEL_RANK = {level: index for index, level in enumerate(EVIDENCE_LEVELS)}


def _as_of_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text[:10] if text else None


def claim_kind(semantic: str) -> str:
    label = str(semantic or "UNKNOWN").upper()
    if label == "OBSERVED":
        return "FACT"
    if label == "DERIVED":
        return "DERIVED"
    if label == "INFERRED":
        return "INFERRED"
    if label == "PREDICTED":
        return "PREDICTED"
    return "UNKNOWN"


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
    resolved_level = level if level in EVIDENCE_LEVELS else evidence_level(
        source_type, inferred=label == "INFERRED"
    )
    resolved_kind = kind if kind in CLAIM_KINDS else claim_kind(label)
    as_of = _as_of_text(as_of_date)
    effective = _as_of_text(effective_date)
    if effective and as_of and effective > as_of:
        return {
            "value": None,
            "semantic": "UNKNOWN",
            "kind": "UNKNOWN",
            "level": resolved_level,
            "source": source,
            "source_type": source_type,
            "effective_date": effective,
            "as_of_date": as_of,
            "confidence": None,
            "evidence_refs": list(evidence_refs or []),
            "reason": "effective_date > as_of",
            "status": "BLOCKED",
            "blocked": True,
        }
    if value is None or value == "" or label == "UNKNOWN":
        return {
            "value": None if label == "UNKNOWN" else value,
            "semantic": "UNKNOWN" if value is None or value == "" else label,
            "kind": "UNKNOWN" if (value is None or value == "" or label == "UNKNOWN") else resolved_kind,
            "level": resolved_level,
            "source": source,
            "source_type": source_type,
            "effective_date": effective_date,
            "as_of_date": as_of_date,
            "confidence": None if value is None or value == "" else confidence,
            "evidence_refs": list(evidence_refs or []),
            "reason": reason or ("no evidence" if value is None or value == "" else None),
            "status": "UNKNOWN",
            "blocked": False,
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
        "status": "OK",
        "blocked": False,
    }


def iter_evidence(items: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def _walk(node: Any, depth: int = 0) -> None:
        if depth > 6 or node is None:
            return
        if isinstance(node, Mapping):
            if node.get("level") in EVIDENCE_LEVELS or node.get("semantic") in SEMANTICS:
                found.append(dict(node))
            for value in node.values():
                _walk(value, depth + 1)
            return
        if isinstance(node, (list, tuple)):
            for child in node:
                _walk(child, depth + 1)

    _walk(items)
    return found


def highest_evidence_quality(claims: Any) -> str | None:
    best = None
    best_rank = 99
    for item in iter_evidence(claims):
        level = item.get("level")
        if level not in LEVEL_RANK:
            continue
        rank = LEVEL_RANK[level]
        if rank < best_rank:
            best = level
            best_rank = rank
    return best


def contradictory_evidence(claims: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    by_subject: dict[str, list[Mapping[str, Any]]] = {}
    for item in claims or []:
        subject = str(item.get("name") or item.get("subject") or item.get("source") or "")
        if not subject:
            continue
        by_subject.setdefault(subject, []).append(item)
    conflicts = []
    for subject, rows in by_subject.items():
        values = [row.get("value") for row in rows if row.get("semantic") not in (None, "UNKNOWN")]
        unique = {str(value) for value in values}
        if len(unique) > 1:
            conflicts.append({"subject": subject, "values": list(unique), "status": "CONTRADICTED"})
    return conflicts


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
