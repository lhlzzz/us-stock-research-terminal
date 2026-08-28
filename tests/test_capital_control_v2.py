from capital import build_capital_assessment
from capital_test_support import ohlcv


def test_control_v2_exposes_directional_efficiency_and_regime():
    control = build_capital_assessment(ohlcv())[
        "control"
    ]
    for key in ("upside_control_efficiency", "downside_control_efficiency", "control_asymmetry", "control_collapse_score"):
        assert -1 <= control[key] <= 1 if key == "control_asymmetry" else 0 <= control[key] <= 1
    assert control["control_regime"] in {"LOW", "MEDIUM", "HIGH", "SHIFTING"}
