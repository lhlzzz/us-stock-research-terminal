from __future__ import annotations

from pathlib import Path

from research.boundary import PRODUCTION_BOUNDARY, RANKING_KEY, assert_research_only
from research.coverage import research_coverage, research_readiness
from research.earnings import earnings_as_of, earnings_event, guidance_change, split_surprises
from research.estimates import derived_revision_windows, estimate_revision_bundle, revisions_as_of
from research.evidence import corroboration, research_evidence
from research.failure import FAILURE_TYPES, failure_memory, learning_pattern
from research.industry import chokepoint_record, persist_industry_graph, universe_as_of, universe_snapshot
from research.providers import DATA_GAP, forbid_cross_semantic_fallback, record_provider_attempt
from research.runtime import bind_outcomes, classify_research, research_thesis_bundle, run_symbol_research, seed_demo_learning
from research.sec import filings_as_of, parse_sec_facts, resolve_amendments, resolve_fact_conflicts, sec_raw_document
from research.snapshots import research_snapshot
from research.store import connect, persist_run
from research_panel import run_full_research_panel


class FakeProvider:
    def fetch_sec(self, symbol, *, as_of=None):
        return {
            "status": DATA_GAP,
            "parsed": None,
            "submissions": None,
            "companyfacts": None,
            "events": None,
        }

    def fetch_earnings(self, symbol, *, as_of=None):
        return {"status": DATA_GAP, "events": []}

    def fetch_estimates(self, symbol, *, as_of=None):
        return {"status": DATA_GAP, "history": []}

    def fetch_industry(self, symbol, *, as_of=None):
        return {"status": DATA_GAP, "entities": []}

    def fetch_universe(self, name, *, as_of=None):
        return {"status": DATA_GAP, "membership": [], "forbids_current_backfill": True}

    def fetch_fundamentals(self, symbol, *, as_of=None):
        return {"status": DATA_GAP, "facts": {}}


def test_evidence_observed_requires_source():
    item = research_evidence(symbol="NVDA", as_of="2026-08-05", status="OBSERVED", facts={"revenue": 1})
    assert item["status"] == "ERROR"
    sourced = research_evidence(symbol="NVDA", as_of="2026-08-05", source="sec_edgar", status="OBSERVED", facts={"revenue": 1})
    assert sourced["status"] == "OBSERVED"
    assert sourced["content_hash"]


def test_sec_as_of_and_amendments():
    filings = [
        {"form": "10-Q", "filing_date": "2026-08-10", "acceptance_datetime": "2026-08-10", "accession_number": "orig", "period_of_report": "2026-07-31", "published_at": "2026-08-10", "available_at": "2026-08-10"},
        {"form": "10-Q/A", "filing_date": "2026-08-20", "acceptance_datetime": "2026-08-20", "accession_number": "amd", "period_of_report": "2026-07-31", "published_at": "2026-08-20", "available_at": "2026-08-20"},
    ]
    assert filings_as_of(filings, as_of="2026-08-05") == []
    assert [row["accession_number"] for row in filings_as_of(filings, as_of="2026-08-11")] == ["orig"]
    versions = resolve_amendments(filings, as_of="2026-08-21")
    selected = [row for row in versions if row.get("selected")]
    assert selected[0]["accession_number"] == "amd"
    assert "orig" in selected[0]["supersedes"]
    assert selected[0]["silent_overwrite"] is False


def test_sec_fact_conflict_keeps_all_evidence():
    facts = [
        {"concept": "Revenues", "period": "2026-07-31", "unit": "USD", "value": 1, "filed": "2026-08-10", "accn": "a"},
        {"concept": "Revenues", "period": "2026-07-31", "unit": "USD", "value": 2, "filed": "2026-08-20", "accn": "b"},
    ]
    resolved = resolve_fact_conflicts(facts, as_of="2026-08-21")
    assert resolved["silent_overwrite"] is False
    assert resolved["conflict_count"] == 1
    assert resolved["selected"][0]["value"] == 2
    assert len(resolved["all_evidence"]) == 2
    parsed = parse_sec_facts(facts, as_of="2026-08-11")
    assert parsed["fields"]["revenue"]["value"] == 1


