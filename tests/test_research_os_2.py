from __future__ import annotations

import pytest

from research.boundary import PRODUCTION_BOUNDARY, assert_research_only, skill_inventory
from research.contracts import (
    capital_behavior,
    company_quality,
    independent_scores,
    industry_position,
    lineage_status,
    market_setup,
    research_horizon_contract,
)
from research.decision import (
    build_company_research,
    contradiction_status,
    research_decision_matrix,
    why_not,
)
from research.evidence import CLAIM_KINDS, EVIDENCE_LEVELS, claim
from research.fundamentals import (
    company_fundamentals,
    earnings_intelligence,
    estimate_revision_direction,
    management_allocation,
    sbc_dilution,
    sec_filing,
)
from research.governance import evolve_change
from research.industry import (
    persist_industry_graph,
    portfolio_risk_graph,
    research_universes,
    supply_chain_portfolio,
    update_industry_memory,
)
from research.market_context import analyst_revision, options_intelligence, short_intelligence
from research.query import research_dashboard, research_query
from research.regime import classify_research_regime, earnings_regime
from research.stability import factor_stability, weight_change_guard
from research.status import completion_status
from research.thesis import (
    attribution,
    calibrate_brain,
    compare_thesis,
    failure_case,
    research_similarity,
    similar_failures,
    thesis_learning,
    thesis_ledger,
)
from research.validate import all_brain_validations


def test_four_brain_schemas_are_independent():
    company = company_quality({"business_quality": 0.9, "as_of_date": "2026-08-27"})
    industry = industry_position({"chokepoint_strength": 0.8, "as_of_date": "2026-08-27"})
    capital = capital_behavior({
        "capital_behavior_score": 0.4,
        "capital_state": "DISTRIBUTION",
        "company_quality": 0.99,
        "statistical_score": 0.99,
        "as_of_date": "2026-08-27",
    })
    market = market_setup({"trend": 0.7, "momentum": 0.6, "as_of_date": "2026-08-27"})
    assert company["schema"] == "company_quality"
    assert industry["schema"] == "industry_position"
    assert capital["schema"] == "capital_behavior"
    assert market["schema"] == "market_setup"
    assert "company_quality" not in capital["evidence"]
    assert "statistical_score" not in capital["evidence"]
    scores = independent_scores(company, industry, capital, market, statistical_score=0.91)
    assert scores["research_composite"] != scores["alpha_score"]
    assert scores["not_a_single_total"] is True
    assert scores["long_term_quality"] == company["score"]
    assert scores["capital_edge"] == 0.4


def test_fundamentals_sec_earnings_sbc():
    fundamentals = company_fundamentals({"revenue": 100, "as_of_date": "2026-08-27"}, symbol="NVDA", as_of="2026-08-27")
    assert "free_cash_flow" in fundamentals["data_gaps"]
    assert fundamentals["status"] == "DATA_GAP"
    filing = sec_filing({"filing_type": "10-K", "ticker": "NVDA"})
    assert filing["status"] == "DATA_GAP"
    assert "10-Q" in filing["supported_types"]
    revision = estimate_revision_direction([1.0, 1.1, 1.2])
    assert revision["estimate_revision_direction"] == "UP"
    earnings = earnings_intelligence({"price_up": True, "eps_estimate_history": [2.0, 1.8, 1.5]})
    assert earnings["estimate_revision_direction"]["estimate_revision_direction"] == "DOWN"
    assert earnings["fundamental_improvement"] is False
    sbc = sbc_dilution({"buyback_announced": True, "buyback_amount": 10, "share_count_start": 100, "share_count_end": 101, "stock_based_compensation": 8, "share_issuance": 3})
    assert "BUYBACK_QUALITY_WARNING" in sbc["warnings"]
    assert sbc["net_shareholder_capital_return"] == -1.0
    mgmt = management_allocation({"management_says": "beat", "management_delivered": "miss", "guidance_hits": [True, False]})
    assert mgmt["says_vs_delivered"] == "SEPARATED"
    assert mgmt["guidance_hit_rate"] == 0.5


