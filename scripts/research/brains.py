"""US-adapted research contexts. Skills are evidence, never pick generators."""
from __future__ import annotations

from typing import Any, Mapping

from .boundary import PRODUCTION_BOUNDARY
from .evidence import claim, observed_number, unknown
from .metric_semantics import normalize_metric, quality_stance


LAYERS = (
    "end_market",
    "system",
    "platform",
    "equipment",
    "component",
    "subcomponent",
    "material",
    "software",
    "service",
    "infrastructure",
)

CONTEXT_STATUS = {
    "Buffett": "directly_applicable_us",
    "Serenity": "us_adapted",
    "Supply": "us_adapted",
    "PricingGap": "us_adapted",
    "FutureBuyerMap": "us_adapted",
    "Uzi": "research_only_adapter_a_share_fields_dropped",
    "TradingAgents": "research_only_adapter",
}


def _as_of(facts: Mapping[str, Any]) -> str | None:
    return str(facts.get("as_of_date") or facts.get("as_of") or "") or None


def _metric(facts: Mapping[str, Any], key: str, *, source: str, source_type: str = "public_quote") -> dict[str, Any]:
    value = observed_number(facts.get(key))
    if value is None:
        return unknown(source, source_type, reason=f"{key} unavailable", as_of_date=_as_of(facts))
    return claim(
        value,
        semantic="OBSERVED",
        source=source,
        source_type=source_type,
        as_of_date=_as_of(facts),
        evidence_refs=[key],
    )


def _stance(score: float | None) -> str:
    return quality_stance(score)


