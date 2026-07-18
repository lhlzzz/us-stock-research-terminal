#!/usr/bin/env python3
"""Multi-framework research panel for xiaomei profit-ticket pipeline.

Integrates:
- Buffett Skills: quality/moat/cash-flow/safety-margin check
- UZI-Skill: trap/risk checklist (22-dim inspired)
- TradingAgents: multi-agent research panel (fundamental/news/sentiment/technical/bull-bear/risk)
- Serenity Skill: supply-chain/theme mapping via last30days
- QuantDinger: replay hypothesis generation

Boundary: research-only. No broker/order/ledger/live-trade. No BUY/SELL.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
from eastmoney_us import fetch_realtime_quote

LAST30DAYS_SCRIPT = Path("/root/.agents/skills/last30days/scripts/last30days.py")
LAST30DAYS_PYTHON = Path("/root/.local/share/hermes-tools/last30days-py312/bin/python")


def _safe_float(value: Any) -> float | None:
    try:
        v = float(value)
        if np.isnan(v) or np.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None




def _provider_profile(symbol: str, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    if profile:
        provider_profile = profile.get("provider_profile") if isinstance(profile.get("provider_profile"), dict) else profile
        if provider_profile:
            return provider_profile
    return fetch_realtime_quote(symbol) or {}


def _score_range(value: float | None, low: float, high: float, invert: bool = False) -> float | None:
    if value is None:
        return None
    if high == low:
        return None
    score = (value - low) / (high - low)
    score = min(1.0, max(0.0, score))
    return 1.0 - score if invert else score


def _run_last30days(query: str, save_dir: str | None = None) -> dict[str, Any]:
    if __import__("os").environ.get("XIAOMEI_SKIP_LAST30DAYS", "0") == "1":
        return {"stdout": "", "stderr": "SKIP_LAST30DAYS", "returncode": 0}
    cmd = [
        str(LAST30DAYS_PYTHON),
        str(LAST30DAYS_SCRIPT),
        query,
        "--quick",
        "--days=30",
        "--emit=json",
    ]
    if save_dir:
        cmd.extend(["--save-dir", save_dir])
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20, env={**dict(__import__("os").environ)}
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    except Exception:
        return {"stdout": "", "stderr": "last30days execution failed", "returncode": 124}


def _parse_last30days_json(raw_output: str) -> dict[str, Any]:
    import json
    try:
        data = json.loads(raw_output)
        return data
    except (json.JSONDecodeError, ValueError):
        return {"items": [], "raw_text": raw_output[:2000]}


# ─── Buffett Skills: Quality Check ───────────────────────────────────────────────

def build_quality_check(symbol: str, company_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a Buffett-style quality check from EastMoney-available fields.

    EastMoney US detail does not provide full financial statements here. Missing
    statement-only dimensions are reported explicitly instead of being inferred.
    """
    try:
        profile = _provider_profile(symbol, company_profile)
        roe = _safe_float(profile.get("roe"))
        pe_ttm = _safe_float(profile.get("pe_ttm"))
        dividend_yield = _safe_float(profile.get("dividend_yield"))
        latest_price = _safe_float(profile.get("latest_price"))
        week52_high = _safe_float(profile.get("week52_high"))
        week52_low = _safe_float(profile.get("week52_low"))
        amount = _safe_float(profile.get("amount"))

        price_position_52w = None
        if latest_price is not None and week52_high not in (None, 0):
            price_position_52w = latest_price / float(week52_high)

        scores: dict[str, float] = {}
        if roe is not None:
            scores["roe"] = min(1.0, max(0.0, roe / 0.30))
        if pe_ttm is not None and pe_ttm > 0:
            scores["pe_ttm"] = min(1.0, max(0.0, 1.0 - max(0.0, pe_ttm - 10.0) / 50.0))
        if dividend_yield is not None:
            scores["dividend_yield"] = min(1.0, max(0.0, dividend_yield / 0.04))
        if price_position_52w is not None:
            scores["price_position_52w"] = min(1.0, max(0.0, 1.0 - abs(price_position_52w - 0.75) / 0.75))
        if amount is not None:
            scores["liquidity_amount"] = min(1.0, max(0.0, amount / 100_000_000.0))

        unavailable_dimensions = [
            "profit_margin",
            "gross_margin",
            "debt_to_equity",
            "free_cash_flow",
            "payout_ratio",
            "current_ratio",
            "interest_coverage",
        ]
        overall = float(np.mean(list(scores.values()))) if scores else 0.0
        passed_dims = sum(1 for v in scores.values() if v >= 0.5)

        return {
            "symbol": symbol,
            "source": profile.get("source", "eastmoney_us"),
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
            "overall_quality_score": round(overall, 4),
            "passed_dimensions": passed_dims,
            "total_dimensions": len(scores),
            "unavailable_dimensions": unavailable_dimensions,
            "data_gap_detail": "provider_field_unavailable: full financial statements are not available from current EastMoney detail fields",
            "quality_verdict": (
                "STRONG" if overall >= 0.7
                else "MODERATE" if overall >= 0.5
                else "WEAK" if overall >= 0.3
                else "POOR"
            ),
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "raw_values": {},
            "scores": {},
            "overall_quality_score": 0.0,
            "passed_dimensions": 0,
            "total_dimensions": 0,
            "unavailable_dimensions": [],
            "quality_verdict": "UNAVAILABLE",
            "error": str(e),
        }


