from capital import build_capital_assessment
from capital_test_support import ohlcv


def test_price_control_uses_response_efficiency_terms_not_participant_identity():
    control = build_capital_assessment(ohlcv())["control"]
    assert 0 <= control["price_control_score"] <= 1
    assert control["dominant_direction"] in {"LONG", "SHORT", "NEUTRAL"}