def build_buffett_context(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Company quality from public fields. Missing statements stay UNKNOWN."""
    facts = dict(facts or {})
    source = str(facts.get("source") or "eastmoney_us")
    as_of = _as_of(facts)
    roe = _metric(facts, "roe", source=source)
    pe = _metric(facts, "pe_ttm", source=source)
    dividend = _metric(facts, "dividend_yield", source=source)
    debt = _metric(facts, "debt_to_equity", source=source)
    fcf = _metric(facts, "free_cash_flow", source=source)
    observed = [item for item in (roe, pe, dividend) if item["semantic"] == "OBSERVED"]
    quality_score = None
    if observed:
        scores = []
        roe_n = normalize_metric("roe", roe["value"])
        if roe_n is not None:
            scores.append(roe_n)
        pe_n = normalize_metric("pe_ttm", pe["value"])
        if pe_n is not None:
            scores.append(pe_n)
        div_n = normalize_metric("dividend_yield", dividend["value"])
        if div_n is not None:
            scores.append(div_n)
        quality_score = round(sum(scores) / len(scores), 4) if scores else None
    quality = claim(
        quality_score,
        semantic="DERIVED" if quality_score is not None else "UNKNOWN",
        source="buffett_quality",
        source_type="skill",
        as_of_date=as_of,
        evidence_refs=["roe", "pe_ttm", "dividend_yield"],
        reason=None if quality_score is not None else "insufficient public financial fields",
    )
    return {
        "context_type": "BuffettContext",
        "status": PRODUCTION_BOUNDARY["status"],
        "adaptation": CONTEXT_STATUS["Buffett"],
        "produces_pick": False,
        "as_of_date": as_of,
        "buffett_quality": quality,
        "buffett_moat": unknown("buffett_moat", "skill", reason="moat requires filings, not inferred from quotes", as_of_date=as_of),
        "buffett_management": unknown("buffett_management", "skill", reason="management quality not in quote fields", as_of_date=as_of),
        "buffett_financial_quality": roe,
        "buffett_capital_allocation": unknown("buffett_capital_allocation", "skill", reason="capital allocation needs cash-flow statements", as_of_date=as_of),
        "buffett_valuation": pe,
        "buffett_risk": debt if debt["semantic"] != "UNKNOWN" else unknown("buffett_risk", "skill", reason="leverage unavailable", as_of_date=as_of),
        "buffett_industry_fit": claim(
            facts.get("sector") or None,
            semantic="OBSERVED" if facts.get("sector") else "UNKNOWN",
            source="universe.sector",
            source_type="market_research",
            as_of_date=as_of,
            evidence_refs=["sector"],
        ),
        "cash_flow": fcf,
        "dividend_yield": dividend,
        "stance": _stance(quality_score),
        "unknown_fields": [
            key for key, item in (
                ("moat", None),
                ("management", None),
                ("capital_allocation", None),
                ("free_cash_flow", fcf),
                ("debt_to_equity", debt),
            )
            if item is None or item.get("semantic") == "UNKNOWN"
        ],
        "boundary": PRODUCTION_BOUNDARY,
    }


def build_serenity_context(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Industry / value-chain / chokepoint context. Never a pick."""
    facts = dict(facts or {})
    as_of = _as_of(facts)
    layers = {layer: facts.get(layer) or facts.get("layers", {}).get(layer) for layer in LAYERS}
    known_layers = {layer: value for layer, value in layers.items() if value}
    bottleneck = facts.get("bottleneck") or facts.get("scarce_layer")
    substitution_cost = facts.get("substitution_cost")
    certification = facts.get("certification_barrier")
    know_how = facts.get("know_how_barrier")
    capacity = facts.get("capacity_barrier")
    repricing = facts.get("repricing")
    candidates = list(facts.get("chokepoint_candidates") or facts.get("candidates") or [])
    evidence_refs = list(facts.get("evidence_refs") or [])
    confidence = observed_number(facts.get("confidence"))
    if not known_layers and not bottleneck:
        bottleneck_claim = unknown("serenity", "skill", reason="no value-chain evidence", as_of_date=as_of)
        stance = "UNKNOWN"
        confidence_claim = unknown("serenity", "skill", reason="no evidence", as_of_date=as_of)
    else:
        bottleneck_claim = claim(
            bottleneck,
            semantic="INFERRED" if bottleneck else "UNKNOWN",
            source="serenity",
            source_type="skill",
            as_of_date=as_of,
            confidence=confidence,
            evidence_refs=evidence_refs,
            reason=None if bottleneck else "layers present but scarce layer not evidenced",
        )
        stance = "BULLISH" if bottleneck and evidence_refs else "NEUTRAL" if known_layers else "UNKNOWN"
        confidence_claim = claim(
            confidence,
            semantic="INFERRED" if confidence is not None else "UNKNOWN",
            source="serenity",
            source_type="skill",
            as_of_date=as_of,
            evidence_refs=evidence_refs,
        )
    return {
        "context_type": "SerenityContext",
        "status": PRODUCTION_BOUNDARY["status"],
        "adaptation": CONTEXT_STATUS["Serenity"],
        "produces_pick": False,
        "as_of_date": as_of,
        "industry": facts.get("industry") or facts.get("sector"),
        "end_market": layers["end_market"],
        "layers": {layer: layers[layer] for layer in LAYERS},
        "bottleneck": bottleneck_claim,
        "critical_dependencies": list(facts.get("critical_dependencies") or []),
        "chokepoint_candidates": candidates,
        "company_implications": list(facts.get("company_implications") or []),
        "substitution_cost": claim(
            substitution_cost,
            semantic="INFERRED" if substitution_cost is not None else "UNKNOWN",
            source="serenity",
            source_type="skill",
            as_of_date=as_of,
            evidence_refs=evidence_refs,
        ),
        "barriers": {
            "certification": certification,
            "know_how": know_how,
            "supply_chain": facts.get("supply_chain_barrier"),
            "capacity": capacity,
        },
        "repricing": claim(
            repricing,
            semantic="INFERRED" if repricing is not None else "UNKNOWN",
            source="serenity",
            source_type="skill",
            as_of_date=as_of,
            evidence_refs=evidence_refs,
        ),
        "questions": {
            "what_is_scarce": bottleneck or "UNKNOWN",
            "who_controls_bottleneck": facts.get("controller") or "UNKNOWN",
            "why_hard_to_replace": facts.get("why_hard_to_replace") or "UNKNOWN",
            "substitution_cost": substitution_cost if substitution_cost is not None else "UNKNOWN",
            "barriers": {
                "certification": certification or "UNKNOWN",
                "know_how": know_how or "UNKNOWN",
                "supply_chain": facts.get("supply_chain_barrier") or "UNKNOWN",
                "capacity": capacity or "UNKNOWN",
            },
            "being_repriced": repricing if repricing is not None else "UNKNOWN",
        },
        "industry_context": facts.get("industry") or facts.get("sector"),
        "confidence": confidence_claim,
        "evidence_refs": evidence_refs,
        "stance": stance,
        "boundary": PRODUCTION_BOUNDARY,
    }


def build_supply_context(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    as_of = _as_of(facts)
    constraint = facts.get("supply_constraint")
    return {
        "context_type": "SupplyContext",
        "status": PRODUCTION_BOUNDARY["status"],
        "adaptation": CONTEXT_STATUS["Supply"],
        "produces_pick": False,
        "as_of_date": as_of,
        "supply_constraint": claim(
            constraint,
            semantic="INFERRED" if constraint is not None else "UNKNOWN",
            source="supply_chain",
            source_type="skill",
            as_of_date=as_of,
            evidence_refs=list(facts.get("evidence_refs") or []),
        ),
        "lead_time": facts.get("lead_time"),
        "capacity": facts.get("capacity"),
        "customers": list(facts.get("customers") or []),
        "boundary": PRODUCTION_BOUNDARY,
    }


def build_pricing_gap_context(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    as_of = _as_of(facts)
    gap = observed_number(facts.get("pricing_gap") or facts.get("gap"))
    return {
        "context_type": "PricingGapContext",
        "status": PRODUCTION_BOUNDARY["status"],
        "adaptation": CONTEXT_STATUS["PricingGap"],
        "produces_pick": False,
        "as_of_date": as_of,
        "price": observed_number(facts.get("price")),
        "pricing_gap": claim(
            gap,
            semantic="DERIVED" if gap is not None else "UNKNOWN",
            source="pricing_gap",
            source_type="skill",
            as_of_date=as_of,
        ),
        "attention": facts.get("attention"),
        "boundary": PRODUCTION_BOUNDARY,
    }


def build_future_buyer_map(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """US buyer map. A-share LHB / main-force rows are dropped, not inferred."""
    facts = dict(facts or {})
    as_of = _as_of(facts)
    buyers = []
    for item in facts.get("future_buyers") or []:
        if not isinstance(item, Mapping):
            continue
        status = str(item.get("evidence_status") or item.get("status") or "UNKNOWN").upper()
        if status not in {"OBSERVED", "EVIDENCE_BACKED"}:
            status = "UNKNOWN"
        if not item.get("evidence") or not item.get("source") or not item.get("observed_at"):
            status = "UNKNOWN"
        if status == "UNKNOWN":
            continue
        buyers.append(dict(item, evidence_status=status))
    return {
        "context_type": "FutureBuyerMap",
        "status": PRODUCTION_BOUNDARY["status"],
        "adaptation": CONTEXT_STATUS["FutureBuyerMap"],
        "produces_pick": False,
        "as_of_date": as_of,
        "buyer_categories": [
            "institutions", "mutual_funds", "ETF/index", "quant",
            "retail", "industry_capital",
        ],
        "observed_buyers": buyers,
        "future_buyer_capacity": None if not buyers else max(
            (observed_number(item.get("capacity")) or 0.0) for item in buyers
        ),
        "dropped_a_share_fields": ("lhb", "main_force", "hot_money", "seat_behavior"),
        "boundary": PRODUCTION_BOUNDARY,
    }


def build_uzi_adapter(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Research-only US adapter. Dragon-tiger / main-force fields are A-share only."""
    facts = dict(facts or {})
    return {
        "context_type": "UziAdapter",
        "status": PRODUCTION_BOUNDARY["status"],
        "adaptation": CONTEXT_STATUS["Uzi"],
        "produces_pick": False,
        "enters_production_ranking": False,
        "as_of_date": _as_of(facts),
        "usable": {
            "dilution_risk": facts.get("dilution_risk"),
            "short_interest": facts.get("short_interest"),
            "liquidity": facts.get("liquidity"),
            "news_red_flags": facts.get("news_red_flags"),
        },
        "a_share_only_deleted": ("lhb", "main_force_flow", "hot_money_flow", "seat_behavior"),
        "boundary": PRODUCTION_BOUNDARY,
    }


def build_tradingagents_adapter(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    return {
        "context_type": "TradingAgentsAdapter",
        "status": PRODUCTION_BOUNDARY["status"],
        "adaptation": CONTEXT_STATUS["TradingAgents"],
        "produces_pick": False,
        "enters_production_ranking": False,
        "as_of_date": _as_of(facts),
        "bull_thesis": facts.get("bull_thesis"),
        "bear_thesis": facts.get("bear_thesis"),
        "missing_evidence": list(facts.get("missing_evidence") or []),
        "boundary": PRODUCTION_BOUNDARY,
    }
