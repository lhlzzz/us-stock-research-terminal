from capital.intraday import build_intraday_capital_assessment


def test_intraday_capital_keeps_daily_and_session_state_separate():
    assessment = build_intraday_capital_assessment(
        {
            "capital_state": "ACTIVE_MARKUP",
            "capital_strength": 0.8,
            "distribution_score": 0.1,
            "trap_score": 0.1,
            "demand_persistence_score": 0.8,
            "volume_pressure": 0.7,
        },
        {"latest_price": 101, "prev_close": 100, "high": 102, "low": 99, "volume": 1000},
    )
    assert assessment["availability"] == "AVAILABLE"
    assert assessment["intraday_capital_state"] in {"ACTIVE_MARKUP", "PULLBACK_ABSORPTION", "NEUTRAL", "SHORT_PRESSURE", "TRAP"}
    assert assessment["semantic"]["assessment"] == "INFERRED"
