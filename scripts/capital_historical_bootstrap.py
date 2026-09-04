#!/usr/bin/env python3
"""Operational entry for historical Capital V2 as-of bootstrap."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capital.historical_bootstrap import main


if __name__ == "__main__":
    main()
