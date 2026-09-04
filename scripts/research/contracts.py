"""Xiaomei 2.0 four-brain contracts. Research quality is never alpha."""
from __future__ import annotations

from typing import Any, Mapping

from .boundary import PRODUCTION_BOUNDARY
from .evidence import claim, observed_number, unknown
from .metric_semantics import quality_stance, risk_stance, score_from_claims

COMPANY_QUALITY_FIELDS = (
    "business_quality",
    "economic_moat",
    "pricing_power",
    "reinvestment_runway",
    "management_quality",
    "capital_allocation",
    "financial_quality",
    "balance_sheet_quality",
    "cashflow_quality",
    "shareholder_dilution",
    "sbc_quality",
    "buyback_quality",
    "valuation_quality",
)

INDUSTRY_POSITION_FIELDS = (
    "industry_attractiveness",
    "industry_growth",
    "supply_chain_position",
    "chokepoint_strength",
    "switching_cost",
    "customer_dependency",
    "supplier_dependency",
    "capacity_constraint",
    "certification_barrier",
    "replacement_difficulty",
    "competitive_intensity",
)

CAPITAL_BEHAVIOR_FIELDS = (
    "capital_behavior_score",
    "capital_state",
    "capital_intent",
    "pressure",
    "absorption",
    "price_control",
    "control_asymmetry",
    "distribution",
    "trap",
)

MARKET_SETUP_FIELDS = (
    "trend",
    "momentum",
    "relative_strength",
    "volume",
    "volatility",
    "breakout",
    "reversal",
    "market_regime",
    "sector_regime",
)

RISK_FIELDS = ("gap_risk", "drawdown_risk", "liquidity_risk", "event_risk", "short_pressure")
PORTFOLIO_CONTEXT_FIELDS = (
    "already_owned",
    "same_value_chain",
    "same_theme",
    "concentration",
    "missing_layer",
)
HISTORICAL_EVIDENCE_FIELDS = ("analogue_count", "failure_count", "win_rate", "thesis_failures")

BRAIN_OWNERS = {
    "Buffett": "Company Research",
    "Serenity": "Industry Research",
    "Capital": "Market Capital Behavior",
    "Quant": "Statistical Validation",
    "Obsidian": "Memory",
    "PostgreSQL": "Structured Facts",
}

FROZEN_SELF_EVOLVE = (
    "Buffett principles",
    "Serenity ontology",
    "fact/inference semantics",
    "evidence hierarchy",
    "no-lookahead rules",
    "production safety boundary",
)

ALLOWED_SELF_EVOLVE = (
    "weights",
    "thresholds",
    "ranking contributions",
    "confidence calibration",
    "research prioritization",
)

HORIZONS = ("LONG_TERM", "MEDIUM_TERM", "SHORT_TERM", "EVENT_TERM")
HORIZON_OWNERS = {
    "LONG_TERM": "Company Quality",
    "MEDIUM_TERM": "Industry",
    "SHORT_TERM": "Capital Behavior / Market Setup",
    "EVENT_TERM": "Earnings/Catalyst",
}

MATRIX_LABELS = ("STRONG", "WEAK", "NEUTRAL", "UNKNOWN")


def _as_of(facts: Mapping[str, Any]) -> str | None:
    return str(facts.get("as_of_date") or facts.get("as_of") or "") or None


def _score_from_claims(
    claims: Mapping[str, Mapping[str, Any]],
    *,
    purpose: str = "quality",
) -> tuple[float | None, float | None, list[str]]:
    return score_from_claims(claims, purpose=purpose)


def _dimension(facts: Mapping[str, Any], key: str, *, source: str, source_type: str, semantic: str = "OBSERVED") -> dict[str, Any]:
    as_of = _as_of(facts)
    raw = facts.get(key)
    number = observed_number(raw)
    if number is not None:
        return claim(number, semantic=semantic, source=source, source_type=source_type, as_of_date=as_of, evidence_refs=[key])
    if raw not in (None, ""):
        return claim(raw, semantic=semantic, source=source, source_type=source_type, as_of_date=as_of, evidence_refs=[key])
    return unknown(source, source_type, reason=f"{key} unavailable", as_of_date=as_of)


