"""Unified research query. PostgreSQL + Obsidian + research graph only."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from .boundary import PRODUCTION_BOUNDARY, assert_research_only
from .contracts import independent_scores, research_horizon_contract
from .decision import contradiction_status
from .industry import persist_industry_graph, supply_chain_portfolio
from .thesis import similar_failures, thesis_ledger

QUERY_KINDS = (
    "research company",
    "research industry",
    "research chokepoint",
    "research portfolio concentration",
    "research similar failures",
    "research historical thesis",
)


def parse_query(text: str) -> dict[str, Any]:
    raw = " ".join((text or "").strip().split())
    lower = raw.lower()
    if lower.startswith("research company"):
        return {"kind": "research company", "target": raw[len("research company"):].strip().upper()}
    if lower.startswith("research industry"):
        return {"kind": "research industry", "target": raw[len("research industry"):].strip()}
    if lower.startswith("research chokepoint"):
        return {"kind": "research chokepoint", "target": raw[len("research chokepoint"):].strip()}
    if lower.startswith("research portfolio"):
        return {"kind": "research portfolio concentration", "target": raw}
    if lower.startswith("research similar failures"):
        return {"kind": "research similar failures", "target": raw[len("research similar failures"):].strip()}
    if lower.startswith("research historical thesis"):
        return {"kind": "research historical thesis", "target": raw[len("research historical thesis"):].strip()}
    return {"kind": None, "target": raw}


def research_query(
    text: str,
    *,
    company: Mapping[str, Any] | None = None,
    industry_graph: Mapping[str, Any] | None = None,
    chokepoints: Iterable[Mapping[str, Any]] | None = None,
    holdings: Iterable[str] | None = None,
    failures: Iterable[Mapping[str, Any]] | None = None,
    theses: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    parsed = parse_query(text)
    kind = parsed["kind"]
    target = parsed["target"]
    answer: dict[str, Any] = {"query": text, "kind": kind, "target": target, "sources": ["PostgreSQL", "Obsidian", "Research Graph"]}
    if kind == "research company":
        answer["payload"] = dict(company or {})
        answer["horizon"] = research_horizon_contract(company or {})
    elif kind == "research industry":
        answer["payload"] = persist_industry_graph(industry_graph)
    elif kind == "research chokepoint":
        rows = [dict(item) for item in chokepoints or [] if target.lower() in str(item).lower()]
        answer["payload"] = rows
    elif kind == "research portfolio concentration":
        answer["payload"] = supply_chain_portfolio(holdings, industry_graph, symbol=None)
    elif kind == "research similar failures":
        answer["payload"] = similar_failures({"failure_reason": target}, failures or [])
    elif kind == "research historical thesis":
        rows = [thesis_ledger(item) for item in theses or [] if not target or target.lower() in str(item).lower()]
        answer["payload"] = rows
    else:
        answer["payload"] = None
        answer["status"] = "UNKNOWN_QUERY"
    answer["produces_pick"] = False
    answer["production_boundary"] = PRODUCTION_BOUNDARY
    assert_research_only(answer)
    return answer


def research_dashboard(research: Mapping[str, Any] | None = None) -> dict[str, Any]:
    research = dict(research or {})
    scores = independent_scores(
        research.get("company_quality"),
        research.get("industry_position"),
        research.get("capital_behavior"),
        research.get("market_setup"),
        research.get("risk"),
        statistical_score=research.get("alpha_score"),
    )
    views = research.get("views") or {}
    contradiction = research.get("contradictions") or contradiction_status(views)
    return {
        "hero": [
            "Company Quality",
            "Industry Position",
            "Capital State",
            "Market Setup",
            "Risk",
            "Portfolio Exposure",
            "Historical Evidence",
        ],
        "not_a_single_total": True,
        "scores": scores,
        "convergence": contradiction.get("status"),
        "production_boundary": PRODUCTION_BOUNDARY,
    }
