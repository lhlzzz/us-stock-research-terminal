from __future__ import annotations

from research.contracts import company_quality, independent_scores, risk_view
from research.decision import contradiction_status, historical_analogue, validation_metrics
from research.evidence import claim, claim_kind, contradictory_evidence, highest_evidence_quality
from research.market_context import analyst_revision, short_intelligence
from research.memory import extract_tickers, ingest_note, portfolio_concentration, portfolio_context
from research.metric_semantics import (
    MetricSpec,
    research_median,
    score_research_metrics,
)
from research.providers import DATA_GAP, GapSECDataProvider, ingest_record
from research.thesis import (
    FAILURE_MEMORY,
    compare_thesis,
    research_failure_lifecycle,
    research_similarity,
    retrieve_failure_context,
)
from research.weight_mutation import KEEP_PREVIOUS_WEIGHT, request_weight_change
from research.stability import weight_change_guard


def test_raw_revenue_and_debt_cannot_become_quality_one():
    revenue = score_research_metrics([{"name": "revenue", "value": 100, "semantic": "OBSERVED"}])
    debt = score_research_metrics([{"name": "debt", "value": 50, "semantic": "OBSERVED"}])
    mixed = score_research_metrics([
        {"name": "revenue", "value": 100, "semantic": "OBSERVED"},
        {"name": "debt", "value": 50, "semantic": "OBSERVED"},
        {"name": "roe", "value": 0.2, "semantic": "OBSERVED"},
    ])
    assert revenue["score"] is None
    assert debt["score"] is None
    assert mixed["score"] != 1
    assert "revenue" in mixed["refused"]
    company = company_quality({"revenue": 100, "debt": 50, "as_of_date": "2026-08-27"})
    assert company["score"] != 1
    assert MetricSpec(name="roe", direction="higher_better", normalization="bounded").direction == "higher_better"


def test_different_units_cannot_be_averaged():
    result = score_research_metrics([
        {"name": "revenue", "value": 100, "semantic": "OBSERVED"},
        {"name": "debt_to_equity", "value": 2.5, "semantic": "OBSERVED"},
        {"name": "shares_outstanding", "value": 1_000_000, "semantic": "OBSERVED"},
    ])
    assert result["score"] is None
    assert result["semantic"] == "UNKNOWN"


def test_high_risk_is_caution_not_strong():
    high = risk_view({"gap_risk": 0.8, "drawdown_risk": 0.75, "liquidity_risk": 0.7, "event_risk": 0.72, "short_pressure": 0.8})
    assert high["score"] >= 0.70
    assert high["stance"] == "CAUTION"
    assert high["risk_level"] == "HIGH"
    assert high["stance"] != "STRONG"
    low = risk_view({"gap_risk": 0.1, "drawdown_risk": 0.1, "liquidity_risk": 0.2, "event_risk": 0.1, "short_pressure": 0.05})
    assert low["risk_level"] == "LOW"
    assert low["stance"] == "FAVORABLE"
    scores = independent_scores(risk=high)
    assert scores["risk"]["stance"] == "CAUTION"
    assert scores["quality"]["stance"] == "UNKNOWN"


def test_weight_mutation_gateway_blocks_bypass():
    writes = []

    def persist():
        writes.append("wrote")
        return "ok"

    blocked = request_weight_change(
        source="self_evolve",
        previous=0.20,
        proposed=0.30,
        persist=persist,
        sample_count=5,
        trading_days=2,
        confirmations=0,
        key="evidence_momentum_weight",
    )
    assert blocked["action"] == KEEP_PREVIOUS_WEIGHT
    assert blocked["persisted"] is False
    assert writes == []

    optimizer = request_weight_change(
        source="weight_optimizer",
        previous={"relative_strength": 0.45},
        proposed={"relative_strength": 0.80},
        persist=persist,
        sample_count=5,
        trading_days=2,
        confirmations=0,
        factor_coverage=0.4,
    )
    assert optimizer["action"] == KEEP_PREVIOUS_WEIGHT
    assert optimizer["persisted"] is False
    assert writes == []

    guard = weight_change_guard(0.45, 0.80, sample_count=5, trading_days=2, confirmations=0)
    failed = request_weight_change(
        source="optimizer",
        previous=0.45,
        proposed=0.80,
        persist=persist,
        sample_count=5,
        trading_days=2,
        confirmations=0,
    )
    assert guard["action"] == KEEP_PREVIOUS_WEIGHT
    assert failed["persisted"] is False
    assert writes == []

    allowed = request_weight_change(
        source="weight_optimizer",
        previous=0.45,
        proposed=0.50,
        persist=persist,
        sample_count=40,
        trading_days=20,
        confirmations=2,
        factor_coverage=0.9,
    )
    assert allowed["action"] == "UPDATE_WEIGHT"
    assert allowed["persisted"] is True
    assert writes == ["wrote"]

    learning_blocked = request_weight_change(
        source="learning",
        previous=0.45,
        proposed=0.50,
        persist=persist,
        sample_count=40,
        trading_days=20,
        confirmations=2,
        factor_coverage=0.9,
    )
    assert learning_blocked["action"] == KEEP_PREVIOUS_WEIGHT
    assert learning_blocked["persisted"] is False
    assert "learning_cannot_auto_weight" in learning_blocked["reasons"]
    assert writes == ["wrote"]


