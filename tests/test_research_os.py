from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from capital.historical_bootstrap import tracking_returns
from capital.learning import empirical_distribution
from capital.scoring import build_capital_assessment
from capital_test_support import ohlcv
from research.boundary import PRODUCTION_BOUNDARY, assert_research_only, ranking_unchanged, skill_inventory
from research.brains import (
    LAYERS,
    build_buffett_context,
    build_future_buyer_map,
    build_serenity_context,
    build_tradingagents_adapter,
    build_uzi_adapter,
)
from research.decision import (
    build_company_research,
    contradiction_status,
    historical_analogue,
    render_company_report,
    validation_metrics,
)
from research.learning import assemble_research_sample, history_census, research_data_ready
from research.memory import filter_obsidian_as_of, ingest_note, portfolio_context
from research.outcomes import completed_horizon_returns, independent_price_outcomes


def test_buffett_context():
    unknown = build_buffett_context({"as_of_date": "2026-06-01"})
    assert unknown["produces_pick"] is False
    assert unknown["buffett_moat"]["semantic"] == "UNKNOWN"
    assert unknown["buffett_management"]["semantic"] == "UNKNOWN"
    assert unknown["buffett_quality"]["semantic"] == "UNKNOWN"
    observed = build_buffett_context({"as_of_date": "2026-06-01", "roe": 0.24, "pe_ttm": 18, "dividend_yield": 0.02})
    assert observed["buffett_quality"]["semantic"] == "DERIVED"
    assert observed["buffett_financial_quality"]["semantic"] == "OBSERVED"
    assert observed["stance"] in {"STRONG", "BULLISH", "NEUTRAL", "WEAK", "BEARISH"}


def test_serenity_context():
    empty = build_serenity_context({"as_of_date": "2026-06-01"})
    assert empty["produces_pick"] is False
    assert empty["bottleneck"]["semantic"] == "UNKNOWN"
    assert set(empty["layers"]) == set(LAYERS)
    filled = build_serenity_context({
        "as_of_date": "2026-06-01",
        "industry": "semiconductors",
        "component": "HBM",
        "bottleneck": "HBM capacity",
        "evidence_refs": ["filing:10k"],
        "chokepoint_candidates": ["MU"],
        "confidence": 0.6,
    })
    assert filled["questions"]["what_is_scarce"] == "HBM capacity"
    assert filled["chokepoint_candidates"] == ["MU"]
    assert filled["produces_pick"] is False


def test_obsidian_asset_ingestion(tmp_path):
    note = ingest_note(
        path=str(tmp_path / "NVDA.md"),
        content="---\neffective_date: 2026-06-01\n---\n# NVDA\n持仓 NVDA thesis 买入逻辑 AI",
        created_at="2026-06-01",
        updated_at="2026-06-01",
    )
    assert "NVDA" in note["tickers"]
    assert "position" in note["kinds"]
    assert note["effective_date"] == "2026-06-01"
    assert note["replay_eligible"] is True


def test_obsidian_as_of_filter():
    notes = [
        ingest_note(path="past.md", content="---\neffective_date: 2026-06-01\n---\n# NVDA past thesis"),
        ingest_note(path="future.md", content="---\neffective_date: 2026-08-01\n---\n# NVDA later conclusion"),
        ingest_note(path="undated.md", content="# NVDA no date"),
    ]
    visible = filter_obsidian_as_of(notes, "2026-06-01", historical=True)
    assert [note["source_path"] for note in visible] == ["past.md"]
    live = filter_obsidian_as_of(notes, "2026-06-01", historical=False)
    assert len(live) == 3


def test_ticket_history_import():
    census = history_census(
        [{"id": 1, "symbol": "NVDA", "as_of_date": "2026-06-01", "research_run_id": 7}],
        [
            {"ticket_id": 1, "horizon_days": 1, "check_status": "completed", "forward_return": 0.01},
            {"ticket_id": 1, "horizon_days": 3, "check_status": "pending", "forward_return": None},
        ],
        research_runs=[{"run_id": 7}],
    )
    assert census["total_tickets"] == 1
    assert census["unique_symbols"] == 1
    assert census["T+1"] == 1
    assert census["missing_outcomes"] == 1


def test_forward_tracking_completed_gate():
    rows = [
        {"horizon_days": 1, "check_status": "pending", "forward_return": 0.99, "return_1d": 0.99},
        {"horizon_days": 3, "check_status": "completed", "forward_return": 0.02},
    ]
    outcome = tracking_returns(rows)
    assert outcome["return_1d"] is None
    assert outcome["return_3d"] == 0.02
    wide = completed_horizon_returns(rows)
    assert wide["return_1d"] is None


