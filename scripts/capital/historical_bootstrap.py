"""Historical Capital Behavior V2 as-of replay and dataset bootstrap.

Replays existing tickets from as-of OHLCV. It does not create tickets, mutate
production scores, or treat the rule engine as an empirical model.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from capital.dataset import (
    CAPITAL_MODEL_VERSION,
    DATASET_VERSION,
    FEATURE_VERSION,
    INTENT_MODEL_VERSION,
    LABEL_VERSION,
    PATH_MODEL_VERSION,
    STATE_MODEL_VERSION,
    assemble_dataset_sample,
    canonical_json,
    prediction_error_types,
    purged_temporal_split,
    sample_fingerprint,
)
from capital.features import availability as ohlcv_availability
from capital.features import normalize_ohlcv
from capital.learning import MIN_SAMPLES, fit_empirical_baseline
from capital.lineage_recovery import RECOVERABLE_STATUSES
from capital.scoring import build_capital_assessment


REPLAY_VERSION = "capital_historical_bootstrap_v1"
RECONSTRUCTION_METHOD = "CAPITAL_V2_AS_OF_REPLAY"
SAMPLE_ORIGIN_HISTORICAL = "HISTORICAL_REPLAY"
SAMPLE_ORIGIN_LIVE = "LIVE_RESEARCH_FORWARD"
LOOKBACK_CALENDAR_DAYS = 90
MIN_OHLCV_BARS = 20
MAX_AS_OF_STALE_DAYS = 5
HORIZONS = (1, 3, 5, 10)
BASELINE_COMMIT = "41e9430"
ELIGIBILITY_REASONS = (
    "VALID",
    "INSUFFICIENT_FORWARD_DATA",
    "MISSING_LINEAGE",
    "SOURCE_INVALID",
    "VERSION_INVALID",
    "DATA_GAP",
    "OUTCOME_CONFLICT",
    "INCOMPLETE_OUTCOME",
)
FAILURE_CLASSES = (
    "MISSING_TICKET",
    "MISSING_FORWARD",
    "MISSING_LINEAGE",
    "SOURCE_INVALID",
    "OHLCV_UNAVAILABLE",
    "REPLAY_ERROR",
    "OUTCOME_ERROR",
    "DATASET_ERROR",
)
PRODUCTION_BOUNDARY = {
    "status": "RESEARCH_ONLY",
    "validation_status": "UNVALIDATED_NO_FIXED_CHAIN",
    "ranking": "KEEP_OBSERVABLE_FOOTPRINT_RANKING_UNCHANGED",
    "production_action": "NO_PRODUCTION_WEIGHT_CHANGE",
}
KEY_TRANSITIONS = (
    "ACCUMULATION->EARLY_BUILD",
    "EARLY_BUILD->ACTIVE_MARKUP",
    "ACTIVE_MARKUP->PULLBACK_ABSORPTION",
    "ACTIVE_MARKUP->LATE_MARKUP",
    "LATE_MARKUP->DISTRIBUTION",
    "PULLBACK_ABSORPTION->SECONDARY_MARKUP",
)
STATE_ORDER = (
    "ACCUMULATION", "EARLY_BUILD", "ACTIVE_MARKUP", "PULLBACK_ABSORPTION",
    "SECONDARY_MARKUP", "LATE_MARKUP", "DISTRIBUTION", "MARKDOWN",
    "SHORT_BUILD", "SHORT_PRESSURE", "SHORT_COVER", "TRAP",
)


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _rows(result) -> list[dict[str, Any]]:
    if result is None:
        return []
    mappings = getattr(result, "mappings", None)
    if callable(mappings):
        return [dict(row) for row in mappings()]
    if isinstance(result, list):
        return [dict(row) for row in result]
    return [dict(row) for row in result]


def discover_horizon_fields(columns: Iterable[str]) -> dict[int, str]:
    """Map T+h to the actual return column. Never assume names."""
    available = {str(column) for column in columns}
    mapping: dict[int, str] = {}
    for horizon in HORIZONS:
        for candidate in (f"return_{horizon}d", f"fwd_return_{horizon}d", f"t{horizon}_return"):
            if candidate in available:
                mapping[horizon] = candidate
                break
    return mapping


def classify_join(
    ticket: Mapping[str, Any],
    tracking_by_ticket: Mapping[Any, list[Mapping[str, Any]]],
    tracking_by_symbol_date: Mapping[tuple[str, str], list[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Join one ticket to tracking without guessing across duplicate symbol/date rows."""
    ticket_id = ticket.get("id")
    by_id = list(tracking_by_ticket.get(ticket_id) or [])
    if by_id:
        return {
            "status": "UNIQUE",
            "method": "ticket_id",
            "rows": by_id,
            "reason": None,
        }
    symbol = str(ticket.get("symbol") or "").upper()
    as_of = str(_as_date(ticket.get("as_of_date")) or "")
    fuzzy = list(tracking_by_symbol_date.get((symbol, as_of)) or [])
    if not fuzzy:
        return {"status": "ORPHAN_TICKET", "method": None, "rows": [], "reason": "MISSING_FORWARD"}
    ticket_ids = {row.get("ticket_id") for row in fuzzy}
    if len(ticket_ids) != 1:
        return {"status": "AMBIGUOUS", "method": "symbol_date", "rows": [], "reason": "MISSING_LINEAGE"}
    only_id = next(iter(ticket_ids))
    if only_id not in (None, "", ticket_id):
        return {"status": "ORPHAN_TICKET", "method": "symbol_date", "rows": [], "reason": "MISSING_FORWARD"}
    return {
        "status": "UNIQUE",
        "method": "symbol_date",
        "rows": fuzzy,
        "reason": None,
    }


