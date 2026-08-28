from capital import build_capital_assessment
from capital_test_support import ohlcv


def test_intent_is_explicitly_inferred_with_invalidation():
    intent = build_capital_assessment(ohlcv())["intent"]
    assert intent["intent_semantic"] == "INFERRED"
    assert intent["capital_intent"]
    assert intent["invalidation_condition"]
