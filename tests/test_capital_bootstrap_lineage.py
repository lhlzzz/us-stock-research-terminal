from datetime import date, datetime

from capital.historical_bootstrap import bootstrap_records, classify_lineage, overlay_recovered_lineage
from capital.lineage_recovery import recover_ticket_lineage
from capital_test_support import ohlcv


def test_missing_research_run_id_is_missing_lineage():
    result = classify_lineage({"id": 1, "research_run_id": None}, {})
    assert result["status"] == "MISSING_LINEAGE"


def test_unknown_research_run_id_is_missing_lineage():
    result = classify_lineage({"id": 1, "research_run_id": 99}, {7: {"run_id": 7}})
    assert result["status"] == "MISSING_LINEAGE"


def test_bootstrap_does_not_invent_lineage_for_unversioned_tickets(tmp_path):
    tickets = [{"id": 1, "symbol": "ABC", "as_of_date": date(2026, 2, 10), "research_run_id": None}]
    tracking = [
        {"id": horizon, "ticket_id": 1, "symbol": "ABC", "as_of_date": date(2026, 2, 10),
         "horizon_days": horizon, "check_status": "completed", "forward_return": 0.01}
        for horizon in (1, 3, 5, 10)
    ]
    payload = bootstrap_records(
        tickets,
        tracking,
        {},
        ohlcv_loader=lambda *_: (ohlcv(), {"source": "fixture"}),
        artifact_root=tmp_path,
    )
    assert payload["eligibility"]["MISSING_LINEAGE"] == 1
    assert payload["eligibility"]["VALID"] == 0
    assert payload["join"]["unique"] == 1


def test_symbol_only_never_recovers_lineage():
    ticket = {
        "id": 1,
        "symbol": "META",
        "as_of_date": date(2026, 7, 11),
        "research_run_id": None,
        "created_at": datetime(2026, 7, 11, 5, 0, 0),
    }
    result = recover_ticket_lineage(
        ticket,
        research_runs={
            40: {"run_id": 40, "output_date": date(2026, 7, 10), "started_at": datetime(2026, 7, 11, 4, 0, 0)},
            41: {"run_id": 41, "output_date": date(2026, 7, 12), "started_at": datetime(2026, 7, 12, 4, 0, 0)},
        },
        runs_by_output_date={},
        candidates_by_symbol_date={},
    )
    assert result["lineage_status"] == "UNRESOLVED"
    assert result["research_run_id"] is None


def test_ambiguous_run_never_recovers():
    ticket = {
        "id": 2,
        "symbol": "NVDA",
        "as_of_date": date(2026, 7, 11),
        "research_run_id": None,
        "created_at": datetime(2026, 7, 11, 4, 10, 0),
    }
    run_a = {"run_id": 40, "output_date": date(2026, 7, 11), "started_at": datetime(2026, 7, 11, 4, 0, 0)}
    run_b = {"run_id": 41, "output_date": date(2026, 7, 11), "started_at": datetime(2026, 7, 11, 4, 5, 0)}
    result = recover_ticket_lineage(
        ticket,
        research_runs={40: run_a, 41: run_b},
        runs_by_output_date={"2026-07-11": [run_a, run_b]},
        candidates_by_symbol_date={
            ("NVDA", "2026-07-11"): [
                {"id": 1, "symbol": "NVDA", "trade_date": date(2026, 7, 11), "research_run_id": 40},
                {"id": 2, "symbol": "NVDA", "trade_date": date(2026, 7, 11), "research_run_id": 41},
            ]
        },
    )
    assert result["lineage_status"] == "AMBIGUOUS"
    assert result["research_run_id"] is None


def test_unique_exact_run_recovers():
    ticket = {
        "id": 160,
        "symbol": "META",
        "as_of_date": date(2026, 7, 11),
        "research_run_id": None,
        "created_at": datetime(2026, 7, 11, 4, 12, 0),
    }
    run = {"run_id": 40, "output_date": date(2026, 7, 11), "started_at": datetime(2026, 7, 11, 4, 0, 0)}
    result = recover_ticket_lineage(
        ticket,
        research_runs={40: run},
        runs_by_output_date={"2026-07-11": [run]},
        candidates_by_symbol_date={},
    )
    assert result["lineage_status"] == "DERIVED_UNIQUE"
    assert result["research_run_id"] == 40
    overlay = overlay_recovered_lineage(ticket, {160: result})
    classified = classify_lineage(overlay, {40: run})
    assert classified["status"] == "VALID"
    assert overlay["research_run_id"] == 40
    assert ticket["research_run_id"] is None


def test_bootstrap_uses_recovered_lineage_without_mutating_tickets(tmp_path):
    tickets = [{"id": 160, "symbol": "META", "as_of_date": date(2026, 7, 11), "research_run_id": None}]
    tracking = [
        {"id": horizon, "ticket_id": 160, "symbol": "META", "as_of_date": date(2026, 7, 11),
         "horizon_days": horizon, "check_status": "completed", "forward_return": 0.01}
        for horizon in (1, 3, 5, 10)
    ]
    recovered = {
        160: {
            "ticket_id": 160,
            "research_run_id": 40,
            "lineage_status": "DERIVED_UNIQUE",
            "lineage_method": "symbol.as_of_date.unique_run.created_at",
            "lineage_source": "research_runs",
        }
    }
    payload = bootstrap_records(
        tickets,
        tracking,
        {40: {"run_id": 40, "status": "done", "output_date": date(2026, 7, 11), "config": {}}},
        ohlcv_loader=lambda *_: (ohlcv(), {"source": "fixture"}),
        artifact_root=tmp_path,
        recovered_by_ticket=recovered,
    )
    record = payload["records"][0]
    assert record["research_run_id"] == 40
    assert record["lineage"]["status"] == "VALID"
    assert record["lineage"]["lineage_status"] == "DERIVED_UNIQUE"
    assert tickets[0]["research_run_id"] is None
    assert payload["lineage_block"]["recovered_lineage"] == 1
