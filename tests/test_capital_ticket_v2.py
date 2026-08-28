from us_profit_ticket_pipeline import build_forward_tracking_rows


def test_forward_tracking_carries_v2_quality_and_path_distribution():
    row = {
        "symbol": "NVDA", "ticket_rank": 1, "market_rank": 1, "as_of_date": "2026-06-10",
        "adj_close": 100.0, "kline_source": "fixture", "quote_source": "fixture",
        "quote_cross_check_gap_pct": 0.0, "data_source_mismatch": False,
        "market_score": 0.8, "catalyst_score": 0.1, "ticket_score": 0.9,
        "research_only": True, "allow_trade": False, "auto_order": False,
        "no_broker_api": True, "classification": "CANDIDATE_FOR_PAPER_REVIEW",
        "capital_model_version": "capital_behavior_v2",
        "capital_validation_status": "UNVALIDATED_NO_FIXED_CHAIN",
        "capital_state": "PULLBACK_ABSORPTION", "capital_intent": "ABSORB_SUPPLY",
        "capital_strength": 0.8, "capital_quality": 0.85, "capital_score": 0.7,
        "distribution_score": 0.1, "distribution_probability": 0.1,
        "trap_score": 0.1, "trap_probability": 0.1, "intent_probability": 0.74,
        "quality_label": "HEALTHY", "path_type": "PULLBACK_CONTINUE",
        "paths": {"t1": {"PULLBACK_CONTINUE": 1.0}},
    }
    rows = build_forward_tracking_rows([row], "2026-06-10")
    assert rows[0]["capital_quality_at_entry"] == 0.85
    assert rows[0]["path_distribution_at_entry"]["t1"]["PULLBACK_CONTINUE"] == 1.0
