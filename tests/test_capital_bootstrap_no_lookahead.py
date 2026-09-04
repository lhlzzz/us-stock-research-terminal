from datetime import date

import pandas as pd

from capital.historical_bootstrap import replay_capital_v2, validate_ohlcv_source
from capital.ohlcv_backfill import select_as_of_bars
from capital_test_support import ohlcv


def test_future_bars_in_the_source_frame_are_source_invalid():
    frame = ohlcv()
    leaked = pd.concat([
        frame,
        pd.DataFrame([{
            "date": pd.Timestamp("2026-12-31"),
            "open": 999, "high": 1000, "low": 998, "close": 999, "volume": 1_000_000,
        }]),
    ], ignore_index=True)
    result = validate_ohlcv_source(leaked, as_of_date=date(2026, 2, 10), source="fixture")
    assert result["status"] == "SOURCE_INVALID"
    assert result["max_bar_date"] == "2026-12-31"


def test_replay_does_not_use_bars_after_as_of():
    bounded = ohlcv()
    leaked = pd.concat([
        bounded,
        pd.DataFrame([{
            "date": pd.Timestamp("2027-01-01"),
            "open": 500, "high": 510, "low": 490, "close": 505, "volume": 9_000_000,
        }]),
    ], ignore_index=True)
    as_of = bounded["date"].max().date()
    clean = validate_ohlcv_source(bounded, as_of_date=as_of, source="fixture")
    assert clean["status"] == "REPLAYABLE"
    first = replay_capital_v2(clean["frame"])
    clipped = leaked.loc[leaked["date"] <= pd.Timestamp(as_of)]
    second = replay_capital_v2(clipped)
    assert first["scores"]["capital_score"] == second["scores"]["capital_score"]
    assert first["state"]["capital_state"] == second["state"]["capital_state"]


def test_historical_ohlcv_never_uses_future_bar():
    as_of = date(2026, 2, 10)
    bars = [
        {"trade_date": date(2026, 2, 9), "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1000},
        {"trade_date": date(2026, 2, 10), "open": 10, "high": 12, "low": 9, "close": 11, "volume": 1000},
        {"trade_date": date(2026, 2, 11), "open": 99, "high": 100, "low": 98, "close": 99, "volume": 1000},
    ]
    selected = select_as_of_bars(bars, as_of_date=as_of)
    assert [row["trade_date"] for row in selected] == [date(2026, 2, 9), date(2026, 2, 10)]
    frame = pd.DataFrame(selected).rename(columns={"trade_date": "date"})
    result = validate_ohlcv_source(frame, as_of_date=as_of, source="provider_cache")
    assert result["status"] in {"REPLAYABLE", "DATA_GAP"}
    assert result["max_bar_date"] <= "2026-02-10"
