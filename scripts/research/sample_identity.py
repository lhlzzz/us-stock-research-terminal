"""Replay / IC sample identity belongs to ticket lineage, not ticker."""
from __future__ import annotations

from typing import Any, Iterable, Mapping


class DuplicateSampleError(ValueError):
    """Same ticket + horizon + replay_date cannot produce two samples."""


def sample_id(
    *,
    ticket_id: Any,
    replay_horizon: Any,
    replay_date: Any,
    symbol: str | None = None,
    output_date: Any = None,
) -> str:
    if ticket_id in (None, ""):
        raise ValueError("sample identity requires ticket_id")
    if replay_horizon in (None, ""):
        raise ValueError("sample identity requires replay_horizon")
    if replay_date in (None, ""):
        raise ValueError("sample identity requires replay_date")
    parts = [str(ticket_id), str(replay_horizon), str(replay_date)[:10]]
    if symbol:
        parts.append(str(symbol).upper())
    if output_date:
        parts.append(str(output_date)[:10])
    return "|".join(parts)


def assert_unique_samples(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    seen: dict[str, Mapping[str, Any]] = {}
    identities: list[str] = []
    for row in rows:
        identity = sample_id(
            ticket_id=row.get("ticket_id") or row.get("id"),
            replay_horizon=row.get("replay_horizon") or row.get("horizon_days"),
            replay_date=row.get("replay_date") or row.get("as_of_date") or row.get("output_date"),
            symbol=row.get("symbol"),
            output_date=row.get("output_date"),
        )
        if identity in seen:
            raise DuplicateSampleError(identity)
        seen[identity] = row
        identities.append(identity)
    return identities