def test_conflicting_outcomes():
    rows = [
        {"ticket_id": 1, "horizon_days": 1, "check_status": "completed", "forward_return": 0.032},
        {"ticket_id": 1, "horizon_days": 1, "check_status": "completed", "forward_return": 0.048},
        {"ticket_id": 1, "horizon_days": 3, "check_status": "completed", "forward_return": 0.01},
        {"ticket_id": 1, "horizon_days": 5, "check_status": "completed", "forward_return": 0.01},
        {"ticket_id": 1, "horizon_days": 10, "check_status": "completed", "forward_return": 0.01},
    ]
    outcome = tracking_returns(rows)
    assert outcome["outcome_conflict"] is True
    assert outcome["eligibility_reason"] == "OUTCOME_CONFLICT"
    assert outcome["return_1d"] is None
    sample = assemble_research_sample(
        {"id": 1, "symbol": "NVDA", "as_of_date": "2026-06-01", "research_run_id": 7},
        tracking_rows=rows,
        research_runs={7: {"run_id": 7}},
    )
    assert sample["valid"] is False
    assert "no_conflicting_outcome" in sample["invalid_reasons"]


def test_condition_min_samples():
    rows = [
        {
            "eligibility_reason": "VALID",
            "capital_state": "ACCUMULATION" if index < 15 else "MARKDOWN",
            "future_outcome": {"state_after_3d": "EARLY_BUILD"},
        }
        for index in range(30)
    ]
    result = empirical_distribution(rows, condition_keys=("capital_state",), outcome_key="future_outcome.state_after_3d")
    assert result["status"] == "NOT_READY"
    assert result["global_samples"] == 30
    assert result["min_condition_samples"] == 20


def test_independent_outcome_labels():
    frame = ohlcv(rows=60)
    as_of = frame["date"].iloc[39].date()
    outcome = independent_price_outcomes(frame, as_of_date=as_of)
    assert outcome["label_kind"] == "INDEPENDENT_PRICE"
    assert outcome["return_1d"] is not None
    assert outcome["mfe"] is not None
    assert outcome["mae"] is not None


def test_post_hoc_state_label_flag():
    sample = assemble_research_sample(
        {"id": 1, "symbol": "NVDA", "as_of_date": "2026-06-01", "research_run_id": 7},
        research_runs={7: {"run_id": 7}},
    )
    assert sample["state_correct_semantic"] == "POST_HOC_PUBLIC_DATA_INFERRED_PROXY"
    assert sample["intent_correct_semantic"] == "POST_HOC_PUBLIC_DATA_INFERRED_PROXY"


def test_capital_score_independence():
    weak = build_capital_assessment(ohlcv(), statistical_score=0.05)
    strong = build_capital_assessment(ohlcv(), statistical_score=0.95)
    assert weak["scores"]["capital_behavior_score"] == strong["scores"]["capital_behavior_score"]
    assert weak["scores"]["capital_score"] == weak["scores"]["capital_behavior_score"]
    assert strong["scores"]["combined_score"] != strong["scores"]["statistical_score"]


def test_no_future_leakage():
    frame = ohlcv(rows=50)
    as_of = frame["date"].iloc[20].date()
    sample = assemble_research_sample(
        {"id": 1, "symbol": "NVDA", "as_of_date": as_of, "research_run_id": 7},
        research_runs={7: {"run_id": 7}},
        ohlcv=frame,
        snapshot_max_date=frame["date"].iloc[-1].date(),
    )
    assert sample["gates"]["no_future_leakage"] is False
    assert sample["valid"] is False
    notes = [
        ingest_note(path="future.md", content="---\neffective_date: 2026-08-01\n---\n# future NVDA conclusion"),
        ingest_note(path="past.md", content="---\neffective_date: 2026-05-01\n---\n# past NVDA note"),
    ]
    leaked = assemble_research_sample(
        {"id": 2, "symbol": "NVDA", "as_of_date": "2026-06-01", "research_run_id": 7},
        research_runs={7: {"run_id": 7}},
        obsidian_notes=notes,
    )
    paths = [note["source_path"] for note in leaked["obsidian_notes"]]
    assert "future.md" not in paths
    assert "past.md" in paths


def test_portfolio_context_not_score():
    notes = [
        ingest_note(
            path="hold.md",
            content="---\neffective_date: 2026-05-01\n---\n# 持仓 NVDA thesis",
            created_at="2026-05-01",
        )
    ]
    context = portfolio_context(notes, as_of="2026-06-01", symbol="NVDA")
    assert context["already_owned"] is True
    assert context["market_alpha_adjustment"] == 0
    assert context["does_not_change_alpha"] is True
    research = build_company_research("NVDA", as_of_date="2026-06-01", notes=notes, facts={"historical_replay": True})
    assert research["market_alpha_from_portfolio"] == 0
    assert research["portfolio_context"]["market_alpha_adjustment"] == 0


