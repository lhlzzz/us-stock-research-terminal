"""Compose three brains + memory into one research decision. Never a pick."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

from capital.case_retrieval import retrieve_similar_cases
from .boundary import PRODUCTION_BOUNDARY
from .brains import (
    build_buffett_context,
    build_future_buyer_map,
    build_pricing_gap_context,
    build_serenity_context,
    build_supply_context,
    build_tradingagents_adapter,
    build_uzi_adapter,
)
from .memory import portfolio_context
from .outcomes import independent_price_outcomes


STANCE_RANK = {
    "STRONG": 2,
    "BULLISH": 1,
    "NEUTRAL": 0,
    "WEAK": -1,
    "BEARISH": -2,
    "UNKNOWN": None,
}


def _stance(view: Mapping[str, Any] | None) -> str:
    if not view:
        return "UNKNOWN"
    if view.get("stance"):
        return str(view["stance"]).upper()
    score = view.get("capital_behavior_score") or view.get("capital_quality")
    if score is None:
        return "UNKNOWN"
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if value >= 0.70:
        return "STRONG"
    if value >= 0.55:
        return "BULLISH"
    if value >= 0.45:
        return "NEUTRAL"
    if value >= 0.30:
        return "WEAK"
    return "BEARISH"


def contradiction_status(views: Mapping[str, str]) -> dict[str, Any]:
    usable = {name: stance for name, stance in views.items() if stance and stance != "UNKNOWN"}
    if len(usable) < 2:
        return {
            "status": "UNKNOWN",
            "views": dict(views),
            "summary": "insufficient overlapping evidence",
        }
    signs = [STANCE_RANK.get(stance, 0) or 0 for stance in usable.values()]
    if all(value > 0 for value in signs) or all(value < 0 for value in signs) or all(value == 0 for value in signs):
        status = "CONVERGENCE"
    elif any(value > 0 for value in signs) and any(value < 0 for value in signs):
        status = "DIVERGENCE"
    else:
        status = "UNKNOWN"
    lines = [f"{name}: {stance}" for name, stance in views.items()]
    narrative = []
    if views.get("fundamental") in {"STRONG", "BULLISH"}:
        narrative.append("优秀公司")
    if views.get("industry") in {"STRONG", "BULLISH"}:
        narrative.append("优秀产业链")
    if views.get("capital") in {"WEAK", "BEARISH", "UNKNOWN"}:
        narrative.append("短期资金行为未确认")
    if views.get("statistical") in {"STRONG", "BULLISH"}:
        narrative.append("统计 setup 偏强")
    return {
        "status": status,
        "views": dict(views),
        "lines": lines,
        "summary": " + ".join(narrative) if narrative else status,
        "not_a_score": True,
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
        "median_return": sorted(returns)[len(returns) // 2] if returns else None,
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
            "median": round(sorted(values)[len(values) // 2], 6),
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
) -> dict[str, Any]:
    facts = dict(facts or {})
    facts.setdefault("as_of_date", str(as_of_date or ""))
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
    views = {
        "fundamental": _stance(fundamental),
        "industry": _stance(industry),
        "capital": _stance(capital_view),
        "statistical": _stance(statistical_view),
    }
    contradiction = contradiction_status(views)
    if contradiction.get("status") == "DIVERGENCE" and portfolio.get("already_owned"):
        flags = list(portfolio.get("flags") or [])
        if "THESIS_CONTRADICTION" not in flags:
            flags.append("THESIS_CONTRADICTION")
        portfolio["flags"] = flags
        portfolio["relevance"] = "THESIS_CONTRADICTION"
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
        "supply": supply,
        "pricing_gap": pricing,
        "future_buyer_map": buyers,
        "uzi_adapter": uzi,
        "tradingagents_adapter": tradingagents,
        "portfolio_context": portfolio,
        "historical_analogue": analogue,
        "independent_outcome_history": independent,
        "contradictions": contradiction,
        "risk": {
            "unknown_fields": fundamental.get("unknown_fields"),
            "capital_distribution": capital_view.get("distribution_probability"),
            "portfolio_flags": portfolio.get("flags"),
        },
        "confidence": {
            "fundamental": fundamental.get("buffett_quality", {}).get("confidence"),
            "industry": (industry.get("confidence") or {}).get("value"),
            "capital": capital_view.get("capital_state_confidence") or capital_view.get("state_confidence"),
        },
        "evidence_refs": list(industry.get("evidence_refs") or []),
        "production_boundary": PRODUCTION_BOUNDARY,
        "market_alpha_from_portfolio": 0,
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
    ])


def write_company_report(research: Mapping[str, Any], root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parents[2] / "research" / "company"
    symbol = str(research.get("symbol") or "UNKNOWN").upper()
    as_of = str(research.get("as_of_date") or date.today().isoformat())[:10]
    path = base / symbol / f"{as_of}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_company_report(research), encoding="utf-8")
    return path
