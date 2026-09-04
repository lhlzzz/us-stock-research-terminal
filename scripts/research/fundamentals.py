"""Company fundamentals, SEC filings, earnings, SBC, and management delivery."""
from __future__ import annotations

from typing import Any, Mapping

from .boundary import PRODUCTION_BOUNDARY
from .evidence import claim, observed_number, unknown
from .providers import DATA_GAP

FUNDAMENTAL_FIELDS = (
    "revenue", "revenue_growth", "gross_profit", "gross_margin",
    "operating_income", "operating_margin", "net_income",
    "free_cash_flow", "operating_cash_flow", "capex",
    "roic", "roe", "roa",
    "cash", "debt", "net_debt", "interest_expense", "interest_coverage",
    "share_count", "diluted_share_count", "stock_based_compensation",
    "share_dilution", "buyback_amount", "dividend",
    "segment_revenue", "segment_margin", "geographic_revenue", "customer_concentration",
    "backlog", "bookings", "remaining_performance_obligation", "guidance",
)

SEC_FILING_TYPES = ("10-K", "10-Q", "8-K", "DEF 14A", "13D", "13G", "Form 3", "Form 4", "Form 5")

EARNINGS_FIELDS = (
    "earnings_calendar", "earnings_history", "earnings_surprise", "revenue_surprise",
    "guidance_change", "estimate_revision", "margin_change", "call_transcript_context",
)

REVISION_DIRECTIONS = ("UP", "DOWN", "FLAT", "UNKNOWN")


def _as_of(facts: Mapping[str, Any]) -> str | None:
    return str(facts.get("as_of_date") or facts.get("as_of") or "") or None


