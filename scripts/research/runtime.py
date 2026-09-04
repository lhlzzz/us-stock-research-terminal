"""Xiaomei 2.2 research runtime. Research OS only; never production ranking."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Mapping

from .boundary import PRODUCTION_BOUNDARY, RANKING_KEY, assert_research_only
from .coverage import research_coverage, research_readiness
from .decision import build_company_research, why_not
from .earnings import earnings_from_sec_facts
from .estimates import estimate_revision_bundle
from .evidence import corroboration, evidence_quality, utc_now
from .failure import failure_memory, learning_pattern, previous_failure_warning, retrieve_failures, retrieve_patterns
from .industry import industry_from_sec
from .outcomes import independent_price_outcomes
from .providers import DATA_GAP, provider_attempts
from .sec import sec_research_bundle
from .snapshots import RESEARCH_VERSION, research_snapshot, snapshot_identity
from .store import (
    connect,
    persist_earnings_events,
    persist_estimate_revisions,
    persist_evidence,
    persist_failure,
    persist_industry_snapshot,
    persist_outcomes,
    persist_pattern,
    persist_provider_attempts,
    persist_run,
    persist_sec_document,
    persist_sec_facts,
    persist_snapshot,
    persist_universe_membership,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def code_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def historical_universe_status(snapshots: list[Mapping[str, Any]] | None) -> dict[str, Any]:
    rows = list(snapshots or [])
    if not rows:
        return {
            "status": DATA_GAP,
            "reason": "no true historical universe source",
            "uses_current_universe": False,
            "forbids_current_backfill": True,
        }
    return {
        "status": "OBSERVED",
        "membership": rows,
        "uses_current_universe": False,
        "forbids_current_backfill": True,
    }


def bind_outcomes(ohlcv, *, as_of: str) -> dict[str, Any]:
    if ohlcv is None:
        return {
            "available": False,
            "horizons": {1: {"complete": False}, 3: {"complete": False}, 5: {"complete": False}, 10: {"complete": False}},
            "independent_records": True,
            "single_total_outcome_forbidden": True,
        }
    payload = independent_price_outcomes(ohlcv, as_of_date=as_of)
    records = []
    for horizon in (1, 3, 5, 10):
        item = (payload.get("horizons") or {}).get(horizon) or {"complete": False, "return": None}
        records.append({"horizon": f"T+{horizon}", "horizon_days": horizon, **item})
    payload["independent_records"] = records
    payload["single_total_outcome_forbidden"] = True
    return payload


def research_thesis_bundle(
    *,
    symbol: str,
    as_of: str,
    supporting: list[Mapping[str, Any]],
    contradicting: list[Mapping[str, Any]],
    unknowns: list[str],
    risks: list[str],
    expected_behavior: str | None = None,
) -> dict[str, Any]:
    status = "CONTRADICTORY" if supporting and contradicting else "INCOMPLETE" if not supporting else "ALIGNED"
    return {
        "symbol": symbol,
        "as_of": as_of,
        "thesis": expected_behavior or "research-only fundamental trajectory",
        "supporting_evidence": supporting,
        "contradicting_evidence": contradicting,
        "unknowns": unknowns,
        "risk": risks,
        "expected_behavior": expected_behavior,
        "status": status,
        "bullish_only_forbidden": True,
        "produces_pick": False,
    }


def _persistable_run(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Store run identity and research conclusions, not raw SEC dumps."""
    copied = dict(payload)
    for key in ("sec", "earnings", "revisions", "industry", "research", "snapshot"):
        value = copied.get(key)
        if not isinstance(value, Mapping):
            continue
        slim = {name: value.get(name) for name in (
            "status", "symbol", "as_of", "cik", "company_name", "sic", "sic_description",
            "content_hash", "data_gaps", "reason", "direction", "events", "history",
            "entities", "relations", "chokepoint", "graph_snapshot_id", "valid_from",
            "valid_to", "fields", "latest", "surprises", "guidance", "consensus_status",
        ) if name in value}
        if key == "sec":
            slim["filing_count"] = len(value.get("filings") or [])
            slim["document_count"] = len(value.get("documents") or [])
            slim["parsed"] = value.get("parsed")
            slim["evidence_count"] = len(value.get("evidence") or [])
        copied[key] = slim
    copied.pop("provider_attempts", None)
    copied.pop("evidence_lineage", None)
    copied.pop("evidence_quality", None)
    return copied


