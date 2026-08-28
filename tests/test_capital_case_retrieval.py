from capital.case_retrieval import analogue_outcome_distribution, retrieve_similar_cases, similarity


def _row(symbol, date, outcome=None):
    return {
        "symbol": symbol, "as_of_date": date, "eligibility_reason": "VALID",
        "capital_state": "PULLBACK_ABSORPTION", "upward_pressure": 0.6,
        "downward_pressure": 0.4, "absorption": 0.8, "control_asymmetry": 0.2,
        "demand_persistence": 0.7, "distribution": 0.1, "crowding": 0.2,
        "future_outcome": outcome or {"path_after_3d": "UP_CONTINUATION"},
    }


def test_retrieval_uses_only_as_of_fields_and_returns_outcomes_as_context():
    current = _row("ABC", "2026-08-28")
    cases = retrieve_similar_cases(current, [_row("OLD", "2026-08-01"), _row("ABC", "2026-08-28")], top_k=5)
    assert len(cases) == 1
    assert cases[0]["symbol"] == "OLD"
    assert 0 <= similarity(current, cases[0]) <= 1
    assert analogue_outcome_distribution(cases)["probabilities"] == {"UP_CONTINUATION": 1.0}