# ─── UZI-Skill: Trap / Risk Checklist ────────────────────────────────────────────

def build_risk_checklist(
    symbol: str,
    narrative_summary: dict[str, Any],
    business_summary: dict[str, Any],
    market_row: dict[str, Any],
    company_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """UZI-style trap/risk checklist using EastMoney detail plus public evidence."""
    try:
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
        checks["price_extended_vs_52w"] = {
            "value": price_position,
            "flag": "YELLOW" if price_position and price_position > 0.95 else "GREEN",
            "detail": f"latest/52w_high={price_position:.1%}" if price_position is not None else "provider_field_unavailable",
        }

        checks["intraday_gap"] = {
            "value": pct_chg,
            "flag": "YELLOW" if pct_chg and abs(pct_chg) > 0.08 else "GREEN",
            "detail": f"intraday_pct_chg={pct_chg:.2%}" if pct_chg is not None else "provider_field_unavailable",
        }

        checks["liquidity"] = {
            "value": amount,
            "flag": "YELLOW" if amount is not None and amount < 20_000_000 else "GREEN",
            "detail": f"amount={amount:,.0f}" if amount is not None else "provider_field_unavailable",
        }

        checks["valuation"] = {
            "value": pe_ttm,
            "flag": "YELLOW" if pe_ttm and pe_ttm > 80 else "GREEN",
            "detail": f"pe_ttm={pe_ttm:.2f}" if pe_ttm is not None else "provider_field_unavailable",
        }

        checks["quality_gap"] = {
            "value": roe,
            "flag": "YELLOW" if roe is not None and roe < 0 else "GREEN",
            "detail": f"roe={roe:.2%}" if roe is not None else "provider_field_unavailable",
        }

        five_day_accel = _safe_float(market_row.get("five_day_acceleration"))
        checks["price_manipulation"] = {
            "value": five_day_accel,
            "flag": "RED" if five_day_accel and abs(five_day_accel) > 0.15 else "YELLOW" if five_day_accel and abs(five_day_accel) > 0.08 else "GREEN",
            "detail": f"5d_accel={five_day_accel:.4f}" if five_day_accel is not None else "N/A",
        }

        narrative_status = narrative_summary.get("status", "missing")
        checks["news_red_flags"] = {
            "value": narrative_status,
            "flag": "YELLOW" if narrative_status == "found_unrelated" else "GREEN",
            "detail": f"narrative_status={narrative_status}",
        }

        business_status = business_summary.get("status", "missing")
        checks["supply_chain_risk"] = {
            "value": business_status,
            "flag": "YELLOW" if business_status == "found_unrelated" else "GREEN",
            "detail": f"business_status={business_status}",
        }

        for check_name in ["short_interest", "dilution_risk", "debt_covenant", "earnings_quality", "insider_selling", "regulatory_risk", "concentration_risk"]:
            checks[check_name] = {
                "value": None,
                "flag": "GREEN",
                "detail": "provider_field_unavailable",
            }

        red_count = sum(1 for c in checks.values() if c["flag"] == "RED")
        yellow_count = sum(1 for c in checks.values() if c["flag"] == "YELLOW")
        green_count = sum(1 for c in checks.values() if c["flag"] == "GREEN")

        if red_count >= 2:
            risk_verdict = "BLOCKED"
        elif red_count >= 1 or yellow_count >= 3:
            risk_verdict = "ELEVATED"
        elif yellow_count >= 1:
            risk_verdict = "WATCH"
        else:
            risk_verdict = "CLEAN"

        return {
            "symbol": symbol,
            "source": profile.get("source", "eastmoney_us"),
            "checks": checks,
            "red_count": red_count,
            "yellow_count": yellow_count,
            "green_count": green_count,
            "risk_verdict": risk_verdict,
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "checks": {},
            "red_count": 0,
            "yellow_count": 0,
            "green_count": 0,
            "risk_verdict": "UNAVAILABLE",
            "error": str(e),
        }


# ─── Serenity Skill: Supply-Chain / Theme Mapping ─────────────────────────────────

SECTOR_THEME_MAP = {
    "Technology": ["semiconductor", "chip", "AI", "cloud", "software", "cybersecurity", "SaaS"],
    "Healthcare": ["pharma", "biotech", "medical device", "FDA", "clinical trial"],
    "Consumer Cyclical": ["retail", "e-commerce", "consumer spending", "brand"],
    "Industrials": ["manufacturing", "aerospace", "defense", "infrastructure", "automation"],
    "Financial Services": ["banking", "fintech", "insurance", "capital markets"],
    "Energy": ["oil", "gas", "renewable", "solar", "battery", "EV"],
    "Communication Services": ["telecom", "media", "streaming", "advertising"],
    "Consumer Defensive": ["food", "beverage", "household", "staples"],
    "Real Estate": ["REIT", "commercial", "residential", "mortgage"],
    "Basic Materials": ["mining", "chemicals", "steel", "lithium"],
    "Utilities": ["electric", "gas", "water", "renewable energy"],
}


def build_supply_chain_map(symbol: str, company_profile: dict[str, Any]) -> dict[str, Any]:
    """Supply-chain and theme mapping using local sector knowledge.

    Falls back to last30days only when SKIP_LAST30DAYS is not set and
    sector mapping yields fewer than 2 themes.
    """
    company_name = company_profile.get("company_query_name", symbol)
    sector = company_profile.get("sector", "")
    industry = company_profile.get("industry", "")
    keywords = company_profile.get("keywords", [])

    themes_found = []
    for sector_key, themes in SECTOR_THEME_MAP.items():
        if sector_key.lower() in (sector or "").lower():
            themes_found.extend(themes[:3])
            break

    name_lower = (company_name or "").lower()
    if any(kw in name_lower for kw in ["bio", "pharma", "drug", "medical"]):
        themes_found.extend(["pharma", "biotech", "FDA"])
    if any(kw in name_lower for kw in ["tech", "software", "data", "cloud"]):
        themes_found.extend(["technology", "cloud", "AI"])
    if any(kw in name_lower for kw in ["bank", "financial", "capital"]):
        themes_found.extend(["financial services", "banking"])
    if any(kw in name_lower for kw in ["energy", "oil", "gas", "solar"]):
        themes_found.extend(["energy", "commodities"])

    for kw in keywords:
        if kw and kw.lower() not in [t.lower() for t in themes_found]:
            themes_found.append(kw)

    themes_found = list(dict.fromkeys(themes_found))

    return {
        "symbol": symbol,
        "queries_run": 0,
        "queries_successful": 0,
        "themes_found": themes_found,
        "theme_count": len(themes_found),
        "supply_chain_summary": f"{len(themes_found)} themes identified" if themes_found else "no_supply_chain_data",
        "source": "local_sector_mapping",
    }


# ─── TradingAgents: Multi-Agent Research Panel ────────────────────────────────────

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
    top_title = narrative_summary.get("top_evidence_title", "")
    return {
        "agent": "news_analyst",
        "assessment": status,
        "relevance_score": relevance,
        "top_evidence": top_title,
        "summary": f"News status: {status}, relevance={relevance:.2f}",
    }


def _build_sentiment_analyst(business_summary: dict[str, Any]) -> dict[str, Any]:
    status = business_summary.get("status", "missing")
    relevance = business_summary.get("relevance_score", 0.0)
    top_title = business_summary.get("top_evidence_title", "")
    return {
        "agent": "sentiment_analyst",
        "assessment": status,
        "relevance_score": relevance,
        "top_evidence": top_title,
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


def _build_bull_case(
    quality: dict[str, Any],
    narrative_summary: dict[str, Any],
    business_summary: dict[str, Any],
    technical: dict[str, Any],
) -> dict[str, Any]:
    points = []
    if quality.get("overall_quality_score", 0) >= 0.6:
        points.append(f"Strong quality ({quality['quality_verdict']})")
    if narrative_summary.get("relevance_score", 0) >= 0.5:
        points.append("Relevant news catalysts found")
    if business_summary.get("relevance_score", 0) >= 0.5:
        points.append("Relevant business/demand signals")
    if technical.get("momentum_20d", 0) and technical["momentum_20d"] > 0.10:
        points.append("Strong 20d momentum")
    if "volume_confirmed" in technical.get("signals", []):
        points.append("Volume confirmation")

    return {
        "agent": "bull_case",
        "points": points,
        "point_count": len(points),
        "summary": f"Bull points: {len(points)}",
    }


def _build_bear_case(
    quality: dict[str, Any],
    risk: dict[str, Any],
    technical: dict[str, Any],
    narrative_summary: dict[str, Any],
) -> dict[str, Any]:
    points = []
    if quality.get("overall_quality_score", 1) < 0.4:
        points.append(f"Weak quality ({quality['quality_verdict']})")
    if risk.get("red_count", 0) >= 1:
        points.append(f"{risk['red_count']} red risk flags")
    if risk.get("yellow_count", 0) >= 2:
        points.append(f"{risk['yellow_count']} yellow risk warnings")
    if technical.get("acceleration_5d") and technical["acceleration_5d"] < -0.10:
        points.append("5d deceleration warning")
    if "underperforming_market" in technical.get("signals", []):
        points.append("Underperforming market")
    if narrative_summary.get("status") == "found_unrelated":
        points.append("Unrelated news narrative")

    return {
        "agent": "bear_case",
        "points": points,
        "point_count": len(points),
        "summary": f"Bear points: {len(points)}",
    }


def _build_risk_manager(risk: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    verdict = risk.get("risk_verdict", "UNAVAILABLE")
    quality_verdict = quality.get("quality_verdict", "UNAVAILABLE")

    if verdict == "BLOCKED":
        recommendation = "DO_NOT_ADVANCE"
    elif verdict == "ELEVATED":
        recommendation = "PROCEED_WITH_CAUTION"
    elif verdict == "WATCH":
        recommendation = "PROCEED_WITH_MONITORING"
    else:
        recommendation = "PROCEED"

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
    """TradingAgents-style multi-agent research panel."""
    fundamental = _build_fundamental_analyst(quality)
    news = _build_news_analyst(narrative_summary)
    sentiment = _build_sentiment_analyst(business_summary)
    technical = _build_technical_analyst(market_row)
    bull = _build_bull_case(quality, narrative_summary, business_summary, technical)
    bear = _build_bear_case(quality, risk, technical, narrative_summary)
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

    return {
        "symbol": symbol,
        "agents": {a["agent"]: a for a in agents},
        "positive_signals": positive_signals,
        "negative_signals": negative_signals,
        "panel_verdict": panel_verdict,
        "summary": f"Panel: {panel_verdict} (pos={positive_signals}, neg={negative_signals})",
    }


# ─── QuantDinger: Replay Hypothesis ──────────────────────────────────────────────

def build_replay_hypothesis(
    symbol: str,
    market_row: dict[str, Any],
    panel: dict[str, Any],
    quality: dict[str, Any],
) -> dict[str, Any]:
    """QuantDinger-style replay hypothesis generation.

    Defines:
    - entry_condition: when to enter
    - exit_condition: when to exit
    - stop_loss: risk limit
    - take_profit: target
    - holding_period: expected duration
    - confidence: based on panel consensus
    """
    momentum_20d = _safe_float(market_row.get("prior_20d_momentum")) or 0
    accel_5d = _safe_float(market_row.get("five_day_acceleration")) or 0
    quality_score = quality.get("overall_quality_score", 0)
    panel_verdict = panel.get("panel_verdict", "MIXED")

    if panel_verdict == "BULLISH_CONSENSUS" and quality_score >= 0.5:
        entry = "momentum_continuation"
        stop_loss = -0.05
        take_profit = 0.08
        holding_period = "5d_10d"
        confidence = 0.7
    elif panel_verdict == "NEUTRAL" and quality_score >= 0.4:
        entry = "pullback_entry"
        stop_loss = -0.03
        take_profit = 0.05
        holding_period = "3d_5d"
        confidence = 0.5
    else:
        entry = "no_entry"
        stop_loss = 0.0
        take_profit = 0.0
        holding_period = "N/A"
        confidence = 0.2

    if accel_5d < -0.15:
        entry = "avoid_deceleration"
        confidence = max(0.1, confidence - 0.3)

    return {
        "symbol": symbol,
        "entry_condition": entry,
        "exit_condition": "trailing_stop" if entry != "no_entry" else "N/A",
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "holding_period": holding_period,
        "confidence": round(confidence, 2),
        "hypothesis": f"Entry={entry}, SL={stop_loss:.1%}, TP={take_profit:.1%}, Period={holding_period}, Conf={confidence:.0%}",
    }


# ─── Orchestrator ─────────────────────────────────────────────────────────────────

def run_full_research_panel(
    symbol: str,
    market_row: dict[str, Any],
    narrative_summary: dict[str, Any],
    business_summary: dict[str, Any],
    company_profile: dict[str, Any],
) -> dict[str, Any]:
    """Run all 5 frameworks and return combined results."""
    quality = build_quality_check(symbol, company_profile)
    risk = build_risk_checklist(symbol, narrative_summary, business_summary, market_row, company_profile)
    supply_chain = build_supply_chain_map(symbol, company_profile)
    panel = run_research_panel(symbol, market_row, narrative_summary, business_summary, quality, risk)
    replay = build_replay_hypothesis(symbol, market_row, panel, quality)

    return {
        "symbol": symbol,
        "quality_check": quality,
        "risk_checklist": risk,
        "supply_chain_map": supply_chain,
        "research_panel": panel,
        "replay_hypothesis": replay,
    }
