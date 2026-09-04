from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from audit_weight_mutation_surface import audit as weight_surface_audit
from full_cycle import step_pipeline_upgrade, step_weight_optimization
from market_calendar import BEIJING_TZ, CALENDAR, canonical_us_session_date, current_session, next_session
from research.boundary import (
    PRODUCTION_BOUNDARY,
    ProductionApplyBlocked,
    WeightMutationBlocked,
    assert_production_apply_blocked,
    assert_weight_mutation_allowed,
    freeze_snapshot,
    strategy_is_frozen,
    weights_are_frozen,
)
from research.failure import FAILURE_MEMORY, failure_memory, load_persistent_memory
from research.production_gate import BLOCK, PASS, evaluate_production_gate
from research.run_manifest import assert_strategy_immutable, assert_weight_version_immutable, build_run_identity
from research.run_quality import STEP_FAILED, run_quality_gate
from research.sample_identity import DuplicateSampleError, assert_unique_samples, sample_id
from research.score_semantics import SCORE_SEMANTICS, assert_no_semantic_upgrade, score_semantics
from research.store import connect, persist_replay_sample
from research.weight_mutation import KEEP_PREVIOUS_WEIGHT, request_weight_change
from risk_manager import assess_trade_risk, build_candidate_risk_record


ROOT = Path(__file__).resolve().parents[1]


def test_no_production_weight_write_bypass():
    hits = weight_surface_audit(ROOT)
    assert hits == []


def test_frozen_strategy_blocks_every_weight_path():
    assert strategy_is_frozen()
    assert weights_are_frozen()
    with pytest.raises(WeightMutationBlocked):
        assert_weight_mutation_allowed(source="daily_optimization")
    with pytest.raises(WeightMutationBlocked):
        assert_weight_mutation_allowed(source="weekly_optimization")
    with pytest.raises(WeightMutationBlocked):
        assert_weight_mutation_allowed(source="pipeline_upgrade")
    with pytest.raises(WeightMutationBlocked):
        assert_weight_mutation_allowed(source="learning")
    with pytest.raises(WeightMutationBlocked):
        assert_weight_mutation_allowed(source="self_evolve")
    with pytest.raises(WeightMutationBlocked):
        assert_weight_mutation_allowed(source="weight_optimizer")
    writes = []
    frozen = request_weight_change(
        source="weight_optimizer",
        previous={"relative_strength_vs_equal_weight": 0.45},
        proposed={"relative_strength_vs_equal_weight": 0.80},
        persist=lambda: writes.append("wrote") or True,
        sample_count=40,
        trading_days=20,
        confirmations=2,
        factor_coverage=0.9,
    )
    assert frozen["action"] == KEEP_PREVIOUS_WEIGHT
    assert frozen["persisted"] is False
    assert frozen["production_apply"] is False
    assert writes == []


