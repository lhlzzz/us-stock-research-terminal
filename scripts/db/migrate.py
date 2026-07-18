#!/usr/bin/env python3
"""Initialize xiaomei database schema."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.db.engine import engine, Base
from scripts.db.models import (
    Universe, RealtimeQuote, FundFlow, Ticket,
    ForwardTracking, RuntimeDecision, MarketSnapshot,
    LifecycleScoreboard, ResearchRun, FactorSnapshot, CeleryTask,
)


def migrate():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")


if __name__ == "__main__":
    migrate()
