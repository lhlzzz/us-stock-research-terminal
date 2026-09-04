"""Metric semantic layer. Raw units are never a research score."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .evidence import observed_number


@dataclass(frozen=True)
class MetricSpec:
    name: str
    direction: str
    normalization: str
    unit: str | None = None
    family: str = "company"
    missing: str = "UNKNOWN"
    confidence: float | None = None


COMPANY_SPECS: dict[str, MetricSpec] = {
    "revenue": MetricSpec("revenue", "higher_better", "relative", "USD", "company"),
    "revenue_growth": MetricSpec("revenue_growth", "higher_better", "relative", "ratio", "company"),
    "gross_margin": MetricSpec("gross_margin", "higher_better", "bounded", "ratio", "company"),
    "operating_margin": MetricSpec("operating_margin", "higher_better", "bounded", "ratio", "company"),
    "net_margin": MetricSpec("net_margin", "higher_better", "bounded", "ratio", "company"),
    "free_cash_flow": MetricSpec("free_cash_flow", "higher_better", "relative", "USD", "company"),
    "fcf_margin": MetricSpec("fcf_margin", "higher_better", "bounded", "ratio", "company"),
    "roe": MetricSpec("roe", "higher_better", "bounded", "ratio", "company"),
    "roic": MetricSpec("roic", "higher_better", "bounded", "ratio", "company"),
    "roa": MetricSpec("roa", "higher_better", "bounded", "ratio", "company"),
    "debt_to_equity": MetricSpec("debt_to_equity", "lower_better", "relative", "multiple", "company"),
    "net_debt": MetricSpec("net_debt", "lower_better", "relative", "USD", "company"),
    "cash": MetricSpec("cash", "higher_better", "relative", "USD", "company"),
    "shares_outstanding": MetricSpec("shares_outstanding", "neutral", "none", "count", "company"),
    "share_dilution": MetricSpec("share_dilution", "lower_better", "relative", "ratio", "company"),
    "sbc": MetricSpec("sbc", "lower_better", "relative", "USD", "company"),
    "buyback": MetricSpec("buyback", "higher_better", "relative", "USD", "company"),
    "backlog": MetricSpec("backlog", "higher_better", "relative", "USD", "company"),
    "guidance": MetricSpec("guidance", "higher_better", "relative", "text", "company"),
}

CAPITAL_SPECS: dict[str, MetricSpec] = {
    "volume": MetricSpec("volume", "higher_better", "relative", "shares", "capital"),
    "turnover": MetricSpec("turnover", "higher_better", "relative", "ratio", "capital"),
    "relative_strength": MetricSpec("relative_strength", "higher_better", "relative", "ratio", "capital"),
    "momentum": MetricSpec("momentum", "higher_better", "relative", "ratio", "capital"),
    "acceleration": MetricSpec("acceleration", "higher_better", "relative", "ratio", "capital"),
    "short_interest": MetricSpec("short_interest", "lower_better", "bounded", "ratio", "capital"),
    "days_to_cover": MetricSpec("days_to_cover", "lower_better", "relative", "days", "capital"),
    "put_call_ratio": MetricSpec("put_call_ratio", "lower_better", "relative", "ratio", "capital"),
    "iv_rank": MetricSpec("iv_rank", "neutral", "bounded", "ratio", "capital"),
}

RISK_SPECS: dict[str, MetricSpec] = {
    "debt": MetricSpec("debt", "lower_better", "relative", "USD", "risk"),
    "leverage": MetricSpec("leverage", "lower_better", "relative", "multiple", "risk"),
    "drawdown": MetricSpec("drawdown", "lower_better", "bounded", "ratio", "risk"),
    "volatility": MetricSpec("volatility", "lower_better", "relative", "ratio", "risk"),
    "short_interest": MetricSpec("short_interest", "lower_better", "bounded", "ratio", "risk"),
    "valuation": MetricSpec("valuation", "lower_better", "relative", "multiple", "risk"),
    "concentration": MetricSpec("concentration", "lower_better", "bounded", "ratio", "risk"),
    "gap_risk": MetricSpec("gap_risk", "lower_better", "bounded", "ratio", "risk"),
    "drawdown_risk": MetricSpec("drawdown_risk", "lower_better", "bounded", "ratio", "risk"),
    "liquidity_risk": MetricSpec("liquidity_risk", "lower_better", "bounded", "ratio", "risk"),
    "event_risk": MetricSpec("event_risk", "lower_better", "bounded", "ratio", "risk"),
    "short_pressure": MetricSpec("short_pressure", "lower_better", "bounded", "ratio", "risk"),
}

METRIC_SPECS: dict[str, MetricSpec] = {**COMPANY_SPECS, **CAPITAL_SPECS, **RISK_SPECS}

PRENORMALIZED_FAMILIES = {
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
    "capital_behavior_score",
    "pressure",
    "absorption",
    "price_control",
    "control_asymmetry",
    "distribution",
    "trap",
    "trend",
    "momentum",
    "relative_strength",
    "volume",
    "volatility",
    "breakout",
    "reversal",
}


def get_spec(name: str) -> MetricSpec | None:
    return METRIC_SPECS.get(name)


def research_median(values: Sequence[Any] | None) -> float | None:
    numbers = [float(item) for item in (values or []) if item is not None]
    if not numbers:
        return None
    return round(float(statistics.median(numbers)), 6)


def normalize_metric(
    name: str,
    value: Any,
    spec: MetricSpec | None = None,
    *,
    purpose: str = "quality",
) -> float | None:
    """Map a typed metric onto [0, 1], or refuse mixed/raw units."""
    number = observed_number(value)
    if number is None:
        return None
    spec = spec or get_spec(name)
    if spec is None:
        if 0.0 <= number <= 1.0 and (
            name in PRENORMALIZED_FAMILIES or name.endswith(("_score", "_quality", "_risk", "_strength"))
        ):
            if purpose == "risk":
                return float(number)
            return float(number)
        return None
    if spec.normalization == "none" or spec.direction == "neutral":
        return None
    if spec.normalization == "relative":
        if 0.0 <= number <= 1.0 and name in PRENORMALIZED_FAMILIES:
            unit = float(number)
            if purpose == "risk":
                return round(1.0 - unit, 6) if spec.direction == "higher_better" else round(unit, 6)
            return round(1.0 - unit, 6) if spec.direction == "lower_better" else round(unit, 6)
        return None
    if spec.normalization == "bounded":
        if spec.unit in {"ratio", None} and -1.5 <= number <= 1.5:
            unit = max(0.0, min(1.0, float(number) if number >= 0 else 0.0))
        elif 0.0 <= number <= 1.0:
            unit = float(number)
        else:
            return None
        if purpose == "risk":
            if spec.direction == "lower_better":
                return round(unit, 6)
            return round(1.0 - unit, 6)
        if spec.direction == "lower_better":
            return round(1.0 - unit, 6)
        return round(unit, 6)
    return None


def score_research_metrics(items: Iterable[Mapping[str, Any]], *, purpose: str = "quality") -> dict[str, Any]:
    """Score only same-family, same-unit, direction-aware metrics.

    Raw dollars, percentages, multiples, and counts are never averaged together.
    Missing metrics stay UNKNOWN. Relative metrics without a peer set are gaps.
    """
    values: list[float] = []
    confidences: list[float] = []
    gaps: list[str] = []
    refused: list[str] = []
    families: set[str] = set()
    units: set[str] = set()
    for item in items:
        name = str(item.get("name") or item.get("metric") or "")
        spec = get_spec(name)
        number = observed_number(item.get("value"))
        if number is None or item.get("semantic") == "UNKNOWN":
            gaps.append(name or "unnamed")
            continue
        if spec is not None:
            families.add(spec.family)
        normalized = normalize_metric(name, number, spec, purpose=purpose)
        if normalized is None:
            refused.append(name)
            gaps.append(name)
            continue
        if spec is not None and spec.unit:
            units.add(spec.unit)
        values.append(normalized)
        if item.get("confidence") is not None:
            confidences.append(float(item["confidence"]))
    if len(units) > 1:
        return {
            "score": None,
            "confidence": None,
            "gaps": gaps,
            "refused": refused + ["mixed_units"],
            "reason": "different units cannot be averaged",
            "semantic": "UNKNOWN",
        }
    if not values:
        return {
            "score": None,
            "confidence": None,
            "gaps": gaps,
            "refused": refused,
            "reason": "no direction-normalized metrics",
            "semantic": "UNKNOWN",
        }
    score = round(sum(values) / len(values), 4)
    confidence = (
        round(sum(confidences) / len(confidences), 4)
        if confidences
        else round(len(values) / max(1, len(values) + len(gaps)), 4)
    )
    return {
        "score": score,
        "confidence": confidence,
        "gaps": gaps,
        "refused": refused,
        "reason": None,
        "semantic": "DERIVED",
    }


def score_from_claims(
    claims: Mapping[str, Mapping[str, Any]],
    *,
    purpose: str = "quality",
) -> tuple[float | None, float | None, list[str]]:
    items = []
    for name, item in (claims or {}).items():
        payload = dict(item or {})
        payload["name"] = name
        items.append(payload)
    result = score_research_metrics(items, purpose=purpose)
    return result["score"], result["confidence"], list(result["gaps"])


def quality_stance(score: float | None) -> str:
    if score is None:
        return "UNKNOWN"
    value = float(score)
    if value >= 0.70:
        return "STRONG"
    if value >= 0.55:
        return "BULLISH"
    if value >= 0.45:
        return "NEUTRAL"
    if value >= 0.30:
        return "WEAK"
    return "BEARISH"


def market_stance(score: float | None) -> str:
    return quality_stance(score)


def capital_stance(score: float | None) -> str:
    return quality_stance(score)


def risk_stance(score: float | None) -> dict[str, Any]:
    """Higher risk score is worse. Never maps high risk to STRONG."""
    if score is None:
        return {"score": None, "risk_level": "UNKNOWN", "stance": "UNKNOWN", "stance_alias": "UNKNOWN"}
    value = float(score)
    if value >= 0.70:
        level, stance = "HIGH", "CAUTION"
    elif value >= 0.55:
        level, stance = "ELEVATED", "CAUTION"
    elif value >= 0.45:
        level, stance = "MODERATE", "NEUTRAL"
    elif value >= 0.30:
        level, stance = "LOW", "FAVORABLE"
    else:
        level, stance = "LOW", "FAVORABLE"
    if value >= 0.70:
        stance_alias = "HIGH_RISK"
    elif value < 0.30:
        stance_alias = "LOW_RISK"
    else:
        stance_alias = stance
    return {
        "score": round(value, 4),
        "risk_level": level,
        "stance": stance,
        "stance_alias": stance_alias,
    }


def metric_record(
    name: str,
    value: Any,
    *,
    source: str,
    effective_date: str | None = None,
    as_of: str | None = None,
    semantic: str = "OBSERVED",
) -> dict[str, Any]:
    spec = get_spec(name)
    number = observed_number(value)
    missing = number is None and value in (None, "")
    return {
        "name": name,
        "value": None if missing else (number if number is not None else value),
        "unit": None if spec is None else spec.unit,
        "direction": None if spec is None else spec.direction,
        "normalization": None if spec is None else spec.normalization,
        "source": source,
        "effective_date": effective_date,
        "as_of": as_of,
        "semantic": "UNKNOWN" if missing else semantic,
        "missing": "UNKNOWN" if missing else None,
    }