def brain_payload(
    name: str,
    fields: tuple[str, ...],
    facts: Mapping[str, Any] | None,
    *,
    source: str,
    source_type: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    facts = dict(facts or {})
    as_of = _as_of(facts)
    dimensions = {field: _dimension(facts, field, source=source, source_type=source_type) for field in fields}
    purpose = "risk" if name == "risk" else "quality"
    score, confidence, gaps = _score_from_claims(dimensions, purpose=purpose)
    payload = {
        "schema": name,
        "as_of_date": as_of,
        "score": score,
        "confidence": confidence,
        "evidence": dimensions,
        "data_gaps": gaps,
        "produces_pick": False,
        "enters_alpha_score": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
    if extra:
        payload.update(dict(extra))
    return payload


def company_quality(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = brain_payload("company_quality", COMPANY_QUALITY_FIELDS, facts, source="buffett", source_type="skill")
    payload["horizon"] = "LONG_TERM"
    payload["owner"] = "Buffett"
    return payload


def industry_position(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = brain_payload("industry_position", INDUSTRY_POSITION_FIELDS, facts, source="serenity", source_type="skill")
    payload["horizon"] = "MEDIUM_TERM"
    payload["owner"] = "Serenity"
    return payload


def capital_behavior(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    forbidden = ("company_quality", "industry_position", "statistical_score")
    cleaned = {key: value for key, value in facts.items() if key not in forbidden}
    payload = brain_payload(
        "capital_behavior",
        CAPITAL_BEHAVIOR_FIELDS,
        cleaned,
        source="capital_brain",
        source_type="capital_brain",
    )
    payload["horizon"] = "SHORT_TERM"
    payload["owner"] = "Capital"
    payload["mixed_into"] = []
    payload["score"] = observed_number(cleaned.get("capital_behavior_score") or cleaned.get("capital_score")) or payload["score"]
    payload["enters_alpha_score"] = False
    return payload


def market_setup(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = brain_payload("market_setup", MARKET_SETUP_FIELDS, facts, source="market_brain", source_type="public_ohlcv")
    payload["horizon"] = "SHORT_TERM"
    payload["owner"] = "Market"
    return payload


def risk_view(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = brain_payload("risk", RISK_FIELDS, facts, source="risk_brain", source_type="market_research")
    payload["horizon"] = "EVENT_TERM"
    stance = risk_stance(payload.get("score"))
    payload["risk_level"] = stance["risk_level"]
    payload["stance"] = stance["stance"]
    payload["stance_alias"] = stance["stance_alias"]
    payload["higher_is_worse"] = True
    return payload


def portfolio_context_schema(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = brain_payload(
        "portfolio_context",
        PORTFOLIO_CONTEXT_FIELDS,
        facts,
        source="obsidian",
        source_type="personal_portfolio",
    )
    payload["enters_alpha_score"] = False
    payload["market_alpha_adjustment"] = 0
    return payload


def historical_evidence(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return brain_payload(
        "historical_evidence",
        HISTORICAL_EVIDENCE_FIELDS,
        facts,
        source="tickets",
        source_type="ticket",
    )


def independent_scores(
    company: Mapping[str, Any] | None = None,
    industry: Mapping[str, Any] | None = None,
    capital: Mapping[str, Any] | None = None,
    market: Mapping[str, Any] | None = None,
    risk: Mapping[str, Any] | None = None,
    statistical_score: float | None = None,
) -> dict[str, Any]:
    company_score = None if not company else observed_number(company.get("score"))
    industry_score = None if not industry else observed_number(industry.get("score"))
    capital_score = None if not capital else observed_number(capital.get("score") or capital.get("capital_behavior_score"))
    market_score = None if not market else observed_number(market.get("score"))
    risk_score = None if not risk else observed_number(risk.get("score"))
    research_values = [value for value in (company_score, industry_score, capital_score, market_score) if value is not None]
    research_composite = round(sum(research_values) / len(research_values), 4) if research_values else None
    alpha = observed_number(statistical_score)
    risk_payload = risk_stance(risk_score)
    brain_total = 4
    brain_count = len(research_values)
    coverage = round(brain_count / brain_total, 4)
    if brain_count == 0:
        readiness = "DATA_GAP"
    elif brain_count < brain_total:
        readiness = "PARTIAL"
    else:
        readiness = "READY"
    return {
        "company_quality_score": company_score,
        "industry_position_score": industry_score,
        "capital_behavior_score": capital_score,
        "market_setup_score": market_score,
        "risk_score": risk_score,
        "quality": {"score": company_score, "stance": quality_stance(company_score)},
        "risk": risk_payload,
        "research_composite": research_composite,
        "score": research_composite,
        "coverage": coverage,
        "brain_count": brain_count,
        "brain_total": brain_total,
        "readiness": readiness,
        "alpha_score": alpha,
        "research_composite_is_not_alpha": True,
        "long_term_quality": company_score,
        "industry_edge": industry_score,
        "capital_edge": capital_score,
        "short_term_edge": market_score,
        "not_a_single_total": True,
        "not_fully_validated": readiness != "READY",
        "production_boundary": PRODUCTION_BOUNDARY,
    }


BRAIN_READY = "READY"
BRAIN_PARTIAL = "PARTIAL"
BRAIN_DATA_GAP = "DATA_GAP"
BRAIN_VALIDATION_GAP = "VALIDATION_GAP"
BRAIN_BLOCKED = "BLOCKED"


def _brain_status(view: Mapping[str, Any] | None) -> str:
    if not view:
        return BRAIN_DATA_GAP
    status = str(view.get("status") or view.get("readiness") or "").upper()
    if status in {BRAIN_READY, BRAIN_PARTIAL, BRAIN_DATA_GAP, BRAIN_VALIDATION_GAP, BRAIN_BLOCKED}:
        return status
    if view.get("blocked") or view.get("status") == "BLOCKED":
        return BRAIN_BLOCKED
    score = observed_number(view.get("score") or view.get("capital_behavior_score"))
    gaps = list(view.get("data_gaps") or [])
    if score is None and not gaps and view.get("semantic") == "UNKNOWN":
        return BRAIN_DATA_GAP
    if score is None:
        return BRAIN_DATA_GAP
    if gaps:
        return BRAIN_PARTIAL
    return BRAIN_PARTIAL if view.get("validation_status") in (None, "", "VALIDATION_GAP", "UNVALIDATED") else BRAIN_READY


def brain_readiness(
    company: Mapping[str, Any] | None = None,
    industry: Mapping[str, Any] | None = None,
    capital: Mapping[str, Any] | None = None,
    statistical: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    brains = {
        "Company": _brain_status(company),
        "Industry": _brain_status(industry),
        "Capital": _brain_status(capital),
        "Statistical": _brain_status(statistical),
    }
    ready = sum(1 for status in brains.values() if status == BRAIN_READY)
    if any(status == BRAIN_BLOCKED for status in brains.values()):
        overall = BRAIN_BLOCKED
    elif ready == 4:
        overall = BRAIN_READY
    elif all(status == BRAIN_DATA_GAP for status in brains.values()):
        overall = BRAIN_DATA_GAP
    elif any(status == BRAIN_VALIDATION_GAP for status in brains.values()) and ready == 0:
        overall = BRAIN_VALIDATION_GAP
    else:
        overall = BRAIN_PARTIAL
    return {
        "brains": brains,
        "overall": overall,
        "ready_count": ready,
        "brain_total": 4,
        "allows_partial_research": True,
        "does_not_require_all_ready": True,
    }


def research_horizon_contract(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    horizon = str(facts.get("research_horizon") or "LONG_TERM").upper()
    if horizon not in HORIZONS:
        horizon = "LONG_TERM"
    return {
        "as_of": _as_of(facts),
        "research_horizon": horizon,
        "expected_holding_period": facts.get("expected_holding_period"),
        "catalyst_horizon": facts.get("catalyst_horizon"),
        "invalidation_horizon": facts.get("invalidation_horizon"),
        "forbids_long_term_as_t1": True,
        "owner": HORIZON_OWNERS[horizon],
    }


def lineage_status(*, source: str, feature: str, source_date: str | None, effective_date: str | None, as_of_date: str | None, brain: str) -> dict[str, Any]:
    as_of = str(as_of_date or "")[:10]
    effective = str(effective_date or source_date or "")[:10]
    blocked = bool(effective and as_of and effective > as_of)
    return {
        "decision": "BLOCK" if blocked else "PASS",
        "brain": brain,
        "feature": feature,
        "source": source,
        "source_date": source_date,
        "effective_date": effective_date,
        "as_of_date": as_of_date,
        "rule": "effective_date <= as_of_date",
        "status": "BLOCK" if blocked else "OK",
    }
