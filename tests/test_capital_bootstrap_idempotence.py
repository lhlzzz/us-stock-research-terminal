from datetime import date
from pathlib import Path

from capital.dataset import sample_fingerprint
from capital.historical_bootstrap import bootstrap_records
from capital.lineage_recovery import persist_lineage
from capital.ohlcv_backfill import persist_bars
from capital_test_support import ohlcv


def _ticket(**overrides):
    row = {
        "id": 1,
        "symbol": "ABC",
        "as_of_date": date(2026, 2, 10),
        "research_run_id": 7,
        "ticket_score": 0.4,
        "market_score": 0.4,
    }
    row.update(overrides)
    return row


def _tracking(ticket_id=1, symbol="ABC", offset=0):
    return [
        {
            "id": horizon + offset,
            "ticket_id": ticket_id,
            "symbol": symbol,
            "as_of_date": date(2026, 2, 10),
            "horizon_days": horizon,
            "check_status": "completed",
            "forward_return": 0.01 * horizon,
        }
        for horizon in (1, 3, 5, 10)
    ]


def _loader(_symbol, as_of):
    frame = ohlcv()
    return frame.loc[frame["date"] <= f"{as_of}"], {"source": "fixture"}


def test_duplicate_samples_are_rejected_by_fingerprint(tmp_path):
    runs = {7: {"run_id": 7, "status": "done", "output_date": date(2026, 2, 10), "config": {}}}
    payload = bootstrap_records(
        [_ticket(), _ticket(id=2)],
        _tracking() + _tracking(ticket_id=2, offset=10),
        runs,
        ohlcv_loader=_loader,
        artifact_root=tmp_path,
    )
    fingerprints = [row.get("fingerprint") for row in payload["records"] if row.get("fingerprint")]
    assert len(fingerprints) == 2
    assert fingerprints[0] == fingerprints[1]
    assert payload["failures"]["DATASET_ERROR"] == 1


def test_persist_rerun_upserts_instead_of_duplicating(tmp_path):
    seen = []

    def persist_fn(record):
        seen.append(record["fingerprint"])

    runs = {7: {"run_id": 7, "status": "done", "output_date": date(2026, 2, 10), "config": {}}}
    first = bootstrap_records(
        [_ticket()],
        _tracking(),
        runs,
        ohlcv_loader=_loader,
        persist=True,
        persist_fn=persist_fn,
        artifact_root=tmp_path / "one",
    )
    second = bootstrap_records(
        [_ticket()],
        _tracking(),
        runs,
        ohlcv_loader=_loader,
        persist=True,
        persist_fn=persist_fn,
        artifact_root=tmp_path / "two",
    )
    assert first["persisted_tickets"] == 1
    assert second["persisted_tickets"] == 1
    assert seen[0] == seen[1]
    assert sample_fingerprint(
        symbol="ABC",
        as_of_date="2026-02-10",
        research_run_id=7,
        model_version="capital_behavior_v2",
    ) == seen[0]


def test_partial_persist_failure_is_recorded_and_does_not_halt(tmp_path):
    calls = []

    def persist_fn(record):
        calls.append(record["ticket_id"])
        if record["ticket_id"] == 1:
            raise RuntimeError("boom")

    payload = bootstrap_records(
        [_ticket(), _ticket(id=3, symbol="DEF")],
        _tracking() + _tracking(ticket_id=3, symbol="DEF", offset=20),
        {7: {"run_id": 7, "status": "done", "output_date": date(2026, 2, 10), "config": {}}},
        ohlcv_loader=_loader,
        persist=True,
        persist_fn=persist_fn,
        artifact_root=tmp_path,
    )
    assert payload["failures"]["DATASET_ERROR"] == 1
    assert payload["persisted_tickets"] == 1
    assert calls == [1, 3]


class _FakeResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    def mappings(self):
        return self._rows


class _FakeSession:
    def __init__(self):
        self.statements = []

    def execute(self, statement, params=None):
        self.statements.append((str(statement), dict(params or {})))
        return _FakeResult()


def test_lineage_persist_is_idempotent_on_ticket_id():
    db = _FakeSession()
    row = {
        "ticket_id": 160,
        "research_run_id": 40,
        "lineage_status": "DERIVED_UNIQUE",
        "lineage_method": "symbol.as_of_date.unique_run.created_at",
        "lineage_source": "research_runs",
        "confidence": 1.0,
        "evidence": {"level": 4},
    }
    first = persist_lineage(db, [row])
    second = persist_lineage(db, [row])
    assert first == 1
    assert second == 1
    assert len(db.statements) == 2
    assert "ON CONFLICT (ticket_id)" in db.statements[0][0]
    assert "ON CONFLICT (ticket_id)" in db.statements[1][0]


def test_ohlcv_persist_is_idempotent_on_symbol_date_provider():
    db = _FakeSession()
    bars = [{"trade_date": date(2026, 2, 10), "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1000}]
    first = persist_bars(db, "ABC", bars, "provider_cache")
    second = persist_bars(db, "ABC", bars, "provider_cache")
    assert first == 1
    assert second == 1
    assert "ON CONFLICT (symbol, trade_date, source_provider)" in db.statements[0][0]
    assert db.statements[0][1]["symbol"] == "ABC"
    assert db.statements[1][1]["symbol"] == "ABC"
