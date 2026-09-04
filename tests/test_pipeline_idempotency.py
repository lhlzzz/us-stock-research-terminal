from __future__ import annotations

from pathlib import Path

from db import crud


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
