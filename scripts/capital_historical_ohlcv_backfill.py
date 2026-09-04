#!/usr/bin/env python3
"""Operational entry for historical as-of OHLCV backfill."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capital.ohlcv_backfill import main


if __name__ == "__main__":
    main()
