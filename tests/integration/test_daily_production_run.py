from __future__ import annotations

from pathlib import Path

import pytest

from daily_loop import run_daily_loop
from market_calendar import CALENDAR
from research.boundary import freeze_snapshot
from research.production_gate import PASS


def test_daily_production_run_skip_pipeline(monkeypatch, tmp_path):
    freeze = freeze_snapshot()
    assert freeze["strategy_status"] == "FROZEN"
    from research import run_manifest

    monkeypatch.setattr(run_manifest, "MANIFEST_DIR", tmp_path / "manifests")
    monkeypatch.setattr("daily_loop.step_backfill", lambda: {"status": "ok"})
    monkeypatch.setattr("daily_loop.step_factor_backtest", lambda: {"status": "DATA_GAP", "reason": "research_data_gap", "result": {}})
    monkeypatch.setattr("daily_loop.step_weight_optimization", lambda _fb: {"status": "ok", "result": {"production_apply": False, "decision": "KEEP_PREVIOUS_WEIGHT"}})
    monkeypatch.setattr("daily_loop.step_scoreboard", lambda: {"status": "ok"})
    monkeypatch.setattr("daily_loop.step_degradation", lambda: {"status": "ok"})

    result = run_daily_loop(output_date=CALENDAR.previous_completed_session().isoformat(), skip_pipeline=True)
    assert result["strategy_status"] == "FROZEN"
    assert result["weight_mutation"] == "BLOCKED"
    assert result["production_apply"] == "BLOCKED"
    assert result["broker"] == "DISABLED"
    assert result["live_order"] == "DISABLED"
    assert result["production_gate"]["production_gate"] in {PASS, "BLOCK"}
    assert result["canonical_us_session_date"]
    assert Path(result["manifest_path"]).exists()


def test_scheduler_dry_identity_uses_canonical_session():
    session = CALENDAR.previous_completed_session().isoformat()
    assert len(session) == 10
    freeze = freeze_snapshot()
    assert freeze["production_runtime_status"] == "PRODUCTION_RUNTIME_READY"
    assert freeze["broker"] == "NO_BROKER"
