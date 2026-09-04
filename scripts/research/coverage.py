"""Research coverage matrix and readiness. Not a production score."""
from __future__ import annotations

from typing import Any, Mapping

from .boundary import PRODUCTION_BOUNDARY, assert_research_only
from .providers import DATA_GAP

COVERAGE_LAYERS = (
    "market",
    "fundamentals",
    "sec",
    "earnings",
    "revision",
    "industry",
    "risk",
    "catalyst",
    "management",
    "supply_chain",
)
READINESS_STATES = ("READY", "PARTIAL", "NEEDS_MORE_EVIDENCE", "DATA_GAP", "BLOCKED")


def _layer_status(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {
            "coverage": 0.0,
            "status": DATA_GAP,
            "evidence_count": 0,
            "latest_available_as_of": None,
        }
    status = str(payload.get("status") or DATA_GAP).upper()
    if status == "READY":
        status = "OBSERVED"
    if status in {"OBSERVED", "DERIVED"}:
        coverage = 1.0
        label = "READY"
    elif status in {"PARTIAL"}:
        coverage = 0.5
        label = "PARTIAL"
    elif status in {"ERROR", "BLOCKED"}:
        coverage = 0.0
        label = "BLOCKED" if status == "BLOCKED" else "ERROR"
    else:
        coverage = 0.0
        label = DATA_GAP if status in {DATA_GAP, "UNKNOWN", ""} else status
    evidence = payload.get("evidence") or payload.get("filings") or payload.get("events") or payload.get("relations") or payload.get("fields")
    if isinstance(evidence, Mapping):
        count = sum(1 for value in evidence.values() if value not in (None, "", {}, []))
    elif isinstance(evidence, list):
        count = len(evidence)
    else:
        count = 1 if payload.get("status") in {"OBSERVED", "READY", "DERIVED"} else 0
    return {
        "coverage": coverage,
        "status": label,
        "evidence_count": count,
        "latest_available_as_of": payload.get("as_of") or payload.get("as_of_date") or payload.get("latest_available_as_of"),
        "raw_status": status,
    }


def research_coverage(
    *,
    symbol: str,
    as_of: str,
    market: Mapping[str, Any] | None = None,
    fundamentals: Mapping[str, Any] | None = None,
    sec: Mapping[str, Any] | None = None,
    earnings: Mapping[str, Any] | None = None,
    revision: Mapping[str, Any] | None = None,
    industry: Mapping[str, Any] | None = None,
    risk: Mapping[str, Any] | None = None,
    catalyst: Mapping[str, Any] | None = None,
    management: Mapping[str, Any] | None = None,
    supply_chain: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    layers = {
        "market": _layer_status(market),
        "fundamentals": _layer_status(fundamentals),
        "sec": _layer_status(sec),
        "earnings": _layer_status(earnings),
        "revision": _layer_status(revision),
        "industry": _layer_status(industry),
        "risk": _layer_status(risk),
        "catalyst": _layer_status(catalyst),
        "management": _layer_status(management),
        "supply_chain": _layer_status(supply_chain),
    }
    payload = {
        "symbol": str(symbol).upper(),
        "as_of": as_of,
        "layers": layers,
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
    assert_research_only(payload)
    return payload


def research_readiness(coverage: Mapping[str, Any] | None) -> dict[str, Any]:
    layers = dict((coverage or {}).get("layers") or {})
    reasons = []
    ready = 0
    blocked = 0
    gaps = 0
    for name in COVERAGE_LAYERS:
        item = layers.get(name) or {"status": DATA_GAP}
        status = str(item.get("status") or DATA_GAP).upper()
        if status == "READY":
            ready += 1
        elif status in {"BLOCKED", "ERROR"}:
            blocked += 1
            reasons.append(f"{name}={status}")
        elif status in {DATA_GAP, "UNKNOWN"}:
            gaps += 1
            reasons.append(f"{name}={status}")
        else:
            reasons.append(f"{name}={status}")
    if blocked:
        state = "BLOCKED"
    elif ready == len(COVERAGE_LAYERS):
        state = "READY"
    elif ready == 0:
        state = DATA_GAP
    elif gaps and ready < 4:
        state = "NEEDS_MORE_EVIDENCE"
    else:
        state = "PARTIAL"
    payload = {
        "status": state,
        "reasons": reasons,
        "ready_count": ready,
        "layer_total": len(COVERAGE_LAYERS),
        "not_a_bool": True,
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
    assert_research_only(payload)
    return payload