def test_raw_document_is_immutable():
    doc = sec_raw_document(source_url="https://www.sec.gov/Archives/edgar/data/1/a/", accession_number="0001", form="10-K", cik="1045810", symbol="NVDA", raw_payload={"x": 1})
    assert doc["immutable"] is True
    assert doc["produces_pick"] is False
    assert doc["content_hash"]


def test_earnings_surprises_and_as_of():
    event = earnings_event(symbol="NVDA", event_date="2026-08-20", announced_at="2026-08-20", source="sec_edgar", reported_eps=1.2, consensus_eps=1.0, reported_revenue=100, consensus_revenue=110)
    split = split_surprises(event)
    assert split["eps_surprise"] == 0.2
    assert split["revenue_surprise"] == -10
    assert split["combined_score_forbidden"] is True
    visible = earnings_as_of([
        {"event_date": "2026-08-20", "announced_at": "2026-08-20", "available_at": "2026-08-20"},
        {"event_date": "2026-09-10", "announced_at": "2026-09-10", "available_at": "2026-09-10"},
    ], as_of="2026-08-25")
    assert len(visible) == 1
    gap = guidance_change(previous=None, current=None, effective_at=None, source=None)
    assert gap["status"] == DATA_GAP
    assert gap["inferred_from_headline"] is False


def test_revision_history_as_of_and_derived_windows():
    history = [
        {"estimate": 4.20, "estimate_date": "2026-07-01", "effective_date": "2026-07-01", "source": "fixture"},
        {"estimate": 4.35, "estimate_date": "2026-07-10", "effective_date": "2026-07-10", "source": "fixture"},
        {"estimate": 4.50, "estimate_date": "2026-07-25", "effective_date": "2026-07-25", "source": "fixture"},
    ]
    visible = revisions_as_of(history, as_of="2026-07-15")
    assert [row["estimate"] for row in visible] == [4.20, 4.35]
    windows = derived_revision_windows(history, as_of="2026-07-15")
    assert windows["derived_from_raw_observations"] is True
    assert windows["windows"]["30D"]["observations"]
    empty = estimate_revision_bundle(symbol="NVDA", as_of="2026-07-15", history=None, source=None)
    assert empty["status"] == DATA_GAP


def test_industry_graph_versioning_and_chokepoint_gap():
    graph = persist_industry_graph(
        None,
        entities=[{"type": "company", "id": "NVDA", "name": "NVDA", "source": "sec_edgar"}],
        relations=[{"type": "depends_on", "src": "NVDA", "dst": "Semiconductors", "source": "sec_edgar"}],
        as_of_date="2026-08-01",
    )
    assert graph["status"] == "OBSERVED"
    assert graph["graph_snapshot_id"]
    assert graph["content_hash"]
    unsourced = persist_industry_graph(None, relations=[{"type": "competes_with", "src": "A", "dst": "B"}], as_of_date="2026-08-01")
    assert unsourced["relations"][0]["status"] == "UNKNOWN"
    choke = chokepoint_record()
    assert choke["status"] == DATA_GAP


def test_universe_as_of_not_current_backfill():
    rows = [
        universe_snapshot(universe_name="CORE_UNIVERSE", symbol="OLD", effective_from="2023-01-01", effective_to="2024-12-31", source="fixture", source_url="https://example.test/2024"),
        universe_snapshot(universe_name="CORE_UNIVERSE", symbol="NEW", effective_from="2025-01-01", source="fixture", source_url="https://example.test/2026"),
    ]
    assert "OLD" in universe_as_of(rows, as_of="2024-06-01")
    assert "NEW" not in universe_as_of(rows, as_of="2024-06-01")


def test_failure_memory_is_not_a_scorer():
    item = failure_memory(symbol="NVDA", as_of="2026-08-01", research_layer="earnings", failure_type="EARNINGS_MISREAD")
    assert item["failure_type"] in FAILURE_TYPES
    assert item["changes_production_ranking"] is False
    pattern = learning_pattern(research_layer="earnings", pattern_type="eps_beat_guidance_cut")
    assert pattern["does_not_modify_ticket_score"] is True
    assert_research_only(item)


