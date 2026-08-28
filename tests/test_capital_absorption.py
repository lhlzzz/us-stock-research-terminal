from capital.evidence import build_capital_evidence
from capital_test_support import ohlcv


def test_volume_spike_without_price_support_is_not_absorption():
    frame = ohlcv(trend=0.0)
    frame.loc[frame.index[-1], ["open", "high", "low", "close", "volume"]] = [100, 101, 90, 91, 10_000_000]
    evidence = build_capital_evidence(frame)["evidence"]
    assert evidence["volume_pressure"]["value"] > 0.5
    assert evidence["absorption"]["value"] < 0.7
