"""Typed research claims. UNKNOWN is never promoted to a fact."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping
from uuid import uuid4


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
    "LEVEL_1": "official filing / company primary source",
    "LEVEL_2": "official transcript / official company publication",
    "LEVEL_3": "regulated/public primary dataset",
    "LEVEL_4": "reputable secondary source",
    "LEVEL_5": "public research / media",
    "LEVEL_6": "discovery-only",
}
EVIDENCE_STATUSES = ("OBSERVED", "DERIVED", "DATA_GAP", "UNKNOWN", "ERROR")
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
    "estimate_revision",
    "industry_graph",
    "universe",
    "rss",
    "xbrl",
)


def evidence_level(source_type: str | None, *, filing: bool = False, transcript: bool = False, social: bool = False, inferred: bool = False) -> str:
    if filing or source_type in {"sec_filing", "xbrl"}:
        return "LEVEL_1"
    if transcript or source_type == "earnings":
        return "LEVEL_2"
    if source_type in {"rss", "discovery"}:
        return "LEVEL_6"
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


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def content_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def research_evidence(
    *,
    symbol: str | None = None,
    as_of: str | None = None,
    published_at: str | None = None,
    effective_date: str | None = None,
    available_at: str | None = None,
    retrieved_at: str | None = None,
    source: str | None = None,
    source_type: str | None = None,
    source_url: str | None = None,
    document_id: str | None = None,
    claim_id: str | None = None,
    status: str = "UNKNOWN",
    level: str | None = None,
    confidence: float | None = None,
    raw_hash: str | None = None,
    facts: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    evidence_id: str | None = None,
) -> dict[str, Any]:
    """Canonical ResearchEvidence. OBSERVED requires a source."""
    label = str(status or "UNKNOWN").upper()
    if label == "READY":
        label = "OBSERVED"
    if label not in EVIDENCE_STATUSES:
        label = "UNKNOWN"
    if label == "OBSERVED" and not source:
        label = "ERROR"
        metadata = {**(metadata or {}), "reason": "OBSERVED requires source"}
    facts_payload = dict(facts or {})
    hashed = raw_hash or content_hash({"facts": facts_payload, "source": source, "source_url": source_url})
    return {
        "evidence_id": evidence_id or str(uuid4()),
        "symbol": None if symbol in (None, "") else str(symbol).upper(),
        "as_of": _as_of_text(as_of),
        "published_at": _as_of_text(published_at),
        "effective_date": _as_of_text(effective_date) or _as_of_text(published_at),
        "available_at": _as_of_text(available_at) or _as_of_text(published_at),
        "retrieved_at": retrieved_at or utc_now(),
        "source": source,
        "source_type": source_type or source,
        "source_url": source_url,
        "document_id": document_id,
        "claim_id": claim_id,
        "status": label,
        "evidence_level": level if level in EVIDENCE_LEVELS else evidence_level(source_type),
        "confidence": confidence,
        "raw_hash": hashed,
        "content_hash": hashed,
        "facts": facts_payload,
        "metadata": dict(metadata or {}),
        "produces_pick": False,
    }


def evidence_quality(
    item: Mapping[str, Any] | None = None,
    *,
    independent_sources: int = 1,
) -> dict[str, Any]:
    payload = dict(item or {})
    level = payload.get("evidence_level") or payload.get("level")
    status = str(payload.get("status") or payload.get("semantic") or "UNKNOWN").upper()
    published = _as_of_text(payload.get("published_at") or payload.get("effective_date"))
    as_of = _as_of_text(payload.get("as_of") or payload.get("as_of_date"))
    temporal_ok = True
    if published and as_of and published > as_of:
        temporal_ok = False
    corroborated = independent_sources >= 2 and status == "OBSERVED"
    return {
        "source_reliability": level,
        "directness": "PRIMARY" if level in {"LEVEL_1", "LEVEL_2", "LEVEL_3"} else "SECONDARY",
        "recency": published,
        "temporal_validity": temporal_ok,
        "independence": independent_sources,
        "corroboration": "CORROBORATED" if corroborated else "SINGLE_SOURCE" if status == "OBSERVED" else "NONE",
        "not_a_production_score": True,
    }


def corroboration(sources: Iterable[str] | None = None) -> dict[str, Any]:
    unique = sorted({str(item) for item in (sources or []) if item})
    return {
        "sources": unique,
        "independent_count": len(unique),
        "status": "CORROBORATED" if len(unique) >= 2 else "SINGLE_SOURCE" if unique else "NONE",
        "one_source_cannot_corroborate": True,
    }
