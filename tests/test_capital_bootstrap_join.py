from datetime import date

from capital.historical_bootstrap import classify_join, join_audit


def test_ticket_id_join_is_unique_even_when_symbol_date_collides():
    ticket = {"id": 1, "symbol": "ABC", "as_of_date": date(2026, 2, 10), "research_run_id": 7}
    tracking = [
        {"id": 10, "ticket_id": 1, "symbol": "ABC", "as_of_date": date(2026, 2, 10), "horizon_days": 1},
        {"id": 11, "ticket_id": 2, "symbol": "ABC", "as_of_date": date(2026, 2, 10), "horizon_days": 1},
    ]
    by_ticket = {1: [tracking[0]], 2: [tracking[1]]}
    by_symbol_date = {("ABC", "2026-02-10"): tracking}
    result = classify_join(ticket, by_ticket, by_symbol_date)
    assert result["status"] == "UNIQUE"
    assert result["method"] == "ticket_id"


def test_symbol_date_join_is_missing_lineage_when_multiple_tickets_share_the_date():
    ticket = {"id": 99, "symbol": "ABC", "as_of_date": date(2026, 2, 10), "research_run_id": None}
    tracking = [
        {"id": 10, "ticket_id": 1, "symbol": "ABC", "as_of_date": date(2026, 2, 10)},
        {"id": 11, "ticket_id": 2, "symbol": "ABC", "as_of_date": date(2026, 2, 10)},
    ]
    result = classify_join(ticket, {}, {("ABC", "2026-02-10"): tracking})
    assert result["status"] == "AMBIGUOUS"
    assert result["reason"] == "MISSING_LINEAGE"
    assert result["rows"] == []


def test_symbol_date_does_not_steal_another_ticket_tracking():
    ticket = {"id": 99, "symbol": "ABC", "as_of_date": date(2026, 2, 10), "research_run_id": None}
    tracking = [
        {"id": 10, "ticket_id": 1, "symbol": "ABC", "as_of_date": date(2026, 2, 10), "horizon_days": 1},
    ]
    result = classify_join(ticket, {}, {("ABC", "2026-02-10"): tracking})
    assert result["status"] == "ORPHAN_TICKET"
    assert result["reason"] == "MISSING_FORWARD"
    assert result["rows"] == []


def test_missing_forward_and_orphan_tracking_are_counted_separately():
    tickets = [
        {"id": 1, "symbol": "ABC", "as_of_date": date(2026, 2, 10)},
        {"id": 2, "symbol": "DEF", "as_of_date": date(2026, 2, 10)},
    ]
    tracking = [
        {"id": 10, "ticket_id": 1, "symbol": "ABC", "as_of_date": date(2026, 2, 10)},
        {"id": 11, "ticket_id": 9, "symbol": "ZZZ", "as_of_date": date(2026, 2, 10)},
    ]
    audit = join_audit(tickets, tracking)
    assert audit["unique"] == 1
    assert audit["orphan_ticket"] == 1
    assert audit["orphan_tracking"] == 1
