from us_profit_ticket_pipeline import build_forward_tracking_rows


def test_tracking_carries_capital_entry_contract():
    row = {
        "symbol": "NVDA", "ticket_rank": 1, "market_rank": 1, "as_of_date": "2026-06-10",
        "adj_close": 100.0, "kline_source": "fixture", "quote_source": "fixture",
        "quote_cross_check_gap_pct": 0.0, "data_source_mismatch": False,
        "market_score": 0.8, "catalyst_score": 0.1, "ticket_score": 0.9,
        "research_only": True, "allow_trade": False, "auto_order": False,
        "no_broker_api": True, "classification": "CANDIDATE_FOR_PAPER_REVIEW",
        "capital_model_version": "capital_behavior_v1", "capital_validation_status": "UNVALIDATED_NOT_READY",
        "capital_state": "ACTIVE_MARKUP", "capital_intent": "PUSH_HIGHER",
        "capital_strength": 0.8, "capital_score": 0.7, "distribution_score": 0.1,
        "trap_score": 0.1, "path_type": "CONTINUE_UP",
    }
    tracking = build_forward_tracking_rows([row], "2026-06-10")
    assert tracking[0]["capital_state_at_entry"] == "ACTIVE_MARKUP"
    assert tracking[0]["predicted_path"] == "CONTINUE_UP"
    assert {item["horizon_days"] for item in tracking} == {1, 3, 5, 10}
