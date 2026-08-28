import pandas as pd

from capital.evidence import build_capital_evidence
from capital_test_support import ohlcv


def test_absorption_requires_selling_activity_and_exposes_efficiency():
    frame = ohlcv(trend=0.0)
    frame.loc[frame.index[-1], ["open", "high", "low", "close", "volume"]] = [100, 101, 99, 100, 8_000_000]
    evidence = build_capital_evidence(frame)
    values = evidence["evidence"]
    assert values["selling_activity"]["value"] > 0
    assert 0 <= values["damage_efficiency"]["value"] <= 1
    assert 0 <= values["absorption_persistence"]["value"] <= 1


def test_missing_history_stays_unavailable():
    evidence = build_capital_evidence(ohlcv(10))
    assert evidence["availability"] == "INSUFFICIENT_HISTORY"
    assert evidence["evidence"]["absorption"]["availability"] == "UNAVAILABLE"
