from capital import build_capital_assessment
from capital_test_support import ohlcv


def test_state_v2_contains_dynamic_transition_and_aging_fields():
    state = build_capital_assessment(
        ohlcv(), previous_state="ACTIVE_MARKUP", previous_duration=9
    )["state"]
    assert state["state_duration"] >= 1
    assert 0 <= state["state_age_score"] <= 1
    assert 0 <= state["late_state_risk"] <= 1
    assert abs(sum(state["transition_probabilities"].values()) - 1.0) < 1e-6
    assert state["transition_matrix"]["from_state"] == state["capital_state"]