def test_all_weight_mutations_use_gateway():
    scripts = ROOT / "scripts"
    illegal = []
    for path in scripts.rglob("*.py"):
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        if rel in {
            "scripts/research/weight_mutation.py",
            "scripts/audit_weight_mutation_surface.py",
            "scripts/xiaomei_production_release_audit.py",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        if "WEIGHTS_FILE.write_text" in text:
            illegal.append(rel)
        if "scoring_weights.json" in text and "write_text(" in text and "request_weight_change" not in text:
            if "run_manifest.py" in rel:
                continue
            illegal.append(rel)
    assert illegal == []


def test_pipeline_upgrade_cannot_apply_in_production():
    with pytest.raises(ProductionApplyBlocked):
        assert_production_apply_blocked(source="pipeline_upgrade")
    result = step_pipeline_upgrade(
        {"degradation": [], "recommended_actions": []},
        {"old_weights": {"a": 0.4}, "new_weights": {"a": 0.7}, "ema_smoothed": False},
    )
    assert result["status"] == "RESEARCH_PROPOSAL"
    assert result["production_apply"] is False
    assert all(action.get("production_apply") is not True for action in result["actions"])


def test_optimizer_keep_previous_on_insufficient_evidence():
    result = step_weight_optimization({"status": "INSUFFICIENT_DATA"})
    assert result["production_apply"] is False if "production_apply" in result else result["status"] == "skipped"
    empty = step_weight_optimization({"overall": {"factors": {}, "ranking": []}})
    assert empty["status"] == "skipped"
    unsigned = step_weight_optimization({
        "overall": {
            "factors": {"prior_20d_momentum": {"n": 3, "significant": False, "ic": 0.2, "abs_ic": 0.2}},
            "ranking": ["prior_20d_momentum"],
        }
    })
    assert unsigned["status"] == KEEP_PREVIOUS_WEIGHT
    assert unsigned["production_apply"] is False


def test_position_size_pct_matches_shares():
    record = build_candidate_risk_record(
        symbol="AAPL",
        entry_price=100.0,
        current_price=100.0,
        account_balance=100_000.0,
        win_rate=0.6,
        avg_win_pct=0.04,
        avg_loss_pct=0.02,
        risk_per_trade=0.02,
        max_single_position_pct=0.10,
    )
    expected_value = record["position_size_shares"] * 100.0
    assert abs(record["position_size_value"] - expected_value) < 1e-9
    assert abs(record["position_size_pct"] - expected_value / 100_000.0) < 1e-9


def test_position_size_cap_recomputes_shares():
    assessment = assess_trade_risk(
        symbol="NVDA",
        entry_price=100.0,
        current_price=100.0,
        account_balance=100_000.0,
        win_rate=0.6,
        avg_win_pct=0.04,
        avg_loss_pct=0.02,
        risk_per_trade=0.02,
        default_stop_loss_pct=0.02,
        max_single_position_pct=0.10,
    )
    assert assessment.risk_parameters.position_size_pct <= 0.10
    expected_shares = (100_000.0 * assessment.risk_parameters.position_size_pct) / 100.0
    assert abs(assessment.suggested_position_size - expected_shares) < 1e-6


def test_risk_position_size_consistency():
    record = build_candidate_risk_record(
        symbol="MSFT",
        entry_price=250.0,
        current_price=250.0,
        account_balance=50_000.0,
        win_rate=0.55,
        risk_per_trade=0.03,
        max_single_position_pct=0.08,
        default_stop_loss_pct=0.01,
    )
    assert record["risk_pass_is_not_buy"] is True
    value = record["position_size_shares"] * 250.0
    assert abs(record["position_size_value"] - value) < 1e-9
    assert abs(record["position_size_pct"] - value / 50_000.0) < 1e-9
    assert record["position_size_pct"] <= 0.08 + 1e-12


def test_risk_uses_caller_config_not_hidden_global():
    record = build_candidate_risk_record(
        symbol="AAPL",
        entry_price=100.0,
        current_price=100.0,
        account_balance=100_000.0,
        win_rate=0.6,
        avg_win_pct=0.04,
        avg_loss_pct=0.05,
        risk_per_trade=0.01,
        default_stop_loss_pct=0.03,
        max_single_position_pct=0.05,
        daily_max_loss_r=2.0,
        max_consecutive_losses=4,
    )
    assert record["stop_loss_pct"] == 0.03
    assert record["daily_max_loss_r"] == 2.0
    assert record["max_consecutive_losses"] == 4
    assert record["position_size_pct"] <= 0.05 + 1e-12


def test_replay_sample_unique_by_ticket():
    rows = [
        {"ticket_id": "A", "replay_horizon": 1, "replay_date": "2026-09-03", "symbol": "NVDA", "output_date": "2026-09-03"},
        {"ticket_id": "B", "replay_horizon": 1, "replay_date": "2026-09-03", "symbol": "NVDA", "output_date": "2026-09-03"},
    ]
    identities = assert_unique_samples(rows)
    assert identities[0] != identities[1]
    with pytest.raises(DuplicateSampleError):
        assert_unique_samples(rows + [rows[0]])


def test_multiple_tickets_same_symbol_do_not_collapse():
    a = sample_id(ticket_id="ticket-a", replay_horizon=1, replay_date="2026-09-03", symbol="NVDA")
    b = sample_id(ticket_id="ticket-b", replay_horizon=1, replay_date="2026-09-03", symbol="NVDA")
    assert a != b
    assert "ticket-a" in a
    assert "ticket-b" in b


def test_no_duplicate_ic_samples(tmp_path):
    conn = connect(tmp_path / "replay.sqlite")
    row = {
        "ticket_id": "t1",
        "symbol": "AAPL",
        "output_date": "2026-09-03",
        "replay_date": "2026-09-03",
        "replay_horizon": 1,
    }
    assert persist_replay_sample(conn, row) is True
    assert persist_replay_sample(conn, row) is False
    conn.close()


def test_score_semantics_are_not_alpha():
    payload = score_semantics({"market_score": 0.7, "ticket_score": 0.6})
    assert payload["alpha_status"] == "NOT_VALIDATED"
    assert payload["ticket_score"]["semantic"] == "candidate_ranking_composite"
    assert payload["market_score"]["semantic"] == "observable_market_footprint_proxy"
    assert payload["not_institutional_order_flow"] is True
    with pytest.raises(ValueError):
        assert_no_semantic_upgrade("observable footprint is institutional_order_flow")


def test_canonical_session_not_local_date():
    monday = datetime(2026, 9, 7, 5, tzinfo=BEIJING_TZ)
    assert CALENDAR.previous_completed_session(monday).isoformat() == "2026-09-04"
    assert canonical_us_session_date(monday).isoformat() == "2026-09-04"
    assert current_session(monday).isoformat() == "2026-09-04"
    assert next_session(monday).isoformat() == "2026-09-08"


def test_production_gate_pass_or_block_only():
    ok = evaluate_production_gate(
        session_date="2026-09-03",
        snapshot_hash="abc",
        start_weight_version="w1",
        finish_weight_version="w1",
    )
    assert ok["production_gate"] in {PASS, BLOCK}
    assert ok["production_gate"] == PASS
    blocked = evaluate_production_gate(
        session_date="2026-09-03",
        snapshot_hash="abc",
        start_weight_version="w1",
        finish_weight_version="w2",
        weight_mutation_attempted=True,
    )
    assert blocked["production_gate"] == BLOCK
    assert blocked["broker"] == "DISABLED"
    assert blocked["live_order"] == "DISABLED"


def test_run_quality_gate_hard_fail_stops_publish():
    result = run_quality_gate({
        "pipeline": {"status": "failed", "reason": "database_failure", "hard_fail": True},
        "ranking": {"status": "ok"},
    })
    assert result["status"] == "FAILED"
    assert result["stop_run"] is True
    assert result["publish_ranking"] is False
    assert result["production_output"] is False
    degraded = run_quality_gate({"research": {"status": "DATA_GAP", "reason": "research_data_gap"}})
    assert degraded["status"] == "DEGRADED"
    assert degraded["status"] != "SUCCESS"


def test_weight_and_strategy_version_immutable():
    assert_weight_version_immutable("w1", "w1")
    assert_strategy_immutable("observable_footprint_v1", "observable_footprint_v1")
    with pytest.raises(AssertionError):
        assert_weight_version_immutable("w1", "w2")
    with pytest.raises(AssertionError):
        assert_strategy_immutable("observable_footprint_v1", "other")
    identity = build_run_identity(session_date="2026-09-03", snapshot_hash="s1", weight_version="w1")
    assert identity["strategy"] == "observable_footprint_v1"
    assert identity["strategy_status"] == "FROZEN"


def test_failure_memory_survives_reload(tmp_path):
    FAILURE_MEMORY.clear()
    db = tmp_path / "fail.sqlite"
    stored = failure_memory(
        symbol="NVDA",
        as_of="2026-08-01",
        research_layer="earnings",
        failure_type="EARNINGS_MISREAD",
        persist=True,
        db_path=db,
    )
    FAILURE_MEMORY.clear()
    loaded = load_persistent_memory(db)
    assert loaded["process_local_is_not_owner"] is True
    assert any(item.get("failure_id") == stored["failure_id"] for item in loaded["failures"])


def test_freeze_keeps_research_ready_and_adds_runtime_ready():
    freeze = freeze_snapshot()
    assert freeze["production_research_status"] == "PRODUCTION_RESEARCH_READY"
    assert freeze["production_runtime_status"] == "PRODUCTION_RUNTIME_READY"
    assert freeze["xiaomei"] == "2.2.1"
    assert PRODUCTION_BOUNDARY["production_apply"] == "BLOCKED"
    assert PRODUCTION_BOUNDARY["auto_weight_change"] == "OFF"
    assert SCORE_SEMANTICS["alpha_status"] == "NOT_VALIDATED"
    assert STEP_FAILED == "STEP_FAILED"
