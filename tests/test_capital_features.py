import numpy as np

from capital.features import build_feature_set, normalize_ohlcv
from capital_test_support import ohlcv


def test_features_deduplicate_and_drop_nonfinite_prices():
    frame = ohlcv()
    duplicate = frame.iloc[[-1]].copy()
    duplicate["close"] = 999
    frame = frame._append(duplicate, ignore_index=True)
    frame.loc[0, "close"] = np.nan
    bars = normalize_ohlcv(frame)
    features = build_feature_set(frame)
    assert len(bars) == 44
    assert bars["close"].iloc[-1] == 999
    assert features["row_count"] == 44


def test_flat_price_and_gap_are_safe():
    frame = ohlcv()
    frame["close"] = 100.0
    frame["open"] = 100.0
    frame["high"] = 100.0
    frame["low"] = 100.0
    result = build_feature_set(frame)
    assert result["flat_price"] is True
    assert 0 <= result["close_position"] <= 1
