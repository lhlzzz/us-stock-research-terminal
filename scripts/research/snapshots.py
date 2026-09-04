"""Historical research snapshots. Hash detects silent mutation."""
from __future__ import annotations

from typing import Any, Mapping

from .boundary import PRODUCTION_BOUNDARY, assert_research_only
from .evidence import content_hash, utc_now
from .temporal import historical_claim_eligible

RESEARCH_VERSION = "xiaomei-2.2.1"


def research_snapshot(
    *,
    as_of: str,
    universe: Mapping[str, Any] | None = None,
    market: Mapping[str, Any] | None = None,
    fundamentals: Mapping[str, Any] | None = None,
    earnings: Mapping[str, Any] | None = None,
    revisions: Mapping[str, Any] | None = None,
    industry: Mapping[str, Any] | None = None,
    risk: Mapping[str, Any] | None = None,
    research_evidence: list[Mapping[str, Any]] | None = None,
    research_version: str = RESEARCH_VERSION,
    code_commit: str | None = None,
) -> dict[str, Any]:
    eligible = []
    blocked = []
    for item in research_evidence or []:
        gate = historical_claim_eligible(item, as_of=as_of)
        if gate["eligible"]:
            eligible.append(dict(item))
        else:
            blocked.append({**dict(item), "replay_status": "DO_NOT_USE_IN_HISTORICAL_REPLAY", "temporal": gate})
    body = {
        "as_of": as_of,
        "universe": dict(universe or {}),
        "market": dict(market or {}),
        "fundamentals": dict(fundamentals or {}),
        "earnings": dict(earnings or {}),
        "revisions": dict(revisions or {}),
        "industry": dict(industry or {}),
        "risk": dict(risk or {}),
        "research_evidence": eligible,
        "blocked_evidence": blocked,
        "research_version": research_version,
        "code_commit": code_commit,
        "strategy": PRODUCTION_BOUNDARY["strategy"],
        "strategy_status": PRODUCTION_BOUNDARY["strategy_status"],
        "calendar_version": "us_market_calendar_nyse",
    }
    hashed = content_hash(body)
    payload = {
        **body,
        "content_hash": hashed,
        "generated_at": utc_now(),
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
    assert_research_only(payload)
    return payload


def snapshot_identity(*, symbol: str, as_of: str, research_version: str, snapshot_hash: str) -> str:
    return "|".join([str(symbol).upper(), str(as_of)[:10], research_version, snapshot_hash])
