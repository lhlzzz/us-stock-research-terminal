#!/usr/bin/env python3
"""Migrate existing CSV/JSON data into PostgreSQL database."""
import json
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
from scripts.db.engine import SessionLocal
from scripts.db.crud import (
    upsert_universe, create_ticket, upsert_forward_tracking,
    create_runtime_decision, upsert_market_snapshot,
)


def migrate_forward_tracking(db):
    """Import forward-tracking CSV files into database."""
    research_dir = Path("/root/hermes/company-ai-system/workspaces/xiaomei/research")
    csv_files = list(research_dir.glob("**/forward-tracking-*.csv"))
    print(f"Found {len(csv_files)} forward-tracking CSV files")

    total = 0
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            if "track_key" not in df.columns:
                continue
            for _, row in df.iterrows():
                track_key = str(row.get("track_key", ""))
                if not track_key:
                    continue
                try:
                    upsert_forward_tracking(
                        db,
                        track_key=track_key,
                        output_date=str(row.get("as_of_date", ""))[:10],
                        symbol=str(row.get("symbol", "")),
                        as_of_date=str(row.get("as_of_date", ""))[:10],
                        horizon_days=int(row["horizon_days"]) if pd.notna(row.get("horizon_days")) else None,
                        due_date=str(row.get("due_date", ""))[:10] if pd.notna(row.get("due_date")) else None,
                        as_of_close=float(row["as_of_close"]) if pd.notna(row.get("as_of_close")) else None,
                        check_status=str(row.get("check_status", "pending")),
                        due_close=float(row["due_close"]) if pd.notna(row.get("due_close")) else None,
                        forward_return=float(row["forward_return"]) if pd.notna(row.get("forward_return")) else None,
                    )
                    total += 1
                except Exception as e:
                    pass
        except Exception as e:
            print(f"  Error processing {csv_file.name}: {e}")

    db.commit()
    print(f"Imported {total} forward tracking rows")


def migrate_tickets_from_ledger(db):
    """Import tickets from runtime decision ledger."""
    ledger_path = Path("/root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/runtime-decision-ledger.jsonl")
    if not ledger_path.exists():
        print("No ledger file found")
        return

    total = 0
    for line in ledger_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            if payload.get("record_type") != "RUNTIME_DECISION":
                continue
            output_date = str(payload.get("output_date", ""))[:10]
            for candidate in payload.get("top_candidates", []):
                try:
                    create_ticket(
                        db,
                        output_date=output_date,
                        symbol=candidate.get("symbol", ""),
                        as_of_date=output_date,
                        ticket_rank=candidate.get("ticket_rank"),
                        ticket_score=candidate.get("ticket_score"),
                        classification=candidate.get("classification"),
                        lifecycle_stage=candidate.get("lifecycle_stage"),
                        evidence_gate_status=candidate.get("evidence_gate_status"),
                        run_name=payload.get("run_name"),
                    )
                    total += 1
                except Exception:
                    pass
        except Exception:
            pass

    db.commit()
    print(f"Imported {total} ticket records")


def migrate_universe(db):
    """Import universe from Wikipedia scrape results."""
    # This would need the actual universe data
    print("Universe migration: skipping (no static source)")


def main():
    db = SessionLocal()
    try:
        print("=== Migrating forward tracking ===")
        migrate_forward_tracking(db)

        print("\n=== Migrating tickets from ledger ===")
        migrate_tickets_from_ledger(db)

        print("\n=== Migration complete ===")
        from sqlalchemy import text
        for table in ["universe", "tickets", "forward_tracking", "runtime_decisions"]:
            count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count} rows")
    finally:
        db.close()


if __name__ == "__main__":
    main()