def overlay_recovered_lineage(
    ticket: Mapping[str, Any],
    recovered_by_ticket: Mapping[Any, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Copy a recovered run onto a ticket without mutating the original tickets row."""
    overlay = dict(ticket)
    if overlay.get("research_run_id") not in (None, ""):
        overlay.setdefault("lineage_recovery", {"lineage_status": "EXPLICIT", "lineage_source": "tickets"})
        return overlay
    recovered = (recovered_by_ticket or {}).get(overlay.get("id"))
    if not recovered:
        return overlay
    status = recovered.get("lineage_status")
    run_id = recovered.get("research_run_id")
    if status in RECOVERABLE_STATUSES and run_id not in (None, ""):
        overlay["research_run_id"] = run_id
        overlay["lineage_recovery"] = dict(recovered)
    return overlay


def classify_lineage(ticket: Mapping[str, Any], research_runs: Mapping[Any, Mapping[str, Any]]) -> dict[str, Any]:
    run_id = ticket.get("research_run_id")
    if run_id in (None, ""):
        return {"status": "MISSING_LINEAGE", "research_run": None}
    run = research_runs.get(run_id)
    if not run:
        return {"status": "MISSING_LINEAGE", "research_run": None}
    recovery = ticket.get("lineage_recovery") or {}
    return {
        "status": "VALID",
        "research_run": dict(run),
        "lineage_status": recovery.get("lineage_status") or "EXPLICIT",
        "lineage_method": recovery.get("lineage_method") or "ticket.research_run_id",
        "lineage_source": recovery.get("lineage_source") or "tickets",
    }


def validate_ohlcv_source(
    frame: pd.DataFrame,
    *,
    as_of_date: date,
    source: str | None = None,
) -> dict[str, Any]:
    if isinstance(frame, pd.DataFrame) and "date" not in frame.columns and "trade_date" in frame.columns:
        frame = frame.rename(columns={"trade_date": "date"})
    bars = normalize_ohlcv(frame)
    if "date" in getattr(frame, "columns", []):
        raw_dates = pd.to_datetime(frame["date"], errors="coerce")
        max_raw = raw_dates.max()
        if pd.notna(max_raw) and max_raw.date() > as_of_date:
            return {
                "status": "SOURCE_INVALID",
                "reason": "SOURCE_INVALID",
                "row_count": int(len(bars)),
                "min_bar_date": None,
                "max_bar_date": max_raw.date().isoformat(),
                "source": source,
            }
    if bars.empty:
        return {
            "status": "OHLCV_UNAVAILABLE",
            "reason": "OHLCV_UNAVAILABLE",
            "row_count": 0,
            "min_bar_date": None,
            "max_bar_date": None,
            "source": source,
        }
    max_bar = bars.index.max().date()
    min_bar = bars.index.min().date()
    if max_bar > as_of_date:
        return {
            "status": "SOURCE_INVALID",
            "reason": "SOURCE_INVALID",
            "row_count": int(len(bars)),
            "min_bar_date": min_bar.isoformat(),
            "max_bar_date": max_bar.isoformat(),
            "source": source,
        }
    bounded = bars.loc[bars.index.date <= as_of_date]
    ready, availability_status = ohlcv_availability(bounded, minimum_rows=MIN_OHLCV_BARS)
    max_bounded = bounded.index.max().date() if not bounded.empty else None
    if max_bounded is not None and (as_of_date - max_bounded).days > MAX_AS_OF_STALE_DAYS:
        return {
            "status": "DATA_GAP",
            "reason": "DATA_GAP",
            "availability": "STALE_AS_OF_BAR",
            "row_count": int(len(bounded)),
            "min_bar_date": bounded.index.min().date().isoformat(),
            "max_bar_date": max_bounded.isoformat(),
            "source": source,
        }
    if not ready:
        reason = "DATA_GAP" if availability_status == "INSUFFICIENT_HISTORY" else "SOURCE_INVALID"
        return {
            "status": reason,
            "reason": reason,
            "availability": availability_status,
            "row_count": int(len(bounded)),
            "min_bar_date": bounded.index.min().date().isoformat() if not bounded.empty else None,
            "max_bar_date": bounded.index.max().date().isoformat() if not bounded.empty else None,
            "source": source,
        }
    return {
        "status": "REPLAYABLE",
        "reason": None,
        "availability": availability_status,
        "row_count": int(len(bounded)),
        "min_bar_date": bounded.index.min().date().isoformat(),
        "max_bar_date": bounded.index.max().date().isoformat(),
        "source": source or "daily_klines",
        "frame": bounded,
    }


def replay_capital_v2(frame: pd.DataFrame, *, statistical_score: float | None = None) -> dict[str, Any]:
    """Deterministic as-of replay. Never injects a live/current capital state."""
    return build_capital_assessment(frame, statistical_score=statistical_score)


def tracking_returns(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Use completed forward_tracking returns only. Conflicting values invalidate."""
    collected: dict[int, list[float]] = {horizon: [] for horizon in HORIZONS}
    conflicts: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("check_status") or "").lower() != "completed":
            continue
        wide_fields = discover_horizon_fields(row)
        long_horizon = int(row.get("horizon_days") or 0)
        if long_horizon in HORIZONS and row.get("forward_return") is not None:
            value = _finite(row["forward_return"])
            if value is not None:
                collected[long_horizon].append(value)
        for horizon, column in wide_fields.items():
            value = _finite(row.get(column))
            if value is not None:
                collected[horizon].append(value)
    outcome: dict[str, Any] = {f"return_{horizon}d": None for horizon in HORIZONS}
    for horizon, values in collected.items():
        unique = []
        for value in values:
            if not any(abs(value - seen) < 1e-12 for seen in unique):
                unique.append(value)
        if len(unique) > 1:
            conflicts.append({
                "ticket_id": next((row.get("ticket_id") for row in rows), None),
                "horizon": horizon,
                "values": unique,
            })
            outcome[f"return_{horizon}d"] = None
        elif unique:
            outcome[f"return_{horizon}d"] = unique[0]
    outcome["outcome_conflict"] = bool(conflicts)
    outcome["outcome_conflicts"] = conflicts
    if conflicts:
        outcome["eligibility_reason"] = "OUTCOME_CONFLICT"
    return outcome


def complete_horizons(outcome: Mapping[str, Any] | None) -> dict[str, bool]:
    payload = dict(outcome or {})
    flags = {f"t{horizon}": payload.get(f"return_{horizon}d") is not None for horizon in HORIZONS}
    flags["all"] = all(flags.values())
    return flags


def label_states_from_existing_bars(
    prior: pd.DataFrame,
    future: pd.DataFrame,
    *,
    as_of_date: date,
    current_state: str | None,
) -> dict[str, Any]:
    """Label states/paths from already stored bars. Never downloads prices."""
    from capital.labels import label_future_outcomes

    if future is None or future.empty:
        return {"available": False, "actual_intent_semantic": "POST_HOC_PUBLIC_DATA_INFERRED_PROXY"}
    prior_bars = normalize_ohlcv(prior)
    future_bars = normalize_ohlcv(future)
    if future_bars.empty:
        return {"available": False, "actual_intent_semantic": "POST_HOC_PUBLIC_DATA_INFERRED_PROXY"}
    combined = pd.concat([prior_bars, future_bars]).sort_index()
    combined = combined[~combined.index.duplicated(keep="last")]
    labels = label_future_outcomes(combined, as_of_date=as_of_date, current_state=current_state)
    labels["actual_intent_semantic"] = "POST_HOC_PUBLIC_DATA_INFERRED_PROXY"
    return labels


def assemble_historical_outcome(
    tracking_rows: Iterable[Mapping[str, Any]],
    *,
    prior: pd.DataFrame | None = None,
    future: pd.DataFrame | None = None,
    as_of_date: date | None = None,
    current_state: str | None = None,
    current_intent: str | None = None,
    predicted_path: str | None = None,
) -> dict[str, Any]:
    outcome = tracking_returns(tracking_rows)
    labels: dict[str, Any] = {}
    if prior is not None and as_of_date is not None:
        labels = label_states_from_existing_bars(
            prior,
            future if future is not None else pd.DataFrame(),
            as_of_date=as_of_date,
            current_state=current_state,
        )
    for horizon in HORIZONS:
        for prefix in ("state_after", "path_after", "intent_after", "transition_after"):
            key = f"{prefix}_{horizon}d"
            if labels.get(key) is not None:
                outcome[key] = labels[key]
    outcome["transition_label"] = labels.get("transition_label") or outcome.get("transition_after_3d") or outcome.get("transition_after_1d")
    outcome["label_version"] = labels.get("label_version") or LABEL_VERSION
    outcome["actual_path"] = labels.get("actual_path") or outcome.get("path_after_3d") or outcome.get("path_after_1d")
    outcome["actual_intent_proxy"] = labels.get("actual_intent_proxy") or outcome.get("intent_after_3d") or outcome.get("intent_after_1d")
    outcome["actual_intent_semantic"] = "POST_HOC_PUBLIC_DATA_INFERRED_PROXY"
    outcome["state_correct_semantic"] = "POST_HOC_PUBLIC_DATA_INFERRED_PROXY"
    outcome["intent_correct_semantic"] = "POST_HOC_PUBLIC_DATA_INFERRED_PROXY"
    if current_state and outcome.get("state_after_3d"):
        family = {
            "ACCUMULATION": "LONG", "EARLY_BUILD": "LONG", "ACTIVE_MARKUP": "LONG",
            "PULLBACK_ABSORPTION": "LONG", "SECONDARY_MARKUP": "LONG", "LATE_MARKUP": "LONG",
            "MARKDOWN": "SHORT", "SHORT_BUILD": "SHORT", "SHORT_PRESSURE": "SHORT",
            "DISTRIBUTION": "RISK", "EXIT": "RISK", "TRAP": "RISK",
        }
        outcome["state_correct"] = family.get(current_state, "NEUTRAL") == family.get(str(outcome["state_after_3d"]), "NEUTRAL")
    if predicted_path and outcome.get("actual_path"):
        outcome["path_correct"] = predicted_path == outcome.get("actual_path")
    if current_intent and outcome.get("return_3d") is not None:
        ret = float(outcome["return_3d"])
        outcome["intent_correct"] = (
            (current_intent in {"ACCUMULATE", "BUILD", "PUSH_HIGHER", "DEFEND_PRICE", "ABSORB_SUPPLY", "REACCELERATE"} and ret > 0)
            or (current_intent in {"DISTRIBUTE", "REDUCE_RISK", "PRESS_LOWER"} and ret < 0)
            or (current_intent in {"WAIT", "UNKNOWN"} and abs(ret) <= 0.005)
        )
    return outcome


def eligibility_for_ticket(
    *,
    lineage_status: str,
    source_status: str,
    versions: Mapping[str, Any],
    outcome: Mapping[str, Any] | None,
) -> str:
    if lineage_status != "VALID":
        return "MISSING_LINEAGE"
    if source_status == "SOURCE_INVALID":
        return "SOURCE_INVALID"
    if source_status in {"OHLCV_UNAVAILABLE", "DATA_GAP"}:
        return "DATA_GAP"
    if any(not versions.get(key) for key in ("data_version", "model_version", "feature_version")):
        return "VERSION_INVALID"
    if outcome and outcome.get("outcome_conflict"):
        return "OUTCOME_CONFLICT"
    if not complete_horizons(outcome)["all"]:
        return "INSUFFICIENT_FORWARD_DATA"
    return "VALID"


def flatten_assessment(
    ticket: Mapping[str, Any],
    assessment: Mapping[str, Any],
    *,
    lineage: Mapping[str, Any],
    outcome: Mapping[str, Any] | None = None,
    ohlcv_meta: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = dict(assessment.get("evidence") or {})
    evidence.update({
        "sample_origin": SAMPLE_ORIGIN_HISTORICAL,
        "reconstruction_method": RECONSTRUCTION_METHOD,
        "replay_version": REPLAY_VERSION,
    })
    features = dict(evidence.get("features") or {})
    scores = dict(assessment.get("scores") or {})
    control = dict(assessment.get("control") or {})
    state = dict(assessment.get("state") or {})
    intent = dict(assessment.get("intent") or {})
    path = dict(assessment.get("path") or {})
    source_lineage = {
        "status": "VALID" if (ohlcv_meta or {}).get("status") == "REPLAYABLE" else "INVALID",
        "source": (ohlcv_meta or {}).get("source") or "daily_klines",
        "sample_origin": SAMPLE_ORIGIN_HISTORICAL,
        "reconstruction_method": RECONSTRUCTION_METHOD,
        "replay_version": REPLAY_VERSION,
        "data_version": assessment.get("data_version"),
        "feature_version": FEATURE_VERSION,
        "capital_model_version": assessment.get("model_version") or CAPITAL_MODEL_VERSION,
        "state_model_version": STATE_MODEL_VERSION,
        "intent_model_version": INTENT_MODEL_VERSION,
        "path_model_version": PATH_MODEL_VERSION,
        **dict(lineage),
    }
    return {
        "symbol": str(ticket.get("symbol") or "").upper(),
        "as_of_date": str(_as_date(ticket.get("as_of_date")) or ""),
        "research_run_id": ticket.get("research_run_id"),
        "ticket_id": ticket.get("id"),
        "ticket_score": ticket.get("ticket_score"),
        "capital_evidence": evidence,
        "capital_model_version": assessment.get("model_version") or CAPITAL_MODEL_VERSION,
        "capital_data_version": assessment.get("data_version"),
        "capital_validation_status": "UNVALIDATED_NO_FIXED_CHAIN",
        "data_version": assessment.get("data_version"),
        "model_version": assessment.get("model_version") or CAPITAL_MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "state_model_version": STATE_MODEL_VERSION,
        "intent_model_version": INTENT_MODEL_VERSION,
        "path_model_version": PATH_MODEL_VERSION,
        "features": features,
        "evidence": evidence,
        "control": control,
        "state": state,
        "intent": intent,
        "path": path,
        "price": features.get("close") or features.get("price"),
        "volume": features.get("volume"),
        "liquidity": features.get("liquidity_proxy"),
        "source_lineage": source_lineage,
        "future_outcome": dict(outcome or {}),
        "sample_origin": SAMPLE_ORIGIN_HISTORICAL,
        "reconstruction_method": RECONSTRUCTION_METHOD,
        "replay_version": REPLAY_VERSION,
        **scores,
        **control,
        **state,
        **intent,
        **path,
    }


def load_inventory(db: Session) -> dict[str, Any]:
    def table_stats(table: str, date_column: str, extra: str = "") -> dict[str, Any]:
        row = db.execute(text(f"""
            SELECT COUNT(*)::int AS row_count,
                   MIN({date_column}) AS min_date,
                   MAX({date_column}) AS max_date,
                   COUNT(DISTINCT symbol)::int AS distinct_symbols
                   {extra}
            FROM {table}
        """)).mappings().one()
        return {key: (value.isoformat() if isinstance(value, date) else value) for key, value in dict(row).items()}

    tickets = table_stats("tickets", "as_of_date", ", COUNT(DISTINCT research_run_id)::int AS distinct_research_runs")
    tracking = table_stats("forward_tracking", "as_of_date", ", COUNT(DISTINCT ticket_id)::int AS distinct_tickets")
    runs = db.execute(text("""
        SELECT COUNT(*)::int AS row_count, MIN(output_date) AS min_date, MAX(output_date) AS max_date,
               COUNT(*)::int AS distinct_research_runs, 0 AS distinct_symbols
        FROM research_runs
    """)).mappings().one()
    candidates = db.execute(text("""
        SELECT COUNT(*)::int AS row_count, MIN(trade_date) AS min_date, MAX(trade_date) AS max_date,
               COUNT(DISTINCT symbol)::int AS distinct_symbols,
               COUNT(DISTINCT research_run_id)::int AS distinct_research_runs
        FROM daily_candidates
    """)).mappings().one()
    capital_tables = {}
    for table in (
        "capital_daily_snapshot", "capital_evidence", "capital_state_history",
        "capital_intent", "capital_path_prediction", "capital_prediction_outcome",
        "capital_behavior_dataset", "capital_prediction_error",
    ):
        capital_tables[table] = table_stats(table, "as_of_date" if table != "capital_prediction_error" else "prediction_date")
    klines = db.execute(text("""
        SELECT COUNT(*)::int AS row_count, MIN(trade_date) AS min_date, MAX(trade_date) AS max_date,
               COUNT(DISTINCT symbol)::int AS distinct_symbols
        FROM daily_klines
    """)).mappings().one()
    tracking_columns = [row[0] for row in db.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name='forward_tracking'
        ORDER BY ordinal_position
    """))]
    return {
        "tickets": tickets,
        "forward_tracking": {**tracking, "columns": tracking_columns},
        "research_runs": {key: (value.isoformat() if isinstance(value, date) else value) for key, value in dict(runs).items()},
        "daily_candidates": {key: (value.isoformat() if isinstance(value, date) else value) for key, value in dict(candidates).items()},
        "daily_klines": {key: (value.isoformat() if isinstance(value, date) else value) for key, value in dict(klines).items()},
        "capital": capital_tables,
        "horizon_fields": discover_horizon_fields(tracking_columns),
    }


def load_tickets(db: Session) -> list[dict[str, Any]]:
    return _rows(db.execute(text("""
        SELECT id, symbol, as_of_date, output_date, research_run_id, ticket_score,
               market_score, capital_score, run_name
        FROM tickets
        ORDER BY as_of_date, id
    """)))


def load_tracking(db: Session) -> list[dict[str, Any]]:
    return _rows(db.execute(text("""
        SELECT id, ticket_id, symbol, as_of_date, output_date, horizon_days, due_date,
               check_status, forward_return, return_1d, return_3d, return_5d, return_10d,
               state_after_1d, state_after_3d, state_after_5d, state_after_10d,
               path_after_1d, path_after_3d, path_after_5d, path_after_10d,
               actual_path, transition_label, label_version,
               capital_model_version, capital_state_at_entry, capital_intent_at_entry
        FROM forward_tracking
        ORDER BY ticket_id, horizon_days, id
    """)))


def load_research_runs(db: Session) -> dict[Any, dict[str, Any]]:
    rows = _rows(db.execute(text("""
        SELECT run_id, run_name, output_date, status, git_commit, config, started_at, finished_at
        FROM research_runs
    """)))
    return {row["run_id"]: row for row in rows}


def _table_exists(db: Session, table_name: str) -> bool:
    row = db.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = :table_name
        LIMIT 1
    """), {"table_name": table_name}).first()
    return bool(row)


def load_recovered_lineage(db: Session) -> dict[Any, dict[str, Any]]:
    """Load audit-only recovered lineage. tickets.research_run_id is never mutated."""
    if not _table_exists(db, "capital_historical_lineage"):
        return {}
    rows = _rows(db.execute(text("""
        SELECT ticket_id, research_run_id, lineage_status, lineage_method,
               lineage_source, confidence, evidence
        FROM capital_historical_lineage
    """)))
    recovered: dict[Any, dict[str, Any]] = {}
    for row in rows:
        recovered[row.get("ticket_id")] = row
    return recovered


def load_bounded_ohlcv(db: Session, symbol: str, as_of_date: date) -> tuple[pd.DataFrame, dict[str, Any]]:
    from capital.ohlcv_backfill import load_replay_ohlcv

    return load_replay_ohlcv(db, symbol, as_of_date)


def load_future_ohlcv(db: Session, symbol: str, as_of_date: date, horizon_days: int = 10) -> pd.DataFrame:
    rows = _rows(db.execute(text("""
        SELECT trade_date, open, high, low, close, volume
        FROM daily_klines
        WHERE symbol = :symbol
          AND trade_date > :as_of_date
        ORDER BY trade_date
        LIMIT :limit
    """), {"symbol": symbol, "as_of_date": as_of_date, "limit": int(horizon_days)}))
    if not rows:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    return pd.DataFrame(rows).rename(columns={"trade_date": "date"})


def horizon_audit(tracking_rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    per_ticket: dict[Any, dict[int, Mapping[str, Any]]] = defaultdict(dict)
    for row in tracking_rows:
        horizon = int(row.get("horizon_days") or 0)
        if horizon in HORIZONS:
            per_ticket[row.get("ticket_id")][horizon] = row

    def completed(row: Mapping[str, Any] | None) -> bool:
        return bool(row) and row.get("check_status") == "completed" and row.get("forward_return") is not None

    counts = {f"t{horizon}": 0 for horizon in HORIZONS}
    counts["all"] = 0
    date_ranges = {f"t{horizon}": {"min": None, "max": None} for horizon in HORIZONS}
    ticket_ids = {f"t{horizon}": set() for horizon in HORIZONS}
    ticket_ids["all"] = set()
    for ticket_id, horizons in per_ticket.items():
        flags = {horizon: completed(horizons.get(horizon)) for horizon in HORIZONS}
        for horizon, ok in flags.items():
            if ok:
                counts[f"t{horizon}"] += 1
                ticket_ids[f"t{horizon}"].add(ticket_id)
                as_of = _as_date((horizons[horizon] or {}).get("as_of_date"))
                current = date_ranges[f"t{horizon}"]
                if as_of and (current["min"] is None or as_of < current["min"]):
                    current["min"] = as_of
                if as_of and (current["max"] is None or as_of > current["max"]):
                    current["max"] = as_of
        if all(flags.values()):
            counts["all"] += 1
            ticket_ids["all"].add(ticket_id)
    return {
        "tickets_with_tracking": len(per_ticket),
        "t1": counts["t1"],
        "t3": counts["t3"],
        "t5": counts["t5"],
        "t10": counts["t10"],
        "all": counts["all"],
        "t10_ticket_count": len(ticket_ids["t10"]),
        "date_ranges": {
            key: {
                "min": value["min"].isoformat() if value["min"] else None,
                "max": value["max"].isoformat() if value["max"] else None,
            }
            for key, value in date_ranges.items()
        },
    }


def join_audit(tickets: Iterable[Mapping[str, Any]], tracking_rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    tracking_list = list(tracking_rows)
    by_ticket: dict[Any, list[Mapping[str, Any]]] = defaultdict(list)
    by_symbol_date: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in tracking_list:
        by_ticket[row.get("ticket_id")].append(row)
        key = (str(row.get("symbol") or "").upper(), str(_as_date(row.get("as_of_date")) or ""))
        by_symbol_date[key].append(row)
    unique = ambiguous = orphan_ticket = 0
    unique_run = 0
    methods = Counter()
    classified = []
    for ticket in tickets:
        result = classify_join(ticket, by_ticket, by_symbol_date)
        classified.append((ticket, result))
        methods[result["method"] or "none"] += 1
        if result["status"] == "UNIQUE":
            unique += 1
            if ticket.get("research_run_id") not in (None, ""):
                unique_run += 1
        elif result["status"] == "AMBIGUOUS":
            ambiguous += 1
        else:
            orphan_ticket += 1
    ticket_ids = {ticket.get("id") for ticket in tickets}
    orphan_tracking = sum(1 for row in tracking_list if row.get("ticket_id") not in ticket_ids)
    return {
        "unique": unique,
        "ambiguous": ambiguous,
        "orphan_tracking": orphan_tracking,
        "orphan_ticket": orphan_ticket,
        "unique_research_run_id": unique_run,
        "methods": dict(methods),
        "classified": classified,
        "by_ticket": by_ticket,
        "by_symbol_date": by_symbol_date,
    }


def _counter() -> dict[str, int]:
    return {key: 0 for key in ELIGIBILITY_REASONS}


def _failure_counter() -> dict[str, int]:
    return {key: 0 for key in FAILURE_CLASSES}


def evaluate_ticket(
    ticket: Mapping[str, Any],
    join: Mapping[str, Any],
    research_runs: Mapping[Any, Mapping[str, Any]],
    ohlcv_loader: Callable[[str, date], tuple[pd.DataFrame, dict[str, Any]]],
    future_loader: Callable[[str, date], pd.DataFrame] | None = None,
    recovered_by_ticket: Mapping[Any, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    record = {
        "ticket_id": ticket.get("id"),
        "symbol": str(ticket.get("symbol") or "").upper(),
        "as_of_date": str(_as_date(ticket.get("as_of_date")) or ""),
        "research_run_id": ticket.get("research_run_id"),
        "join_status": join.get("status"),
        "join_method": join.get("method"),
        "failure": None,
        "eligibility_reason": None,
        "replay": None,
        "sample": None,
        "persist_row": None,
        "tracking_ids": [row.get("id") for row in join.get("rows") or []],
    }
    ticket = overlay_recovered_lineage(ticket, recovered_by_ticket)
    record["research_run_id"] = ticket.get("research_run_id")
    lineage = classify_lineage(ticket, research_runs)
    record["lineage"] = {
        "status": lineage["status"],
        "run": None,
        "lineage_status": lineage.get("lineage_status"),
        "lineage_method": lineage.get("lineage_method"),
        "lineage_source": lineage.get("lineage_source"),
    }
    if lineage["research_run"]:
        run = lineage["research_run"]
        config = run.get("config") or {}
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except ValueError:
                config = {}
        record["lineage"]["run"] = {
            "run_id": run.get("run_id"),
            "status": run.get("status"),
            "output_date": str(_as_date(run.get("output_date")) or ""),
            "git_commit": run.get("git_commit"),
            "data_version": (config or {}).get("data_as_of") or (config or {}).get("version_status"),
            "model_version": ((config or {}).get("capital_model") or {}).get("model_version"),
            "source_lineage": (config or {}).get("version_status"),
        }
    if join.get("status") == "ORPHAN_TICKET":
        record["failure"] = "MISSING_FORWARD"
        record["eligibility_reason"] = "INSUFFICIENT_FORWARD_DATA" if lineage["status"] == "VALID" else "MISSING_LINEAGE"
        return record
    if join.get("status") == "AMBIGUOUS" or lineage["status"] != "VALID":
        record["failure"] = "MISSING_LINEAGE"
        record["eligibility_reason"] = "MISSING_LINEAGE"
        return record
    as_of = _as_date(ticket.get("as_of_date"))
    if as_of is None:
        record["failure"] = "MISSING_LINEAGE"
        record["eligibility_reason"] = "MISSING_LINEAGE"
        return record
    try:
        frame, meta = ohlcv_loader(str(ticket.get("symbol") or "").upper(), as_of)
    except Exception as exc:
        record["failure"] = "OHLCV_UNAVAILABLE"
        record["eligibility_reason"] = "DATA_GAP"
        record["error"] = str(exc)
        return record
    source = validate_ohlcv_source(frame, as_of_date=as_of, source=meta.get("source"))
    record["ohlcv"] = {key: value for key, value in source.items() if key != "frame"}
    if source["status"] == "OHLCV_UNAVAILABLE":
        record["failure"] = "OHLCV_UNAVAILABLE"
        record["eligibility_reason"] = "DATA_GAP"
        return record
    if source["status"] != "REPLAYABLE":
        record["failure"] = "SOURCE_INVALID" if source["status"] == "SOURCE_INVALID" else "OHLCV_UNAVAILABLE"
        record["eligibility_reason"] = source["status"] if source["status"] in ELIGIBILITY_REASONS else "DATA_GAP"
        return record
    try:
        assessment = replay_capital_v2(
            source["frame"],
            statistical_score=_finite(ticket.get("market_score") or ticket.get("ticket_score")),
        )
    except Exception as exc:
        record["failure"] = "REPLAY_ERROR"
        record["eligibility_reason"] = "VERSION_INVALID"
        record["error"] = str(exc)
        return record
    future = pd.DataFrame()
    if future_loader is not None:
        future = future_loader(str(ticket.get("symbol") or "").upper(), as_of)
    try:
        outcome = assemble_historical_outcome(
            join.get("rows") or [],
            prior=source["frame"],
            future=future,
            as_of_date=as_of,
            current_state=(assessment.get("state") or {}).get("capital_state"),
            current_intent=(assessment.get("intent") or {}).get("capital_intent"),
            predicted_path=(assessment.get("path") or {}).get("path_type"),
        )
    except Exception as exc:
        record["failure"] = "OUTCOME_ERROR"
        record["eligibility_reason"] = "INSUFFICIENT_FORWARD_DATA"
        record["error"] = str(exc)
        return record
    persist_row = flatten_assessment(
        ticket,
        assessment,
        lineage=record["lineage"],
        outcome=outcome,
        ohlcv_meta=source,
    )
    try:
        sample = assemble_dataset_sample(persist_row, outcome=outcome, lineage=persist_row["source_lineage"])
    except Exception as exc:
        record["failure"] = "DATASET_ERROR"
        record["eligibility_reason"] = "VERSION_INVALID"
        record["error"] = str(exc)
        return record
    reason = eligibility_for_ticket(
        lineage_status="VALID",
        source_status="REPLAYABLE",
        versions=persist_row,
        outcome=outcome,
    )
    sample["eligibility_reason"] = reason
    persist_row["eligibility_reason"] = reason
    record["eligibility_reason"] = reason
    record["replay"] = {
        "capital_state": persist_row.get("capital_state"),
        "capital_intent": persist_row.get("capital_intent"),
        "path_type": persist_row.get("path_type"),
        "capital_score": persist_row.get("capital_score"),
        "capital_strength": persist_row.get("capital_strength"),
    }
    record["sample"] = sample
    record["persist_row"] = persist_row
    record["outcome"] = outcome
    record["fingerprint"] = sample.get("sample_fingerprint") or sample_fingerprint(
        symbol=sample.get("symbol"),
        as_of_date=sample.get("as_of_date"),
        research_run_id=sample.get("research_run_id"),
        model_version=sample.get("model_version"),
    )
    return record


def persist_ticket(db: Session, record: Mapping[str, Any]) -> None:
    from backfill_forward_tracking import _upsert_capital_outcome
    from db.pipeline_bridge import _persist_capital_assessments, _persist_capital_dataset

    row = record.get("persist_row")
    if not row or record.get("research_run_id") in (None, ""):
        return
    _persist_capital_assessments(
        db,
        output_date=str(row.get("as_of_date")),
        research_run_id=int(row["research_run_id"]),
        candidate_rows=[row],
    )
    outcome = dict(record.get("outcome") or {})
    outcome.setdefault("model_version", row.get("model_version"))
    outcome.setdefault("data_version", row.get("data_version"))
    for horizon in HORIZONS:
        outcome.setdefault(f"return_{horizon}d", None)
        outcome.setdefault(f"state_after_{horizon}d", None)
        outcome.setdefault(f"path_after_{horizon}d", None)
    outcome.setdefault("transition_label", None)
    outcome.setdefault("label_version", LABEL_VERSION)
    outcome.setdefault("actual_path", None)
    outcome.setdefault("actual_intent_proxy", None)
    outcome.setdefault("actual_intent_semantic", "POST_HOC_PUBLIC_DATA_INFERRED_PROXY")
    outcome.setdefault("state_correct", None)
    outcome.setdefault("intent_correct", None)
    outcome.setdefault("path_correct", None)
    db_outcome = dict(outcome)
    # capital_prediction_outcome.actual_intent_semantic is VARCHAR(32).
    db_outcome["actual_intent_semantic"] = "POST_HOC_INFERRED_PROXY"
    for tracking_id in record.get("tracking_ids") or []:
        _upsert_capital_outcome(
            db,
            forward_tracking_id=int(tracking_id),
            symbol=row["symbol"],
            as_of_date=_as_date(row["as_of_date"]),
            research_run_id=int(row["research_run_id"]),
            outcome=db_outcome,
        )
    _persist_capital_dataset(
        db,
        output_date=str(row.get("as_of_date")),
        research_run_id=int(row["research_run_id"]),
        candidate_rows=[row],
    )
    sample_row = db.execute(text("""
        SELECT id FROM capital_behavior_dataset
        WHERE symbol = :symbol AND as_of_date = :as_of_date
          AND research_run_id = :research_run_id AND model_version = :model_version
        LIMIT 1
    """), {
        "symbol": row["symbol"],
        "as_of_date": row["as_of_date"],
        "research_run_id": row["research_run_id"],
        "model_version": row.get("model_version") or CAPITAL_MODEL_VERSION,
    }).mappings().first()
    if not sample_row:
        return
    sample = dict(record.get("sample") or {})
    for error in prediction_error_types(sample, outcome):
        db.execute(text("""
            INSERT INTO capital_prediction_error (
                dataset_sample_id, model_version, prediction_date, symbol,
                predicted_state, actual_state, predicted_intent, actual_intent_proxy,
                predicted_path, actual_path, error_type, error_magnitude, confidence, metadata
            ) VALUES (
                :dataset_sample_id, :model_version, :prediction_date, :symbol,
                :predicted_state, :actual_state, :predicted_intent, :actual_intent_proxy,
                :predicted_path, :actual_path, :error_type, :error_magnitude, :confidence,
                CAST(:metadata AS jsonb)
            )
            ON CONFLICT (dataset_sample_id, error_type) DO UPDATE SET
                actual_state = EXCLUDED.actual_state,
                actual_intent_proxy = EXCLUDED.actual_intent_proxy,
                actual_path = EXCLUDED.actual_path,
                error_magnitude = EXCLUDED.error_magnitude,
                confidence = EXCLUDED.confidence,
                metadata = EXCLUDED.metadata
        """), {
            "dataset_sample_id": sample_row["id"],
            "model_version": sample.get("model_version") or CAPITAL_MODEL_VERSION,
            "prediction_date": row["as_of_date"],
            "symbol": row["symbol"],
            "predicted_state": sample.get("capital_state"),
            "actual_state": outcome.get("state_after_3d") or outcome.get("state_after_1d"),
            "predicted_intent": sample.get("capital_intent"),
            "actual_intent_proxy": outcome.get("actual_intent_proxy"),
            "predicted_path": sample.get("path_type") or (sample.get("predicted_path") or {}).get("path_type"),
            "actual_path": outcome.get("actual_path") or outcome.get("path_after_3d"),
            "error_type": error["error_type"],
            "error_magnitude": error.get("error_magnitude"),
            "confidence": sample.get("capital_state_confidence"),
            "metadata": json.dumps({
                "sample_origin": SAMPLE_ORIGIN_HISTORICAL,
                "label_version": outcome.get("label_version") or LABEL_VERSION,
            }, sort_keys=True),
        })


def _ratio(count: int, total: int) -> float:
    return round((count / total) * 100.0, 4) if total else 0.0


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"mean": None, "median": None, "win_rate": None, "profit_factor": None, "mfe": None, "mae": None, "tail_loss": None, "count": 0}
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    profit_factor = round(sum(wins) / abs(sum(losses)), 6) if losses and sum(losses) != 0 else None
    return {
        "count": len(values),
        "mean": round(sum(values) / len(values), 6),
        "median": round(statistics.median(values), 6),
        "win_rate": round(len(wins) / len(values), 6),
        "profit_factor": profit_factor,
        "mfe": round(max(values), 6),
        "mae": round(min(values), 6),
        "tail_loss": round(sorted(values)[max(0, int(len(values) * 0.05) - 1)] if values else 0.0, 6),
    }


def research_report(samples: list[Mapping[str, Any]]) -> dict[str, Any]:
    valid = [row for row in samples if row.get("eligibility_reason") == "VALID"]
    states = Counter(str(row.get("capital_state") or "UNKNOWN") for row in valid)
    total = len(valid)
    distribution = {
        state: {"count": states.get(state, 0), "pct": _ratio(states.get(state, 0), total)}
        for state in STATE_ORDER
    }
    by_state: dict[str, dict[str, Any]] = {}
    for state in STATE_ORDER:
        cohort = [row for row in valid if row.get("capital_state") == state]
        outcomes = [dict(row.get("future_outcome") or {}) for row in cohort]
        by_state[state] = {
            horizon: _stats([
                float(outcome[f"return_{horizon}d"])
                for outcome in outcomes
                if outcome.get(f"return_{horizon}d") is not None
            ])
            for horizon in HORIZONS
        }
    transitions: dict[str, Counter[str]] = defaultdict(Counter)
    for row in valid:
        outcome = row.get("future_outcome") or {}
        source_state = str(row.get("capital_state") or "UNKNOWN")
        target = outcome.get("state_after_3d") or outcome.get("state_after_1d")
        if target:
            transitions[source_state][str(target)] += 1
    rule_by_state: dict[str, Mapping[str, Any]] = {}
    for row in valid:
        source = str(row.get("capital_state") or "UNKNOWN")
        rule_by_state.setdefault(source, (row.get("inferred_state") or {}).get("transition_probabilities") or {})
    matrix = []
    rule_vs_empirical = []
    seen_pairs: set[tuple[str, str]] = set()
    for source, counter in sorted(transitions.items()):
        denom = sum(counter.values())
        rule = rule_by_state.get(source) or {}
        for target, count in sorted(counter.items()):
            empirical = round(count / denom, 6) if denom else None
            matrix.append({
                "from_state": source,
                "to_state": target,
                "count": count,
                "empirical_probability": empirical,
                "rule_probability": _finite(rule.get(target)),
            })
            pair = (source, target)
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                rule_vs_empirical.append({
                    "from_state": source,
                    "to_state": target,
                    "rule_probability": _finite(rule.get(target)),
                    "empirical_probability": empirical,
                })
    key_transition_outcomes = {}
    for name in KEY_TRANSITIONS:
        source, _, target = name.partition("->")
        matched = [
            row for row in valid
            if row.get("capital_state") == source
            and (row.get("future_outcome") or {}).get("state_after_3d") == target
        ]
        key_transition_outcomes[name] = {
            "count": len(matched),
            "t3": _stats([
                float((row.get("future_outcome") or {}).get("return_3d"))
                for row in matched
                if (row.get("future_outcome") or {}).get("return_3d") is not None
            ]),
        }
    absorption = {"high": [], "low": []}
    for row in valid:
        value = _finite(row.get("absorption"))
        ret = _finite((row.get("future_outcome") or {}).get("return_3d"))
        if value is None or ret is None:
            continue
        absorption["high" if value >= 0.62 else "low"].append(row)
    absorption_study = {
        bucket: {
            "count": len(rows),
            **{
                f"t{horizon}": _stats([
                    float((row.get("future_outcome") or {}).get(f"return_{horizon}d"))
                    for row in rows
                    if (row.get("future_outcome") or {}).get(f"return_{horizon}d") is not None
                ])
                for horizon in (1, 3, 5)
            },
        }
        for bucket, rows in absorption.items()
    }
    distribution_risk = [
        row for row in valid
        if _finite(row.get("distribution")) is not None and float(row.get("distribution") or 0) >= 0.66
        and _finite(row.get("capital_strength")) is not None and float(row.get("capital_strength") or 0) >= 0.70
    ]
    pullback_abs = [row for row in valid if row.get("capital_state") == "PULLBACK_ABSORPTION"]
    pullback_other = [
        row for row in valid
        if str(row.get("capital_state") or "").startswith("PULLBACK") and row.get("capital_state") != "PULLBACK_ABSORPTION"
    ]
    continuation = lambda rows: round(
        sum(1 for row in rows if (row.get("future_outcome") or {}).get("path_after_3d") in {"UP_CONTINUATION", "ACCELERATION", "PULLBACK_CONTINUE"})
        / len(rows),
        6,
    ) if rows else None
    collapse = [
        row for row in valid
        if _finite(row.get("control_collapse")) is not None and float(row.get("control_collapse") or 0) >= 0.60
    ]
    return {
        "valid_samples": total,
        "state_distribution": distribution,
        "state_outcomes": by_state,
        "transition_matrix": matrix,
        "rule_vs_empirical": rule_vs_empirical,
        "key_transitions": key_transition_outcomes,
        "absorption": absorption_study,
        "distribution_risk_high_momentum": {
            "count": len(distribution_risk),
            "drawdown": _stats([
                float((row.get("future_outcome") or {}).get("return_10d"))
                for row in distribution_risk
                if (row.get("future_outcome") or {}).get("return_10d") is not None
            ]),
        },
        "control_collapse": {
            "count": len(collapse),
            "reversal_or_distribution": sum(
                1 for row in collapse
                if (row.get("future_outcome") or {}).get("path_after_3d") in {"BREAKDOWN", "DISTRIBUTION", "TRAP"}
            ),
        },
        "pullback_absorption_vs_pullback": {
            "pullback_absorption": {"count": len(pullback_abs), "continuation": continuation(pullback_abs)},
            "other_pullback": {"count": len(pullback_other), "continuation": continuation(pullback_other)},
        },
    }


def assign_splits(samples: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in samples if row.get("eligibility_reason") == "VALID"]
    split = purged_temporal_split([row.get("as_of_date") for row in valid], horizon_days=10)
    assigned = {"TRAIN": 0, "VALIDATION": 0, "TEST": 0, "PURGED": 0}
    dates = {
        "TRAIN": set(split.train_dates),
        "VALIDATION": set(split.validation_dates),
        "TEST": set(split.test_dates),
        "EMBARGO": set(split.embargo_dates),
    }
    for row in valid:
        day = _as_date(row.get("as_of_date"))
        partition = None
        if day in dates["TRAIN"]:
            partition = "TRAIN"
        elif day in dates["VALIDATION"]:
            partition = "VALIDATION"
        elif day in dates["TEST"]:
            partition = "TEST"
        row["dataset_split"] = partition
        if partition:
            row["eligible_for_training"] = partition == "TRAIN"
            row["eligible_for_validation"] = partition == "VALIDATION"
            row["eligible_for_test"] = partition == "TEST"
            assigned[partition] += 1
        else:
            assigned["PURGED"] += 1
    return {
        "TRAIN": assigned["TRAIN"],
        "VALIDATION": assigned["VALIDATION"],
        "TEST": assigned["TEST"],
        "PURGED": assigned["PURGED"],
        "EMBARGO": [day.isoformat() for day in split.embargo_dates],
        "split": split,
    }


def empirical_section(samples: list[Mapping[str, Any]]) -> dict[str, Any]:
    valid = [row for row in samples if row.get("eligibility_reason") == "VALID"]
    if len(valid) < MIN_SAMPLES:
        return {
            "status": "NOT_READY",
            "reason": "VALID dataset below MIN_SAMPLES",
            "sample_count": len(valid),
            "min_samples": MIN_SAMPLES,
        }
    fitted = fit_empirical_baseline(valid, min_samples=MIN_SAMPLES, split="TRAIN")
    return fitted


def funnel_from_counts(total_tickets: int, counts: Mapping[str, int]) -> list[dict[str, Any]]:
    stages = [
        ("Historical Tickets", total_tickets, None),
        ("Unique Forward Tracking Join", counts.get("unique_join", 0), "ambiguous/orphan"),
        ("Valid Lineage", counts.get("valid_lineage", 0), "MISSING_LINEAGE"),
        ("Historical OHLCV Replayable", counts.get("ohlcv_replayable", 0), "SOURCE_INVALID/OHLCV_UNAVAILABLE/DATA_GAP"),
        ("Capital V2 Replay Success", counts.get("replay_success", 0), "REPLAY_ERROR"),
        ("Complete T+1/T+3/T+5/T+10", counts.get("complete_forward", 0), "INSUFFICIENT_FORWARD_DATA"),
        ("VALID Dataset", counts.get("valid", 0), "eligibility gates"),
    ]
    rows = []
    for name, count, drop in stages:
        rows.append({
            "stage": name,
            "count": count,
            "percentage": _ratio(count, total_tickets),
            "drop_reasons": drop,
        })
    return rows


def write_artifacts(root: Path, payload: Mapping[str, Any], run_date: str) -> dict[str, Path]:
    artifact_root = root / "capital-learning"
    artifact_root.mkdir(parents=True, exist_ok=True)
    json_path = artifact_root / f"historical-bootstrap-{run_date}.json"
    md_path = artifact_root / f"historical-bootstrap-{run_date}.md"
    v2_json = artifact_root / f"historical-bootstrap-v2-{run_date}.json"
    v2_md = artifact_root / f"historical-bootstrap-v2-{run_date}.md"
    encoded = json.dumps(payload, indent=2, ensure_ascii=True, default=str) + "\n"
    json_path.write_text(encoded, encoding="utf-8")
    v2_json.write_text(encoded, encoding="utf-8")
    funnel_lines = [
        f"- {row['stage']}: `{row['count']}` ({row['percentage']}%) drop={row['drop_reasons']}"
        for row in payload.get("funnel", [])
    ]
    eligibility = payload.get("eligibility") or {}
    horizon = payload.get("horizon_coverage") or {}
    date_ranges = horizon.get("date_ranges") or {}
    join = payload.get("join") or {}
    ohlcv = payload.get("ohlcv") or {}
    md = [
        f"# Historical Capital Bootstrap - {run_date}",
        "",
        f"- Baseline: `{payload.get('baseline_commit')}`",
        "- Status: `RESEARCH_ONLY`",
        "- Validation: `UNVALIDATED_NO_FIXED_CHAIN`",
        "- Production: `NO_PRODUCTION_WEIGHT_CHANGE`",
        "- Historical replay is not model validation.",
        "",
        "## Database Reality",
        "",
        f"- tickets = `{payload.get('tickets')}`",
        f"- forward_tracking = `{payload.get('forward_tracking')}`",
        f"- T+1 = `{horizon.get('t1')}`",
        f"- T+3 = `{horizon.get('t3')}`",
        f"- T+5 = `{horizon.get('t5')}`",
        f"- T+10 = `{horizon.get('t10')}`",
        f"- all = `{horizon.get('all')}`",
        f"- T+10 confirmed tickets = `{horizon.get('t10_confirmed_tickets')}`",
        f"- T+10 date range = `{((date_ranges.get('t10') or {}).get('min'))}` .. `{((date_ranges.get('t10') or {}).get('max'))}`",
        "",
        "## Join Reality",
        "",
        f"- unique = `{join.get('unique')}`",
        f"- ambiguous = `{join.get('ambiguous')}`",
        f"- orphan_ticket = `{join.get('orphan_ticket')}`",
        f"- orphan_tracking = `{join.get('orphan_tracking')}`",
        f"- unique_research_run_id = `{join.get('unique_research_run_id')}`",
        "",
        "## Replay Reality",
        "",
        f"- replay candidates = `{payload.get('capital_replay', {}).get('candidates')}`",
        f"- replay success = `{payload.get('capital_replay', {}).get('success')}`",
        f"- replay failed = `{payload.get('capital_replay', {}).get('failed')}`",
        f"- ohlcv replayable = `{ohlcv.get('replayable')}`",
        f"- ohlcv unavailable = `{ohlcv.get('unavailable')}`",
        f"- ohlcv invalid = `{ohlcv.get('invalid')}`",
        f"- ohlcv data_gap = `{ohlcv.get('data_gap')}`",
        "",
        "## Dataset Reality",
        "",
        *[f"- {key} = `{eligibility.get(key, 0)}`" for key in ELIGIBILITY_REASONS],
        "",
        "## Funnel",
        "",
        *funnel_lines,
        "",
        "## Empirical Reality",
        "",
        f"- status = `{payload.get('empirical', {}).get('status', 'NOT_READY')}`",
        f"- sample_count = `{(payload.get('empirical') or {}).get('sample_count', 0)}`",
        f"- min_samples = `{(payload.get('empirical') or {}).get('min_samples')}`",
        "",
        "## Lineage Block",
        "",
        f"- unversioned_tickets = `{(payload.get('lineage_block') or {}).get('unversioned_tickets')}`",
        f"- unique_join_unversioned = `{(payload.get('lineage_block') or {}).get('unique_join_unversioned')}`",
        f"- complete_four_horizon_tickets = `{(payload.get('lineage_block') or {}).get('complete_four_horizon_tickets')}`",
        f"- recovered_lineage = `{(payload.get('lineage_block') or {}).get('recovered_lineage')}`",
        "- Recovered lineage is audit-only. tickets.research_run_id is never guessed or overwritten.",
        "",
        "## Production",
        "",
        "- `RESEARCH_ONLY`",
        "- `UNVALIDATED_NO_FIXED_CHAIN`",
        "- `NO_PRODUCTION_WEIGHT_CHANGE`",
        "",
    ]
    md_path.write_text("\n".join(md), encoding="utf-8")
    v2_md.write_text("\n".join(md), encoding="utf-8")
    return {"json": json_path, "markdown": md_path, "v2_json": v2_json, "v2_markdown": v2_md}


def write_case_libraries(root: Path, samples: Iterable[Mapping[str, Any]]) -> dict[str, Path]:
    from capital.case_retrieval import classify_case

    cases_path = root / "capital-cases" / "cases.jsonl"
    counter_path = root / "capital-counterexamples" / "cases.jsonl"
    cases_path.parent.mkdir(parents=True, exist_ok=True)
    counter_path.parent.mkdir(parents=True, exist_ok=True)
    cases = []
    counters = []
    for sample in samples:
        if sample.get("eligibility_reason") != "VALID":
            continue
        outcome = sample.get("future_outcome") or {}
        case = {
            "symbol": sample.get("symbol"),
            "date": sample.get("as_of_date"),
            "state": sample.get("capital_state"),
            "intent": sample.get("capital_intent"),
            "path": outcome.get("path_after_3d") or outcome.get("actual_path"),
            "evidence": {
                key: sample.get(key)
                for key in ("absorption", "distribution", "control_collapse", "capital_strength")
            },
            "outcome": outcome,
            "return_3d": outcome.get("return_3d"),
            "sample_origin": SAMPLE_ORIGIN_HISTORICAL,
        }
        extra = None
        state = str(sample.get("capital_state") or "")
        path = str(case["path"] or "")
        if state == "ACCUMULATION" and path in {"BREAKDOWN", "MARKDOWN"}:
            extra = "ACCUMULATION_TO_MARKDOWN"
        elif state == "ACTIVE_MARKUP" and path == "DISTRIBUTION":
            extra = "ACTIVE_MARKUP_TO_DISTRIBUTION"
        elif state == "PULLBACK_ABSORPTION" and path == "BREAKDOWN":
            extra = "PULLBACK_ABSORPTION_TO_BREAKDOWN"
        elif _finite(sample.get("capital_strength")) is not None and float(sample.get("capital_strength") or 0) >= 0.70 and path == "TRAP":
            extra = "HIGH_SCORE_TO_TRAP"
        case_type = extra or classify_case(sample)
        if case_type:
            case["counterexample_type"] = case_type
            counters.append(case)
        else:
            cases.append(case)
    cases_path.write_text("".join(canonical_json(row) + "\n" for row in cases), encoding="utf-8")
    counter_path.write_text("".join(canonical_json(row) + "\n" for row in counters), encoding="utf-8")
    return {"cases": cases_path, "counterexamples": counter_path}


def bootstrap_records(
    tickets: list[Mapping[str, Any]],
    tracking_rows: list[Mapping[str, Any]],
    research_runs: Mapping[Any, Mapping[str, Any]],
    *,
    ohlcv_loader: Callable[[str, date], tuple[pd.DataFrame, dict[str, Any]]],
    future_loader: Callable[[str, date], pd.DataFrame] | None = None,
    persist: bool = False,
    persist_fn: Callable[[Mapping[str, Any]], None] | None = None,
    inventory: Mapping[str, Any] | None = None,
    artifact_root: Path | None = None,
    run_date: str = "2026-09-03",
    baseline_commit: str = BASELINE_COMMIT,
    recovered_by_ticket: Mapping[Any, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    joins = join_audit(tickets, tracking_rows)
    horizons = horizon_audit(tracking_rows)
    eligibility = _counter()
    failures = _failure_counter()
    failures["MISSING_TICKET"] = joins["orphan_tracking"]
    fingerprints: set[str] = set()
    samples: list[dict[str, Any]] = []
    replay_success = replay_failed = ohlcv_replayable = ohlcv_unavailable = ohlcv_invalid = ohlcv_gap = 0
    valid_lineage = unique_join = complete_forward = 0
    persisted = 0
    records: list[dict[str, Any]] = []

    for ticket, join in joins["classified"]:
        if join.get("status") == "UNIQUE":
            unique_join += 1
        record = evaluate_ticket(
            ticket, join, research_runs, ohlcv_loader, future_loader, recovered_by_ticket,
        )
        records.append(record)
        reason = record.get("eligibility_reason") or "MISSING_LINEAGE"
        eligibility[reason] = eligibility.get(reason, 0) + 1
        if record.get("lineage", {}).get("status") == "VALID":
            valid_lineage += 1
        if record.get("failure"):
            failures[record["failure"]] = failures.get(record["failure"], 0) + 1
            if record["failure"] in {"REPLAY_ERROR", "OHLCV_UNAVAILABLE", "SOURCE_INVALID"}:
                replay_failed += 1
        ohlcv_status = (record.get("ohlcv") or {}).get("status")
        if ohlcv_status == "REPLAYABLE":
            ohlcv_replayable += 1
        elif ohlcv_status == "OHLCV_UNAVAILABLE":
            ohlcv_unavailable += 1
        elif ohlcv_status == "SOURCE_INVALID":
            ohlcv_invalid += 1
        elif ohlcv_status == "DATA_GAP":
            ohlcv_gap += 1
        if record.get("replay"):
            replay_success += 1
        if complete_horizons(record.get("outcome"))["all"]:
            complete_forward += 1
        sample = record.get("sample")
        if sample:
            fingerprint = record.get("fingerprint")
            if fingerprint in fingerprints:
                record["failure"] = record.get("failure") or "DATASET_ERROR"
                failures["DATASET_ERROR"] += 1
                continue
            if fingerprint:
                fingerprints.add(fingerprint)
            samples.append(sample)
            if persist and record.get("persist_row") and record.get("research_run_id") not in (None, ""):
                try:
                    if persist_fn:
                        persist_fn(record)
                    persisted += 1
                except Exception as exc:
                    record["failure"] = "DATASET_ERROR"
                    record["error"] = str(exc)
                    failures["DATASET_ERROR"] += 1
                    replay_failed += 1

    split_info = assign_splits(samples)
    empirical = empirical_section(samples)
    research = research_report(samples)
    ticket_count = len(tickets) if inventory is None else int((inventory.get("tickets") or {}).get("row_count") or len(tickets))
    tracking_count = len(tracking_rows) if inventory is None else int((inventory.get("forward_tracking") or {}).get("row_count") or len(tracking_rows))
    funnel = funnel_from_counts(ticket_count, {
        "unique_join": unique_join,
        "valid_lineage": valid_lineage,
        "ohlcv_replayable": ohlcv_replayable,
        "replay_success": replay_success,
        "complete_forward": complete_forward,
        "valid": eligibility.get("VALID", 0),
    })
    payload = {
        "run_date": run_date,
        "baseline_commit": baseline_commit,
        "mode": "persist" if persist else "dry-run",
        "sample_origin": SAMPLE_ORIGIN_HISTORICAL,
        "live_sample_origin": SAMPLE_ORIGIN_LIVE,
        "tickets": ticket_count,
        "forward_tracking": tracking_count,
        "inventory": inventory or {},
        "horizon_coverage": {
            "t1": horizons["t1"],
            "t3": horizons["t3"],
            "t5": horizons["t5"],
            "t10": horizons["t10"],
            "all": horizons["all"],
            "t10_confirmed_tickets": horizons["t10_ticket_count"],
            "date_ranges": horizons["date_ranges"],
        },
        "join": {
            "unique": joins["unique"],
            "ambiguous": joins["ambiguous"],
            "orphan_tracking": joins["orphan_tracking"],
            "orphan_ticket": joins["orphan_ticket"],
            "unique_research_run_id": joins["unique_research_run_id"],
            "methods": joins["methods"],
        },
        "ohlcv": {
            "replayable": ohlcv_replayable,
            "unavailable": ohlcv_unavailable,
            "invalid": ohlcv_invalid,
            "data_gap": ohlcv_gap,
        },
        "capital_replay": {
            "candidates": ohlcv_replayable,
            "success": replay_success,
            "failed": replay_failed,
        },
        "dataset": {
            "valid": eligibility.get("VALID", 0),
            "not_ready": ticket_count - eligibility.get("VALID", 0),
        },
        "eligibility": eligibility,
        "failures": failures,
        "split": {
            "TRAIN": split_info["TRAIN"],
            "VALIDATION": split_info["VALIDATION"],
            "TEST": split_info["TEST"],
            "PURGED": split_info["PURGED"],
            "EMBARGO": split_info["EMBARGO"],
        },
        "empirical": empirical,
        "research": research,
        "funnel": funnel,
        "lineage_block": {
            "unversioned_tickets": sum(1 for ticket in tickets if ticket.get("research_run_id") in (None, "")),
            "unique_join_unversioned": max(unique_join - joins["unique_research_run_id"], 0),
            "complete_four_horizon_tickets": horizons["all"],
            "recovered_lineage": sum(
                1 for record in records
                if (record.get("lineage") or {}).get("lineage_status") in {"DERIVED_EXACT", "DERIVED_UNIQUE"}
            ),
            "note": "Recovered lineage is audit-only. tickets.research_run_id is never guessed or overwritten.",
        },
        "versioned_ticket_report": [
            {
                "ticket_id": record.get("ticket_id"),
                "symbol": record.get("symbol"),
                "as_of_date": record.get("as_of_date"),
                "research_run_id": record.get("research_run_id"),
                "ohlcv_source": (record.get("ohlcv") or {}).get("source"),
                "ohlcv_last_bar": (record.get("ohlcv") or {}).get("max_bar_date"),
                "replay_status": "REPLAYABLE" if record.get("replay") else (record.get("ohlcv") or {}).get("status") or record.get("failure"),
                "failure_reason": record.get("failure") or record.get("eligibility_reason"),
            }
            for record in records
            if record.get("ticket_id") in {506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517}
            or (record.get("lineage") or {}).get("lineage_status") == "EXPLICIT"
        ],
        "persisted_tickets": persisted if persist else 0,
        "records": records,
        "samples": samples,
        "production": PRODUCTION_BOUNDARY,
        "note": "Historical replay uses capital_behavior_v2 rules. It does not prove the capital model.",
    }
    root = artifact_root or Path(__file__).resolve().parents[2] / "research"
    artifact_payload = {key: value for key, value in payload.items() if key not in {"records", "samples"}}
    write_artifacts(root, artifact_payload, run_date)
    if persist:
        write_case_libraries(root, samples)
    return payload


def run_bootstrap(
    db: Session,
    *,
    persist: bool = False,
    artifact_root: Path | None = None,
    run_date: str = "2026-09-03",
    baseline_commit: str = BASELINE_COMMIT,
    ohlcv_loader: Callable[[str, date], tuple[pd.DataFrame, dict[str, Any]]] | None = None,
    future_loader: Callable[[str, date], pd.DataFrame] | None = None,
) -> dict[str, Any]:
    inventory = load_inventory(db)
    tickets = load_tickets(db)
    tracking_rows = load_tracking(db)
    runs = load_research_runs(db)
    recovered_by_ticket = load_recovered_lineage(db)
    loader = ohlcv_loader or (lambda symbol, as_of: load_bounded_ohlcv(db, symbol, as_of))
    future = future_loader or (lambda symbol, as_of: load_future_ohlcv(db, symbol, as_of))

    def persist_one(record: Mapping[str, Any]) -> None:
        nested = getattr(db, "begin_nested", None)
        if callable(nested):
            with db.begin_nested():
                persist_ticket(db, record)
            return
        persist_ticket(db, record)

    payload = bootstrap_records(
        tickets,
        tracking_rows,
        runs,
        ohlcv_loader=loader,
        future_loader=future,
        persist=persist,
        persist_fn=persist_one if persist else None,
        inventory=inventory,
        artifact_root=artifact_root,
        run_date=run_date,
        baseline_commit=baseline_commit,
        recovered_by_ticket=recovered_by_ticket,
    )
    if persist:
        from db.pipeline_bridge import _refresh_capital_dataset_splits
        _refresh_capital_dataset_splits(db)
    payload.pop("records", None)
    payload.pop("samples", None)
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay historical tickets through Capital V2 as-of.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Audit only; do not write business tables.")
    mode.add_argument("--persist", action="store_true", help="Persist snapshots, outcomes, dataset, and errors.")
    parser.add_argument("--run-date", default="2026-09-03")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    from db.engine import SessionLocal

    persist = bool(args.persist)
    db = SessionLocal()
    try:
        payload = run_bootstrap(db, persist=persist, run_date=args.run_date)
        if persist:
            db.commit()
        else:
            db.rollback()
        return payload
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    result = main()
    print(canonical_json({
        "mode": result.get("mode"),
        "tickets": result.get("tickets"),
        "forward_tracking": result.get("forward_tracking"),
        "horizon_coverage": result.get("horizon_coverage"),
        "eligibility": result.get("eligibility"),
        "empirical": {"status": (result.get("empirical") or {}).get("status")},
    }))