def test_readiness_is_not_bool_and_rss_cannot_corroborate_alone():
    coverage = research_coverage(symbol="NVDA", as_of="2026-08-01")
    ready = research_readiness(coverage)
    assert ready["not_a_bool"] is True
    assert ready["status"] == DATA_GAP
    assert corroboration(["rss"])["status"] == "SINGLE_SOURCE"
    assert corroboration(["sec_edgar", "company_ir"])["status"] == "CORROBORATED"


def test_cross_semantic_fallback_forbidden():
    blocked = forbid_cross_semantic_fallback("news", "sec_filing")
    assert blocked["blocked"] is True
    attempt = record_provider_attempt(provider="sec_edgar", request="fetch_sec", symbol="NVDA", as_of="2026-08-01", status="ERROR", error="timeout")
    assert attempt["silent_fallback"] is False


def test_research_run_idempotent(tmp_path: Path):
    first = run_symbol_research(symbol="NVDA", as_of="2026-08-01", provider=FakeProvider(), persist=True, db_path=tmp_path / "r.sqlite")
    second = run_symbol_research(symbol="NVDA", as_of="2026-08-01", provider=FakeProvider(), persist=True, db_path=tmp_path / "r.sqlite")
    assert first["classification"] not in {"BUY", "SELL", "ORDER"}
    assert first["produces_pick"] is False
    assert first["ranking_owner"] == "observable_footprint_v1"
    assert list(first["production_ranking_key"]) == list(RANKING_KEY)
    assert second["reused"] is True
    assert "revision" in first["data_gaps"]
    assert "universe" in first["data_gaps"]


def test_snapshot_hash_detects_mutation():
    a = research_snapshot(as_of="2026-08-01", universe={"status": DATA_GAP})
    b = research_snapshot(as_of="2026-08-01", universe={"status": DATA_GAP})
    assert a["content_hash"] == b["content_hash"]
    c = research_snapshot(as_of="2026-08-01", universe={"status": "OBSERVED", "membership": ["NVDA"]})
    assert a["content_hash"] != c["content_hash"]


def test_thesis_contradiction_and_outcomes():
    thesis = research_thesis_bundle(
        symbol="NVDA",
        as_of="2026-08-01",
        supporting=[{"name": "revenue", "value": 1}],
        contradicting=[{"name": "guidance", "value": "LOWERED"}],
        unknowns=["revision"],
        risks=["risk_unverified"],
    )
    assert thesis["status"] == "CONTRADICTORY"
    assert thesis["bullish_only_forbidden"] is True
    outcomes = bind_outcomes(None, as_of="2026-08-01")
    assert outcomes["single_total_outcome_forbidden"] is True
    assert classify_research(readiness={"status": DATA_GAP}, contradiction=thesis) == "NEEDS_MORE_EVIDENCE"


def test_legacy_adapter_and_production_boundary():
    research = run_full_research_panel(
        "NVDA",
        {"prior_20d_momentum": 0.12, "five_day_acceleration": 0.01, "relative_strength_vs_equal_weight": 0.02, "volume_confirmation_ratio": 0.4},
        {"status": "missing", "relevance_score": 0.0},
        {"status": "missing", "relevance_score": 0.0},
        {},
    )
    assert research["canonical_owner"] == "scripts.research"
    assert research["compatibility_adapter"] is True
    assert PRODUCTION_BOUNDARY["ranking_owner"] == "observable_footprint_v1"


def test_seed_learning_persists(tmp_path: Path):
    seeded = seed_demo_learning(symbol="NVDA", as_of="2026-08-01", db_path=tmp_path / "learn.sqlite")
    assert seeded["failure"]["failure_type"] == "EARNINGS_MISREAD"
    assert seeded["pattern"]["pattern_type"] == "eps_beat_guidance_cut"
    conn = connect(tmp_path / "learn.sqlite")
    rows = conn.execute("SELECT COUNT(*) FROM failure_memory").fetchone()[0]
    conn.close()
    assert rows == 1
