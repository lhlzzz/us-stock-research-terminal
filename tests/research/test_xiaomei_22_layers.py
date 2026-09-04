from __future__ import annotations

from research.earnings import earnings_from_sec_facts
from research.estimates import estimate_revision
from research.industry import industry_from_sec
from research.providers import DATA_GAP
from research.sec import sec_research_bundle


def test_sec_bundle_gap_without_submissions():
    payload = sec_research_bundle(symbol="NVDA", as_of="2026-08-01", submissions=None, status=DATA_GAP)
    assert payload["status"] == DATA_GAP
    assert payload["produces_pick"] is False


def test_earnings_from_empty_sec_is_data_gap():
    payload = earnings_from_sec_facts(symbol="NVDA", as_of="2026-08-01", parsed={"fields": {}}, filings=[])
    assert payload["status"] == DATA_GAP
    assert payload["consensus_status"] == DATA_GAP if "consensus_status" in payload else True


def test_estimate_revision_unknown_without_source():
    row = estimate_revision(symbol="NVDA", metric="eps", estimate=1.2, estimate_date="2026-07-01", source=None)
    assert row["status"] == DATA_GAP
    assert row["revision_direction"] == "UNKNOWN"


def test_industry_from_sec_without_sic_is_data_gap():
    graph = industry_from_sec({"symbol": "NVDA"}, as_of="2026-08-01")
    assert graph["status"] == DATA_GAP
    assert graph["chokepoint"]["status"] == DATA_GAP
