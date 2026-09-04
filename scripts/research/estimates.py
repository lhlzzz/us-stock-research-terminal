"""Estimate revision history. Derived windows must trace to raw observations."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Iterable, Mapping

from .boundary import PRODUCTION_BOUNDARY, assert_research_only
from .evidence import observed_number
from .fundamentals import estimate_revision_direction
from .providers import DATA_GAP
from .temporal import historical_claim_eligible

REVISION_DIRECTIONS = ("UP", "DOWN", "FLAT", "UNKNOWN")


def _as_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value)[:10]
    return text if len(text) == 10 else None


def estimate_revision(
    *,
    symbol: str,
    metric: str,
    estimate: Any,
    estimate_date: str | None,
    effective_date: str | None = None,
    source: str | None = None,
    analyst_count: int | None = None,
    revision_direction: str | None = None,
) -> dict[str, Any]:
    direction = str(revision_direction or "UNKNOWN").upper()
    if direction not in REVISION_DIRECTIONS:
        direction = "UNKNOWN"
    value = observed_number(estimate)
    status = "OBSERVED" if source and value is not None else DATA_GAP if not source else "UNKNOWN"
    return {
        "symbol": str(symbol).upper(),
        "metric": metric,
        "estimate": value,
        "estimate_date": _as_date(estimate_date),
        "effective_date": _as_date(effective_date) or _as_date(estimate_date),
        "source": source,
        "analyst_count": analyst_count,
        "revision_direction": direction,
        "status": status,
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def revisions_as_of(history: Iterable[Mapping[str, Any]] | None, *, as_of: str) -> list[dict[str, Any]]:
    visible = []
    for row in history or []:
        payload = dict(row)
        gate = historical_claim_eligible(
            {
                "published_at": payload.get("estimate_date") or payload.get("published_at"),
                "effective_date": payload.get("effective_date") or payload.get("estimate_date"),
                "available_at": payload.get("available_at") or payload.get("effective_date") or payload.get("estimate_date"),
                "retrieved_at": payload.get("retrieved_at"),
            },
            as_of=as_of,
        )
        if not gate["eligible"]:
            payload["replay_status"] = "DO_NOT_USE_IN_HISTORICAL_REPLAY"
            continue
        visible.append(payload)
    return sorted(visible, key=lambda item: str(item.get("estimate_date") or item.get("effective_date") or ""))


def revision_direction_from_history(history: Iterable[Mapping[str, Any]] | None, *, as_of: str) -> dict[str, Any]:
    visible = revisions_as_of(history, as_of=as_of)
    values = [observed_number(item.get("estimate") or item.get("value")) for item in visible]
    derived = estimate_revision_direction(values)
    return {
        **derived,
        "as_of": as_of,
        "observations": visible,
        "raw_observation_count": len(visible),
        "semantic": derived.get("semantic"),
        "produces_pick": False,
    }


def _window_end(as_of: str, days: int) -> str:
    cutoff = date.fromisoformat(as_of[:10]) - timedelta(days=days)
    return cutoff.isoformat()


def derived_revision_windows(history: Iterable[Mapping[str, Any]] | None, *, as_of: str) -> dict[str, Any]:
    visible = revisions_as_of(history, as_of=as_of)
    windows = {}
    for days in (30, 60, 90):
        start = _window_end(as_of, days)
        rows = [row for row in visible if str(row.get("estimate_date") or "") >= start]
        values = [observed_number(row.get("estimate") or row.get("value")) for row in rows]
        values = [item for item in values if item is not None]
        derived = estimate_revision_direction(values)
        windows[f"{days}D"] = {
            "window_days": days,
            "start": start,
            "as_of": as_of,
            "direction": derived["estimate_revision_direction"],
            "observations": rows,
            "raw_values": values,
            "semantic": "DERIVED" if derived["estimate_revision_direction"] != "UNKNOWN" else "UNKNOWN",
            "status": "DERIVED" if rows else DATA_GAP,
        }
    return {
        "as_of": as_of,
        "windows": windows,
        "derived_from_raw_observations": True,
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def estimate_revision_bundle(
    *,
    symbol: str,
    as_of: str,
    history: Iterable[Mapping[str, Any]] | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    ticker = str(symbol).upper()
    rows = [dict(item) for item in history or []]
    if not rows:
        payload = {
            "symbol": ticker,
            "as_of": as_of,
            "status": DATA_GAP,
            "reason": "estimate revision history not ingested",
            "history": [],
            "direction": "UNKNOWN",
            "windows": derived_revision_windows([], as_of=as_of)["windows"],
            "source": source,
            "produces_pick": False,
            "production_boundary": PRODUCTION_BOUNDARY,
        }
        assert_research_only(payload)
        return payload
    visible = revisions_as_of(rows, as_of=as_of)
    direction = revision_direction_from_history(rows, as_of=as_of)
    windows = derived_revision_windows(rows, as_of=as_of)
    payload = {
        "symbol": ticker,
        "as_of": as_of,
        "status": "OBSERVED" if visible and source else DATA_GAP if not source else "UNKNOWN",
        "history": visible,
        "direction": direction["estimate_revision_direction"],
        "windows": windows["windows"],
        "source": source,
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
    assert_research_only(payload)
    return payload
