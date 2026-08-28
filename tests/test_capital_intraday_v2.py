from capital.intraday import build_intraday_capital_assessment


def test_intraday_v2_preserves_daily_context_and_risk_gate():
    result = build_intraday_capital_assessment(
        {
            "capital_state": "ACTIVE_MARKUP", "capital_intent": "PUSH_HIGHER",
            "capital_strength": 0.9, "capital_quality": 0.8,
            "distribution_probability": 0.9, "trap_probability": 0.1,
            "path_type": "UP_CONTINUATION", "path_distribution": {"t1": {"UP_CONTINUATION": 1.0}},
            "demand_persistence_score": 0.9,
        },
        {"latest_price": 101, "prev_close": 100, "high": 102, "low": 99, "volume": 1000},
    )
    assert result["daily_capital_state"] == "ACTIVE_MARKUP"
    assert result["daily_path"] == "UP_CONTINUATION"
    assert result["daily_distribution_probability"] == 0.9
    assert result["daily_trap_probability"] == 0.1
    assert 0 <= result["intraday_distribution_risk"] <= 1