def test_self_evolve_cannot_bypass_guard(monkeypatch):
    import xiaomei_self_evolve

    class _Engine:
        pass

    monkeypatch.setattr(xiaomei_self_evolve, "_get_config", lambda _engine, _key: "0.20")
    persisted = []
    monkeypatch.setattr(xiaomei_self_evolve, "_persist_config", lambda *_a, **_k: persisted.append(1))
    result = xiaomei_self_evolve._set_config(_Engine(), "evidence_momentum_weight", "0.30", "bypass attempt")
    assert result["persisted"] is False
    assert persisted == []
    assert result["source"] == "self_evolve"


def test_short_states_are_all_reachable():
    build = short_intelligence({"short_interest_change": 0.05, "short_interest": 0.2})
    pressure = short_intelligence({"short_interest_change": 0, "borrow_tightness": 0.8, "short_interest": 0.2})
    cover = short_intelligence({
        "short_interest_change": -0.04,
        "borrow_tightness": 0.9,
        "price_change": 0.06,
        "volume": 2.0,
        "short_interest": 0.22,
    })
    neutral = short_intelligence({"short_interest": 0.05, "short_interest_change": 0, "borrow_tightness": 0.1})
    assert build["state"] == "short_build"
    assert pressure["state"] == "short_pressure"
    assert cover["state"] == "forced_cover"
    assert neutral["state"] == "neutral"


def test_obsidian_ticker_universe_and_note_kinds():
    assert extract_tickers("AI USD USA CEO GDP SEC ETF") == []
    assert extract_tickers("the SEC reviewed GDP in the USA") == []
    mention = ingest_note(
        path="research.md",
        content="---\neffective_date: 2026-05-01\n---\nNVDA remains an important research paragraph.",
    )
    assert "NVDA" in mention["tickers"]
    assert mention["note_kind"] == "mention"
    context = portfolio_context([mention], as_of="2026-06-01", symbol="NVDA")
    assert context["already_owned"] is False
    assert "NVDA" not in context["owned_symbols"]

    holding = ingest_note(
        path="hold.md",
        content="---\nkind: holding\nticker: NVDA\neffective_date: 2026-05-01\n---\nNVDA thesis",
    )
    assert holding["note_kind"] == "holding"
    owned = portfolio_context([holding], as_of="2026-06-01", symbol="NVDA")
    assert owned["already_owned"] is True
    assert owned["owned_symbols"] == ["NVDA"]

    watch = ingest_note(
        path="watch.md",
        content="---\nkind: watching\nticker: NVDA\neffective_date: 2026-05-01\n---\nwatch NVDA",
    )
    watched = portfolio_context([watch], as_of="2026-06-01", symbol="NVDA")
    assert watched["already_owned"] is False
    assert "NVDA" in watched["watchlist_symbols"]


def test_evidence_quality_dates_and_unknown_not_inferred():
    future = claim(
        1,
        semantic="OBSERVED",
        source="10-K",
        source_type="sec_filing",
        effective_date="2026-07-10",
        as_of_date="2026-07-01",
    )
    assert future["status"] == "BLOCKED"
    assert future["blocked"] is True
    assert future["value"] is None
    unknown = claim(None, semantic="UNKNOWN", source="gap", source_type="public_quote")
    assert unknown["semantic"] == "UNKNOWN"
    assert unknown["kind"] == "UNKNOWN"
    assert unknown["kind"] != "INFERRED"
    assert claim_kind("UNKNOWN") == "UNKNOWN"
    quality = highest_evidence_quality([
        {"level": "LEVEL_4", "semantic": "OBSERVED", "value": 1},
        {"level": "LEVEL_1", "semantic": "OBSERVED", "value": 1},
    ])
    assert quality == "LEVEL_1"
    conflicts = contradictory_evidence([
        {"name": "revenue", "value": 10, "semantic": "OBSERVED"},
        {"name": "revenue", "value": 99, "semantic": "OBSERVED"},
    ])
    assert conflicts
    status = contradiction_status(
        {"company": "STRONG", "capital": "WEAK"},
        claims=[{"level": "LEVEL_1"}, {"level": "LEVEL_6"}],
    )
    assert status["highest_evidence_quality"] == "LEVEL_1"


