from __future__ import annotations

from pathlib import Path

import pytest

from daily_loop import run_daily_loop
from full_cycle import step_pipeline_upgrade
from research.boundary import ProductionApplyBlocked, WeightMutationBlocked, assert_production_apply_blocked, assert_weight_mutation_allowed
from research.production_gate import BLOCK, evaluate_production_gate
from research.sample_identity import DuplicateSampleError, assert_unique_samples
from research.score_semantics import assert_no_semantic_upgrade
from research.weight_mutation import KEEP_PREVIOUS_WEIGHT, request_weight_change


def test_simulate_direct_weight_write_is_blocked():
    with pytest.raises(WeightMutationBlocked):
        assert_weight_mutation_allowed(source="direct_file_write")


def test_simulate_optimizer_mutation_is_blocked():
    writes = []
    result = request_weight_change(
        source="weight_optimizer",
        previous={"a": 0.2},
        proposed={"a": 0.9},
        persist=lambda: writes.append(1),
        sample_count=100,
        trading_days=40,
        confirmations=4,
        factor_coverage=1.0,
    )
    assert result["action"] == KEEP_PREVIOUS_WEIGHT
    assert result["production_apply"] is False
    assert writes == []


def test_simulate_strategy_version_change_blocks_gate():
    gate = evaluate_production_gate(
        session_date="2026-09-03",
        snapshot_hash="hash",
        strategy="other_strategy",
        strategy_status="LIVE",
        start_weight_version="w1",
        finish_weight_version="w1",
    )
    assert gate["production_gate"] == BLOCK


def test_simulate_duplicate_replay_blocks():
    rows = [
        {"ticket_id": "t1", "replay_horizon": 1, "replay_date": "2026-09-03"},
        {"ticket_id": "t1", "replay_horizon": 1, "replay_date": "2026-09-03"},
    ]
    with pytest.raises(DuplicateSampleError):
        assert_unique_samples(rows)
    gate = evaluate_production_gate(
        session_date="2026-09-03",
        snapshot_hash="hash",
        samples=rows,
        start_weight_version="w1",
        finish_weight_version="w1",
    )
    assert gate["production_gate"] == BLOCK
    assert gate["checks"]["sample_integrity"] == BLOCK


def test_simulate_future_dated_data_blocks_semantic_upgrade():
    with pytest.raises(ValueError):
        assert_no_semantic_upgrade("this is smart_money institutional buying")


def test_simulate_missing_provider_blocks_gate():
    gate = evaluate_production_gate(
        session_date="2026-09-03",
        snapshot_hash="hash",
        provider_status={"sec": "INFRA_FAILURE"},
        start_weight_version="w1",
        finish_weight_version="w1",
    )
    assert gate["production_gate"] == BLOCK
    assert gate["checks"]["provider_integrity"] == BLOCK


def test_simulate_calendar_mismatch_blocks_gate():
    gate = evaluate_production_gate(
        session_date=None,
        snapshot_hash="hash",
        start_weight_version="w1",
        finish_weight_version="w1",
    )
    assert gate["production_gate"] == BLOCK
    assert gate["checks"]["canonical_session"] == BLOCK


def test_simulate_invalid_risk_configuration_blocks_gate():
    gate = evaluate_production_gate(
        session_date="2026-09-03",
        snapshot_hash="hash",
        risk_ok=False,
        start_weight_version="w1",
        finish_weight_version="w1",
    )
    assert gate["production_gate"] == BLOCK
    assert gate["checks"]["risk_integrity"] == BLOCK


def test_simulate_pipeline_partial_failure_blocks_gate():
    gate = evaluate_production_gate(
        session_date="2026-09-03",
        snapshot_hash="hash",
        database_ok=False,
        start_weight_version="w1",
        finish_weight_version="w1",
    )
    assert gate["production_gate"] == BLOCK


def test_simulate_broker_and_live_order_blocked():
    gate = evaluate_production_gate(
        session_date="2026-09-03",
        snapshot_hash="hash",
        broker_enabled=True,
        live_order_enabled=True,
        start_weight_version="w1",
        finish_weight_version="w1",
    )
    assert gate["production_gate"] == BLOCK
    assert gate["checks"]["no_broker"] == BLOCK
    assert gate["checks"]["no_live_order"] == BLOCK


def test_simulate_production_apply_blocked():
    with pytest.raises(ProductionApplyBlocked):
        assert_production_apply_blocked(source="full_cycle")
    result = step_pipeline_upgrade({}, {})
    assert result["production_apply"] is False
    assert result["status"] == "RESEARCH_PROPOSAL"


def test_daily_loop_skip_pipeline_does_not_mutate_weights(monkeypatch, tmp_path):
    from research import run_manifest

    monkeypatch.setattr(run_manifest, "WEIGHTS_FILE", tmp_path / "scoring_weights.json")
    (tmp_path / "scoring_weights.json").write_text('{"weights": {"relative_strength_vs_equal_weight": 0.45}}')
    monkeypatch.setattr("daily_loop.step_backfill", lambda: {"status": "ok"})
    monkeypatch.setattr("daily_loop.step_factor_backtest", lambda: {"status": "ok", "result": {}})
    monkeypatch.setattr("daily_loop.step_weight_optimization", lambda _fb: {"status": "ok", "result": {"production_apply": False}})
    monkeypatch.setattr("daily_loop.step_scoreboard", lambda: {"status": "ok"})
    monkeypatch.setattr("daily_loop.step_degradation", lambda: {"status": "ok"})
    monkeypatch.setattr(run_manifest, "MANIFEST_DIR", tmp_path / "manifests")
    result = run_daily_loop(output_date="2026-09-03", skip_pipeline=True)
    assert result["weight_mutation"] == "BLOCKED"
    assert result["production_apply"] == "BLOCKED"
    assert result["broker"] == "DISABLED"
    assert result["live_order"] == "DISABLED"
    assert result["strategy_status"] == "FROZEN"
    assert Path(result["identity"] and run_manifest.WEIGHTS_FILE).read_text().find("0.45") >= 0