def classify_research(*, readiness: Mapping[str, Any], contradiction: Mapping[str, Any]) -> str:
    status = str(readiness.get("status") or DATA_GAP).upper()
    if status in {DATA_GAP, "BLOCKED"}:
        return "NEEDS_MORE_EVIDENCE"
    if status == "NEEDS_MORE_EVIDENCE":
        return "MARKET_WATCHLIST_NEEDS_EVIDENCE"
    if contradiction.get("status") == "CONTRADICTORY":
        return "NEEDS_MORE_EVIDENCE"
    if status == "PARTIAL":
        return "WATCHLIST"
    return "RESEARCH_ONLY"


def run_symbol_research(
    *,
    symbol: str,
    as_of: str,
    provider,
    ohlcv=None,
    universe_snapshots: list[Mapping[str, Any]] | None = None,
    db_path: Path | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    started = time.time()
    started_at = utc_now()
    ticker = str(symbol).upper()
    commit = code_commit()
    conn = connect(db_path) if persist else None

    sec_fetch = provider.fetch_sec(ticker, as_of=as_of)
    earnings_fetch = provider.fetch_earnings(ticker, as_of=as_of)
    estimate_fetch = provider.fetch_estimates(ticker, as_of=as_of)
    industry_fetch = provider.fetch_industry(ticker, as_of=as_of)
    universe_fetch = provider.fetch_universe("CORE_UNIVERSE", as_of=as_of)
    fundamentals_fetch = provider.fetch_fundamentals(ticker, as_of=as_of)

    sec_bundle = sec_fetch if sec_fetch.get("parsed") else sec_research_bundle(
        symbol=ticker,
        as_of=as_of,
        submissions=sec_fetch.get("submissions"),
        companyfacts=sec_fetch.get("companyfacts"),
        retrieved_at=sec_fetch.get("retrieved_at"),
        status=sec_fetch.get("status") or DATA_GAP,
        error=sec_fetch.get("error"),
    )
    if sec_fetch.get("parsed"):
        sec_bundle = sec_fetch

    earnings_bundle = earnings_fetch if earnings_fetch.get("events") is not None else earnings_from_sec_facts(
        symbol=ticker,
        as_of=as_of,
        parsed=sec_bundle.get("parsed"),
        filings=sec_bundle.get("filings"),
        source="sec_edgar" if sec_bundle.get("status") == "OBSERVED" else None,
        retrieved_at=sec_bundle.get("temporal", {}).get("retrieved_at") if isinstance(sec_bundle.get("temporal"), Mapping) else None,
    )
    if earnings_fetch.get("status") in {"OBSERVED", DATA_GAP, "ERROR"} and earnings_fetch.get("events") is not None:
        earnings_bundle = earnings_fetch

    revision_bundle = estimate_fetch if estimate_fetch.get("history") is not None else estimate_revision_bundle(
        symbol=ticker,
        as_of=as_of,
        history=estimate_fetch.get("history"),
        source=estimate_fetch.get("source"),
    )
    industry_graph = industry_fetch if industry_fetch.get("entities") is not None else industry_from_sec(sec_bundle, as_of=as_of)
    if industry_fetch.get("status") in {DATA_GAP, "ERROR"} and not industry_fetch.get("entities"):
        industry_graph = industry_from_sec(sec_bundle, as_of=as_of)

    universe = historical_universe_status(universe_snapshots or universe_fetch.get("membership"))
    if universe_fetch.get("status") == DATA_GAP and not universe_snapshots:
        universe = universe_fetch if universe_fetch.get("status") else universe

    facts = {
        "symbol": ticker,
        "as_of_date": as_of,
        "industry": sec_bundle.get("sic_description"),
        "sector": sec_bundle.get("sic_description"),
        "entities": industry_graph.get("entities"),
        "relations": industry_graph.get("relations"),
    }
    parsed_fields = (sec_bundle.get("parsed") or {}).get("fields") or {}
    for name, item in parsed_fields.items():
        if isinstance(item, Mapping) and item.get("value") is not None:
            facts[name] = item["value"]
    research = build_company_research(ticker, as_of_date=as_of, facts=facts, ohlcv=ohlcv, industry_graph=industry_graph)

    supporting = []
    contradicting = []
    if parsed_fields.get("revenue") and parsed_fields.get("net_income"):
        rev = (parsed_fields.get("revenue") or {}).get("value")
        ni = (parsed_fields.get("net_income") or {}).get("value")
        if rev not in (None, "") and ni not in (None, ""):
            supporting.append({"name": "reported_fundamentals", "value": "present", "source": "sec_edgar"})
            if float(ni) < 0 < float(rev):
                contradicting.append({"name": "profitability", "value": "revenue_up_income_down", "source": "sec_edgar"})
    guidance = (earnings_bundle.get("guidance") or {})
    if guidance.get("direction") == "LOWERED" and supporting:
        contradicting.append({"name": "guidance", "value": "LOWERED", "source": guidance.get("source")})
    unknowns = []
    if revision_bundle.get("status") == DATA_GAP:
        unknowns.append("estimate_revision")
    if (industry_graph.get("chokepoint") or {}).get("status") == DATA_GAP:
        unknowns.append("chokepoint")
    if universe.get("status") == DATA_GAP:
        unknowns.append("historical_universe")
    risks = list(research.get("risk_view", {}).get("data_gaps") or []) or ["risk_unverified"]
    thesis = research_thesis_bundle(
        symbol=ticker,
        as_of=as_of,
        supporting=supporting,
        contradicting=contradicting,
        unknowns=unknowns,
        risks=risks,
        expected_behavior="fundamental trajectory from SEC facts; consensus/revision remain DATA_GAP unless sourced",
    )
    contradiction = {
        "status": "CONTRADICTORY" if contradicting and supporting else research.get("contradictions", {}).get("status"),
        "bull": supporting,
        "bear": contradicting,
        "not_merged_into_bullish": True,
    }
    coverage = research_coverage(
        symbol=ticker,
        as_of=as_of,
        market={"status": "OBSERVED" if ohlcv is not None else DATA_GAP, "as_of": as_of},
        fundamentals=research.get("fundamentals"),
        sec=sec_bundle,
        earnings=earnings_bundle,
        revision=revision_bundle,
        industry=industry_graph,
        risk=research.get("risk_view"),
        catalyst={"status": DATA_GAP},
        management=research.get("management"),
        supply_chain=industry_graph,
    )
    readiness = research_readiness(coverage)
    why = why_not(
        {
            "company": "UNKNOWN",
            "industry": "UNKNOWN" if industry_graph.get("status") == DATA_GAP else "NEUTRAL",
            "capital": "UNKNOWN",
            "market": "UNKNOWN" if ohlcv is None else "NEUTRAL",
            "risk": "UNKNOWN",
            "sec": "UNKNOWN" if sec_bundle.get("status") != "OBSERVED" else "NEUTRAL",
            "revision": "DATA_GAP" if revision_bundle.get("status") == DATA_GAP else "NEUTRAL",
        }
    )
    why["why_not"] = list(why.get("why_not") or []) + list(readiness.get("reasons") or [])
    outcomes = bind_outcomes(ohlcv, as_of=as_of)
    snapshot = research_snapshot(
        as_of=as_of,
        universe=universe,
        market={"ohlcv_present": ohlcv is not None},
        fundamentals=research.get("fundamentals"),
        earnings=earnings_bundle,
        revisions=revision_bundle,
        industry=industry_graph,
        risk=research.get("risk_view"),
        research_evidence=sec_bundle.get("evidence") or [],
        code_commit=commit,
    )
    classification = classify_research(readiness=readiness, contradiction=contradiction)
    if classification in {"BUY", "SELL"}:
        classification = "RESEARCH_ONLY"
    failures = retrieve_failures(symbol=ticker)
    warning = previous_failure_warning({"symbol": ticker, "as_of": as_of})
    patterns = retrieve_patterns()
    evidence_show = [
        {
            "claim": "sec_filing",
            "evidence": item,
            "source": item.get("source"),
            "document": item.get("document_id"),
            "retrieved": item.get("retrieved_at"),
            "as_of": as_of,
        }
        for item in (sec_bundle.get("evidence") or [])
    ]
    quality = [evidence_quality(item) for item in (sec_bundle.get("evidence") or [])]
    run_id = snapshot_identity(symbol=ticker, as_of=as_of, research_version=RESEARCH_VERSION, snapshot_hash=snapshot["content_hash"])
    payload = {
        "run_id": run_id,
        "symbol": ticker,
        "as_of": as_of,
        "research_version": RESEARCH_VERSION,
        "code_commit": commit,
        "dataset_version": snapshot["content_hash"],
        "snapshot_hash": snapshot["content_hash"],
        "started_at": started_at,
        "completed_at": utc_now(),
        "duration_ms": int((time.time() - started) * 1000),
        "providers": {
            "sec": sec_fetch.get("status"),
            "earnings": earnings_bundle.get("status"),
            "estimates": revision_bundle.get("status"),
            "industry": industry_graph.get("status"),
            "universe": universe.get("status"),
            "fundamentals": fundamentals_fetch.get("status"),
        },
        "evidence_count": len(sec_bundle.get("evidence") or []),
        "classification": classification,
        "error_count": sum(1 for item in provider_attempts(symbol=ticker) if item.get("status") == "ERROR"),
        "sec": sec_bundle,
        "earnings": earnings_bundle,
        "revisions": revision_bundle,
        "industry": industry_graph,
        "universe": universe,
        "coverage": coverage,
        "readiness": readiness,
        "thesis": thesis,
        "contradictions": contradiction,
        "why_not": why,
        "outcomes": outcomes,
        "snapshot": snapshot,
        "research": research,
        "failures": failures,
        "failure_warning": warning,
        "learning_patterns": patterns,
        "evidence_lineage": evidence_show,
        "evidence_quality": quality,
        "corroboration": corroboration(["sec_edgar"] if sec_bundle.get("status") == "OBSERVED" else []),
        "production_ranking_key": list(RANKING_KEY),
        "ranking_owner": PRODUCTION_BOUNDARY["ranking_owner"],
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
        "provider_attempts": provider_attempts(symbol=ticker),
    }
    payload["data_gaps"] = [name for name, status in {
        "sec": sec_bundle.get("status"),
        "earnings": earnings_bundle.get("status"),
        "revision": revision_bundle.get("status"),
        "industry": industry_graph.get("status"),
        "chokepoint": (industry_graph.get("chokepoint") or {}).get("status"),
        "universe": universe.get("status"),
    }.items() if status in {DATA_GAP, "UNKNOWN", "ERROR"}]
    assert_research_only(payload)
    if conn is not None:
        for doc in sec_bundle.get("documents") or []:
            persist_sec_document(conn, doc)
        persist_sec_facts(conn, sec_bundle.get("xbrl_facts") or [], symbol=ticker)
        persist_earnings_events(conn, earnings_bundle.get("events") or [])
        persist_estimate_revisions(conn, revision_bundle.get("history") or [])
        if universe.get("membership"):
            persist_universe_membership(conn, universe.get("membership") or [])
        for item in sec_bundle.get("evidence") or []:
            persist_evidence(conn, item)
        persist_snapshot(conn, snapshot)
        persist_industry_snapshot(conn, {**industry_graph, "as_of": as_of, "content_hash": snapshot["content_hash"]})
        persist_provider_attempts(conn, payload["provider_attempts"])
        if outcomes.get("horizons"):
            persist_outcomes(conn, ticker, as_of, outcomes["horizons"])
        stored = persist_run(conn, _persistable_run(payload))
        conn.commit()
        payload["reused"] = stored.get("reused")
        payload["run_id"] = stored.get("run_id") or payload["run_id"]
        conn.close()
    else:
        payload["reused"] = False
    return payload


def seed_demo_learning(*, symbol: str, as_of: str, db_path: Path | None = None) -> dict[str, Any]:
    failure = failure_memory(
        symbol=symbol,
        as_of=as_of,
        research_layer="earnings",
        failure_type="EARNINGS_MISREAD",
        expected="guidance maintained",
        observed="guidance lowered after earnings beat",
        diagnosis="treated EPS beat as confirmation while guidance was cut",
        root_cause="merged EPS and guidance into one bullish narrative",
        evidence_gap="guidance previous/current not split",
        outcome_horizon="T+5",
        severity="HIGH",
        confidence=0.8,
        source_episode="xiaomei-2.2-demo",
        persist=True,
        db_path=db_path,
    )
    pattern = learning_pattern(
        research_layer="earnings",
        pattern_type="eps_beat_guidance_cut",
        condition={"eps_surprise": "positive", "guidance": "LOWERED"},
        outcome={"caution": True, "do_not_merge": True},
        sample_count=1,
        success_count=0,
        failure_count=1,
        confidence=0.5,
        source_failures=[failure["failure_id"]],
        source_samples=[f"{symbol}:{as_of}"],
        persist=True,
        db_path=db_path,
    )
    conn = connect(db_path)
    persist_failure(conn, failure)
    persist_pattern(conn, pattern)
    conn.commit()
    conn.close()
    return {"failure": failure, "pattern": pattern}
