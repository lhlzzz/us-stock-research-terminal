"""As-of historical OHLCV inventory and backfill for Capital replay.

Never writes daily_klines. Never uses bars after as_of_date. Never recomputes
forward returns.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from capital.dataset import canonical_json
from capital.historical_bootstrap import (
    LOOKBACK_CALENDAR_DAYS,
    MAX_AS_OF_STALE_DAYS,
    MIN_OHLCV_BARS,
    _as_date,
    _rows,
    validate_ohlcv_source,
)
from capital.lineage_recovery import RECOVERABLE_STATUSES


CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "provider-cache"
CACHE_NAME = re.compile(r"^([A-Z0-9.-]+)_klines_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.json$")
PRICE_SEMANTICS = "PUBLIC_OHLCV_UNADJUSTED_OR_PROVIDER_NATIVE"
ADJUSTMENT_MODE = "PROVIDER_NATIVE"
TIMEZONE = "America/New_York"
FREQUENCY = "1D"
SOURCE_CACHE = "provider_cache"
SOURCE_DAILY_KLINES = "daily_klines"


def _finite_bar(row: Mapping[str, Any]) -> dict[str, Any] | None:
    trade_date = _as_date(row.get("date") or row.get("trade_date"))
    if trade_date is None:
        return None
    try:
        open_px = float(row.get("open"))
        high = float(row.get("high"))
        low = float(row.get("low"))
        close = float(row.get("close"))
        volume = float(row.get("volume") or 0)
    except (TypeError, ValueError):
        return None
    if min(open_px, high, low, close) <= 0:
        return None
    return {
        "trade_date": trade_date,
        "open": open_px,
        "high": high,
        "low": low,
        "close": close,
        "volume": int(volume),
    }


def load_cache_bars(symbol: str, cache_dir: Path = CACHE_DIR) -> list[dict[str, Any]]:
    """Read local provider-cache klines as canonical historical data."""
    bars: dict[date, dict[str, Any]] = {}
    prefix = f"{symbol}_klines_"
    for path in cache_dir.glob(f"{symbol}_klines_*.json"):
        if not CACHE_NAME.match(path.name):
            continue
        if not path.name.startswith(prefix):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rows = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            continue
        for raw in rows:
            bar = _finite_bar(raw or {})
            if bar:
                bars[bar["trade_date"]] = bar
    return [bars[key] for key in sorted(bars)]


def inventory_sources(db: Session, cache_dir: Path = CACHE_DIR) -> dict[str, Any]:
    klines = db.execute(text("""
        SELECT COUNT(*)::int AS row_count, MIN(trade_date) AS min_date, MAX(trade_date) AS max_date,
               COUNT(DISTINCT symbol)::int AS distinct_symbols,
               COUNT(DISTINCT source)::int AS distinct_sources
        FROM daily_klines
    """)).mappings().one()
    sources = _rows(db.execute(text("""
        SELECT source, COUNT(*)::int AS row_count, MIN(trade_date) AS min_date, MAX(trade_date) AS max_date
        FROM daily_klines
        GROUP BY source
        ORDER BY row_count DESC
    """)))
    cache_files = list(cache_dir.glob("*_klines_*.json"))
    cache_symbols = sorted({
        match.group(1)
        for path in cache_files
        if (match := CACHE_NAME.match(path.name))
    })
    cache_ends = [
        match.group(3)
        for path in cache_files
        if (match := CACHE_NAME.match(path.name))
    ]
    historical = {"row_count": 0, "missing_table": True}
    exists = db.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'capital_historical_ohlcv'
        LIMIT 1
    """)).first()
    if exists:
        historical = dict(db.execute(text("""
            SELECT COUNT(*)::int AS row_count, MIN(trade_date) AS min_date, MAX(trade_date) AS max_date,
                   COUNT(DISTINCT symbol)::int AS distinct_symbols,
                   COUNT(DISTINCT source_provider)::int AS distinct_providers
            FROM capital_historical_ohlcv
        """)).mappings().one())
    return {
        "daily_klines": {
            **{key: (value.isoformat() if isinstance(value, date) else value) for key, value in dict(klines).items()},
            "providers": [
                {**row, "min_date": _as_date(row.get("min_date")).isoformat() if _as_date(row.get("min_date")) else None,
                 "max_date": _as_date(row.get("max_date")).isoformat() if _as_date(row.get("max_date")) else None}
                for row in sources
            ],
            "mutated": False,
        },
        "provider_cache": {
            "files": len(cache_files),
            "symbols": len(cache_symbols),
            "max_window_end": max(cache_ends) if cache_ends else None,
            "min_window_end": min(cache_ends) if cache_ends else None,
            "path": str(cache_dir),
            "adjustment_mode": ADJUSTMENT_MODE,
            "timezone": TIMEZONE,
            "frequency": FREQUENCY,
        },
        "capital_historical_ohlcv": {
            key: (value.isoformat() if isinstance(value, date) else value)
            for key, value in historical.items()
        },
        "covers_2026_08_15_to_2026_08_27": {
            "daily_klines": str(klines.get("max_date") or "") >= "2026-08-27",
            "provider_cache": bool(cache_ends) and max(cache_ends) >= "2026-08-27",
        },
    }


