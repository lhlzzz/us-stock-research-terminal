"""Canonical temporal model for research claims and market bars."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping

from market_calendar import CALENDAR, ET

BAR_DAILY_COMPLETE = "DAILY_COMPLETE"
BAR_DAILY_PARTIAL = "DAILY_PARTIAL"
BAR_INTRADAY = "INTRADAY"
BAR_SNAPSHOT = "SNAPSHOT"
BAR_INTRADAY_PARTIAL = "INTRADAY_PARTIAL"

TEMPORAL_FIELDS = (
    "published_at",
    "effective_date",
    "retrieved_at",
    "as_of",
    "session_date",
    "event_time",
    "available_at",
)


def _as_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text[:10] if len(text) >= 10 else None


def temporal_record(
    *,
    published_at: Any = None,
    effective_date: Any = None,
    retrieved_at: Any = None,
    as_of: Any = None,
    session_date: Any = None,
    event_time: Any = None,
    available_at: Any = None,
) -> dict[str, Any]:
    published = _as_date(published_at)
    effective = _as_date(effective_date) or published
    retrieved = _as_date(retrieved_at)
    as_of_s = _as_date(as_of)
    available = _as_date(available_at)
    return {
        "published_at": published,
        "effective_date": effective,
        "retrieved_at": retrieved,
        "as_of": as_of_s,
        "session_date": _as_date(session_date),
        "event_time": str(event_time) if event_time not in (None, "") else None,
        "available_at": available,
        "published_at_is_not_retrieved_at": published != retrieved if published and retrieved else True,
        "effective_date_is_not_as_of": effective != as_of_s if effective and as_of_s else True,
    }


def historical_claim_eligible(record: Mapping[str, Any] | None, *, as_of: Any = None) -> dict[str, Any]:
    payload = dict(record or {})
    as_of_s = _as_date(as_of or payload.get("as_of") or payload.get("as_of_date"))
    published = _as_date(payload.get("published_at"))
    effective = _as_date(payload.get("effective_date") or payload.get("source_date"))
    available = _as_date(payload.get("available_at"))
    retrieved = _as_date(payload.get("retrieved_at"))
    blocked = False
    reasons = []
    if effective and as_of_s and effective > as_of_s:
        blocked = True
        reasons.append("effective_date > as_of")
    if published and as_of_s and published > as_of_s:
        blocked = True
        reasons.append("published_at > as_of")
    if available and as_of_s and available > as_of_s:
        blocked = True
        reasons.append("available_at > as_of")
    retrieved_after = bool(retrieved and as_of_s and retrieved > as_of_s)
    return {
        "eligible": not blocked,
        "blocked": blocked,
        "reasons": reasons,
        "retrieved_at_after_as_of": retrieved_after,
        "retrieved_at_after_as_of_is_not_violation": True,
        "as_of": as_of_s,
        "published_at": published,
        "effective_date": effective,
        "available_at": available,
        "retrieved_at": retrieved,
    }


def classify_bar(
    *,
    bar_type: str | None = None,
    is_complete: bool | None = None,
    session_status: str | None = None,
    coverage_start: Any = None,
    coverage_end: Any = None,
    market_open: bool | None = None,
    market_closed: bool | None = None,
) -> dict[str, Any]:
    kind = str(bar_type or "").upper() or BAR_SNAPSHOT
    complete = bool(is_complete) if is_complete is not None else kind == BAR_DAILY_COMPLETE
    if kind in {BAR_INTRADAY, BAR_INTRADAY_PARTIAL, BAR_SNAPSHOT, BAR_DAILY_PARTIAL}:
        complete = False
    if kind == BAR_DAILY_COMPLETE:
        complete = True
    return {
        "bar_type": kind,
        "is_complete": complete,
        "session_status": session_status,
        "market_open": market_open,
        "market_closed": market_closed,
        "coverage_start": None if coverage_start in (None, "") else str(coverage_start),
        "coverage_end": None if coverage_end in (None, "") else str(coverage_end),
        "usable_for_daily_factors": complete and kind == BAR_DAILY_COMPLETE,
        "usable_for_daily_ranking": complete and kind == BAR_DAILY_COMPLETE,
        "usable_for_historical_daily_replay": complete and kind == BAR_DAILY_COMPLETE,
        "usable_for_forward_outcome_anchor": complete and kind == BAR_DAILY_COMPLETE,
    }


def daily_bar_gate(bar: Mapping[str, Any] | None) -> bool:
    payload = classify_bar(**{
        key: (bar or {}).get(key)
        for key in ("bar_type", "is_complete", "session_status", "coverage_start", "coverage_end", "market_open", "market_closed")
    })
    return bool(payload["usable_for_daily_factors"])


def quote_session_date(now: datetime | None = None) -> str:
    current = (now or datetime.now(ET)).astimezone(ET)
    return current.date().isoformat()


def compatible_sessions(left: Any, right: Any) -> bool:
    a = _as_date(left)
    b = _as_date(right)
    return bool(a and b and a == b)