def test_portfolio_concentration_real_weights_or_unknown():
    real = portfolio_concentration(
        ["NVDA", "MSFT", "META"],
        {"NVDA": 0.45, "MSFT": 0.25, "META": 0.10, "CASH": 0.20},
        cash=0.20,
    )
    assert real["top_position"] == 0.45
    assert abs(real["top3_concentration"] - 0.80) < 1e-9
    assert real["forged_equal_weight"] is False
    missing = portfolio_concentration(["NVDA", "MSFT"])
    assert missing["position_weight"] == "UNKNOWN"
    assert missing["top_position"] == "UNKNOWN"


def test_missing_is_not_zero():
    analyst = analyst_revision({})
    assert analyst["analyst_upgrades"] is None
    assert analyst["analyst_downgrades"] is None
    assert analyst["analyst_upgrades"] != 0
    assert analyst["missing"] == "UNKNOWN"
    assert analyst["estimate_momentum"] == "UNKNOWN"


def test_thesis_structured_diff():
    added = compare_thesis({}, {"thesis": {"valuation": "cheap"}})
    assert added["fields"]["valuation"] == "ADDED"
    removed = compare_thesis({"thesis": {"valuation": "cheap", "risk": "low"}}, {"thesis": {"risk": "low"}})
    assert removed["fields"]["valuation"] == "REMOVED"
    changed = compare_thesis({"thesis": {"valuation": "cheap"}}, {"thesis": {"valuation": "fair"}})
    assert changed["fields"]["valuation"] == "CHANGED"
    contradicted = compare_thesis({"thesis": {"valuation": "cheap"}}, {"thesis": {"valuation": "expensive"}})
    assert contradicted["fields"]["valuation"] == "CONTRADICTED"


def test_similarity_is_explained_and_not_industry_one():
    same_industry = research_similarity({"industry": "semiconductors"}, {"industry": "semiconductors"})
    assert same_industry["score"] != 1.0
    assert same_industry["components"]["industry"] == 1.0
    explained = research_similarity(
        {"ticker": "NVDA", "industry": "semiconductors", "thesis": "demand growth", "capital_behavior": "accumulation", "market_regime": "risk_on"},
        {"ticker": "NVDA", "industry": "semiconductors", "thesis": "demand stall", "capital_behavior": "accumulation", "market_regime": "risk_off"},
    )
    assert set(explained["components"]) <= {"ticker", "industry", "thesis", "factor", "market_regime", "capital_behavior", "outcome"}
    assert explained["score"] is not None
    assert explained["score"] < 1.0


def test_failure_lifecycle_is_retrievable_warning_only():
    FAILURE_MEMORY.clear()
    record = research_failure_lifecycle(
        {"symbol": "XYZ", "thesis": "breakout holds", "prediction": "up", "failure_reason": "THESIS_FAILURE"},
        {"outcome": "down", "failed": True, "root_cause": "false breakout"},
    )
    assert record["failed_hypothesis"] is True
    assert record["memory"] is True
    assert record["not_a_production_signal"] is True
    retrieved = retrieve_failure_context({"failure_reason": "THESIS_FAILURE"})
    assert retrieved["count"] >= 1
    assert retrieved["not_a_production_signal"] is True
    assert retrieved["future_research_context"] is True


def test_research_median_even_odd_single_empty():
    assert research_median([]) is None
    assert research_median([3]) == 3
    assert research_median([1, 3, 2]) == 2
    assert research_median([1, 2, 3, 4]) == 2.5
    analogue = historical_analogue(
        {"symbol": "NVDA", "as_of_date": "2026-08-01"},
        [
            {"symbol": "AAPL", "as_of_date": "2026-06-01", "eligibility_reason": "VALID", "future_outcome": {"return_5d": 0.1}},
            {"symbol": "MSFT", "as_of_date": "2026-06-02", "eligibility_reason": "VALID", "future_outcome": {"return_5d": 0.2}},
        ],
    )
    assert analogue["median_return"] == 0.15
    metrics = validation_metrics([
        {"valid": True, "as_of_date": "2026-08-01", "symbol": "A", "independent_outcome": {"return_1d": 0.1}},
        {"valid": True, "as_of_date": "2026-08-02", "symbol": "B", "independent_outcome": {"return_1d": 0.2}},
    ])
    assert metrics["T+1"]["median"] == 0.15


def test_ingestion_contract_blocks_future_but_not_late_retrieval():
    blocked = ingest_record(
        1,
        source="sec",
        effective_date="2026-07-10",
        as_of="2026-07-01",
        retrieved_at="2026-07-11",
    )
    assert blocked["status"] == "BLOCKED"
    assert blocked["future_leakage"] is True
    late = ingest_record(
        1,
        source="sec",
        published_at="2026-06-01",
        effective_date="2026-06-01",
        as_of="2026-07-01",
        retrieved_at="2026-07-10",
    )
    assert late["status"] == "READY"
    assert late["dropped_because_retrieved_late"] is False
    assert late["retrieved_after_as_of_is_not_future_leakage"] is True
    gap = GapSECDataProvider().get("NVDA", as_of="2026-07-01")
    assert gap["status"] == DATA_GAP
    assert gap["empty_is_not_no_filing"] is True
