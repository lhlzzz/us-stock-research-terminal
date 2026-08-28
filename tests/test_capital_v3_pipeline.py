from __future__ import annotations

import json
from pathlib import Path

from capital.lifecycle import write_capital_case_libraries, write_capital_learning_artifacts
from scripts.db import pipeline_bridge


class _Result:
    def mappings(self):
        return self

    def one(self):
        return {
            "total_samples": 0,
            "valid_samples": 0,
            "train_samples": 0,
            "validation_samples": 0,
            "test_samples": 0,
            "trading_days": 0,
            "symbols": 0,
            "label_versions": [],
            "model_versions": [],
        }

    def scalar(self):
        return 0

    def __iter__(self):
        return iter(())


class _Connection:
    def execute(self, *_args, **_kwargs):
        return _Result()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _Engine:
    def connect(self):
        return _Connection()


def test_learning_artifacts_are_explicitly_not_ready_without_samples(tmp_path):
    paths = write_capital_learning_artifacts(tmp_path, "2026-08-28", engine=_Engine())
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    weekly = json.loads(paths["weekly_json"].read_text(encoding="utf-8"))

    assert payload["validation_status"] == "UNVALIDATED_NO_FIXED_CHAIN"
    assert payload["metrics"]["state_accuracy"] == "NOT_READY"
    assert weekly["production_action"] == "NO_PRODUCTION_WEIGHT_CHANGE"
    assert paths["markdown"].exists()
    assert paths["weekly_markdown"].exists()
    assert paths["cases"].exists()
    assert paths["counterexamples"].exists()


def test_case_libraries_are_empty_but_replayable_without_valid_samples(tmp_path):
    paths = write_capital_case_libraries(tmp_path, engine=_Engine())
    assert paths["cases"].read_text(encoding="utf-8") == ""
    assert paths["counterexamples"].read_text(encoding="utf-8") == ""


def test_pipeline_dataset_projection_is_skipped_without_capital_evidence(monkeypatch):
    executed = []

    class _Db:
        def execute(self, statement, params=None):
            executed.append((str(statement), params))

    count = pipeline_bridge._persist_capital_dataset(
        _Db(),
        output_date="2026-08-28",
        research_run_id=1,
        candidate_rows=[{"symbol": "ABC", "capital_evidence": {}}],
    )

    assert count == 0
    assert executed == []


def test_learning_artifact_paths_match_requested_daily_contract(tmp_path):
    paths = write_capital_learning_artifacts(tmp_path, "2026-08-28", engine=_Engine())
    assert paths["json"].name == "2026-08-28.json"
    assert paths["markdown"].name == "2026-08-28.md"
    assert paths["weekly_json"].name == "weekly-model-review-2026-35.json"
