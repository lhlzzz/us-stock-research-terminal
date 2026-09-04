"""Compose three brains + memory into one research decision. Never a pick."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

from capital.case_retrieval import retrieve_similar_cases
from .boundary import PRODUCTION_BOUNDARY, validate
from .evidence import highest_evidence_quality
from .metric_semantics import capital_stance, market_stance, quality_stance, research_median, risk_stance
from .brains import (
    build_buffett_context,
    build_future_buyer_map,
    build_pricing_gap_context,
    build_serenity_context,
    build_supply_context,
    build_tradingagents_adapter,
    build_uzi_adapter,
)
from .contracts import (
    brain_readiness,
    capital_behavior,
    company_quality,
    historical_evidence,
    independent_scores,
    industry_position,
    lineage_status,
    market_setup,
    research_horizon_contract,
    risk_view,
)
from .coverage import research_coverage, research_readiness
from .fundamentals import (
    company_fundamentals,
    earnings_intelligence,
    management_allocation,
    sbc_dilution,
    sec_filing,
)
from .failure import previous_failure_warning
from .industry import persist_industry_graph, portfolio_risk_graph, supply_chain_portfolio, update_industry_memory
from .market_context import analyst_revision, options_intelligence, short_intelligence
from .memory import portfolio_context
from .outcomes import independent_price_outcomes
from .regime import classify_research_regime, earnings_regime
from .thesis import compare_thesis, failure_case, research_failure_lifecycle, thesis_ledger


STANCE_RANK = {
    "STRONG": 2,
    "BULLISH": 1,
    "FAVORABLE": 1,
    "LOW_RISK": 1,
    "NEUTRAL": 0,
    "WEAK": -1,
    "BEARISH": -2,
    "CAUTION": -2,
    "HIGH_RISK": -2,
    "UNKNOWN": None,
}


def _stance(view: Mapping[str, Any] | None, *, purpose: str = "quality") -> str:
    if not view:
        return "UNKNOWN"
    if view.get("stance") and purpose != "risk":
        return str(view["stance"]).upper()
    if purpose == "risk" and view.get("stance") in {"CAUTION", "FAVORABLE", "HIGH_RISK", "LOW_RISK", "NEUTRAL", "UNKNOWN"}:
        return str(view["stance"]).upper()
    score = view.get("capital_behavior_score") or view.get("capital_quality") or view.get("score")
    if score is None:
        return "UNKNOWN"
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if purpose == "risk":
        return str(risk_stance(value)["stance"])
    if purpose == "capital":
        return capital_stance(value)
    if purpose == "market":
        return market_stance(value)
    return quality_stance(value)


def _label(stance: str) -> str:
    if stance in {"STRONG", "BULLISH", "FAVORABLE", "LOW_RISK"}:
        return "STRONG"
    if stance in {"WEAK", "BEARISH", "CAUTION", "HIGH_RISK"}:
        return "WEAK"
    if stance == "NEUTRAL":
        return "NEUTRAL"
    return "UNKNOWN"


def contradiction_status(views: Mapping[str, str], claims: Any = None) -> dict[str, Any]:
    usable = {name: stance for name, stance in views.items() if stance and stance != "UNKNOWN"}
    if len(usable) < 2:
        return {
            "status": "UNKNOWN",
            "views": dict(views),
            "summary": "insufficient overlapping evidence",
            "why_conflict": "insufficient overlapping evidence",
            "highest_evidence_quality": highest_evidence_quality(claims),
            "timescale_mismatch": False,
            "missing_data": [name for name, stance in views.items() if stance in (None, "", "UNKNOWN")],
            "not_a_score": True,
            "not_averaged": True,
        }
    signs = [STANCE_RANK.get(stance, 0) or 0 for stance in usable.values()]
    if all(value > 0 for value in signs) or all(value < 0 for value in signs) or all(value == 0 for value in signs):
        status = "CONVERGENCE"
    elif any(value > 0 for value in signs) and any(value < 0 for value in signs):
        status = "DIVERGENCE"
    else:
        status = "UNRESOLVED"
    lines = [f"{name}: {stance}" for name, stance in views.items()]
    narrative = []
    if views.get("fundamental") in {"STRONG", "BULLISH"} or views.get("company") in {"STRONG", "BULLISH"}:
        narrative.append("优秀公司")
    if views.get("industry") in {"STRONG", "BULLISH"}:
        narrative.append("优秀产业链")
    if views.get("capital") in {"WEAK", "BEARISH", "UNKNOWN"}:
        narrative.append("短期资金行为未确认")
    if views.get("statistical") in {"STRONG", "BULLISH"} or views.get("market") in {"STRONG", "BULLISH"}:
        narrative.append("统计 setup 偏强")
    if views.get("options") in {"WEAK", "BEARISH"}:
        narrative.append("期权定位偏空")
    if views.get("portfolio") in {"WEAK", "BEARISH", "OVERWEIGHT"}:
        narrative.append("组合已超配")
    long_pos = any(views.get(name) in {"STRONG", "BULLISH"} for name in ("fundamental", "company", "industry"))
    short_neg = any(views.get(name) in {"WEAK", "BEARISH"} for name in ("capital", "market", "options"))
    return {
        "status": status,
        "views": dict(views),
        "lines": lines,
        "summary": " + ".join(narrative) if narrative else status,
        "why_conflict": "brains disagree across time scales" if status == "DIVERGENCE" else None,
        "highest_evidence_quality": highest_evidence_quality(claims),
        "timescale_mismatch": bool(long_pos and short_neg),
        "missing_data": [name for name, stance in views.items() if stance in (None, "", "UNKNOWN")],
        "not_a_score": True,
        "not_averaged": True,
    }


def research_decision_matrix(views: Mapping[str, str]) -> dict[str, Any]:
    rows = {}
    aliases = {"company": ("company", "fundamental"), "market": ("market", "statistical")}
    for name in ("company", "industry", "capital", "market", "risk"):
        value = "UNKNOWN"
        for key in aliases.get(name, (name,)):
            if views.get(key) not in (None, "", "UNKNOWN"):
                value = str(views[key])
                break
        rows[name] = _label(value)
    unknown = sum(1 for value in rows.values() if value == "UNKNOWN")
    divergence = len({value for value in rows.values() if value in {"STRONG", "WEAK"}}) > 1
    if unknown >= 3:
        priority = "FILL_DATA_GAPS"
    elif divergence:
        priority = "RESOLVE_CONTRADICTION"
    elif rows.get("company") == "STRONG" and rows.get("industry") == "STRONG":
        priority = "HIGH"
    else:
        priority = "WATCH"
    return {
        "matrix": rows,
        "labels": ("STRONG", "WEAK", "NEUTRAL", "UNKNOWN"),
        "research_priority": priority,
        "not_only_score": True,
    }


def why_not(views: Mapping[str, str], *, capital: Mapping[str, Any] | None = None, options: Mapping[str, Any] | None = None, portfolio: Mapping[str, Any] | None = None) -> dict[str, Any]:
    reasons = []
    capital = dict(capital or {})
    options = dict(options or {})
    portfolio = dict(portfolio or {})
    if views.get("capital") in {"WEAK", "BEARISH"} or str(capital.get("capital_state") or "").upper() == "DISTRIBUTION":
        reasons.append("Capital = distribution")
    if views.get("market") in {"WEAK", "BEARISH"}:
        reasons.append("Market = overextended")
    if options.get("stance") in {"BEARISH", "WEAK"} or options.get("options_positioning") == "SUPPRESS":
        reasons.append("Options = crowded")
    if portfolio.get("already_owned") or portfolio.get("relevance") in {"PORTFOLIO_CONCENTRATION_RISK", "PORTFOLIO_RELEVANCE", "ALREADY_OWNED"}:
        reasons.append("Portfolio = already owned")
    if portfolio.get("overweight"):
        reasons.append("Portfolio = overweight")
    if "sec" in views and views.get("sec") in {None, "", "UNKNOWN", "DATA_GAP"}:
        reasons.append("missing SEC")
    if "revision" in views and views.get("revision") in {None, "", "UNKNOWN", "DATA_GAP"}:
        reasons.append("missing revision")
    if "industry" in views and views.get("industry") in {None, "", "UNKNOWN", "DATA_GAP"}:
        reasons.append("industry relationship uncertain")
    if "risk" in views and views.get("risk") in {None, "", "UNKNOWN", "DATA_GAP"}:
        reasons.append("risk unverified")
    long_ok = views.get("fundamental") in {"STRONG", "BULLISH"} or views.get("company") in {"STRONG", "BULLISH"}
    short_block = bool(reasons)
    conclusion = "RESEARCH_BULLISH" if long_ok else "RESEARCH_INCOMPLETE"
    if short_block:
        conclusion = "RESEARCH_BULLISH / SHORT_TERM_NOT_READY" if long_ok else "SHORT_TERM_NOT_READY"
    return {
        "why_candidate": [f"{name}={stance}" for name, stance in views.items() if stance in {"STRONG", "BULLISH"}],
        "why_not": reasons,
        "conclusion": conclusion,
        "not_a_buy_sell": True,
    }


def historical_analogue(
    current: Mapping[str, Any],
    historical: Iterable[Mapping[str, Any]],
    *,
    top_k: int = 5,
) -> dict[str, Any]:
    cases = retrieve_similar_cases(current, historical, top_k=top_k)
    returns = []
    mfe = []
    mae = []
    for case in cases:
        outcome = case.get("future_outcome") or {}
        value = outcome.get("return_5d") or outcome.get("return_3d")
        if value is not None:
            returns.append(float(value))
        if outcome.get("mfe") is not None:
            mfe.append(float(outcome["mfe"]))
        if outcome.get("mae") is not None:
            mae.append(float(outcome["mae"]))
    win_rate = (sum(1 for value in returns if value > 0) / len(returns)) if returns else None
    return {
        "historical_cases": cases,
        "sample_size": len(cases),
        "win_rate": win_rate,
        "median_return": research_median(returns),
        "tail_loss": min(returns) if returns else None,
        "mfe": sum(mfe) / len(mfe) if mfe else None,
        "mae": sum(mae) / len(mae) if mae else None,
        "failure_modes": [
            case for case in cases
            if (case.get("future_outcome") or {}).get("return_5d") is not None
            and float(case["future_outcome"]["return_5d"]) < 0
        ],
        "not_a_production_pick": True,
    }


def validation_metrics(samples: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in samples if row.get("valid") or row.get("eligibility_reason") == "VALID"]
    dates = sorted({str(row.get("as_of_date")) for row in rows if row.get("as_of_date")})
    symbols = sorted({str(row.get("symbol")) for row in rows if row.get("symbol")})

    def _horizon(key: str) -> dict[str, Any]:
        values = []
        for row in rows:
            outcome = row.get("independent_outcome") or row.get("future_outcome") or {}
            value = outcome.get(key)
            if value is not None:
                values.append(float(value))
        if not values:
            return {"mean": None, "median": None, "win_rate": None, "profit_factor": None, "sample_size": 0}
        gains = sum(v for v in values if v > 0)
        losses = sum(v for v in values if v < 0)
        return {
            "mean": round(sum(values) / len(values), 6),
            "median": None if research_median(values) is None else round(research_median(values), 6),
            "win_rate": round(sum(1 for v in values if v > 0) / len(values), 6),
            "profit_factor": round(gains / abs(losses), 6) if losses else None,
            "sample_size": len(values),
        }

    return {
        "sample_size": len(rows),
        "distinct_dates": len(dates),
        "distinct_symbols": len(symbols),
        "T+1": _horizon("return_1d"),
        "T+3": _horizon("return_3d"),
        "T+5": _horizon("return_5d"),
        "T+10": _horizon("return_10d"),
        "split": "chronological/purged/walk-forward only; random split forbidden",
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def build_company_research(
    symbol: str,
    *,
    as_of_date: date | str | None = None,
    facts: Mapping[str, Any] | None = None,
    capital: Mapping[str, Any] | None = None,
    statistical: Mapping[str, Any] | None = None,
    notes: Iterable[Mapping[str, Any]] | None = None,
    historical: Iterable[Mapping[str, Any]] | None = None,
    ohlcv=None,
    industry_graph: Mapping[str, Any] | None = None,
    previous_thesis: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    facts = dict(facts or {})
    facts.setdefault("as_of_date", str(as_of_date or ""))
    facts.setdefault("symbol", symbol)
    fundamental = build_buffett_context(facts)
    industry = build_serenity_context(facts)
    supply = build_supply_context(facts)
    pricing = build_pricing_gap_context(facts)
    buyers = build_future_buyer_map(facts)
    uzi = build_uzi_adapter(facts)
    tradingagents = build_tradingagents_adapter(facts)
    capital_view = dict(capital or {})
    if "stance" not in capital_view:
        capital_view["stance"] = _stance(capital_view)
    statistical_view = dict(statistical or {})
    if "stance" not in statistical_view:
        statistical_view["stance"] = _stance(statistical_view)
    portfolio = portfolio_context(
        notes or [],
        as_of=as_of_date,
        symbol=symbol,
        historical=bool(facts.get("historical_replay")),
    )
    analogue = historical_analogue(
        {"symbol": symbol, "as_of_date": str(as_of_date or ""), "capital_state": capital_view.get("capital_state")},
        historical or [],
    )
    independent = independent_price_outcomes(ohlcv, as_of_date=as_of_date or date.today()) if ohlcv is not None else {"available": False}
    company = company_quality(facts)
    industry_pos = industry_position(facts)
    capital_schema = capital_behavior({**facts, **capital_view})
    market = market_setup(facts)
    risk_schema = risk_view(facts)
    scores = independent_scores(
        company,
        industry_pos,
        capital_schema,
        market,
        risk_schema,
        statistical_score=statistical_view.get("statistical_score") or statistical_view.get("score"),
    )
    readiness = brain_readiness(company, industry_pos, capital_schema, statistical_view)
    options = options_intelligence(facts)
    short = short_intelligence(facts)
    analyst = analyst_revision(facts)
    fundamentals = company_fundamentals(facts, symbol=symbol, as_of=str(as_of_date or facts.get("as_of_date") or "") or None)
    filings = sec_filing(facts.get("sec_filing") if isinstance(facts.get("sec_filing"), Mapping) else facts, symbol=symbol, as_of=str(as_of_date or facts.get("as_of_date") or "") or None)
    earnings = earnings_intelligence(facts, symbol=symbol, as_of=str(as_of_date or facts.get("as_of_date") or "") or None)
    sbc = sbc_dilution(facts)
    management = management_allocation(facts)
    graph = persist_industry_graph(industry_graph, entities=facts.get("entities"), relations=facts.get("relations"), as_of_date=str(as_of_date or ""))
    memory = update_industry_memory({"graph": industry_graph} if industry_graph else None, {"entities": facts.get("entities"), "relations": facts.get("relations"), "as_of_date": str(as_of_date or ""), "note": facts.get("industry_note")})
    chain = supply_chain_portfolio(portfolio.get("owned_symbols") or [], graph, symbol=symbol)
    chain["enters_alpha_score"] = False
    risk_graph = portfolio_risk_graph(
        portfolio.get("owned_symbols") or [],
        industries={symbol: facts.get("industry") or facts.get("sector")} if facts.get("industry") or facts.get("sector") else {},
        themes={symbol: facts.get("theme")} if facts.get("theme") else {},
        graph=graph,
    )
    market_regime = classify_research_regime(facts)
    event_regime = earnings_regime(facts)
    horizon = research_horizon_contract(facts)
    thesis = thesis_ledger({"symbol": symbol, **(facts.get("thesis") if isinstance(facts.get("thesis"), Mapping) else facts)})
    thesis_cmp = compare_thesis(previous_thesis, {"thesis": thesis.get("thesis"), "evidence": facts.get("new_evidence"), "conflicts": facts.get("thesis_conflicts"), "as_of": str(as_of_date or "")})
    views = {
        "fundamental": _stance(fundamental),
        "company": _stance(fundamental),
        "industry": _stance(industry),
        "capital": _stance(capital_view),
        "market": _stance(statistical_view) if statistical_view.get("stance") != "UNKNOWN" else _stance(market),
        "statistical": _stance(statistical_view),
        "options": str(options.get("stance") or "UNKNOWN"),
        "portfolio": (
            "OVERWEIGHT" if portfolio.get("overweight") else
            "ALREADY_OWNED" if portfolio.get("already_owned") else
            "WATCHING" if portfolio.get("watching") else
            "UNKNOWN"
        ),
        "risk": _stance(risk_schema, purpose="risk"),
    }
    contradiction = contradiction_status(
        views,
        claims={
            "company": company,
            "industry": industry_pos,
            "capital": capital_schema,
            "market": market,
            "risk": risk_schema,
            "fundamentals": fundamentals,
        },
    )
    matrix = research_decision_matrix(views)
    rejected = why_not(views, capital=capital_view, options=options, portfolio=portfolio)
    if contradiction.get("status") == "DIVERGENCE" and portfolio.get("already_owned"):
        flags = list(portfolio.get("flags") or [])
        if "THESIS_CONTRADICTION" not in flags:
            flags.append("THESIS_CONTRADICTION")
        portfolio["flags"] = flags
        portfolio["relevance"] = "THESIS_CONTRADICTION"
    long_term = views.get("company")
    short_term = views.get("capital") if views.get("capital") != "UNKNOWN" else views.get("market")
    multi_horizon = {
        "LONG_TERM": long_term,
        "MEDIUM_TERM": views.get("industry"),
        "SHORT_TERM": short_term,
        "EVENT_TERM": event_regime.get("regime") or "UNKNOWN",
        "allows_long_bull_short_bear": True,
        "long_term_thesis_is_not_t1": True,
    }
    lineage = [
        lineage_status(source="buffett", feature="company_quality", source_date=str(as_of_date or ""), effective_date=str(as_of_date or ""), as_of_date=str(as_of_date or ""), brain="Company"),
        lineage_status(source="serenity", feature="industry_position", source_date=str(as_of_date or ""), effective_date=str(as_of_date or ""), as_of_date=str(as_of_date or ""), brain="Industry"),
        lineage_status(source="capital_brain", feature="capital_behavior", source_date=str(as_of_date or ""), effective_date=str(as_of_date or ""), as_of_date=str(as_of_date or ""), brain="Capital"),
        lineage_status(source="market_setup", feature="market_setup", source_date=str(as_of_date or ""), effective_date=str(as_of_date or ""), as_of_date=str(as_of_date or ""), brain="Market"),
    ]
    if readiness["overall"] == "READY":
        research_mode = "FULL_RESEARCH"
    elif all(status == "DATA_GAP" for status in readiness["brains"].values()):
        research_mode = "MARKET_ONLY_RESEARCH" if views.get("market") not in (None, "", "UNKNOWN") else "DATA_GAP_RESEARCH"
    elif readiness["brains"].get("Company") == "DATA_GAP" and readiness["brains"].get("Industry") == "DATA_GAP":
        research_mode = "MARKET_ONLY_RESEARCH"
    else:
        research_mode = "PARTIAL_RESEARCH"
    coverage_matrix = research_coverage(
        symbol=symbol,
        as_of=str(as_of_date or facts.get("as_of_date") or ""),
        market=market,
        fundamentals=fundamentals,
        sec=filings,
        earnings=earnings,
        revision=analyst,
        industry=graph,
        risk=risk_schema,
        catalyst=event_regime,
        management=management,
        supply_chain=chain,
    )
    readiness_matrix = research_readiness(coverage_matrix)
    conclusion = {
        "status": "RESEARCH_CONCLUSION",
        "not_buy_sell": True,
        "company": views.get("company"),
        "industry": views.get("industry"),
        "capital": views.get("capital"),
        "market": views.get("market"),
        "event": event_regime.get("setup"),
        "options": options.get("options_positioning"),
        "portfolio": portfolio.get("flags"),
        "history": analogue.get("sample_size"),
        "contradiction": contradiction.get("status"),
        "risk": risk_schema.get("data_gaps"),
        "confidence": scores.get("research_composite"),
        "coverage": scores.get("coverage"),
        "readiness": scores.get("readiness"),
        "brain_readiness": readiness,
        "research_mode": research_mode,
        "outcome": independent,
        "why_not": rejected,
        "priority": matrix.get("research_priority"),
        "why_partial": [
            f"{name}={status}" for name, status in readiness["brains"].items() if status != "READY"
        ],
    }
    return {
        "symbol": symbol.upper(),
        "as_of_date": str(as_of_date or facts.get("as_of_date") or ""),
        "status": PRODUCTION_BOUNDARY["status"],
        "produces_pick": False,
        "ranking_owner": PRODUCTION_BOUNDARY["ranking_owner"],
        "fundamental_view": fundamental,
        "industry_view": industry,
        "capital_view": capital_view,
        "statistical_view": statistical_view,
        "company_quality": company,
        "industry_position": industry_pos,
        "capital_behavior": capital_schema,
        "market_setup": market,
        "risk_view": risk_schema,
        "scores": scores,
        "research_composite": scores.get("research_composite"),
        "alpha_score": scores.get("alpha_score"),
        "brain_readiness": readiness,
        "evidence_coverage": scores.get("coverage"),
        "validation_status": readiness["overall"],
        "research_mode": research_mode,
        "supply": supply,
        "pricing_gap": pricing,
        "future_buyer_map": buyers,
        "uzi_adapter": uzi,
        "tradingagents_adapter": tradingagents,
        "portfolio_context": portfolio,
        "supply_chain_portfolio": chain,
        "portfolio_risk_graph": risk_graph,
        "historical_analogue": analogue,
        "historical_evidence": historical_evidence({"analogue_count": analogue.get("sample_size"), "failure_count": len(analogue.get("failure_modes") or []), "win_rate": analogue.get("win_rate")}),
        "independent_outcome_history": independent,
        "contradictions": contradiction,
        "decision_matrix": matrix,
        "why_not": rejected,
        "horizon": horizon,
        "multi_horizon": multi_horizon,
        "fundamentals": fundamentals,
        "sec_filing": filings,
        "earnings": earnings,
        "sbc_dilution": sbc,
        "management": management,
        "industry_graph": graph,
        "industry_memory": memory,
        "options": options,
        "short_borrow": short,
        "analyst_revision": analyst,
        "research_regime": market_regime,
        "earnings_regime": event_regime,
        "thesis": thesis,
        "thesis_compare": thesis_cmp,
        "failure_case": failure_case(facts.get("failure") if isinstance(facts.get("failure"), Mapping) else {}),
        "failure_lifecycle": research_failure_lifecycle(
            {"symbol": symbol, **(facts["failure"] if isinstance(facts.get("failure"), Mapping) else {})},
            facts.get("outcome") if isinstance(facts.get("outcome"), Mapping) else {},
        ),
        "lineage": lineage,
        "research_conclusion": conclusion,
        "quality": scores.get("quality"),
        "risk": {
            "unknown_fields": fundamental.get("unknown_fields"),
            "capital_distribution": capital_view.get("distribution_probability"),
            "portfolio_flags": portfolio.get("flags"),
            "score": risk_schema.get("score"),
            "risk_level": risk_schema.get("risk_level"),
            "stance": risk_schema.get("stance"),
        },
        "confidence": {
            "fundamental": fundamental.get("buffett_quality", {}).get("confidence"),
            "industry": (industry.get("confidence") or {}).get("value"),
            "capital": capital_view.get("capital_state_confidence") or capital_view.get("state_confidence"),
        },
        "evidence_refs": list(industry.get("evidence_refs") or []),
        "coverage_matrix": coverage_matrix,
        "research_readiness": readiness_matrix,
        "failure_warning": previous_failure_warning({"symbol": symbol, "as_of": str(as_of_date or "")}),
        "production_boundary": PRODUCTION_BOUNDARY,
        "market_alpha_from_portfolio": 0,
        "boundary": validate({
            "produces_pick": False,
            "allow_trade": False,
            "classification": PRODUCTION_BOUNDARY["status"],
        }),
    }


def render_company_report(research: Mapping[str, Any]) -> str:
    symbol = research.get("symbol")
    as_of = research.get("as_of_date")
    fund = research.get("fundamental_view") or {}
    industry = research.get("industry_view") or {}
    capital = research.get("capital_view") or {}
    statistical = research.get("statistical_view") or {}
    portfolio = research.get("portfolio_context") or {}
    analogue = research.get("historical_analogue") or {}
    independent = research.get("independent_outcome_history") or {}
    contradiction = research.get("contradictions") or {}
    risk = research.get("risk") or {}
    return "\n".join([
        "# Company Research",
        "",
        f"symbol: {symbol}  as_of: {as_of}  status: RESEARCH_ONLY",
        "",
        "## 1. Portfolio Context",
        f"- already_owned: {portfolio.get('already_owned')}",
        f"- flags: {portfolio.get('flags')}",
        f"- market_alpha_adjustment: {portfolio.get('market_alpha_adjustment', 0)}",
        "",
        "## 2. Buffett Fundamental Analysis",
        f"- stance: {fund.get('stance')}",
        f"- quality: {fund.get('buffett_quality')}",
        f"- unknown: {fund.get('unknown_fields')}",
        "",
        "## 3. Serenity Industry Analysis",
        f"- stance: {industry.get('stance')}",
        f"- bottleneck: {industry.get('bottleneck')}",
        f"- questions: {industry.get('questions')}",
        "",
        "## 4. Supply Chain / Chokepoint",
        f"- supply: {research.get('supply')}",
        "",
        "## 5. Capital Behavior",
        f"- stance: {capital.get('stance')}",
        f"- state: {capital.get('capital_state')}",
        f"- capital_behavior_score: {capital.get('capital_behavior_score') or capital.get('capital_score')}",
        "",
        "## 6. Statistical Setup",
        f"- stance: {statistical.get('stance')}",
        "",
        "## 7. Historical Analogues",
        f"- sample_size: {analogue.get('sample_size')} win_rate: {analogue.get('win_rate')}",
        "",
        "## 8. Independent Future Outcomes",
        f"- {independent}",
        "",
        "## 9. Contradictions",
        f"- {contradiction.get('status')}: {contradiction.get('summary')}",
        "",
        "## 10. Risks",
        f"- {risk}",
        "",
        "## 11. Research Conclusion",
        "- Knowledge + company quality + industry bottleneck + capital + statistics + portfolio + history.",
        "- This is not a BUY/SELL/PAPER_PICK.",
        "",
        "## 12. Evidence",
        f"- refs: {research.get('evidence_refs')}",
        f"- boundary: {PRODUCTION_BOUNDARY['status']}",
        "",
        "## 13. Four-Brain Scores",
        f"- company_quality_score: {(research.get('scores') or {}).get('company_quality_score')}",
        f"- industry_position_score: {(research.get('scores') or {}).get('industry_position_score')}",
        f"- capital_behavior_score: {(research.get('scores') or {}).get('capital_behavior_score')}",
        f"- market_setup_score: {(research.get('scores') or {}).get('market_setup_score')}",
        f"- risk_score: {(research.get('scores') or {}).get('risk_score')}",
        f"- research_composite: {research.get('research_composite')} (not alpha_score={research.get('alpha_score')})",
        "",
        "## 14. Horizon / Why Not / Matrix",
        f"- horizon: {research.get('horizon')}",
        f"- multi_horizon: {research.get('multi_horizon')}",
        f"- matrix: {research.get('decision_matrix')}",
        f"- why_not: {research.get('why_not')}",
        "",
        "## 15. Research Conclusion",
        f"- {research.get('research_conclusion')}",
        "- This is RESEARCH_CONCLUSION, not BUY/SELL.",
        "",
        "## 16. SEC / Earnings / Industry / Failures",
        f"- sec: {research.get('sec_filing')}",
        f"- earnings: {research.get('earnings')}",
        f"- coverage: {research.get('coverage_matrix')}",
        f"- readiness: {research.get('research_readiness')}",
        f"- failure_warning: {research.get('failure_warning')}",
        "",
    ])


def write_company_report(research: Mapping[str, Any], root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parents[2] / "research" / "company"
    symbol = str(research.get("symbol") or "UNKNOWN").upper()
    as_of = str(research.get("as_of_date") or date.today().isoformat())[:10]
    path = base / symbol / f"{as_of}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_company_report(research), encoding="utf-8")
    return path