def test_industry_graph_memory_and_universes():
    first = persist_industry_graph(None, entities=[{"type": "company", "name": "NVDA"}], relations=[{"type": "bottlenecks", "src": "TSM", "dst": "NVDA"}], as_of_date="2026-08-01")
    second = persist_industry_graph(first, entities=[{"type": "component", "name": "HBM"}], as_of_date="2026-08-27")
    assert len(second["entities"]) == 2
    memory = update_industry_memory({"graph": first}, {"entities": [{"type": "material", "name": "CoWoS"}], "note": "added cowos"})
    assert memory["rezeroed"] is False
    universes = research_universes(core=["NVDA", "AAPL"], industry=["AVGO"], chokepoint=["TSM"])
    assert universes["does_not_replace_production_universe"] is True
    chain = supply_chain_portfolio(["NVDA", "AMD"], second, symbol="NVDA")
    assert chain["enters_alpha_score"] is False
    graph = portfolio_risk_graph(["NVDA", "AMD", "AVGO"], themes={"NVDA": "AI capex", "AMD": "AI capex", "AVGO": "AI capex"})
    assert graph["concentrated"] is True
    assert graph["enters_alpha_score"] is False


def test_factor_guard_and_regimes():
    stable = factor_stability({"factor": "rs", "current_ic": 0.2, "rolling_30d_ic": 0.18, "rolling_60d_ic": 0.19, "rolling_120d_ic": 0.21, "sample_count": 40, "coverage": 0.9})
    assert stable["factor_status"] == "STABLE"
    reversed_ = factor_stability({"factor": "rs", "current_ic": -0.2, "rolling_30d_ic": 0.2, "sample_count": 40})
    assert reversed_["factor_status"] == "REVERSED"
    guard = weight_change_guard(0.45, 0.80, sample_count=5, trading_days=2, confirmations=0)
    assert guard["action"] == "KEEP_PREVIOUS_WEIGHT"
    regime = classify_research_regime({"breadth": 0.8})
    assert regime["regime"] == "RISK_ON"
    assert regime["does_not_replace_production_classifier"] is True
    event = earnings_regime({"is_earnings_day": True, "gap_risk": 0.04})
    assert event["setup"] == "EVENT_SETUP"
    assert event["regime"] == "EARNINGS_DAY"


def test_options_short_analyst_not_buy_signals():
    options = options_intelligence({"put_call": 1.4, "implied_volatility": 0.4, "iv_rank": 80, "options_open_interest": 1, "gamma": 0, "dealer_gamma": 0, "gamma_walls": 0, "skew": 0, "expiration": "2026-09-19"})
    assert options["not_a_buy_condition"] is True
    assert options["stance"] == "BEARISH"
    short = short_intelligence({"short_interest": 0.25, "short_interest_change": 0.05})
    assert short["high_si_is_not_bullish"] is True
    assert short["state"] == "short_build"
    analyst = analyst_revision({"analyst_upgrades": 8, "analyst_downgrades": 1})
    assert analyst["estimate_momentum"] == "ESTIMATE_MOMENTUM_UP"


def test_contradiction_matrix_why_not_and_horizon():
    views = {
        "company": "STRONG",
        "fundamental": "STRONG",
        "industry": "STRONG",
        "capital": "WEAK",
        "market": "STRONG",
        "options": "BEARISH",
        "portfolio": "OVERWEIGHT",
    }
    contradiction = contradiction_status(views)
    assert contradiction["status"] == "DIVERGENCE"
    assert contradiction["not_averaged"] is True
    unresolved = contradiction_status({"company": "STRONG", "capital": "NEUTRAL"})
    assert unresolved["status"] == "UNRESOLVED"
    matrix = research_decision_matrix(views)
    assert matrix["matrix"]["company"] == "STRONG"
    assert matrix["not_only_score"] is True
    rejected = why_not(views, capital={"capital_state": "DISTRIBUTION"}, options={"stance": "BEARISH"}, portfolio={"already_owned": True})
    assert "Capital = distribution" in rejected["why_not"]
    assert "SHORT_TERM_NOT_READY" in rejected["conclusion"]
    horizon = research_horizon_contract({"as_of_date": "2026-08-27", "research_horizon": "LONG_TERM"})
    assert horizon["forbids_long_term_as_t1"] is True