def test_contradiction_engine():
    result = contradiction_status({
        "fundamental": "STRONG",
        "industry": "STRONG",
        "capital": "WEAK",
        "statistical": "STRONG",
    })
    assert result["status"] == "DIVERGENCE"
    assert result["not_a_score"] is True
    assert "优秀公司" in result["summary"]
    assert "短期资金行为未确认" in result["summary"]
    assert contradiction_status({"fundamental": "BULLISH", "industry": "BULLISH"})["status"] == "CONVERGENCE"
    assert contradiction_status({"fundamental": "UNKNOWN"})["status"] == "UNKNOWN"


def test_historical_analogue():
    analogue = historical_analogue(
        {"symbol": "NVDA", "as_of_date": "2026-06-10", "capital_state": "ACCUMULATION"},
        [
            {
                "symbol": "AMD",
                "as_of_date": "2026-05-01",
                "capital_state": "ACCUMULATION",
                "eligibility_reason": "VALID",
                "future_outcome": {"return_5d": 0.04, "mfe": 0.06, "mae": -0.02},
            }
        ],
    )
    assert analogue["not_a_production_pick"] is True
    assert analogue["sample_size"] == 1
    assert analogue["win_rate"] == 1.0


def test_production_boundary():
    assert PRODUCTION_BOUNDARY["status"] == "RESEARCH_ONLY"
    assert PRODUCTION_BOUNDARY["production_research_status"] == "PRODUCTION_RESEARCH_READY"
    assert PRODUCTION_BOUNDARY["strategy"] == "observable_footprint_v1"
    assert PRODUCTION_BOUNDARY["strategy_status"] == "FROZEN"
    assert PRODUCTION_BOUNDARY["research"] == "LIVE"
    assert PRODUCTION_BOUNDARY["replay"] == "LIVE"
    assert PRODUCTION_BOUNDARY["learning"] == "LIVE"
    assert PRODUCTION_BOUNDARY["paper"] == "PAPER_ONLY"
    assert PRODUCTION_BOUNDARY["broker"] == "NO_BROKER"
    assert PRODUCTION_BOUNDARY["live_order"] == "NO_LIVE_ORDER"
    assert ranking_unchanged(
        {"ticket_score": 1, "market_score": 0.8, "volume_confirmation_ratio": 1.2},
        {"ticket_score": 1, "market_score": 0.8, "volume_confirmation_ratio": 1.2},
    )
    uzi = build_uzi_adapter({})
    agents = build_tradingagents_adapter({})
    assert uzi["enters_production_ranking"] is False
    assert agents["enters_production_ranking"] is False
    buyers = build_future_buyer_map({"future_buyers": [{"name": "lhb", "evidence_status": "UNKNOWN"}]})
    assert buyers["observed_buyers"] == []
    research = build_company_research("NVDA", as_of_date="2026-06-01")
    assert research["produces_pick"] is False
    report = render_company_report(research)
    assert "PAPER_PICK" not in report or "not a BUY/SELL/PAPER_PICK" in report
    assert_research_only(research)
    with pytest.raises(ValueError):
        assert_research_only({"produces_pick": True})
    names = {item["name"] for item in skill_inventory()}
    assert {"buffett", "serenity", "observable_footprint_v1"} <= names


def test_candidate_id_lineage_not_available():
    sample = assemble_research_sample(
        {"id": 1, "symbol": "NVDA", "as_of_date": "2026-06-01", "research_run_id": 7},
        research_runs={7: {"run_id": 7}},
        tracking_rows=[
            {"ticket_id": 1, "horizon_days": horizon, "check_status": "completed", "forward_return": 0.01}
            for horizon in (1, 3, 5, 10)
        ],
    )
    assert sample["candidate_id_status"] == "NOT_AVAILABLE"
    assert sample["gates"]["candidate_id_lineage"] is False


def test_research_data_ready_does_not_lower_gate():
    samples = [
        {
            "valid": True,
            "as_of_date": "2026-06-01",
            "symbol": f"S{index}",
            "capital_state": "ACCUMULATION",
            "future_outcome": {},
            "gates": {"no_future_leakage": True},
        }
        for index in range(5)
    ]
    gate = research_data_ready(samples)
    assert gate["status"] == "BLOCKED"
    assert gate["sample_size"] == 5


def test_company_research_report_sections():
    report = render_company_report(build_company_research("NVDA", as_of_date="2026-06-01"))
    for heading in (
        "## 1. Portfolio Context",
        "## 2. Buffett Fundamental Analysis",
        "## 3. Serenity Industry Analysis",
        "## 4. Supply Chain / Chokepoint",
        "## 5. Capital Behavior",
        "## 6. Statistical Setup",
        "## 7. Historical Analogues",
        "## 8. Independent Future Outcomes",
        "## 9. Contradictions",
        "## 10. Risks",
        "## 11. Research Conclusion",
        "## 12. Evidence",
    ):
        assert heading in report


def test_validation_metrics_forbid_random_split_language():
    metrics = validation_metrics([])
    assert "random split forbidden" in metrics["split"]
