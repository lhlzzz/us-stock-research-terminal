from capital.evidence import build_capital_evidence
from capital_test_support import ohlcv


def test_high_volume_rejection_increases_distribution_and_trap_risk():
    frame = ohlcv(trend=0.8)
    frame.loc[frame.index[-1], ["open", "high", "low", "close", "volume"]] = [135, 140, 130, 131, 12_000_000]
    evidence = build_capital_evidence(frame)["evidence"]
    assert evidence["distribution"]["value"] > 0.2
    assert evidence["trap"]["value"] > 0.2
