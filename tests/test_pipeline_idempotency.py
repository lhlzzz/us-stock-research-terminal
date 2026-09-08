from __future__ import annotations

from pathlib import Path

from db import crud
from daily_loop import _python_env
from xiaomei_scheduler import _python_env as scheduler_python_env


def test_duplicate_ticket_run_is_upsert():
    source = Path(crud.__file__).read_text()
    assert "def create_ticket" in source
    assert "return upsert_ticket" in source
    assert "output_date=output_date, symbol=symbol, as_of_date=as_of_date" in source


def test_pipeline_lock_and_step_state_exist():
    script = Path(__file__).resolve().parents[1] / "scripts" / "daily_pipeline.sh"
    text = script.read_text()
    assert "daily-pipeline.lock" in text
    assert "acquire_lock" in text
    assert "skip_if_completed" in text
    assert "step_status" in text
    assert "artifact_hash" in text
    assert 'export PYTHONPATH="$PROJECT_DIR:$SCRIPT_DIR' in text


def test_backfill_uses_scripts_dir_pipeline_bridge_import():
    source = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "backfill_forward_tracking.py"
    ).read_text()
    assert "from db.pipeline_bridge import _refresh_capital_dataset_splits" in source
    assert "from scripts.db.pipeline_bridge import _refresh_capital_dataset_splits" not in source


def test_runtime_pythonpath_includes_project_and_scripts():
    root = Path(__file__).resolve().parents[1]
    for env in (_python_env(), scheduler_python_env()):
        parts = env["PYTHONPATH"].split(":")
        assert str(root) in parts
        assert str(root / "scripts") in parts


def test_us_stock_knowledge_loop_is_scheduled_and_gated():
    root = Path(__file__).resolve().parents[1]
    scheduler = (root / "scripts" / "xiaomei_scheduler.py").read_text()
    pipeline = (root / "scripts" / "daily_pipeline.sh").read_text()
    assert 'id="knowledge_loop"' in scheduler
    assert "obsidian_vault" in scheduler
    assert "require_production_vaults" in pipeline
    from obsidian.paths import DAILY_FOLDER, require_production_vaults
    assert str(DAILY_FOLDER) == "美股/xiaomei_memory/daily"
    vaults = require_production_vaults()
    assert "美股" in vaults["us_root"]
    assert "xiaomei_memory/daily" in vaults["daily_dir"]
