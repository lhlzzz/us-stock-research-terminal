from capital.evidence import build_capital_evidence
from capital.state import transition_state
from capital_test_support import ohlcv


def test_nonadjacent_weak_transition_holds_previous_state():
    evidence = build_capital_evidence(ohlcv())
    result = transition_state(evidence, previous_state="DISTRIBUTION", previous_duration=4)
    assert result["previous_capital_state"] == "DISTRIBUTION"
    assert result["state_duration"] >= 1
