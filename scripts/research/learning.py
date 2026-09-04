"""Historical ticket learning with as-of isolation and data-quality gates."""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from capital.historical_bootstrap import HORIZONS, classify_lineage, tracking_returns
from capital.learning import MIN_CONDITION_SAMPLES, MIN_SAMPLES
from .boundary import PRODUCTION_BOUNDARY
from .sample_identity import sample_id
from .memory import filter_obsidian_as_of
from .outcomes import completed_horizon_returns, independent_price_outcomes


DATA_QUALITY_GATES = (
    "valid_lineage",
    "valid_as_of_data",
    "no_future_leakage",
    "completed_outcome",
    "no_conflicting_outcome",
    "valid_obsidian_effective_date",
    "valid_evidence",
    "minimum_sample_support",
)

CENSUS_DIR = Path(__file__).resolve().parents[2] / "research" / "xiaomei-learning"


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def history_census(
    tickets: Iterable[Mapping[str, Any]],
    tracking: Iterable[Mapping[str, Any]],
    *,
    research_runs: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    tickets = [dict(row) for row in tickets]
    tracking = [dict(row) for row in tracking]
    symbols = sorted({str(row.get("symbol") or "").upper() for row in tickets if row.get("symbol")})
    dates = sorted({str(_as_date(row.get("as_of_date")) or "") for row in tickets if _as_date(row.get("as_of_date"))})
    completed = [row for row in tracking if str(row.get("check_status") or "").lower() == "completed"]
    by_horizon = Counter(int(row.get("horizon_days") or 0) for row in completed if row.get("horizon_days"))
    pending = [row for row in tracking if str(row.get("check_status") or "").lower() != "completed"]
    grouped: dict[tuple[Any, int], list[float]] = defaultdict(list)
    conflicts = []
    for row in completed:
        ticket_id = row.get("ticket_id")
        horizon = int(row.get("horizon_days") or 0)
        value = row.get("forward_return")
        if ticket_id in (None, "") or horizon not in HORIZONS or value is None:
            continue
        grouped[(ticket_id, horizon)].append(float(value))
    for key, values in grouped.items():
        unique = sorted(set(round(v, 6) for v in values))
        if len(unique) > 1:
            conflicts.append({"ticket_id": key[0], "horizon": key[1], "values": unique})
    duplicate_tickets = sum(
        1 for _, count in Counter((str(r.get("symbol")), str(_as_date(r.get("as_of_date")))) for r in tickets).items() if count > 1
    )
    payload = {
        "total_tickets": len(tickets),
        "unique_symbols": len(symbols),
        "unique_dates": len(dates),
        "date_range": {"min": dates[0] if dates else None, "max": dates[-1] if dates else None},
        "completed_forward_tracking": len(completed),
        "pending_forward_tracking": len(pending),
        "T+1": int(by_horizon.get(1, 0)),
        "T+3": int(by_horizon.get(3, 0)),
        "T+5": int(by_horizon.get(5, 0)),
        "T+10": int(by_horizon.get(10, 0)),
        "missing_outcomes": len(pending),
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "duplicate_rows": duplicate_tickets,
        "versioned_tickets": sum(1 for row in tickets if row.get("research_run_id") not in (None, "")),
        "research_runs": len(list(research_runs or [])),
        "production_boundary": PRODUCTION_BOUNDARY,
    }
    return payload


def load_history_census_from_db(conn) -> dict[str, Any]:
    from sqlalchemy import text

    tickets = [dict(row) for row in conn.execute(text(
        "SELECT id, symbol, as_of_date, output_date, research_run_id FROM tickets"
    )).mappings()]
    tracking = [dict(row) for row in conn.execute(text(
        "SELECT ticket_id, symbol, as_of_date, horizon_days, check_status, forward_return FROM forward_tracking"
    )).mappings()]
    runs = [dict(row) for row in conn.execute(text(
        "SELECT run_id FROM research_runs"
    )).mappings()]
    return history_census(tickets, tracking, research_runs=runs)


def write_history_census(payload: Mapping[str, Any], *, as_of: date | None = None) -> dict[str, Path]:
    CENSUS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = (as_of or date.today()).isoformat()
    json_path = CENSUS_DIR / f"history-census-{stamp}.json"
    md_path = CENSUS_DIR / f"history-census-{stamp}.md"
    json_path.write_text(json.dumps(_jsonable(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(
        "\n".join([
            f"# Historical Ticket Census {stamp}",
            "",
            f"- total_tickets: {payload.get('total_tickets')}",
            f"- unique_symbols: {payload.get('unique_symbols')}",
            f"- unique_dates: {payload.get('unique_dates')}",
            f"- date_range: {payload.get('date_range')}",
            f"- completed_forward_tracking: {payload.get('completed_forward_tracking')}",
            f"- T+1/3/5/10: {payload.get('T+1')}/{payload.get('T+3')}/{payload.get('T+5')}/{payload.get('T+10')}",
            f"- missing_outcomes: {payload.get('missing_outcomes')}",
            f"- conflicts: {payload.get('conflict_count')}",
            f"- duplicate_rows: {payload.get('duplicate_rows')}",
            f"- versioned_tickets: {payload.get('versioned_tickets')}",
            "",
            "candidate_id lineage: NOT_AVAILABLE on tickets table.",
            "Do not invent nearest-run or symbol-only lineage.",
        ]),
        encoding="utf-8",
    )
    return {"json": json_path, "md": md_path}


def assemble_research_sample(
    ticket: Mapping[str, Any],
    *,
    tracking_rows: Iterable[Mapping[str, Any]] | None = None,
    research_runs: Mapping[Any, Mapping[str, Any]] | None = None,
    buffett: Mapping[str, Any] | None = None,
    serenity: Mapping[str, Any] | None = None,
    capital: Mapping[str, Any] | None = None,
    obsidian_notes: Iterable[Mapping[str, Any]] | None = None,
    ohlcv=None,
    feature_as_of: date | str | None = None,
    snapshot_max_date: date | str | None = None,
) -> dict[str, Any]:
    as_of = _as_date(ticket.get("as_of_date"))
    feature_date = _as_date(feature_as_of) or as_of
    lineage = classify_lineage(ticket, research_runs or {})
    tracking = list(tracking_rows or [])
    outcome = tracking_returns(tracking) if tracking else completed_horizon_returns([])
    independent = independent_price_outcomes(ohlcv, as_of_date=as_of or date.today()) if ohlcv is not None else {}
    notes = filter_obsidian_as_of(obsidian_notes or [], as_of or date.today(), historical=True)
    leakage = False
    if feature_date and as_of and feature_date > as_of:
        leakage = True
    snapshot_date = _as_date(snapshot_max_date)
    if snapshot_date and as_of and snapshot_date > as_of:
        leakage = True
    gates = {
        "valid_lineage": lineage.get("status") == "VALID",
        "valid_as_of_data": as_of is not None and not leakage,
        "no_future_leakage": not leakage,
        "completed_outcome": bool(outcome.get("return_1d") is not None and outcome.get("return_3d") is not None and outcome.get("return_5d") is not None and outcome.get("return_10d") is not None),
        "no_conflicting_outcome": not bool(outcome.get("outcome_conflict")),
        "valid_obsidian_effective_date": all(note.get("effective_date") for note in notes) if notes else True,
        "valid_evidence": True,
        "minimum_sample_support": False,
    }
    invalid_reasons = [name for name, ok in gates.items() if name != "minimum_sample_support" and not ok]
    if ticket.get("candidate_id") in (None, ""):
        gates["candidate_id_lineage"] = False
        candidate_id_status = "NOT_AVAILABLE"
    else:
        gates["candidate_id_lineage"] = True
        candidate_id_status = "AVAILABLE"
    valid = not invalid_reasons and lineage.get("status") == "VALID"
    reason_map = {
        "valid_lineage": "MISSING_LINEAGE",
        "valid_as_of_data": "INVALID_AS_OF",
        "no_future_leakage": "FUTURE_LEAKAGE",
        "completed_outcome": "INSUFFICIENT_FORWARD_DATA",
        "no_conflicting_outcome": "OUTCOME_CONFLICT",
        "valid_obsidian_effective_date": "INVALID_OBSIDIAN_DATE",
        "valid_evidence": "INVALID_EVIDENCE",
    }
    eligibility = "VALID" if valid else reason_map.get(invalid_reasons[0], invalid_reasons[0].upper()) if invalid_reasons else "INVALID"
    replay_date = as_of.isoformat() if as_of else None
    identity = None
    if ticket.get("id") not in (None, "") and replay_date:
        identity = sample_id(
            ticket_id=ticket.get("id"),
            replay_horizon=ticket.get("horizon_days") or ticket.get("replay_horizon") or "ticket",
            replay_date=replay_date,
            symbol=ticket.get("symbol"),
            output_date=ticket.get("output_date"),
        )
    sample = {
        "ticket_id": ticket.get("id"),
        "sample_id": identity,
        "symbol": str(ticket.get("symbol") or "").upper(),
        "as_of_date": as_of.isoformat() if as_of else None,
        "feature_as_of": feature_date.isoformat() if feature_date else None,
        "label_date_rule": "label_date > ticket_as_of",
        "lineage": lineage,
        "candidate_id_status": candidate_id_status,
        "buffett_context": dict(buffett or {}),
        "serenity_context": dict(serenity or {}),
        "capital_context": dict(capital or {}),
        "obsidian_notes": notes,
        "future_outcome": outcome,
        "independent_outcome": independent,
        "state_correct_semantic": "POST_HOC_PUBLIC_DATA_INFERRED_PROXY",
        "intent_correct_semantic": "POST_HOC_PUBLIC_DATA_INFERRED_PROXY",
        "gates": gates,
        "valid": valid,
        "invalid_reasons": invalid_reasons,
        "eligibility_reason": eligibility,
        "production_boundary": PRODUCTION_BOUNDARY,
        "does_not_change_ranking": True,
    }
    return sample


def research_data_ready(
    samples: Iterable[Mapping[str, Any]],
    *,
    min_samples: int = MIN_SAMPLES,
    min_condition_samples: int = MIN_CONDITION_SAMPLES,
) -> dict[str, Any]:
    rows = [dict(row) for row in samples]
    valid = [row for row in rows if row.get("valid") or row.get("eligibility_reason") == "VALID"]
    dates = {str(row.get("as_of_date")) for row in valid if row.get("as_of_date")}
    symbols = {str(row.get("symbol")) for row in valid if row.get("symbol")}
    conditions = Counter(str((row.get("capital_context") or {}).get("capital_state") or row.get("capital_state") or "UNKNOWN") for row in valid)
    condition_ok = sum(count for count in conditions.values() if count >= min_condition_samples)
    gates = {
        "global_samples": len(valid) >= min_samples,
        "distinct_dates": len(dates) >= 1,
        "distinct_symbols": len(symbols) >= 1,
        "condition_samples": (min(conditions.values(), default=0) >= min_condition_samples) if conditions else False,
        "no_conflicts": not any((row.get("future_outcome") or {}).get("outcome_conflict") for row in valid),
        "no_future_leakage": all((row.get("gates") or {}).get("no_future_leakage", True) for row in valid),
    }
    ready = all(gates.values()) and len(valid) >= min_samples
    return {
        "status": "RESEARCH_DATA_READY" if ready else "BLOCKED",
        "sample_size": len(valid),
        "imported": len(rows),
        "invalid": len(rows) - len(valid),
        "distinct_dates": len(dates),
        "distinct_symbols": len(symbols),
        "condition_counts": dict(conditions),
        "min_samples": min_samples,
        "min_condition_samples": min_condition_samples,
        "gates": gates,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
