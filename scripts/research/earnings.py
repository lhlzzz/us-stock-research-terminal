"""Earnings events, surprises, and guidance. Research context only."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from .boundary import PRODUCTION_BOUNDARY, assert_research_only
from .evidence import observed_number, research_evidence
from .providers import DATA_GAP
from .temporal import historical_claim_eligible

GUIDANCE_DIRECTIONS = ("RAISED", "MAINTAINED", "LOWERED", "UNKNOWN")


def earnings_event(
    *,
    symbol: str,
    event_date: str | None,
    fiscal_period: str | None = None,
    announced_at: str | None = None,
    retrieved_at: str | None = None,
    source: str | None = None,
    source_url: str | None = None,
    status: str = "UNKNOWN",
    reported_eps: Any = None,
    consensus_eps: Any = None,
    reported_revenue: Any = None,
    consensus_revenue: Any = None,
    guidance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ticker = str(symbol).upper()
    eps_surprise = None
    revenue_surprise = None
    reported = observed_number(reported_eps)
    consensus = observed_number(consensus_eps)
    if reported is not None and consensus is not None:
        eps_surprise = round(reported - consensus, 6)
    reported_rev = observed_number(reported_revenue)
    consensus_rev = observed_number(consensus_revenue)
    if reported_rev is not None and consensus_rev is not None:
        revenue_surprise = round(reported_rev - consensus_rev, 6)
    label = str(status or "UNKNOWN").upper()
    if not source:
        label = DATA_GAP if label == "OBSERVED" else label
    payload = {
        "symbol": ticker,
        "event_date": event_date,
        "fiscal_period": fiscal_period,
        "announced_at": announced_at or event_date,
        "retrieved_at": retrieved_at,
        "source": source,
        "source_url": source_url,
        "status": label if source or label in {DATA_GAP, "ERROR", "UNKNOWN"} else DATA_GAP,
        "reported_eps": reported,
        "consensus_eps": consensus,
        "eps_surprise": eps_surprise,
        "reported_revenue": reported_rev,
        "consensus_revenue": consensus_rev,
        "revenue_surprise": revenue_surprise,
        "guidance": dict(guidance or {}),
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
    return payload


def earnings_as_of(events: Iterable[Mapping[str, Any]] | None, *, as_of: str) -> list[dict[str, Any]]:
    visible = []
    for row in events or []:
        payload = dict(row)
        available = payload.get("available_at") or payload.get("announced_at") or payload.get("event_date")
        gate = historical_claim_eligible(
            {
                "published_at": payload.get("published_at") or payload.get("announced_at") or payload.get("event_date"),
                "effective_date": payload.get("effective_date") or available,
                "available_at": available,
                "retrieved_at": payload.get("retrieved_at"),
            },
            as_of=as_of,
        )
        if not gate["eligible"]:
            payload["replay_status"] = "DO_NOT_USE_IN_HISTORICAL_REPLAY"
            continue
        visible.append(payload)
    return visible


def split_surprises(event: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(event or {})
    return {
        "eps_surprise": payload.get("eps_surprise"),
        "revenue_surprise": payload.get("revenue_surprise"),
        "combined_score_forbidden": True,
        "status": "OBSERVED" if payload.get("eps_surprise") is not None or payload.get("revenue_surprise") is not None else DATA_GAP,
    }


def guidance_change(
    *,
    previous: Any,
    current: Any,
    effective_at: str | None,
    source: str | None,
    direction: str | None = None,
) -> dict[str, Any]:
    prev = observed_number(previous)
    curr = observed_number(current)
    label = str(direction or "UNKNOWN").upper()
    if label not in GUIDANCE_DIRECTIONS:
        label = "UNKNOWN"
    if source and prev is not None and curr is not None and direction in (None, "", "UNKNOWN"):
        if curr > prev:
            label = "RAISED"
        elif curr < prev:
            label = "LOWERED"
        else:
            label = "MAINTAINED"
    if not source:
        return {
            "previous": prev,
            "current": curr,
            "effective_at": effective_at,
            "source": source,
            "direction": "UNKNOWN",
            "status": DATA_GAP,
            "inferred_from_headline": False,
            "produces_pick": False,
        }
    return {
        "previous": prev,
        "current": curr,
        "effective_at": effective_at,
        "source": source,
        "direction": label,
        "status": "OBSERVED" if label != "UNKNOWN" else "UNKNOWN",
        "inferred_from_headline": False,
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def earnings_from_sec_facts(
    *,
    symbol: str,
    as_of: str,
    parsed: Mapping[str, Any] | None,
    filings: Iterable[Mapping[str, Any]] | None = None,
    source: str = "sec_edgar",
    source_url: str | None = None,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    ticker = str(symbol).upper()
    fields = dict((parsed or {}).get("fields") or {})
    eps = (fields.get("eps_diluted") or {}).get("value")
    revenue = (fields.get("revenue") or {}).get("value")
    period = (fields.get("eps_diluted") or fields.get("revenue") or {}).get("period")
    form = (fields.get("eps_diluted") or fields.get("revenue") or {}).get("form")
    filed = (fields.get("eps_diluted") or fields.get("revenue") or {}).get("filed")
    visible_filings = earnings_as_of(
        [
            {
                **dict(row),
                "available_at": row.get("available_at") or row.get("filing_date"),
                "announced_at": row.get("acceptance_datetime") or row.get("filing_date"),
                "event_date": row.get("filing_date"),
            }
            for row in filings or []
        ],
        as_of=as_of,
    )
    if eps is None and revenue is None and not visible_filings:
        payload = {
            "symbol": ticker,
            "as_of": as_of,
            "status": DATA_GAP,
            "events": [],
            "reason": "earnings facts not ingested",
            "produces_pick": False,
            "production_boundary": PRODUCTION_BOUNDARY,
        }
        assert_research_only(payload)
        return payload
    event = earnings_event(
        symbol=ticker,
        event_date=filed or period,
        fiscal_period=form,
        announced_at=filed,
        retrieved_at=retrieved_at,
        source=source,
        source_url=source_url,
        status="OBSERVED" if source else DATA_GAP,
        reported_eps=eps,
        reported_revenue=revenue,
    )
    evidence = research_evidence(
        symbol=ticker,
        as_of=as_of,
        published_at=filed,
        effective_date=filed,
        available_at=filed,
        retrieved_at=retrieved_at,
        source=source,
        source_type="earnings",
        source_url=source_url,
        status="OBSERVED" if source else DATA_GAP,
        level="LEVEL_1",
        facts={"reported_eps": eps, "reported_revenue": revenue, "eps_surprise": None, "revenue_surprise": None},
    )
    payload = {
        "symbol": ticker,
        "as_of": as_of,
        "status": "OBSERVED" if source and (eps is not None or revenue is not None or visible_filings) else DATA_GAP,
        "events": [event, *visible_filings],
        "latest": event,
        "surprises": split_surprises(event),
        "guidance": guidance_change(previous=None, current=None, effective_at=None, source=None),
        "evidence": [evidence],
        "consensus_status": DATA_GAP,
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
    assert_research_only(payload)
    return payload
