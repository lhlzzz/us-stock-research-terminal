#!/usr/bin/env python3
"""Compatibility adapter: legacy research_panel API → Research OS.

Canonical owner is ``scripts/research/``. This module keeps the historical
dict shape used by the ticket pipeline and tests. It does not keep a second
quality / risk / panel scoring engine.
"""

from __future__ import annotations

from typing import Any

from research.brains import build_buffett_context, build_serenity_context, build_tradingagents_adapter, build_uzi_adapter
from research.contracts import company_quality, independent_scores, risk_view
from research.metric_semantics import (
    RISK_DISPLAY,
    REGISTRY,
    normalize_metric,
    risk_manager_recommendation,
)
from research.evidence import observed_number


MISSING_RISK_FIELDS = (
    "short_interest",
    "dilution_risk",
    "debt_covenant",
    "earnings_quality",
    "insider_selling",
    "regulatory_risk",
    "concentration_risk",
)


def _safe_float(value: Any) -> float | None:
    return observed_number(value)


def _provider_profile(symbol: str, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    if profile:
        provider_profile = profile.get("provider_profile") if isinstance(profile.get("provider_profile"), dict) else profile
        if provider_profile:
            return dict(provider_profile)
    return {}


def _risk_item(*, value: Any, status: str, detail: str) -> dict[str, Any]:
    known = status != "UNKNOWN"
    display = RISK_DISPLAY.get(status, "GRAY")
    return {
        "value": value,
        "status": status,
        "risk_known": known,
        "display": display,
        "flag": display,
        "detail": detail,
    }


def build_quality_check(symbol: str, company_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Legacy key. Scores come from ResearchMetricRegistry, never raw unit ratios."""
    profile = _provider_profile(symbol, company_profile)
    as_of = str(profile.get("as_of") or profile.get("as_of_date") or "") or None
    facts = {
        "symbol": symbol,
        "as_of_date": as_of,
        "roe": profile.get("roe"),
        "pe_ttm": profile.get("pe_ttm"),
        "dividend_yield": profile.get("dividend_yield"),
        "source": profile.get("source") or "eastmoney_us",
    }
    buffett = build_buffett_context(facts)
    quality = company_quality(facts)
    latest_price = _safe_float(profile.get("latest_price"))
    week52_high = _safe_float(profile.get("week52_high"))
    week52_low = _safe_float(profile.get("week52_low"))
    amount = _safe_float(profile.get("amount"))
    roe = _safe_float(profile.get("roe"))
    pe_ttm = _safe_float(profile.get("pe_ttm"))
    dividend_yield = _safe_float(profile.get("dividend_yield"))
    price_position_52w = None
    if latest_price is not None and week52_high not in (None, 0):
        price_position_52w = latest_price / float(week52_high)

    scores: dict[str, float] = {}
    for name, value in (("roe", roe), ("pe_ttm", pe_ttm), ("dividend_yield", dividend_yield)):
        REGISTRY.require(name)
        normalized = normalize_metric(name, value)
        if normalized is not None:
            scores[name] = round(normalized, 4)
    overall = quality.get("score")
    if overall is None and scores:
        overall = round(sum(scores.values()) / len(scores), 4)
    if overall is None:
        overall = 0.0
        verdict = "UNAVAILABLE" if not scores else "POOR"
    else:
        verdict = (
            "STRONG" if overall >= 0.7
            else "MODERATE" if overall >= 0.5
            else "WEAK" if overall >= 0.3
            else "POOR"
        )
    unavailable = [
        "profit_margin",
        "gross_margin",
        "debt_to_equity",
        "free_cash_flow",
        "payout_ratio",
        "current_ratio",
        "interest_coverage",
    ]
    return {
        "symbol": symbol,
        "source": facts["source"],
        "raw_values": {
            "roe": roe,
            "pe_ttm": pe_ttm,
            "dividend_yield": dividend_yield,
            "latest_price": latest_price,
            "week52_high": week52_high,
            "week52_low": week52_low,
            "price_position_52w": price_position_52w,
            "amount": amount,
        },
        "scores": scores,
        "overall_quality_score": round(float(overall), 4),
        "passed_dimensions": sum(1 for v in scores.values() if v >= 0.5),
        "total_dimensions": len(scores),
        "unavailable_dimensions": unavailable,
        "data_gap_detail": "provider_field_unavailable: full financial statements are not available from current EastMoney detail fields",
        "quality_verdict": verdict,
        "metric_registry": "research.metric_semantics.REGISTRY",
        "buffett_context": buffett,
        "research_quality": quality,
    }


def build_risk_checklist(
    symbol: str,
    narrative_summary: dict[str, Any],
    business_summary: dict[str, Any],
    market_row: dict[str, Any],
    company_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = _provider_profile(symbol, company_profile)
    latest_price = _safe_float(profile.get("latest_price"))
    prev_close = _safe_float(profile.get("prev_close"))
    pct_chg = _safe_float(profile.get("pct_chg"))
    if pct_chg is None and latest_price is not None and prev_close not in (None, 0):
        pct_chg = latest_price / float(prev_close) - 1.0
    week52_high = _safe_float(profile.get("week52_high"))
    amount = _safe_float(profile.get("amount"))
    pe_ttm = _safe_float(profile.get("pe_ttm"))
    roe = _safe_float(profile.get("roe"))
    checks: dict[str, dict[str, Any]] = {}

    price_position = None
    if latest_price is not None and week52_high not in (None, 0):
        price_position = latest_price / float(week52_high)
    if price_position is None:
        checks["price_extended_vs_52w"] = _risk_item(value=None, status="UNKNOWN", detail="provider_field_unavailable")
    else:
        checks["price_extended_vs_52w"] = _risk_item(
            value=price_position,
            status="ELEVATED_RISK" if price_position > 0.95 else "LOW_RISK",
            detail=f"latest/52w_high={price_position:.1%}",
        )

    if pct_chg is None:
        checks["intraday_gap"] = _risk_item(value=None, status="UNKNOWN", detail="provider_field_unavailable")
    else:
        checks["intraday_gap"] = _risk_item(
            value=pct_chg,
            status="ELEVATED_RISK" if abs(pct_chg) > 0.08 else "LOW_RISK",
            detail=f"intraday_pct_chg={pct_chg:.2%}",
        )

    if amount is None:
        checks["liquidity"] = _risk_item(value=None, status="UNKNOWN", detail="provider_field_unavailable")
    else:
        checks["liquidity"] = _risk_item(
            value=amount,
            status="ELEVATED_RISK" if amount < 20_000_000 else "LOW_RISK",
            detail=f"amount={amount:,.0f}",
        )

    if pe_ttm is None:
        checks["valuation"] = _risk_item(value=None, status="UNKNOWN", detail="provider_field_unavailable")
    else:
        checks["valuation"] = _risk_item(
            value=pe_ttm,
            status="ELEVATED_RISK" if pe_ttm > 80 else "LOW_RISK",
            detail=f"pe_ttm={pe_ttm:.2f}",
        )

    if roe is None:
        checks["quality_gap"] = _risk_item(value=None, status="UNKNOWN", detail="provider_field_unavailable")
    else:
        checks["quality_gap"] = _risk_item(
            value=roe,
            status="ELEVATED_RISK" if roe < 0 else "LOW_RISK",
            detail=f"roe={roe:.2%}",
        )

    five_day_accel = _safe_float(market_row.get("five_day_acceleration"))
    if five_day_accel is None:
        checks["price_manipulation"] = _risk_item(value=None, status="UNKNOWN", detail="N/A")
    else:
        if abs(five_day_accel) > 0.15:
            status = "HIGH_RISK"
        elif abs(five_day_accel) > 0.08:
            status = "ELEVATED_RISK"
        else:
            status = "LOW_RISK"
        checks["price_manipulation"] = _risk_item(
            value=five_day_accel,
            status=status,
            detail=f"5d_accel={five_day_accel:.4f}",
        )

    narrative_status = narrative_summary.get("status", "missing")
    checks["news_red_flags"] = _risk_item(
        value=narrative_status,
        status="ELEVATED_RISK" if narrative_status == "found_unrelated" else "LOW_RISK" if narrative_status == "found_relevant" else "UNKNOWN",
        detail=f"narrative_status={narrative_status}",
    )
    business_status = business_summary.get("status", "missing")
    checks["supply_chain_risk"] = _risk_item(
        value=business_status,
        status="ELEVATED_RISK" if business_status == "found_unrelated" else "LOW_RISK" if business_status == "found_relevant" else "UNKNOWN",
        detail=f"business_status={business_status}",
    )

    for check_name in MISSING_RISK_FIELDS:
        checks[check_name] = _risk_item(value=None, status="UNKNOWN", detail="provider_field_unavailable")

    red_count = sum(1 for c in checks.values() if c["status"] == "HIGH_RISK")
    yellow_count = sum(1 for c in checks.values() if c["status"] in {"ELEVATED_RISK", "MODERATE_RISK"})
    unknown_count = sum(1 for c in checks.values() if c["status"] == "UNKNOWN")
    green_count = sum(1 for c in checks.values() if c["status"] == "LOW_RISK")
    known_blocked = red_count >= 2
    known_elevated = red_count >= 1 or yellow_count >= 3
    known_clean = unknown_count == 0 and red_count == 0 and yellow_count == 0
    insufficient = unknown_count > 0 and not known_blocked
    if known_blocked:
        risk_verdict = "BLOCKED"
    elif known_elevated:
        risk_verdict = "ELEVATED"
    elif insufficient:
        risk_verdict = "UNKNOWN"
    elif yellow_count >= 1:
        risk_verdict = "WATCH"
    else:
        risk_verdict = "CLEAN"
    recommendation = risk_manager_recommendation(
        known_blocked=known_blocked,
        known_elevated=known_elevated,
        known_clean=known_clean,
        insufficient=insufficient,
    )
    uzi = build_uzi_adapter({"symbol": symbol, **profile})
    return {
        "symbol": symbol,
        "source": profile.get("source", "eastmoney_us"),
        "checks": checks,
        "red_count": red_count,
        "yellow_count": yellow_count,
        "green_count": green_count,
        "unknown_count": unknown_count,
        "risk_verdict": risk_verdict,
        "recommendation": recommendation,
        "uzi_adapter": uzi,
        "research_risk": risk_view({"as_of_date": profile.get("as_of_date")}),
    }


def build_supply_chain_map(symbol: str, company_profile: dict[str, Any]) -> dict[str, Any]:
    serenity = build_serenity_context({
        "symbol": symbol,
        "sector": company_profile.get("sector"),
        "industry": company_profile.get("industry"),
        "as_of_date": company_profile.get("as_of_date"),
    })
    themes = []
    if company_profile.get("sector"):
        themes.append(str(company_profile["sector"]))
    if company_profile.get("industry"):
        themes.append(str(company_profile["industry"]))
    for kw in company_profile.get("keywords") or []:
        if kw and str(kw) not in themes:
            themes.append(str(kw))
    return {
        "symbol": symbol,
        "queries_run": 0,
        "queries_successful": 0,
        "themes_found": themes,
        "theme_count": len(themes),
        "supply_chain_summary": f"{len(themes)} themes identified" if themes else "no_supply_chain_data",
        "source": "research.brains.build_serenity_context",
        "serenity_context": serenity,
    }


def _build_fundamental_analyst(quality: dict[str, Any]) -> dict[str, Any]:
    verdict = quality.get("quality_verdict", "UNAVAILABLE")
    score = quality.get("overall_quality_score", 0.0)
    return {
        "agent": "fundamental_analyst",
        "assessment": verdict,
        "score": score,
        "summary": f"Quality verdict: {verdict} (score={score:.2f})",
    }


def _build_news_analyst(narrative_summary: dict[str, Any]) -> dict[str, Any]:
    status = narrative_summary.get("status", "missing")
    relevance = narrative_summary.get("relevance_score", 0.0)
    return {
        "agent": "news_analyst",
        "assessment": status,
        "relevance_score": relevance,
        "top_evidence": narrative_summary.get("top_evidence_title", ""),
        "summary": f"News status: {status}, relevance={relevance:.2f}",
    }


def _build_sentiment_analyst(business_summary: dict[str, Any]) -> dict[str, Any]:
    status = business_summary.get("status", "missing")
    relevance = business_summary.get("relevance_score", 0.0)
    return {
        "agent": "sentiment_analyst",
        "assessment": status,
        "relevance_score": relevance,
        "top_evidence": business_summary.get("top_evidence_title", ""),
        "summary": f"Business/sentiment status: {status}, relevance={relevance:.2f}",
    }


def _build_technical_analyst(market_row: dict[str, Any]) -> dict[str, Any]:
    momentum_20d = _safe_float(market_row.get("prior_20d_momentum"))
    accel_5d = _safe_float(market_row.get("five_day_acceleration"))
    rs = _safe_float(market_row.get("relative_strength_vs_equal_weight"))
    vol_confirm = _safe_float(market_row.get("volume_confirmation_ratio"))
    signals = []
    if momentum_20d and momentum_20d > 0.10:
        signals.append("strong_momentum")
    elif momentum_20d and momentum_20d > 0.05:
        signals.append("moderate_momentum")
    elif momentum_20d and momentum_20d < 0:
        signals.append("negative_momentum")
    if accel_5d and accel_5d < -0.10:
        signals.append("deceleration_warning")
    elif accel_5d and accel_5d > 0.05:
        signals.append("acceleration_bullish")
    if rs and rs > 0.05:
        signals.append("outperforming_market")
    elif rs and rs < -0.05:
        signals.append("underperforming_market")
    if vol_confirm and vol_confirm > 0.3:
        signals.append("volume_confirmed")
    return {
        "agent": "technical_analyst",
        "signals": signals,
        "momentum_20d": momentum_20d,
        "acceleration_5d": accel_5d,
        "relative_strength": rs,
        "volume_confirmation": vol_confirm,
        "summary": f"Signals: {', '.join(signals) if signals else 'neutral'}",
    }


def _build_risk_manager(risk: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    verdict = risk.get("risk_verdict", "UNAVAILABLE")
    quality_verdict = quality.get("quality_verdict", "UNAVAILABLE")
    recommendation = risk.get("recommendation") or risk_manager_recommendation(
        known_blocked=verdict == "BLOCKED",
        known_elevated=verdict == "ELEVATED",
        known_clean=verdict == "CLEAN",
        insufficient=verdict in {"UNKNOWN", "UNAVAILABLE"},
    )
    return {
        "agent": "risk_manager",
        "risk_verdict": verdict,
        "quality_verdict": quality_verdict,
        "recommendation": recommendation,
        "summary": f"Risk: {verdict}, Quality: {quality_verdict}, Rec: {recommendation}",
    }


def run_research_panel(
    symbol: str,
    market_row: dict[str, Any],
    narrative_summary: dict[str, Any],
    business_summary: dict[str, Any],
    quality: dict[str, Any],
    risk: dict[str, Any],
) -> dict[str, Any]:
    fundamental = _build_fundamental_analyst(quality)
    news = _build_news_analyst(narrative_summary)
    sentiment = _build_sentiment_analyst(business_summary)
    technical = _build_technical_analyst(market_row)
    bull_points = []
    if quality.get("overall_quality_score", 0) >= 0.6:
        bull_points.append(f"Strong quality ({quality['quality_verdict']})")
    if narrative_summary.get("relevance_score", 0) >= 0.5:
        bull_points.append("Relevant news catalysts found")
    if business_summary.get("relevance_score", 0) >= 0.5:
        bull_points.append("Relevant business/demand signals")
    if technical.get("momentum_20d") and technical["momentum_20d"] > 0.10:
        bull_points.append("Strong 20d momentum")
    bear_points = []
    if quality.get("overall_quality_score", 1) < 0.4:
        bear_points.append(f"Weak quality ({quality['quality_verdict']})")
    if risk.get("red_count", 0) >= 1:
        bear_points.append(f"{risk['red_count']} red risk flags")
    if technical.get("acceleration_5d") and technical["acceleration_5d"] < -0.10:
        bear_points.append("5d deceleration warning")
    bull = {"agent": "bull_case", "points": bull_points, "point_count": len(bull_points), "summary": f"Bull points: {len(bull_points)}"}
    bear = {"agent": "bear_case", "points": bear_points, "point_count": len(bear_points), "summary": f"Bear points: {len(bear_points)}"}
    risk_mgr = _build_risk_manager(risk, quality)
    agents = [fundamental, news, sentiment, technical, bull, bear, risk_mgr]
    positive_signals = sum(1 for a in [fundamental, news, sentiment, technical] if a.get("assessment") in ("STRONG", "MODERATE", "found_relevant"))
    negative_signals = bear.get("point_count", 0)
    if positive_signals >= 3 and negative_signals <= 1:
        panel_verdict = "BULLISH_CONSENSUS"
    elif positive_signals >= 2 and negative_signals <= 2:
        panel_verdict = "NEUTRAL"
    elif negative_signals >= 3:
        panel_verdict = "BEARISH_CONSENSUS"
    else:
        panel_verdict = "MIXED"
    adapter = build_tradingagents_adapter({
        "symbol": symbol,
        "bull_thesis": bull_points,
        "bear_thesis": bear_points,
        "missing_evidence": [name for name, item in (risk.get("checks") or {}).items() if item.get("status") == "UNKNOWN"],
    })
    return {
        "symbol": symbol,
        "agents": {a["agent"]: a for a in agents},
        "positive_signals": positive_signals,
        "negative_signals": negative_signals,
        "panel_verdict": panel_verdict,
        "summary": f"Panel: {panel_verdict} (pos={positive_signals}, neg={negative_signals})",
        "method": "DETERMINISTIC_PANEL_RULE",
        "not_multi_agent_vote": True,
        "tradingagents_adapter": adapter,
    }


def build_replay_hypothesis(
    symbol: str,
    market_row: dict[str, Any],
    panel: dict[str, Any],
    quality: dict[str, Any],
) -> dict[str, Any]:
    momentum_20d = _safe_float(market_row.get("prior_20d_momentum")) or 0
    accel_5d = _safe_float(market_row.get("five_day_acceleration")) or 0
    quality_score = quality.get("overall_quality_score", 0)
    panel_verdict = panel.get("panel_verdict", "MIXED")
    if panel_verdict == "BULLISH_CONSENSUS" and quality_score >= 0.5:
        entry = "momentum_continuation"
        stop_loss = -0.05
        take_profit = 0.08
        holding_period = "5d_10d"
        heuristic_confidence = 0.7
    elif panel_verdict == "NEUTRAL" and quality_score >= 0.4:
        entry = "pullback_entry"
        stop_loss = -0.03
        take_profit = 0.05
        holding_period = "3d_5d"
        heuristic_confidence = 0.5
    else:
        entry = "no_entry"
        stop_loss = 0.0
        take_profit = 0.0
        holding_period = "N/A"
        heuristic_confidence = 0.2
    if accel_5d < -0.15:
        entry = "avoid_deceleration"
        heuristic_confidence = max(0.1, heuristic_confidence - 0.3)
    return {
        "symbol": symbol,
        "entry_condition": entry,
        "exit_condition": "trailing_stop" if entry != "no_entry" else "N/A",
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "holding_period": holding_period,
        "heuristic_confidence": round(heuristic_confidence, 2),
        "confidence": round(heuristic_confidence, 2),
        "model_probability": None,
        "historically_calibrated_probability": None,
        "status": "UNCALIBRATED_HYPOTHESIS",
        "not_a_prediction": True,
        "hypothesis": (
            f"Entry={entry}, SL={stop_loss:.1%}, TP={take_profit:.1%}, "
            f"Period={holding_period}, heuristic={heuristic_confidence:.0%}"
        ),
        "unused_momentum_20d": momentum_20d,
    }


def run_full_research_panel(
    symbol: str,
    market_row: dict[str, Any],
    narrative_summary: dict[str, Any],
    business_summary: dict[str, Any],
    company_profile: dict[str, Any],
) -> dict[str, Any]:
    quality = build_quality_check(symbol, company_profile)
    risk = build_risk_checklist(symbol, narrative_summary, business_summary, market_row, company_profile)
    supply_chain = build_supply_chain_map(symbol, company_profile)
    panel = run_research_panel(symbol, market_row, narrative_summary, business_summary, quality, risk)
    replay = build_replay_hypothesis(symbol, market_row, panel, quality)
    scores = independent_scores(
        quality.get("research_quality"),
        None,
        None,
        None,
        risk.get("research_risk"),
    )
    return {
        "symbol": symbol,
        "quality_check": quality,
        "risk_checklist": risk,
        "supply_chain_map": supply_chain,
        "research_panel": panel,
        "replay_hypothesis": replay,
        "canonical_owner": "scripts.research",
        "compatibility_adapter": True,
        "scores": scores,
    }
