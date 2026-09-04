"""Persisted industry graph, chokepoints, memory, and research universes."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from .boundary import PRODUCTION_BOUNDARY

ENTITY_TYPES = (
    "industry", "system", "platform", "equipment", "module", "component",
    "material", "software", "service", "infrastructure", "company",
)
RELATION_TYPES = (
    "supplies", "depends_on", "competes_with", "enables", "replaces",
    "bottlenecks", "certified_by", "capacity_constrained",
)
CHOKEPOINT_STATUSES = ("EMERGING", "CONFIRMED", "STRESSED", "RELAXING", "BROKEN")
UNIVERSES = {
    "CORE_UNIVERSE": "nasdaq100_sp500_union",
    "INDUSTRY_DISCOVERY_UNIVERSE": "industry_discovery",
    "CHOKEPOINT_UNIVERSE": "chokepoint_discovery",
}
PORTFOLIO_RELATIONS = (
    "same_value_chain", "same_theme", "supplier_relationship",
    "customer_relationship", "substitute_relationship",
)


def empty_graph() -> dict[str, Any]:
    return {"entities": [], "relations": [], "as_of_date": None, "status": "DATA_GAP"}


def persist_industry_graph(
    previous: Mapping[str, Any] | None,
    *,
    entities: Iterable[Mapping[str, Any]] | None = None,
    relations: Iterable[Mapping[str, Any]] | None = None,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    graph = {
        "entities": [dict(item) for item in (previous or {}).get("entities") or []],
        "relations": [dict(item) for item in (previous or {}).get("relations") or []],
        "as_of_date": as_of_date or (previous or {}).get("as_of_date"),
    }
    seen_entities = {(item.get("type"), item.get("id") or item.get("name")) for item in graph["entities"]}
    for entity in entities or []:
        kind = entity.get("type")
        if kind not in ENTITY_TYPES:
            continue
        key = (kind, entity.get("id") or entity.get("name"))
        if key in seen_entities:
            for existing in graph["entities"]:
                if (existing.get("type"), existing.get("id") or existing.get("name")) == key:
                    existing.update(dict(entity))
                    break
            continue
        graph["entities"].append(dict(entity))
        seen_entities.add(key)
    seen_relations = {(item.get("type"), item.get("src"), item.get("dst")) for item in graph["relations"]}
    for relation in relations or []:
        kind = relation.get("type")
        if kind not in RELATION_TYPES:
            continue
        key = (kind, relation.get("src"), relation.get("dst"))
        if key in seen_relations:
            continue
        graph["relations"].append(dict(relation))
        seen_relations.add(key)
    graph["status"] = "READY" if graph["entities"] else "DATA_GAP"
    graph["produces_pick"] = False
    graph["production_boundary"] = PRODUCTION_BOUNDARY
    return graph


def update_industry_memory(previous: Mapping[str, Any] | None, new_evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    previous = dict(previous or {})
    evidence = dict(new_evidence or {})
    graph = persist_industry_graph(previous.get("graph"), entities=evidence.get("entities"), relations=evidence.get("relations"), as_of_date=evidence.get("as_of_date"))
    notes = list(previous.get("notes") or [])
    if evidence.get("note"):
        notes.append(evidence["note"])
    return {
        "layer": "industry_memory",
        "graph": graph,
        "notes": notes,
        "updated": bool(new_evidence),
        "rezeroed": False,
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def chokepoint_record(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    status = str(facts.get("status") or "EMERGING").upper()
    if status not in CHOKEPOINT_STATUSES:
        status = "EMERGING"
    required = (
        "industry", "layer", "company", "product", "dependency", "substitutability",
        "switching_cost", "qualification_time", "capacity", "market_share",
        "customer_dependency", "evidence", "confidence",
    )
    gaps = [key for key in required if facts.get(key) in (None, "")]
    return {
        "schema": "chokepoint",
        **{key: facts.get(key) for key in required},
        "status": status,
        "data_gaps": gaps,
        "coverage_status": "DATA_GAP" if gaps else "READY",
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def research_universes(*, core: Iterable[str] | None = None, industry: Iterable[str] | None = None, chokepoint: Iterable[str] | None = None) -> dict[str, Any]:
    return {
        "CORE_UNIVERSE": sorted({str(item).upper() for item in core or []}),
        "INDUSTRY_DISCOVERY_UNIVERSE": sorted({str(item).upper() for item in industry or []}),
        "CHOKEPOINT_UNIVERSE": sorted({str(item).upper() for item in chokepoint or []}),
        "rules": {
            "CORE_UNIVERSE": "default research; production ranking universe remains nasdaq100_sp500_union",
            "INDUSTRY_DISCOVERY_UNIVERSE": "expand when industry changes",
            "CHOKEPOINT_UNIVERSE": "auto-watch when Serenity finds a key node",
        },
        "sources": ("Russell 2000", "industry sets", "supplier/customer", "ETF constituents", "Serenity discovery"),
        "does_not_replace_production_universe": True,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def supply_chain_portfolio(
    holdings: Iterable[str] | None = None,
    graph: Mapping[str, Any] | None = None,
    symbol: str | None = None,
) -> dict[str, Any]:
    owned = [str(item).upper() for item in holdings or []]
    relations = []
    for edge in (graph or {}).get("relations") or []:
        if edge.get("type") not in RELATION_TYPES:
            continue
        src = str(edge.get("src") or "").upper()
        dst = str(edge.get("dst") or "").upper()
        if symbol and symbol.upper() not in {src, dst} and src not in owned and dst not in owned:
            continue
        kind = {
            "supplies": "supplier_relationship",
            "depends_on": "customer_relationship",
            "competes_with": "substitute_relationship",
            "replaces": "substitute_relationship",
            "enables": "same_theme",
            "bottlenecks": "same_value_chain",
            "certified_by": "same_value_chain",
            "capacity_constrained": "same_value_chain",
        }.get(edge.get("type"), "same_theme")
        relations.append({"type": kind, "src": src, "dst": dst})
    layers = {item.get("type") for item in (graph or {}).get("entities") or [] if item.get("type") in ENTITY_TYPES}
    missing = [layer for layer in ("component", "equipment", "material") if layer not in layers]
    return {
        "context_type": "PORTFOLIO_SUPPLY_CHAIN",
        "owned": owned,
        "relations": relations,
        "questions": {
            "current_exposure": owned,
            "missing_layers": missing,
            "better_chokepoint": None,
            "duplicate_risk": len(owned) > 1 and any(item["type"] == "same_value_chain" for item in relations),
        },
        "enters_alpha_score": False,
        "market_alpha_adjustment": 0,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def portfolio_risk_graph(
    holdings: Iterable[str] | None = None,
    *,
    industries: Mapping[str, str] | None = None,
    themes: Mapping[str, str] | None = None,
    graph: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    owned = [str(item).upper() for item in holdings or []]
    industries = {str(k).upper(): v for k, v in dict(industries or {}).items()}
    themes = {str(k).upper(): v for k, v in dict(themes or {}).items()}
    theme_counts: dict[str, list[str]] = {}
    industry_counts: dict[str, list[str]] = {}
    for symbol in owned:
        theme = themes.get(symbol) or "UNKNOWN"
        industry = industries.get(symbol) or "UNKNOWN"
        theme_counts.setdefault(theme, []).append(symbol)
        industry_counts.setdefault(industry, []).append(symbol)
    common_themes = {name: symbols for name, symbols in theme_counts.items() if len(symbols) > 1 and name != "UNKNOWN"}
    common_industries = {name: symbols for name, symbols in industry_counts.items() if len(symbols) > 1 and name != "UNKNOWN"}
    return {
        "layer": "portfolio_risk_graph",
        "path": ("Portfolio", "Company", "Industry", "Theme", "Supply Chain", "Common Risk"),
        "holdings": owned,
        "industries": industry_counts,
        "themes": theme_counts,
        "common_risk": {
            "themes": common_themes,
            "industries": common_industries,
            "chokepoints": [
                edge for edge in (graph or {}).get("relations") or []
                if edge.get("type") in {"bottlenecks", "capacity_constrained"}
            ],
        },
        "surface_count": len(owned),
        "concentrated": bool(common_themes or common_industries),
        "enters_alpha_score": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
