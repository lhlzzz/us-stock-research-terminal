"""Strict historical ticket → research_run lineage recovery.

Does not mutate tickets. Ambiguous or guessed matches stay UNRESOLVED.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session

from capital.dataset import canonical_json


LINEAGE_STATUSES = (
    "EXPLICIT",
    "DERIVED_EXACT",
    "DERIVED_UNIQUE",
    "AMBIGUOUS",
    "UNRESOLVED",
)
RECOVERABLE_STATUSES = {"EXPLICIT", "DERIVED_EXACT", "DERIVED_UNIQUE"}
TICKET_RUN_WINDOW = timedelta(hours=1)


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _rows(result) -> list[dict[str, Any]]:
    if result is None:
        return []
    mappings = getattr(result, "mappings", None)
    if callable(mappings):
        return [dict(row) for row in mappings()]
    if isinstance(result, list):
        return [dict(row) for row in result]
    return [dict(row) for row in result]


def _naive(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _record(
    ticket: Mapping[str, Any],
    *,
    status: str,
    method: str | None,
    source: str,
    confidence: float,
    research_run_id: Any = None,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ticket_id": ticket.get("id"),
        "symbol": str(ticket.get("symbol") or "").upper(),
        "as_of_date": str(_as_date(ticket.get("as_of_date")) or ""),
        "research_run_id": research_run_id,
        "lineage_status": status,
        "lineage_method": method,
        "lineage_source": source,
        "confidence": confidence,
        "evidence": dict(evidence or {}),
    }


def recover_ticket_lineage(
    ticket: Mapping[str, Any],
    *,
    research_runs: Mapping[Any, Mapping[str, Any]],
    runs_by_output_date: Mapping[str, list[Mapping[str, Any]]],
    candidates_by_symbol_date: Mapping[tuple[str, str], list[Mapping[str, Any]]],
    candidates_by_id: Mapping[Any, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Recover one ticket's research_run_id using the allowed priority only."""
    run_id = ticket.get("research_run_id")
    if run_id not in (None, "") and run_id in research_runs:
        return _record(
            ticket,
            status="EXPLICIT",
            method="ticket.research_run_id",
            source="tickets",
            confidence=1.0,
            research_run_id=run_id,
            evidence={"level": 1, "ticket_research_run_id": run_id},
        )
    if run_id not in (None, ""):
        return _record(
            ticket,
            status="UNRESOLVED",
            method=None,
            source="tickets",
            confidence=0.0,
            evidence={"level": 1, "unknown_research_run_id": run_id},
        )

    symbol = str(ticket.get("symbol") or "").upper()
    as_of = str(_as_date(ticket.get("as_of_date")) or "")
    candidate_id = ticket.get("candidate_id")
    if candidate_id not in (None, "") and candidates_by_id:
        candidate = candidates_by_id.get(candidate_id)
        if candidate and candidate.get("research_run_id") not in (None, ""):
            return _record(
                ticket,
                status="DERIVED_EXACT",
                method="ticket.candidate_id",
                source="daily_candidates",
                confidence=1.0,
                research_run_id=candidate.get("research_run_id"),
                evidence={
                    "level": 3,
                    "candidate_id": candidate_id,
                    "candidate_research_run_id": candidate.get("research_run_id"),
                },
            )

    matches = list(candidates_by_symbol_date.get((symbol, as_of)) or [])
    with_run = [row for row in matches if row.get("research_run_id") not in (None, "")]
    run_ids = {row.get("research_run_id") for row in with_run}
    if len(run_ids) == 1:
        only_run = next(iter(run_ids))
        return _record(
            ticket,
            status="DERIVED_EXACT",
            method="ticket.symbol_as_of_date.daily_candidate",
            source="daily_candidates",
            confidence=1.0,
            research_run_id=only_run,
            evidence={
                "level": 2,
                "candidate_ids": [row.get("id") for row in with_run],
                "research_run_id": only_run,
            },
        )
    if len(run_ids) > 1:
        return _record(
            ticket,
            status="AMBIGUOUS",
            method=None,
            source="daily_candidates",
            confidence=0.0,
            evidence={"level": 2, "candidate_run_ids": sorted(run_ids)},
        )

    unique_runs = list(runs_by_output_date.get(as_of) or [])
    created_at = _naive(ticket.get("created_at"))
    if len(unique_runs) == 1 and created_at is not None:
        run = unique_runs[0]
        started = _naive(run.get("started_at"))
        if started is not None and started <= created_at < started + TICKET_RUN_WINDOW:
            return _record(
                ticket,
                status="DERIVED_UNIQUE",
                method="symbol.as_of_date.unique_run.created_at",
                source="research_runs",
                confidence=1.0,
                research_run_id=run.get("run_id"),
                evidence={
                    "level": 4,
                    "as_of_date": as_of,
                    "run_id": run.get("run_id"),
                    "run_started_at": _iso(started),
                    "ticket_created_at": _iso(created_at),
                    "window_hours": TICKET_RUN_WINDOW.total_seconds() / 3600.0,
                },
            )
    if len(unique_runs) > 1:
        return _record(
            ticket,
            status="AMBIGUOUS",
            method=None,
            source="research_runs",
            confidence=0.0,
            evidence={
                "level": 4,
                "as_of_date": as_of,
                "run_ids": [row.get("run_id") for row in unique_runs],
            },
        )
    return _record(
        ticket,
        status="UNRESOLVED",
        method=None,
        source="none",
        confidence=0.0,
        evidence={"level": None, "as_of_date": as_of, "unique_runs_on_as_of": len(unique_runs)},
    )


