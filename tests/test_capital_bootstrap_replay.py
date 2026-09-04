from datetime import date

import pandas as pd

from capital.historical_bootstrap import replay_capital_v2, validate_ohlcv_source
from capital_test_support import ohlcv


def test_replay_is_deterministic_for_the_same_as_of_frame():
    frame = ohlcv()
    first = replay_capital_v2(frame, statistical_score=0.4)
    second = replay_capital_v2(frame, statistical_score=0.4)
    assert first["state"]["capital_state"] == second["state"]["capital_state"]
    assert first["intent"]["capital_intent"] == second["intent"]["capital_intent"]
    assert first["path"]["path_type"] == second["path"]["path_type"]
    assert first["scores"]["capital_score"] == second["scores"]["capital_score"]
    assert first["evidence"]["evidence"] == second["evidence"]["evidence"]


def test_insufficient_history_is_data_gap_not_replayable():
    frame = ohlcv(rows=5)
    result = validate_ohlcv_source(frame, as_of_date=date(2026, 1, 8), source="fixture")
    assert result["status"] == "DATA_GAP"
    assert "frame" not in result


def test_missing_ohlcv_is_unavailable():
    empty = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    result = validate_ohlcv_source(empty, as_of_date=date(2026, 2, 10))
    assert result["status"] == "OHLCV_UNAVAILABLE"


def test_stale_last_bar_is_data_gap():
    frame = ohlcv()
    result = validate_ohlcv_source(frame, as_of_date=date(2026, 6, 1), source="fixture")
    assert result["status"] == "DATA_GAP"
    assert result["availability"] == "STALE_AS_OF_BAR"


def test_trade_date_column_is_accepted_without_future_leak():
    frame = ohlcv().rename(columns={"date": "trade_date"})
    as_of = frame["trade_date"].max().date()
    result = validate_ohlcv_source(frame, as_of_date=as_of, source="daily_klines")
    assert result["status"] == "REPLAYABLE"
    assert result["max_bar_date"] == as_of.isoformat()