def company_fundamentals(facts: Mapping[str, Any] | None = None, provider=None) -> dict[str, Any]:
    facts = dict(facts or {})
    as_of = _as_of(facts)
    if not facts and provider is not None:
        fetched = provider.get(str(facts.get("symbol") or ""), as_of=as_of)
        if fetched.get("status") == DATA_GAP:
            return {**fetched, "layer": "company_fundamentals", "fields": {}, "data_gaps": list(FUNDAMENTAL_FIELDS), "coverage": 0.0, "produces_pick": False}
    fields = {}
    gaps = []
    for name in FUNDAMENTAL_FIELDS:
        value = observed_number(facts.get(name))
        if value is None and facts.get(name) in (None, ""):
            fields[name] = unknown("company_fundamentals", "public_quote", reason=f"{name} missing", as_of_date=as_of)
            gaps.append(name)
        elif value is not None:
            fields[name] = claim(value, semantic="OBSERVED", source="company_fundamentals", source_type="public_quote", as_of_date=as_of, evidence_refs=[name])
        else:
            fields[name] = claim(facts.get(name), semantic="OBSERVED", source="company_fundamentals", source_type="public_quote", as_of_date=as_of, evidence_refs=[name])
    coverage = round((len(FUNDAMENTAL_FIELDS) - len(gaps)) / len(FUNDAMENTAL_FIELDS), 4)
    return {
        "layer": "company_fundamentals",
        "as_of_date": as_of,
        "fields": fields,
        "data_gaps": gaps,
        "coverage": coverage,
        "status": "DATA_GAP" if gaps else "READY",
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def sec_filing(record: Mapping[str, Any] | None = None, provider=None) -> dict[str, Any]:
    record = dict(record or {})
    if provider is not None and not record:
        fetched = provider.get("", as_of=None)
        if fetched.get("status") == DATA_GAP:
            return {**fetched, "layer": "sec_filing", "supported_types": list(SEC_FILING_TYPES), "data_gaps": ["source_url", "filing_type", "filing_date", "period_end", "effective_date", "retrieved_at", "company", "ticker"], "evidence_level": "LEVEL_6", "produces_pick": False}
    filing_type = record.get("filing_type")
    known = filing_type in SEC_FILING_TYPES
    required = ("source_url", "filing_type", "filing_date", "period_end", "effective_date", "retrieved_at", "company", "ticker")
    gaps = [key for key in required if record.get(key) in (None, "")]
    return {
        "layer": "sec_filing",
        "supported_types": list(SEC_FILING_TYPES),
        "filing_type": filing_type if known else None,
        "source_url": record.get("source_url"),
        "filing_date": record.get("filing_date"),
        "period_end": record.get("period_end"),
        "effective_date": record.get("effective_date"),
        "retrieved_at": record.get("retrieved_at"),
        "company": record.get("company"),
        "ticker": record.get("ticker") or record.get("symbol"),
        "data_gaps": gaps,
        "status": "DATA_GAP" if gaps or not known else "READY",
        "evidence_level": "LEVEL_1" if not gaps and known else "LEVEL_6",
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def estimate_revision_direction(history: list[Any] | None = None) -> dict[str, Any]:
    values = [observed_number(item) for item in (history or [])]
    values = [item for item in values if item is not None]
    if len(values) < 2:
        direction = "UNKNOWN"
    else:
        diffs = [b - a for a, b in zip(values, values[1:])]
        if all(diff > 0 for diff in diffs):
            direction = "UP"
        elif all(diff < 0 for diff in diffs):
            direction = "DOWN"
        elif all(diff == 0 for diff in diffs):
            direction = "FLAT"
        else:
            direction = "UNKNOWN"
    return {
        "estimate_revision_direction": direction,
        "history": values,
        "independent_of_price": True,
        "price_up_is_not_fundamental_improvement": True,
        "semantic": "DERIVED" if direction != "UNKNOWN" else "UNKNOWN",
    }


def earnings_intelligence(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    as_of = _as_of(facts)
    fields = {}
    gaps = []
    for name in EARNINGS_FIELDS:
        if facts.get(name) in (None, ""):
            fields[name] = unknown("earnings", "public_quote", reason=f"{name} missing", as_of_date=as_of)
            gaps.append(name)
        else:
            fields[name] = claim(facts.get(name), semantic="OBSERVED", source="earnings", source_type="public_quote", as_of_date=as_of, evidence_refs=[name])
    revision = estimate_revision_direction(facts.get("eps_estimate_history") or facts.get("estimate_history"))
    price_up = bool(facts.get("price_up"))
    return {
        "layer": "earnings_intelligence",
        "as_of_date": as_of,
        "fields": fields,
        "estimate_revision_direction": revision,
        "price_up": price_up,
        "fundamental_improvement": False if price_up and revision["estimate_revision_direction"] != "UP" else revision["estimate_revision_direction"] == "UP",
        "data_gaps": gaps,
        "status": "DATA_GAP" if gaps else "READY",
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def sbc_dilution(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    gross_buyback = observed_number(facts.get("buyback_amount") or facts.get("gross_buyback"))
    sbc = observed_number(facts.get("stock_based_compensation"))
    issuance = observed_number(facts.get("share_issuance"))
    if facts.get("buyback_amount") in (None, "") and facts.get("gross_buyback") in (None, ""):
        gross_buyback = None
    present_buyback = 0.0 if gross_buyback is None else gross_buyback
    present_sbc = 0.0 if sbc is None else sbc
    present_issuance = 0.0 if issuance is None else issuance
    missing_capital = gross_buyback is None or sbc is None or issuance is None
    share_start = observed_number(facts.get("share_count_start") or facts.get("share_count"))
    share_end = observed_number(facts.get("share_count_end") or facts.get("diluted_share_count") or facts.get("share_count"))
    announced = bool(facts.get("buyback_announced") or (present_buyback > 0))
    net_return = None if missing_capital else round(present_buyback - present_sbc - present_issuance, 6)
    share_change = None if share_start in (None, 0) or share_end is None else round(share_end - share_start, 6)
    warning = announced and (share_change is None or share_change >= 0)
    return {
        "layer": "sbc_dilution",
        "gross_buyback": gross_buyback,
        "stock_based_compensation": sbc,
        "share_issuance": issuance,
        "missing_is_not_zero": True,
        "net_shareholder_capital_return": net_return,
        "net_share_count_change": share_change,
        "buyback_effectiveness": "INEFFECTIVE" if warning else "EFFECTIVE" if share_change is not None and share_change < 0 else "UNKNOWN",
        "warnings": ["BUYBACK_QUALITY_WARNING"] if warning else [],
        "status": "DATA_GAP" if share_change is None else "READY",
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def management_allocation(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    said = facts.get("management_says")
    delivered = facts.get("management_delivered")
    hits = facts.get("guidance_hits")
    revisions = facts.get("guidance_revisions")
    hit_rate = None
    revision_rate = None
    if isinstance(hits, list) and hits:
        hit_rate = round(sum(1 for item in hits if item) / len(hits), 4)
    if isinstance(revisions, list) and revisions:
        revision_rate = round(sum(1 for item in revisions if item) / len(revisions), 4)
    consistency = facts.get("capital_allocation_consistency")
    return {
        "layer": "management_capital_allocation",
        "management_track_record": facts.get("management_track_record"),
        "capital_allocation_history": facts.get("capital_allocation_history"),
        "acquisition_history": facts.get("acquisition_history"),
        "buyback_history": facts.get("buyback_history"),
        "dividend_history": facts.get("dividend_history"),
        "debt_management": facts.get("debt_management"),
        "guidance_credibility": facts.get("guidance_credibility"),
        "management_says": said,
        "management_delivered": delivered,
        "says_vs_delivered": "ALIGNED" if said and delivered and said == delivered else "SEPARATED",
        "guidance_hit_rate": hit_rate,
        "guidance_revision_rate": revision_rate,
        "capital_allocation_consistency": consistency,
        "status": "DATA_GAP" if hit_rate is None else "READY",
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
