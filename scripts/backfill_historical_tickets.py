#!/usr/bin/env python3
"""Backfill historical tickets by running pipeline for multiple dates."""
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

def main():
    # Get date range from args or default to last 60 days
    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    else:
        days = 60

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Generate list of dates (weekdays only)
    current = start_date
    dates = []
    while current <= end_date:
        if current.weekday() < 5:  # Mon-Fri
            dates.append(current)
        current += timedelta(days=1)

    print(f"Backfilling {len(dates)} trading days from {start_date} to {end_date}")

    # Run pipeline for each date
    for d in dates:
        date_str = d.isoformat()
        print(f"\n=== Processing {date_str} ===")
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_DIR / "scripts" / "us_profit_ticket_pipeline.py"),
                    "--save-db",
                    "--skip-last30days",
                    "--top-k", "3",
                    "--output-date", date_str,
                    "--universe-source", "explicit",
                    "--universe", "AAPL", "MSFT", "META", "NVDA", "AMZN", "GOOGL",
                ],
                cwd=str(PROJECT_DIR),
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                print(f"  ✓ {date_str} completed")
            else:
                print(f"  ✗ {date_str} failed: {result.stderr[:200]}")
        except Exception as e:
            print(f"  ✗ {date_str} error: {e}")

    print("\n=== Backfill complete ===")

if __name__ == "__main__":
    main()
