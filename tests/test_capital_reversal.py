from capital.reversal import capital_advantage_decay, detect_reversal


def test_reversal_and_decay_are_bounded_and_explainable():
    previous = {"capital_state": "ACTIVE_MARKUP", "upward_pressure": 0.8, "downward_pressure": 0.2, "control_asymmetry": 0.4, "price_response_efficiency": 0.8, "demand_persistence": 0.8, "distribution": 0.1, "crowding": 0.4}
    current = {"capital_state": "DISTRIBUTION", "upward_pressure": 0.3, "downward_pressure": 0.7, "control_asymmetry": -0.3, "price_response_efficiency": 0.4, "demand_persistence": 0.3, "distribution": 0.8, "crowding": 0.7, "absorption_failure": 0.8}
    decay = capital_advantage_decay(previous, current)
    reversal = detect_reversal(previous, current)
    assert 0 <= decay["capital_advantage_decay_score"] <= 1
    assert 0 <= reversal["reversal_probability"] <= 1
    assert reversal["from_direction"] == "LONG"
    assert reversal["to_direction"] == "SHORT"
    assert reversal["transition_evidence"]["state_transition"] == "ACTIVE_MARKUP->DISTRIBUTION"
