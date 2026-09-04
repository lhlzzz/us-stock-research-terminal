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


SHORT_STATES = ("short_build", "short_pressure", "forced_cover", "neutral")


def short_intelligence(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    fields = {name: facts.get(name) for name in SHORT_FIELDS}
    change = observed_number(facts.get("short_interest_change"))
    si = observed_number(facts.get("short_interest"))
    tightness = observed_number(facts.get("borrow_tightness"))
    dtc = observed_number(facts.get("days_to_cover"))
    price_change = observed_number(facts.get("price_change"))
    volume = observed_number(facts.get("volume") or facts.get("relative_volume"))
    missing = all(item is None for item in (change, si, tightness, dtc))
    # Covering while borrow is tight and price/volume confirm is forced_cover.
    # Must be checked before tightness-only short_pressure, or it is unreachable.
    if (
        change is not None
        and change < 0
        and tightness is not None
        and tightness >= 0.7
        and (
            (price_change is not None and price_change > 0)
            or (volume is not None and volume >= 1.5)
        )
    ):
        state = "forced_cover"
    elif change is not None and change > 0:
        state = "short_build"
    elif tightness is not None and tightness >= 0.7:
        state = "short_pressure"
    elif dtc is not None and dtc >= 5 and si is not None and si >= 0.15:
        state = "short_pressure"
    elif missing:
        state = "neutral"
    else:
        state = "neutral"
    return {
        "layer": "short_borrow",
        "role": "Capital / Risk Context",
        "fields": fields,
        "state": state,
        "states": list(SHORT_STATES),
        "high_si_is_not_bullish": True,
        "stance": "UNKNOWN",
        "status": "DATA_GAP" if si is None and change is None and tightness is None else "READY",
        "missing_is_not_zero": True,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def analyst_revision(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    fields = {name: facts.get(name) for name in ANALYST_FIELDS}
    ups = observed_number(facts.get("analyst_upgrades"))
    downs = observed_number(facts.get("analyst_downgrades"))
    if ups is None and downs is None:
        total = None
        breadth = None
        missing = "UNKNOWN"
    else:
        missing = None
        up_count = 0.0 if ups is None else ups
        down_count = 0.0 if downs is None else downs
        total = up_count + down_count
        breadth = None if total == 0 else round((up_count - down_count) / total, 4)
    acceleration = observed_number(facts.get("revision_acceleration"))
    dispersion = observed_number(facts.get("estimate_dispersion"))
    surprise = facts.get("earnings_surprise")
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
        "analyst_upgrades": ups,
        "analyst_downgrades": downs,
        "earnings_surprise": surprise if surprise not in (None, "") else None,
        "revision_breadth": breadth,
        "revision_acceleration": acceleration,
        "dispersion": dispersion,
        "estimate_momentum": momentum,
        "missing": missing,
        "missing_is_not_zero": True,
        "status": "DATA_GAP" if total in (None, 0) else "READY",
        "production_boundary": PRODUCTION_BOUNDARY,
    }
