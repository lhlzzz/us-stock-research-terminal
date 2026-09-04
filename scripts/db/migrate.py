#!/usr/bin/env python3
"""Initialize xiaomei database schema."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(ROOT))

from scripts.db.engine import engine, Base
from scripts.db.models import (  # noqa: F401
    Universe, RealtimeQuote, FundFlow, Ticket,
    ForwardTracking, RuntimeDecision, MarketSnapshot,
    LifecycleScoreboard, ResearchRun, FactorSnapshot, CeleryTask,
)


REQUIRED_TABLES = (
    "universe",
    "tickets",
    "forward_tracking",
    "runtime_decisions",
    "market_snapshots",
    "research_runs",
)


def migrate():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")


def verify() -> int:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    names = set(inspector.get_table_names())
    missing = [name for name in REQUIRED_TABLES if name not in names]
    print("PostgreSQL tables:", sorted(names))
    if missing:
        print("MISSING:", missing)
        return 1
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    from research.store import SCHEMA, connect as research_connect

    conn = research_connect()
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    research_tables = {row[0] for row in rows}
    required_research = (
        "research_evidence",
        "sec_documents",
        "sec_facts",
        "earnings_events",
        "estimate_revisions",
        "industry_snapshots",
        "universe_membership",
        "research_snapshots",
        "research_runs",
        "failure_memory",
        "research_learning_patterns",
        "provider_attempts",
        "research_outcomes",
    )
    missing_research = [name for name in required_research if name not in research_tables]
    print("Research SQLite tables:", sorted(research_tables))
    conn.close()
    if missing_research:
        print("MISSING RESEARCH TABLES:", missing_research)
        return 1
    print("SCHEMA_OK")
    print("verify=PASS")
    print("research_store_schema_chars", len(SCHEMA))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        raise SystemExit(verify())
    migrate()
