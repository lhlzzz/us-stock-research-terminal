from __future__ import annotations

import pandas as pd

from research.temporal import classify_bar, daily_bar_gate, historical_claim_eligible, temporal_record
from us_profit_ticket_pipeline import _enrich_panels_with_realtime


def test_historical_claim_as_of_contract():
    record = temporal_record(published_at="2026-01-01", effective_date="2026-01-02", retrieved_at="2026-09-01", as_of="2026-06-01")
    assert record["published_at_is_not_retrieved_at"] is True
    ok = historical_claim_eligible(record, as_of="2026-06-01")
    assert ok["eligible"] is True
    assert ok["retrieved_at_after_as_of_is_not_violation"] is True
    blocked = historical_claim_eligible({"published_at": "2026-07-01", "effective_date": "2026-07-01"}, as_of="2026-06-01")
    assert blocked["eligible"] is False


def test_realtime_is_not_daily_complete():
    idx = pd.to_datetime(["2026-09-03"])
    close = pd.DataFrame({"NVDA": [100.0]}, index=idx)
    adj = close.copy()
    long_panel = pd.DataFrame({"date": ["2026-09-03"], "symbol": ["NVDA"], "Close": [100.0]})
    out_close, out_adj, out_long = _enrich_panels_with_realtime(close, adj, long_panel, ["NVDA"])
    assert list(out_close.index) == list(close.index)
    assert len(out_long) == 1
    bar = classify_bar(bar_type="INTRADAY_PARTIAL", is_complete=False)
    assert bar["usable_for_daily_factors"] is False
    assert daily_bar_gate(bar) is False
    assert classify_bar(bar_type="DAILY_COMPLETE", is_complete=True)["usable_for_daily_ranking"] is True
