from datetime import date

import pandas as pd

import backfill_forward_tracking
from capital_test_support import ohlcv


def test_bounded_ohlcv_drops_bars_after_requested_date(monkeypatch):
    frame = ohlcv()
    frame.loc[len(frame)] = [pd.Timestamp("2026-12-31"), 200, 201, 199, 200, 1_000_000]

    class Provider:
        def fetch_klines(self, *_args):
            return frame.to_dict("records"), "fixture", {}

    monkeypatch.setattr(backfill_forward_tracking, "get_provider", lambda: Provider())
    result = backfill_forward_tracking.fetch_bounded_ohlcv("NVDA", date(2026, 2, 10))
    assert result["date"].max().date() <= date(2026, 2, 10)
