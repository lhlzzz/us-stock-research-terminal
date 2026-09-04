"""Research data providers. Empty is DATA_GAP, never 'no risk'."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping, Protocol

from .boundary import PRODUCTION_BOUNDARY
from .evidence import claim


DATA_GAP = "DATA_GAP"
NOT_INGESTED = "not ingested"
NOT_VALIDATED = "not validated"
NOT_AVAILABLE = "not available"

INGESTION_STAGES = (
    "raw",
    "normalized",
    "validated",
    "timestamped",
    "effective_dated",
    "persisted",
    "research_claim",
)


def _as_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value)[:10]
    return text if len(text) == 10 else None


def provider_record(
    *,
    symbol: str | None = None,
    as_of: str | None = None,
    published_at: str | None = None,
    effective_date: str | None = None,
    retrieved_at: str | None = None,
    source: str | None = None,
    source_type: str | None = None,
    status: str = DATA_GAP,
    facts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    label = str(status or DATA_GAP).upper()
    if label not in {"OBSERVED", DATA_GAP, "ERROR", "READY", "BLOCKED"}:
        label = DATA_GAP
    if label == "READY":
        label = "OBSERVED"
    return {
        "symbol": symbol,
        "as_of": as_of,
        "published_at": published_at,
        "effective_date": effective_date or published_at,
        "retrieved_at": retrieved_at,
        "source": source,
        "source_type": source_type or source,
        "status": label,
        "facts": dict(facts or {}),
    }


def gap_payload(layer: str, *, reason: str = NOT_INGESTED, symbol: str | None = None, as_of: str | None = None) -> dict[str, Any]:
    return {
        **provider_record(symbol=symbol, as_of=as_of, source=layer, status=DATA_GAP, facts={}),
        "layer": layer,
        "symbol": symbol,
        "as_of": as_of,
        "status": DATA_GAP,
        "reason": reason,
        "not_ingested": reason == NOT_INGESTED,
        "not_validated": reason == NOT_VALIDATED,
        "not_available": reason == NOT_AVAILABLE,
        "empty_is_not_no_risk": True,
        "empty_is_not_no_filing": True,
        "empty_is_not_no_industry_relationship": True,
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def ingest_record(
    raw: Any,
    *,
    source: str,
    source_url: str | None = None,
    retrieved_at: str | None = None,
    effective_date: str | None = None,
    as_of: str | None = None,
    published_at: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    """Unify raw → claim. Future effective dates are blocked.

    ``retrieved_at > as_of`` does not drop already-public data.
    Filter uses published/effective dates, not retrieval time.
    """
    published = _as_date(published_at) or _as_date(effective_date)
    effective = _as_date(effective_date) or published
    as_of_s = _as_date(as_of)
    retrieved = _as_date(retrieved_at)
    blocked = bool(effective and as_of_s and effective > as_of_s)
    retrieved_after_as_of = bool(retrieved and as_of_s and retrieved > as_of_s)
    status = "BLOCKED" if blocked else "READY" if raw not in (None, "") else DATA_GAP
    payload = {
        "raw": raw if not blocked else None,
        "source": source,
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "published_at": published,
        "effective_date": effective,
        "as_of": as_of_s,
        "confidence": None if blocked else confidence,
        "status": status,
        "lifecycle": list(INGESTION_STAGES),
        "retrieved_after_as_of_is_not_future_leakage": True,
        "used_published_not_retrieved_for_as_of": True,
        "dropped_because_retrieved_late": False,
        "future_leakage": blocked,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
    if blocked:
        payload["reason"] = "effective_date > as_of"
        payload["claim"] = claim(
            None,
            semantic="UNKNOWN",
            source=source,
            source_type="market_research",
            effective_date=effective,
            as_of_date=as_of_s,
            reason="effective_date > as_of",
        )
        return payload
    if retrieved_after_as_of and not blocked:
        payload["note"] = "retrieved_at after as_of; published/effective still eligible"
    if raw in (None, ""):
        payload["claim"] = claim(
            None,
            semantic="UNKNOWN",
            source=source,
            source_type="market_research",
            effective_date=effective,
            as_of_date=as_of_s,
            reason=NOT_AVAILABLE,
        )
        return payload
    payload["claim"] = claim(
        raw,
        semantic="OBSERVED",
        source=source,
        source_type="market_research",
        effective_date=effective,
        as_of_date=as_of_s,
        confidence=confidence,
    )
    return payload


class CompanyDataProvider(Protocol):
    def get(self, symbol: str, *, as_of: str | None = None) -> dict[str, Any]:
        ...


class SECDataProvider(Protocol):
    def get(self, symbol: str, *, as_of: str | None = None) -> dict[str, Any]:
        ...


class EarningsDataProvider(Protocol):
    def get(self, symbol: str, *, as_of: str | None = None) -> dict[str, Any]:
        ...


class IndustryGraphProvider(Protocol):
    def get(self, name: str, *, as_of: str | None = None) -> dict[str, Any]:
        ...


class ChokepointProvider(Protocol):
    def get(self, name: str, *, as_of: str | None = None) -> dict[str, Any]:
        ...


class GapCompanyDataProvider:
    def get(self, symbol: str, *, as_of: str | None = None) -> dict[str, Any]:
        return gap_payload("company", symbol=symbol, as_of=as_of, reason=NOT_INGESTED)


class GapSECDataProvider:
    def get(self, symbol: str, *, as_of: str | None = None) -> dict[str, Any]:
        return gap_payload("sec", symbol=symbol, as_of=as_of, reason=NOT_INGESTED)


class GapEarningsDataProvider:
    def get(self, symbol: str, *, as_of: str | None = None) -> dict[str, Any]:
        return gap_payload("earnings", symbol=symbol, as_of=as_of, reason=NOT_INGESTED)


class GapIndustryGraphProvider:
    def get(self, name: str, *, as_of: str | None = None) -> dict[str, Any]:
        return gap_payload("industry_graph", symbol=name, as_of=as_of, reason=NOT_INGESTED)


class GapChokepointProvider:
    def get(self, name: str, *, as_of: str | None = None) -> dict[str, Any]:
        return gap_payload("chokepoint", symbol=name, as_of=as_of, reason=NOT_INGESTED)


DEFAULT_PROVIDERS = {
    "company": GapCompanyDataProvider(),
    "sec": GapSECDataProvider(),
    "earnings": GapEarningsDataProvider(),
    "industry": GapIndustryGraphProvider(),
    "chokepoint": GapChokepointProvider(),
}
