from capital import build_capital_assessment
from capital_test_support import ohlcv


def test_path_has_horizon_probabilities_and_predicted_semantic():
    path = build_capital_assessment(ohlcv())["path"]
    assert path["path_semantic"] == "PREDICTED"
    assert all(0 <= path[key] <= 1 for key in ("t1_probability", "t3_probability", "t5_probability"))