def test_thesis_failure_calibration_similarity_attribution():
    ledger = thesis_ledger({"symbol": "NVDA", "thesis": "demand growth", "anti_thesis": "capex peak", "invalidation": "revenue deceleration"})
    compared = compare_thesis(ledger, {"thesis": "demand stall", "conflicts": True, "as_of": "2026-08-27"})
    assert compared["status"] == "CONFLICT"
    learned = thesis_learning({"thesis": "需求增长", "prediction": "revenue acceleration", "outcome": "no acceleration", "error": "thesis failure", "failure_modes": ["THESIS_BREAK"]})
    assert "THESIS_BREAK" in learned["thesis_failure_modes"]
    failed = failure_case({"symbol": "XYZ", "failure_reason": "FALSE_BREAKOUT", "brain_at_entry": "Market"})
    assert failed["failure_reason"] == "FALSE_BREAKOUT"
    similar = similar_failures({"failure_reason": "FALSE_BREAKOUT"}, [failed])
    assert similar["count"] == 1
    cal = calibrate_brain("Buffett", [{"confidence": 0.9, "hit": False}, {"confidence": 0.9, "hit": True}])
    assert cal["buckets"][0]["confidence_bucket"] == "0.9"
    assert cal["buckets"][0]["actual_hit_rate"] == 0.5
    sim = research_similarity({"company": "NVDA", "industry": "AI", "setup": "breakout"}, {"company": "NVDA", "industry": "AI", "setup": "reversal"})
    assert sim["not_text_only"] is True
    assert sim["dimensions"]["company"] == 1.0
    attr = attribution({"alpha_from_company": 0.01, "alpha_from_market": 0.04})
    assert attr["alpha_from_market"] == 0.04


def test_query_dashboard_lineage_governance_status():
    payload = research_query("research company NVDA", company={"symbol": "NVDA"})
    assert payload["produces_pick"] is False
    assert research_query("research industry AI datacenter")["kind"] == "research industry"
    dash = research_dashboard({"company_quality": {"score": 0.8}, "alpha_score": 0.3})
    assert dash["not_a_single_total"] is True
    assert "Company Quality" in dash["hero"]
    blocked = lineage_status(source="filing", feature="revenue", source_date="2026-09-01", effective_date="2026-09-01", as_of_date="2026-08-01", brain="Company")
    assert blocked["decision"] == "BLOCK"
    rejected = evolve_change(key="buffett_principles", before="keep", after="change")
    assert rejected["action"] == "REJECT"
    recorded = evolve_change(key="evidence_momentum_weight", before=0.2, after=0.22, evidence={"ic": 0.1}, validation={"status": "READY"})
    assert recorded["rollback"] == 0.2
    status = completion_status({"valid_ticket_count": 0, "company_data_coverage": 0.1})
    assert status["status"] in {"PARTIAL", "DATA_GAP", "VALIDATION_GAP"}
    assert status["status"] != "COMPLETE_RESEARCH_OS"
    assert status["feature_implemented_is_not_research_validated"] is True


def test_evidence_hierarchy_and_skill_owners():
    item = claim(1, semantic="OBSERVED", source="10-K", source_type="sec_filing")
    assert item["kind"] == "FACT"
    assert item["level"] == "LEVEL_1"
    predicted = claim(0.5, semantic="PREDICTED", source="model", source_type="statistical_brain")
    assert predicted["kind"] == "PREDICTED"
    assert set(CLAIM_KINDS) == {"FACT", "DERIVED", "INFERRED", "PREDICTED"}
    assert "LEVEL_1" in EVIDENCE_LEVELS
    names = {item["name"] for item in skill_inventory()}
    assert {"buffett", "serenity", "quant", "obsidian", "postgresql"} <= names
    for item in skill_inventory():
        if item["name"] != "observable_footprint_v1":
            assert item["produces_pick"] is False
    with pytest.raises(ValueError):
        assert_research_only({"classification": "BUY"})


def test_company_research_keeps_production_boundary():
    research = build_company_research(
        "NVDA",
        as_of_date="2026-08-27",
        facts={"business_quality": 0.8, "chokepoint_strength": 0.7, "trend": 0.6},
        capital={"capital_behavior_score": 0.3, "capital_state": "DISTRIBUTION", "stance": "WEAK"},
        statistical={"statistical_score": 0.8, "stance": "STRONG"},
    )
    assert research["produces_pick"] is False
    assert research["market_alpha_from_portfolio"] == 0
    assert research["scores"]["research_composite_is_not_alpha"] is True
    assert research["research_conclusion"]["not_buy_sell"] is True
    assert research["supply_chain_portfolio"]["enters_alpha_score"] is False
    assert PRODUCTION_BOUNDARY["live_order"] == "NO_LIVE_ORDER"
    assert PRODUCTION_BOUNDARY["production_research_status"] == "PRODUCTION_RESEARCH_READY"
    assert PRODUCTION_BOUNDARY["strategy_status"] == "FROZEN"
    validations = all_brain_validations([])
    assert validations["company_quality"]["status"] == "VALIDATION_GAP"
