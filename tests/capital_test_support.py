from __future__ import annotations

import numpy as np
import pandas as pd


def ohlcv(rows: int = 45, *, trend: float = 0.35, volume: float = 1_000_000) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="B")
    close = 100 + np.arange(rows, dtype=float) * trend
    return pd.DataFrame({
        "date": dates,
        "open": close - 0.2,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": np.full(rows, volume),
    })