def recover_lineage_records(
    tickets: Iterable[Mapping[str, Any]],
    research_runs: Mapping[Any, Mapping[str, Any]],
    *,
    candidates: Iterable[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    runs_by_date: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for run in research_runs.values():
        key = str(_as_date(run.get("output_date")) or "")
        if key:
            runs_by_date[key].append(run)
    candidates_by_symbol_date: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    candidates_by_id: dict[Any, Mapping[str, Any]] = {}
    for row in candidates or []:
        candidates_by_id[row.get("id")] = row
        key = (str(row.get("symbol") or "").upper(), str(_as_date(row.get("trade_date")) or ""))
        candidates_by_symbol_date[key].append(row)
    return [
        recover_ticket_lineage(
            ticket,
            research_runs=research_runs,
            runs_by_output_date=runs_by_date,
            candidates_by_symbol_date=candidates_by_symbol_date,
            candidates_by_id=candidates_by_id,
        )
        for ticket in tickets
    ]


def summarize_lineage(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    counts = {status: 0 for status in LINEAGE_STATUSES}
    for row in rows:
        status = str(row.get("lineage_status") or "UNRESOLVED")
        counts[status] = counts.get(status, 0) + 1
    recoverable = sum(counts.get(status, 0) for status in RECOVERABLE_STATUSES if status != "EXPLICIT")
    explicit = counts.get("EXPLICIT", 0)
    return {
        "tickets": len(rows),
        "unversioned_tickets": sum(1 for row in rows if row.get("lineage_status") != "EXPLICIT"),
        **counts,
        "recoverable": recoverable,
        "valid_lineage": explicit + recoverable,
    }


def load_lineage_inputs(db: Session) -> dict[str, Any]:
    tickets = _rows(db.execute(text("""
        SELECT id, symbol, as_of_date, output_date, research_run_id, created_at, run_name
        FROM tickets
        ORDER BY as_of_date, id
    """)))
    runs = _rows(db.execute(text("""
        SELECT run_id, run_name, output_date, status, git_commit, started_at, finished_at, candidate_count, pass_count
        FROM research_runs
    """)))
    candidates = _rows(db.execute(text("""
        SELECT id, symbol, trade_date, research_run_id, created_at, is_official_pick
        FROM daily_candidates
    """)))
    return {
        "tickets": tickets,
        "research_runs": {row["run_id"]: row for row in runs},
        "candidates": candidates,
    }


def persist_lineage(db: Session, records: Iterable[Mapping[str, Any]]) -> int:
    written = 0
    for row in records:
        db.execute(text("""
            INSERT INTO capital_historical_lineage (
                ticket_id, research_run_id, lineage_status, lineage_method,
                lineage_source, confidence, evidence, created_at, updated_at
            ) VALUES (
                :ticket_id, :research_run_id, :lineage_status, :lineage_method,
                :lineage_source, :confidence, CAST(:evidence AS jsonb), NOW(), NOW()
            )
            ON CONFLICT (ticket_id) DO UPDATE SET
                research_run_id = EXCLUDED.research_run_id,
                lineage_status = EXCLUDED.lineage_status,
                lineage_method = EXCLUDED.lineage_method,
                lineage_source = EXCLUDED.lineage_source,
                confidence = EXCLUDED.confidence,
                evidence = EXCLUDED.evidence,
                updated_at = NOW()
        """), {
            "ticket_id": row["ticket_id"],
            "research_run_id": row.get("research_run_id"),
            "lineage_status": row["lineage_status"],
            "lineage_method": row.get("lineage_method"),
            "lineage_source": row["lineage_source"],
            "confidence": row["confidence"],
            "evidence": json.dumps(row.get("evidence") or {}, sort_keys=True, default=str),
        })
        written += 1
    return written


def write_lineage_artifacts(root: Path, payload: Mapping[str, Any], run_date: str) -> dict[str, Path]:
    artifact_root = root / "capital-learning"
    artifact_root.mkdir(parents=True, exist_ok=True)
    json_path = artifact_root / f"lineage-recovery-{run_date}.json"
    md_path = artifact_root / f"lineage-recovery-{run_date}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    summary = payload.get("summary") or {}
    md = [
        f"# Lineage Recovery - {run_date}",
        "",
        f"- unversioned tickets = `{summary.get('unversioned_tickets')}`",
        f"- EXPLICIT = `{summary.get('EXPLICIT')}`",
        f"- DERIVED_EXACT = `{summary.get('DERIVED_EXACT')}`",
        f"- DERIVED_UNIQUE = `{summary.get('DERIVED_UNIQUE')}`",
        f"- AMBIGUOUS = `{summary.get('AMBIGUOUS')}`",
        f"- UNRESOLVED = `{summary.get('UNRESOLVED')}`",
        f"- recoverable = `{summary.get('recoverable')}`",
        f"- valid_lineage = `{summary.get('valid_lineage')}`",
        "",
        "- Original `tickets.research_run_id` is unchanged.",
        "- Symbol-only / nearest-run matches are never recovered.",
        "",
    ]
    md_path.write_text("\n".join(md), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def run_lineage_recovery(
    db: Session,
    *,
    persist: bool = False,
    artifact_root: Path | None = None,
    run_date: str = "2026-09-03",
) -> dict[str, Any]:
    inputs = load_lineage_inputs(db)
    records = recover_lineage_records(
        inputs["tickets"],
        inputs["research_runs"],
        candidates=inputs["candidates"],
    )
    summary = summarize_lineage(records)
    persisted = persist_lineage(db, records) if persist else 0
    payload = {
        "run_date": run_date,
        "mode": "persist" if persist else "dry-run",
        "summary": summary,
        "records": records,
        "persisted_rows": persisted,
        "tickets_mutated": False,
    }
    root = artifact_root or Path(__file__).resolve().parents[2] / "research"
    artifact_payload = {key: value for key, value in payload.items() if key != "records"}
    artifact_payload["recovered"] = [
        row for row in records if row.get("lineage_status") in RECOVERABLE_STATUSES
    ]
    write_lineage_artifacts(root, artifact_payload, run_date)
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recover historical ticket lineage without mutating tickets.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--persist", action="store_true")
    parser.add_argument("--run-date", default="2026-09-03")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    from db.engine import SessionLocal

    persist = bool(args.persist)
    db = SessionLocal()
    try:
        payload = run_lineage_recovery(db, persist=persist, run_date=args.run_date)
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
    summary = result.get("summary") or {}
    print(canonical_json({
        "mode": result.get("mode"),
        "unversioned_tickets": summary.get("unversioned_tickets"),
        "EXPLICIT": summary.get("EXPLICIT"),
        "DERIVED_EXACT": summary.get("DERIVED_EXACT"),
        "DERIVED_UNIQUE": summary.get("DERIVED_UNIQUE"),
        "AMBIGUOUS": summary.get("AMBIGUOUS"),
        "UNRESOLVED": summary.get("UNRESOLVED"),
        "recoverable": summary.get("recoverable"),
    }))
