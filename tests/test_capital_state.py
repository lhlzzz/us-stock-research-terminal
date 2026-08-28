from capital import build_capital_assessment
from capital.state import CapitalState
from capital_test_support import ohlcv


def test_state_is_from_supported_enumeration():
    assessment = build_capital_assessment(ohlcv())
    assert assessment["state"]["capital_state"] in {state.value for state in CapitalState}
    assert assessment["state"]["state_confidence"] >= 0
