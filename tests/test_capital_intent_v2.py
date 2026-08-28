from capital import build_capital_assessment
from capital_test_support import ohlcv


def test_intent_v2_competes_and_allows_uncertainty():
    intent = build_capital_assessment(ohlcv())["intent"]
    assert abs(sum(intent["intent_probabilities"].values()) - 1.0) < 1e-6
    assert intent["intent_transition"]
    assert intent["intent_semantic"] == "INFERRED"
