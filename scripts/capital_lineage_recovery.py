#!/usr/bin/env python3
"""Operational entry for historical ticket lineage recovery."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capital.lineage_recovery import main


if __name__ == "__main__":
    main()
