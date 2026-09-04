"""Options, short/borrow, and analyst revision as research context only."""
from __future__ import annotations

from typing import Any, Mapping

from .boundary import PRODUCTION_BOUNDARY
from .evidence import observed_number

OPTIONS_FIELDS = (
    "options_open_interest", "implied_volatility", "iv_rank", "put_call",
    "gamma", "dealer_gamma", "gamma_walls", "skew", "expiration",
)
SHORT_FIELDS = (
    "short_interest", "days_to_cover", "short_interest_change",
    "borrow_tightness", "short_squeeze_risk",
)
ANALYST_FIELDS = (
    "analyst_upgrades", "analyst_downgrades", "eps_revision",
    "revenue_revision", "target_price_revision", "estimate_dispersion",
)


def options_intelligence(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    fields = {name: facts.get(name) for name in OPTIONS_FIELDS}
    gaps = [name for name, value in fields.items() if value in (None, "")]
    put_call = observed_number(facts.get("put_call"))
    iv_rank = observed_number(facts.get("iv_rank"))
    if put_call is not None and put_call >= 1.2:
        path = "SUPPRESS"
        stance = "BEARISH"
    elif put_call is not None and put_call <= 0.7 and (iv_rank is None or iv_rank < 70):
        path = "SUPPORT"
        stance = "BULLISH"
    elif not gaps:
        path = "NEUTRAL"
        stance = "NEUTRAL"
    else:
        path = "UNKNOWN"
        stance = "UNKNOWN"
    return {
        "layer": "options_intelligence",
        "role": "MARKET_CONTEXT",
        "fields": fields,
        "data_gaps": gaps,
        "options_positioning": path,
        "stance": stance,
        "not_a_buy_condition": True,
        "status": "DATA_GAP" if gaps else "READY",
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def short_intelligence(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    fields = {name: facts.get(name) for name in SHORT_FIELDS}
    change = observed_number(facts.get("short_interest_change"))
    si = observed_number(facts.get("short_interest"))
    tightness = observed_number(facts.get("borrow_tightness"))
    if change is not None and change > 0:
        state = "short_build"
    elif tightness is not None and tightness >= 0.7:
        state = "short_pressure"
    elif change is not None and change < 0 and tightness is not None and tightness >= 0.7:
        state = "forced_cover"
    elif si is not None and si >= 0.2:
        state = "crowded_short"
    else:
        state = "UNKNOWN" if si is None else "observed"
    return {
        "layer": "short_borrow",
        "role": "Capital / Risk Context",
        "fields": fields,
        "state": state,
        "high_si_is_not_bullish": True,
        "stance": "UNKNOWN",
        "status": "DATA_GAP" if si is None else "READY",
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def analyst_revision(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    fields = {name: facts.get(name) for name in ANALYST_FIELDS}
    ups = int(facts.get("analyst_upgrades") or 0)
    downs = int(facts.get("analyst_downgrades") or 0)
    total = ups + downs
    breadth = None if total == 0 else round((ups - downs) / total, 4)
    acceleration = observed_number(facts.get("revision_acceleration"))
    dispersion = observed_number(facts.get("estimate_dispersion"))
    if breadth is None:
        momentum = "UNKNOWN"
    elif breadth > 0.2:
        momentum = "ESTIMATE_MOMENTUM_UP"
    elif breadth < -0.2:
        momentum = "ESTIMATE_MOMENTUM_DOWN"
    else:
        momentum = "ESTIMATE_MOMENTUM_FLAT"
    return {
        "layer": "analyst_revision",
        "fields": fields,
        "revision_breadth": breadth,
        "revision_acceleration": acceleration,
        "dispersion": dispersion,
        "estimate_momentum": momentum,
        "status": "DATA_GAP" if total == 0 else "READY",
        "production_boundary": PRODUCTION_BOUNDARY,
    }