def bars_to_frame(bars: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    rows = list(bars)
    if not rows:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    frame = pd.DataFrame(rows).rename(columns={"trade_date": "date"})
    return frame[["date", "open", "high", "low", "close", "volume"]]


def select_as_of_bars(
    bars: Iterable[Mapping[str, Any]],
    *,
    as_of_date: date,
    lookback_days: int = LOOKBACK_CALENDAR_DAYS,
) -> list[dict[str, Any]]:
    start = as_of_date - timedelta(days=lookback_days)
    selected = []
    for bar in bars:
        trade_date = _as_date(bar.get("trade_date") or bar.get("date"))
        if trade_date is None or trade_date < start or trade_date > as_of_date:
            continue
        selected.append({**bar, "trade_date": trade_date})
    selected.sort(key=lambda row: row["trade_date"])
    return selected


def last_bar_policy(as_of_date: date, max_bar_date: date | None) -> str:
    """Existing V2 contract: D-n within MAX_AS_OF_STALE_DAYS is prior-bar, else DATA_GAP."""
    if max_bar_date is None:
        return "DATA_GAP"
    if max_bar_date > as_of_date:
        return "SOURCE_INVALID"
    if max_bar_date == as_of_date:
        return "AS_OF_BAR"
    if (as_of_date - max_bar_date).days <= MAX_AS_OF_STALE_DAYS:
        return "LATEST_AVAILABLE_PRIOR_BAR"
    return "DATA_GAP"


def load_historical_table_bars(db: Session, symbol: str, as_of_date: date) -> list[dict[str, Any]]:
    start = as_of_date - timedelta(days=LOOKBACK_CALENDAR_DAYS)
    exists = db.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'capital_historical_ohlcv'
        LIMIT 1
    """)).first()
    if not exists:
        return []
    rows = _rows(db.execute(text("""
        SELECT trade_date, open, high, low, close, volume, source_provider
        FROM capital_historical_ohlcv
        WHERE symbol = :symbol
          AND trade_date <= :as_of_date
          AND trade_date >= :start_date
        ORDER BY trade_date
    """), {"symbol": symbol, "as_of_date": as_of_date, "start_date": start}))
    bars = []
    for row in rows:
        bar = _finite_bar(row)
        if bar:
            bar["source_provider"] = row.get("source_provider")
            bars.append(bar)
    return bars


def load_replay_ohlcv(db: Session, symbol: str, as_of_date: date) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load as-of bars for replay. Future bars are never returned."""
    table_bars = select_as_of_bars(load_historical_table_bars(db, symbol, as_of_date), as_of_date=as_of_date)
    cache_bars = select_as_of_bars(load_cache_bars(symbol), as_of_date=as_of_date)
    db_bars = select_as_of_bars(load_daily_kline_bars(db, symbol, as_of_date), as_of_date=as_of_date)
    candidates = []
    if table_bars:
        provider = str(table_bars[-1].get("source_provider") or "capital_historical_ohlcv")
        candidates.append((table_bars, provider))
    if cache_bars:
        candidates.append((cache_bars, SOURCE_CACHE))
    if db_bars:
        candidates.append((db_bars, SOURCE_DAILY_KLINES))
    empty = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    fallback_meta = {"source": None, "row_count": 0, "min_bar_date": None, "max_bar_date": None}
    for bars, provider in candidates:
        frame = bars_to_frame(bars)
        if not frame.empty:
            parsed = pd.to_datetime(frame["date"], errors="coerce")
            frame = frame.loc[parsed.dt.date <= as_of_date].copy()
        validated = validate_ohlcv_source(frame, as_of_date=as_of_date, source=provider)
        if validated.get("status") == "REPLAYABLE":
            bounded = validated["frame"]
            if "date" in getattr(bounded, "columns", []):
                out = bounded.copy()
            else:
                out = bounded.reset_index()
                if "date" not in out.columns:
                    out = out.rename(columns={out.columns[0]: "date"})
            return out[["date", "open", "high", "low", "close", "volume"]], {
                "source": provider,
                "row_count": int(validated.get("row_count") or 0),
                "min_bar_date": validated.get("min_bar_date"),
                "max_bar_date": validated.get("max_bar_date"),
            }
        fallback_meta = {
            "source": provider,
            "row_count": int(validated.get("row_count") or 0),
            "min_bar_date": validated.get("min_bar_date"),
            "max_bar_date": validated.get("max_bar_date"),
        }
    return empty, fallback_meta


def load_daily_kline_bars(db: Session, symbol: str, as_of_date: date) -> list[dict[str, Any]]:
    start = as_of_date - timedelta(days=LOOKBACK_CALENDAR_DAYS)
    rows = _rows(db.execute(text("""
        SELECT trade_date, open, high, low, close, volume
        FROM daily_klines
        WHERE symbol = :symbol
          AND trade_date <= :as_of_date
          AND trade_date >= :start_date
        ORDER BY trade_date
    """), {"symbol": symbol, "as_of_date": as_of_date, "start_date": start}))
    bars = []
    for row in rows:
        bar = _finite_bar(row)
        if bar:
            bars.append(bar)
    return bars


def choose_source(
    *,
    cache_bars: list[dict[str, Any]],
    db_bars: list[dict[str, Any]],
    as_of_date: date,
) -> dict[str, Any]:
    cache_window = select_as_of_bars(cache_bars, as_of_date=as_of_date)
    db_window = select_as_of_bars(db_bars, as_of_date=as_of_date)
    cache_frame = bars_to_frame(cache_window)
    db_frame = bars_to_frame(db_window)
    cache_valid = validate_ohlcv_source(cache_frame, as_of_date=as_of_date, source=SOURCE_CACHE)
    db_valid = validate_ohlcv_source(db_frame, as_of_date=as_of_date, source=SOURCE_DAILY_KLINES)
    if cache_valid.get("status") == "REPLAYABLE":
        chosen = cache_valid
        chosen["provider"] = SOURCE_CACHE
        chosen["bars"] = cache_window
        chosen["last_bar_policy"] = last_bar_policy(as_of_date, _as_date(chosen.get("max_bar_date")))
        return chosen
    if db_valid.get("status") == "REPLAYABLE":
        chosen = db_valid
        chosen["provider"] = SOURCE_DAILY_KLINES
        chosen["bars"] = db_window
        chosen["last_bar_policy"] = last_bar_policy(as_of_date, _as_date(chosen.get("max_bar_date")))
        return chosen
    fallback = cache_valid if cache_window else db_valid
    fallback["provider"] = SOURCE_CACHE if cache_window else (SOURCE_DAILY_KLINES if db_window else None)
    fallback["bars"] = cache_window or db_window
    fallback["last_bar_policy"] = last_bar_policy(as_of_date, _as_date(fallback.get("max_bar_date")))
    return fallback


def lineage_tickets(db: Session) -> list[dict[str, Any]]:
    has_lineage = db.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'capital_historical_lineage'
        LIMIT 1
    """)).first()
    if has_lineage:
        tickets = _rows(db.execute(text("""
            SELECT t.id, t.symbol, t.as_of_date, t.research_run_id AS ticket_research_run_id,
                   l.research_run_id AS recovered_research_run_id,
                   l.lineage_status, l.lineage_method
            FROM tickets t
            LEFT JOIN capital_historical_lineage l ON l.ticket_id = t.id
            ORDER BY t.as_of_date, t.id
        """)))
    else:
        tickets = _rows(db.execute(text("""
            SELECT id, symbol, as_of_date, research_run_id AS ticket_research_run_id,
                   NULL AS recovered_research_run_id, NULL AS lineage_status,
                   NULL AS lineage_method
            FROM tickets
            ORDER BY as_of_date, id
        """)))
    selected = []
    for row in tickets:
        status = row.get("lineage_status")
        run_id = row.get("ticket_research_run_id")
        if run_id not in (None, ""):
            row["research_run_id"] = run_id
            row["lineage_status"] = status or "EXPLICIT"
            selected.append(row)
            continue
        if status in RECOVERABLE_STATUSES and row.get("recovered_research_run_id") not in (None, ""):
            row["research_run_id"] = row.get("recovered_research_run_id")
            selected.append(row)
    return selected


def persist_bars(db: Session, symbol: str, bars: Iterable[Mapping[str, Any]], provider: str) -> int:
    written = 0
    for bar in bars:
        db.execute(text("""
            INSERT INTO capital_historical_ohlcv (
                symbol, trade_date, open, high, low, close, volume,
                source_provider, price_semantics, adjustment_mode, timezone, frequency
            ) VALUES (
                :symbol, :trade_date, :open, :high, :low, :close, :volume,
                :source_provider, :price_semantics, :adjustment_mode, :timezone, :frequency
            )
            ON CONFLICT (symbol, trade_date, source_provider) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                price_semantics = EXCLUDED.price_semantics,
                adjustment_mode = EXCLUDED.adjustment_mode
        """), {
            "symbol": symbol,
            "trade_date": bar["trade_date"],
            "open": bar["open"],
            "high": bar["high"],
            "low": bar["low"],
            "close": bar["close"],
            "volume": bar["volume"],
            "source_provider": provider,
            "price_semantics": PRICE_SEMANTICS,
            "adjustment_mode": ADJUSTMENT_MODE,
            "timezone": TIMEZONE,
            "frequency": FREQUENCY,
        })
        written += 1
    return written


def backfill_ticket(
    db: Session,
    ticket: Mapping[str, Any],
    *,
    persist: bool = False,
    cache_dir: Path = CACHE_DIR,
) -> dict[str, Any]:
    as_of = _as_date(ticket.get("as_of_date"))
    symbol = str(ticket.get("symbol") or "").upper()
    record = {
        "ticket_id": ticket.get("id"),
        "symbol": symbol,
        "as_of_date": str(as_of or ""),
        "research_run_id": ticket.get("research_run_id"),
        "ohlcv_source": None,
        "ohlcv_last_bar": None,
        "replay_status": "OHLCV_UNAVAILABLE",
        "failure_reason": "OHLCV_UNAVAILABLE",
        "last_bar_policy": "DATA_GAP",
        "persisted_bars": 0,
    }
    if as_of is None:
        record["failure_reason"] = "MISSING_LINEAGE"
        return record
    cache_bars = load_cache_bars(symbol, cache_dir=cache_dir)
    db_bars = load_daily_kline_bars(db, symbol, as_of)
    chosen = choose_source(cache_bars=cache_bars, db_bars=db_bars, as_of_date=as_of)
    record["ohlcv_source"] = chosen.get("provider")
    record["ohlcv_last_bar"] = chosen.get("max_bar_date")
    record["row_count"] = chosen.get("row_count")
    record["min_bar_date"] = chosen.get("min_bar_date")
    record["last_bar_policy"] = chosen.get("last_bar_policy")
    record["replay_status"] = chosen.get("status")
    record["failure_reason"] = None if chosen.get("status") == "REPLAYABLE" else chosen.get("reason") or chosen.get("status")
    if persist and chosen.get("status") == "REPLAYABLE" and chosen.get("bars"):
        record["persisted_bars"] = persist_bars(db, symbol, chosen["bars"], chosen["provider"])
    return record


def write_ohlcv_artifacts(root: Path, payload: Mapping[str, Any], run_date: str) -> dict[str, Path]:
    artifact_root = root / "capital-learning"
    artifact_root.mkdir(parents=True, exist_ok=True)
    json_path = artifact_root / f"historical-ohlcv-backfill-{run_date}.json"
    md_path = artifact_root / f"historical-ohlcv-backfill-{run_date}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    funnel = payload.get("funnel") or []
    versioned = payload.get("versioned_tickets") or []
    md = [
        f"# Historical OHLCV Backfill - {run_date}",
        "",
        f"- daily_klines mutated = `{False}`",
        f"- replayable = `{(payload.get('counts') or {}).get('replayable')}`",
        f"- data_gap = `{(payload.get('counts') or {}).get('data_gap')}`",
        f"- unavailable = `{(payload.get('counts') or {}).get('unavailable')}`",
        "",
        "## Source Inventory",
        "",
        f"- daily_klines max_bar_date = `{(payload.get('inventory') or {}).get('daily_klines', {}).get('max_date')}`",
        f"- provider_cache max_window_end = `{(payload.get('inventory') or {}).get('provider_cache', {}).get('max_window_end')}`",
        f"- covers 2026-08-15..2026-08-27 via provider_cache = `{(payload.get('inventory') or {}).get('covers_2026_08_15_to_2026_08_27', {}).get('provider_cache')}`",
        "",
        "## OHLCV Funnel",
        "",
        *[f"- {row['stage']}: `{row['count']}` ({row['percentage']}%) drop={row.get('drop_reasons')}" for row in funnel],
        "",
        "## Versioned Tickets",
        "",
    ]
    for row in versioned:
        md.append(
            f"- ticket `{row.get('ticket_id')}` {row.get('symbol')} {row.get('as_of_date')} "
            f"run={row.get('research_run_id')} source={row.get('ohlcv_source')} "
            f"last_bar={row.get('ohlcv_last_bar')} status={row.get('replay_status')} "
            f"reason={row.get('failure_reason')}"
        )
    md.append("")
    md_path.write_text("\n".join(md), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def _ratio(count: int, total: int) -> float:
    return round((count / total) * 100.0, 4) if total else 0.0


def run_ohlcv_backfill(
    db: Session,
    *,
    persist: bool = False,
    ticket_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    artifact_root: Path | None = None,
    run_date: str = "2026-09-03",
    cache_dir: Path = CACHE_DIR,
) -> dict[str, Any]:
    inventory = inventory_sources(db, cache_dir=cache_dir)
    tickets = lineage_tickets(db)
    if ticket_id is not None:
        tickets = [row for row in tickets if row.get("id") == ticket_id]
    if from_date:
        tickets = [row for row in tickets if _as_date(row.get("as_of_date")) and _as_date(row.get("as_of_date")) >= from_date]
    if to_date:
        tickets = [row for row in tickets if _as_date(row.get("as_of_date")) and _as_date(row.get("as_of_date")) <= to_date]
    records = [backfill_ticket(db, ticket, persist=persist, cache_dir=cache_dir) for ticket in tickets]
    counts = {
        "lineage_valid": len(tickets),
        "replayable": sum(1 for row in records if row.get("replay_status") == "REPLAYABLE"),
        "data_gap": sum(1 for row in records if row.get("replay_status") == "DATA_GAP"),
        "unavailable": sum(1 for row in records if row.get("replay_status") == "OHLCV_UNAVAILABLE"),
        "invalid": sum(1 for row in records if row.get("replay_status") == "SOURCE_INVALID"),
    }
    total = max(len(tickets), 1)
    funnel = [
        {"stage": "Valid lineage", "count": counts["lineage_valid"], "percentage": _ratio(counts["lineage_valid"], len(tickets)), "drop_reasons": "MISSING_LINEAGE"},
        {"stage": "Source available", "count": sum(1 for row in records if row.get("ohlcv_source")), "percentage": _ratio(sum(1 for row in records if row.get("ohlcv_source")), len(tickets)), "drop_reasons": "OHLCV_UNAVAILABLE"},
        {"stage": "Sufficient history", "count": sum(1 for row in records if int(row.get("row_count") or 0) >= MIN_OHLCV_BARS), "percentage": _ratio(sum(1 for row in records if int(row.get("row_count") or 0) >= MIN_OHLCV_BARS), len(tickets)), "drop_reasons": "INSUFFICIENT_HISTORY"},
        {"stage": "As-of valid", "count": sum(1 for row in records if row.get("last_bar_policy") in {"AS_OF_BAR", "LATEST_AVAILABLE_PRIOR_BAR"}), "percentage": _ratio(sum(1 for row in records if row.get("last_bar_policy") in {"AS_OF_BAR", "LATEST_AVAILABLE_PRIOR_BAR"}), len(tickets)), "drop_reasons": "DATA_GAP"},
        {"stage": "Replayable", "count": counts["replayable"], "percentage": _ratio(counts["replayable"], len(tickets)), "drop_reasons": "SOURCE_INVALID/OHLCV_UNAVAILABLE/DATA_GAP"},
    ]
    payload = {
        "run_date": run_date,
        "mode": "persist" if persist else "dry-run",
        "inventory": inventory,
        "counts": counts,
        "funnel": funnel,
        "versioned_tickets": [row for row in records if row.get("ticket_id") in {506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517}],
        "records": records,
        "daily_klines_mutated": False,
        "forward_returns_recomputed": False,
    }
    root = artifact_root or Path(__file__).resolve().parents[2] / "research"
    write_ohlcv_artifacts(root, {key: value for key, value in payload.items() if key != "records"} | {"records": records}, run_date)
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill as-of OHLCV for legally lined-up tickets.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--persist", action="store_true")
    parser.add_argument("--ticket-id", type=int)
    parser.add_argument("--from-date")
    parser.add_argument("--to-date")
    parser.add_argument("--run-date", default="2026-09-03")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    from db.engine import SessionLocal

    persist = bool(args.persist)
    db = SessionLocal()
    try:
        payload = run_ohlcv_backfill(
            db,
            persist=persist,
            ticket_id=args.ticket_id,
            from_date=_as_date(args.from_date),
            to_date=_as_date(args.to_date),
            run_date=args.run_date,
        )
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
        "counts": result.get("counts"),
        "daily_klines_mutated": False,
    }))
