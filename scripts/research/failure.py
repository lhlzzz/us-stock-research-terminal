"""Persistent failure memory. Learning only; never a production scorer."""
from __future__ import annotations

from typing import Any, Iterable, Mapping
from uuid import uuid4

from .boundary import PRODUCTION_BOUNDARY, assert_research_only
from .evidence import utc_now

FAILURE_TYPES = (
    "TEMPORAL_LEAK",
    "MISSING_EVIDENCE",
    "WRONG_SOURCE",
    "WRONG_UNIT",
    "WRONG_AS_OF",
    "FALSE_POSITIVE",
    "FALSE_NEGATIVE",
    "THESIS_BREAK",
    "CATALYST_MISREAD",
    "EARNINGS_MISREAD",
    "REVISION_MISREAD",
    "INDUSTRY_MISREAD",
    "RISK_UNDERESTIMATED",
    "UNIVERSE_SURVIVORSHIP_ERROR",
    "DATA_PROVIDER_FAILURE",
)
FAILURE_MEMORY: list[dict[str, Any]] = []
LEARNING_PATTERNS: list[dict[str, Any]] = []


def failure_memory(
    *,
    symbol: str,
    as_of: str,
    research_layer: str,
    failure_type: str,
    expected: Any = None,
    observed: Any = None,
    diagnosis: str | None = None,
    root_cause: str | None = None,
    evidence_gap: str | None = None,
    outcome_horizon: str | None = None,
    severity: str | None = None,
    confidence: float | None = None,
    source_episode: str | None = None,
    replay_id: str | None = None,
    created_at: str | None = None,
    failure_id: str | None = None,
) -> dict[str, Any]:
    klass = str(failure_type or "").upper()
    if klass not in FAILURE_TYPES:
        klass = "THESIS_BREAK"
    payload = {
        "failure_id": failure_id or str(uuid4()),
        "symbol": str(symbol).upper(),
        "as_of": as_of,
        "research_layer": research_layer,
        "failure_type": klass,
        "expected": expected,
        "observed": observed,
        "diagnosis": diagnosis,
        "root_cause": root_cause,
        "evidence_gap": evidence_gap,
        "outcome_horizon": outcome_horizon,
        "severity": severity,
        "confidence": confidence,
        "source_episode": source_episode,
        "replay_id": replay_id,
        "created_at": created_at or utc_now(),
        "produces_pick": False,
        "changes_production_ranking": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
    assert_research_only(payload)
    FAILURE_MEMORY.append(payload)
    return payload


def retrieve_failures(
    *,
    symbol: str | None = None,
    failure_type: str | None = None,
    research_layer: str | None = None,
    as_of: str | None = None,
    library: Iterable[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows = [dict(item) for item in (library if library is not None else FAILURE_MEMORY)]
    if symbol:
        rows = [row for row in rows if row.get("symbol") == str(symbol).upper()]
    if failure_type:
        rows = [row for row in rows if row.get("failure_type") == str(failure_type).upper()]
    if research_layer:
        rows = [row for row in rows if row.get("research_layer") == research_layer]
    if as_of:
        rows = [row for row in rows if str(row.get("as_of") or "") <= str(as_of)]
    return rows


def learning_pattern(
    *,
    research_layer: str,
    pattern_type: str,
    condition: Mapping[str, Any] | None = None,
    outcome: Mapping[str, Any] | None = None,
    sample_count: int = 0,
    success_count: int = 0,
    failure_count: int = 0,
    confidence: float | None = None,
    source_failures: Iterable[str] | None = None,
    source_samples: Iterable[str] | None = None,
    pattern_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    payload = {
        "pattern_id": pattern_id or str(uuid4()),
        "research_layer": research_layer,
        "pattern_type": pattern_type,
        "condition": dict(condition or {}),
        "outcome": dict(outcome or {}),
        "sample_count": sample_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "confidence": confidence,
        "source_failures": list(source_failures or []),
        "source_samples": list(source_samples or []),
        "created_at": created_at or utc_now(),
        "updated_at": utc_now(),
        "produces_pick": False,
        "changes_production_ranking": False,
        "does_not_modify_ticket_score": True,
        "does_not_modify_market_score": True,
        "does_not_modify_volume_confirmation_ratio": True,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
    assert_research_only(payload)
    LEARNING_PATTERNS.append(payload)
    return payload


def retrieve_patterns(
    *,
    research_layer: str | None = None,
    pattern_type: str | None = None,
    library: Iterable[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows = [dict(item) for item in (library if library is not None else LEARNING_PATTERNS)]
    if research_layer:
        rows = [row for row in rows if row.get("research_layer") == research_layer]
    if pattern_type:
        rows = [row for row in rows if row.get("pattern_type") == pattern_type]
    return rows


def previous_failure_warning(query: Mapping[str, Any] | None = None) -> dict[str, Any]:
    matches = retrieve_failures(
        symbol=(query or {}).get("symbol"),
        failure_type=(query or {}).get("failure_type"),
        research_layer=(query or {}).get("research_layer"),
        as_of=(query or {}).get("as_of"),
    )
    return {
        "matches": matches,
        "count": len(matches),
        "prompt": "previous failure pattern" if matches else None,
        "not_a_production_signal": True,
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
