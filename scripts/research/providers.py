"""Research data providers. Empty is DATA_GAP, never 'no risk'."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Mapping, Protocol
from uuid import uuid4

from .boundary import PRODUCTION_BOUNDARY
from .evidence import claim


DATA_GAP = "DATA_GAP"
INFRA_FAILURE = "INFRA_FAILURE"
NOT_INGESTED = "not ingested"
NOT_VALIDATED = "not validated"
NOT_AVAILABLE = "not available"
ERROR_CLASSES = (
    "NETWORK",
    "RATE_LIMIT",
    "AUTH",
    "NOT_FOUND",
    "PARSE",
    "SCHEMA",
    "TEMPORAL",
    "DATA_QUALITY",
    "INFRA_FAILURE",
    "UNKNOWN",
)
CROSS_SEMANTIC_FORBIDDEN = (
    ("realtime_quote", "historical_daily_close"),
    ("news", "sec_filing"),
    ("current_universe", "historical_universe"),
)
PROVIDER_ATTEMPTS: list[dict[str, Any]] = []

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
    if label not in {"OBSERVED", "DERIVED", DATA_GAP, "ERROR", "READY", "BLOCKED", "UNKNOWN", INFRA_FAILURE}:
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


class GapEstimateProvider:
    def get(self, symbol: str, *, as_of: str | None = None) -> dict[str, Any]:
        return gap_payload("estimate_revision", symbol=symbol, as_of=as_of, reason=NOT_INGESTED)


class GapUniverseProvider:
    def get(self, name: str, *, as_of: str | None = None) -> dict[str, Any]:
        return gap_payload("universe", symbol=name, as_of=as_of, reason=NOT_INGESTED)


DEFAULT_PROVIDERS = {
    "company": GapCompanyDataProvider(),
    "sec": GapSECDataProvider(),
    "earnings": GapEarningsDataProvider(),
    "estimates": GapEstimateProvider(),
    "industry": GapIndustryGraphProvider(),
    "chokepoint": GapChokepointProvider(),
    "universe": GapUniverseProvider(),
}


def classify_provider_error(exc: BaseException | None, *, http_status: int | None = None) -> str:
    if http_status == 429:
        return "RATE_LIMIT"
    if http_status in {401, 403}:
        return "AUTH"
    if http_status == 404:
        return "NOT_FOUND"
    if http_status is not None and http_status >= 500:
        return "NETWORK"
    text = str(exc or "").lower()
    if "timeout" in text or "network" in text or "connection" in text:
        return "NETWORK"
    if "parse" in text or "json" in text:
        return "PARSE"
    if "schema" in text:
        return "SCHEMA"
    if "as_of" in text or "temporal" in text:
        return "TEMPORAL"
    if exc is None:
        return "UNKNOWN"
    return "UNKNOWN"


def record_provider_attempt(
    *,
    provider: str,
    request: str,
    symbol: str | None = None,
    entity_id: str | None = None,
    as_of: str | None = None,
    attempt: int = 1,
    started_at: str | None = None,
    completed_at: str | None = None,
    status: str = DATA_GAP,
    http_status: int | None = None,
    source: str | None = None,
    fallback: str | None = None,
    fallback_used: bool = False,
    error: str | None = None,
    error_class: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload = {
        "attempt_id": str(uuid4()),
        "provider": provider,
        "request": request,
        "symbol": None if symbol in (None, "") else str(symbol).upper(),
        "entity_id": entity_id,
        "as_of": as_of,
        "attempt": attempt,
        "started_at": started_at or now,
        "completed_at": completed_at or now,
        "status": status,
        "http_status": http_status,
        "source": source or provider,
        "fallback": fallback,
        "fallback_used": fallback_used,
        "error": error,
        "error_class": error_class if error_class in ERROR_CLASSES else (classify_provider_error(None, http_status=http_status) if error else None),
        "silent_fallback": False,
    }
    PROVIDER_ATTEMPTS.append(payload)
    return payload


def provider_attempts(*, symbol: str | None = None, provider: str | None = None) -> list[dict[str, Any]]:
    rows = list(PROVIDER_ATTEMPTS)
    if symbol:
        rows = [row for row in rows if row.get("symbol") == str(symbol).upper()]
    if provider:
        rows = [row for row in rows if row.get("provider") == provider]
    return rows


def clear_provider_attempts() -> None:
    PROVIDER_ATTEMPTS.clear()


def forbid_cross_semantic_fallback(from_kind: str, to_kind: str) -> dict[str, Any]:
    pair = (str(from_kind), str(to_kind))
    blocked = pair in CROSS_SEMANTIC_FORBIDDEN or (pair[1], pair[0]) in CROSS_SEMANTIC_FORBIDDEN
    return {
        "from": from_kind,
        "to": to_kind,
        "blocked": blocked,
        "status": "ERROR" if blocked else "OK",
        "reason": "cross-semantic fallback forbidden" if blocked else None,
    }
