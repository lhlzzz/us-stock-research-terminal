"""Research-side regime models. Parallel to production market_regime.py."""
from __future__ import annotations

from typing import Any, Mapping

from .boundary import PRODUCTION_BOUNDARY

MARKET_REGIMES = (
    "RISK_ON", "RISK_OFF", "TRENDING", "MEAN_REVERSION",
    "HIGH_VOL", "LOW_VOL", "EARNINGS_SEASON", "POST_EARNINGS",
)
EARNINGS_REGIMES = ("PRE_EARNINGS", "EARNINGS_DAY", "POST_EARNINGS", "POST_GUIDANCE")
SETUP_KINDS = ("NORMAL_SETUP", "EVENT_SETUP")


def classify_research_regime(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    named = str(facts.get("regime") or "").upper()
    if named in MARKET_REGIMES:
        regime = named
    else:
        vol = facts.get("volatility")
        trend = facts.get("trend")
        breadth = facts.get("breadth")
        if facts.get("earnings_season"):
            regime = "EARNINGS_SEASON"
        elif facts.get("post_earnings"):
            regime = "POST_EARNINGS"
        elif vol is not None and float(vol) >= 0.03:
            regime = "HIGH_VOL"
        elif vol is not None and float(vol) <= 0.01:
            regime = "LOW_VOL"
        elif breadth is not None and float(breadth) >= 0.65:
            regime = "RISK_ON"
        elif breadth is not None and float(breadth) <= 0.35:
            regime = "RISK_OFF"
        elif trend is not None and abs(float(trend)) >= 0.03:
            regime = "TRENDING"
        elif trend is not None:
            regime = "MEAN_REVERSION"
        else:
            regime = None
    return {
        "layer": "research_regime",
        "regime": regime,
        "supported": list(MARKET_REGIMES),
        "same_factor_not_all_regimes": True,
        "does_not_replace_production_classifier": True,
        "production_classifier": "scripts/market_regime.py",
        "status": "DATA_GAP" if regime is None else "READY",
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def earnings_regime(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    named = str(facts.get("earnings_regime") or "").upper()
    if named not in EARNINGS_REGIMES:
        named = None
        if facts.get("is_earnings_day"):
            named = "EARNINGS_DAY"
        elif facts.get("post_guidance"):
            named = "POST_GUIDANCE"
        elif facts.get("post_earnings"):
            named = "POST_EARNINGS"
        elif facts.get("pre_earnings"):
            named = "PRE_EARNINGS"
    event = named in EARNINGS_REGIMES
    checks = {
        "gap_risk": facts.get("gap_risk"),
        "volatility_expansion": facts.get("volatility_expansion"),
        "volume_expansion": facts.get("volume_expansion"),
        "drift": facts.get("drift"),
        "reversal": facts.get("reversal"),
        "estimate_revision": facts.get("estimate_revision"),
    }
    return {
        "layer": "earnings_regime",
        "regime": named,
        "setup": "EVENT_SETUP" if event else "NORMAL_SETUP",
        "checks": checks,
        "status": "DATA_GAP" if named is None else "READY",
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def regime_effectiveness(rows: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, Any]:
    payload = {}
    for name in MARKET_REGIMES:
        item = dict((rows or {}).get(name) or {})
        payload[name] = {
            "factor_effectiveness": item.get("factor_effectiveness"),
            "capital_behavior_effectiveness": item.get("capital_behavior_effectiveness"),
            "setup_effectiveness": item.get("setup_effectiveness"),
            "sample_count": item.get("sample_count") or 0,
            "status": "VALIDATION_GAP" if (item.get("sample_count") or 0) < 20 else "READY",
        }
    return {
        "layer": "regime_effectiveness",
        "regimes": payload,
        "assumption_rejected": "same factor = all market regimes",
        "production_boundary": PRODUCTION_BOUNDARY,
    }
