from __future__ import annotations

import asyncio

import xiaomei_api


class _Result:
    def __init__(self, *, one=None, first=None, rows=None):
        self._one = one
        self._first = first
        self._rows = rows or []

    def mappings(self):
        return self

    def one(self):
        return self._one

    def first(self):
        return self._first

    def __iter__(self):
        return iter(self._rows)


class _Connection:
    def execute(self, statement, _params=None):
        sql = str(statement)
        if "COUNT(*) AS total_samples" in sql:
            return _Result(one={
                "total_samples": 0, "valid_samples": 0, "train_samples": 0,
                "validation_samples": 0, "test_samples": 0, "trading_days": 0,
                "symbols": 0, "label_versions": None, "model_versions": None,
            })
        return _Result(first=None, rows=[])

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _Engine:
    def connect(self):
        return _Connection()


def test_v3_api_empty_dataset_stays_not_ready(monkeypatch):
    monkeypatch.setattr(xiaomei_api, "get_engine", lambda: _Engine())

    status = asyncio.run(xiaomei_api.get_capital_dataset_status())
    probabilities = asyncio.run(xiaomei_api.get_capital_probabilities("ABC"))
    analogues = asyncio.run(xiaomei_api.get_capital_analogues("ABC"))
    errors = asyncio.run(xiaomei_api.get_capital_errors("ABC"))
    lifecycle = asyncio.run(xiaomei_api.get_capital_lifecycle("ABC"))
    performance = asyncio.run(xiaomei_api.get_capital_model_performance())
    drift = asyncio.run(xiaomei_api.get_capital_model_drift())

    assert status["dataset_status"] == "NOT_READY"
    assert status["validation_status"] == "UNVALIDATED_NO_FIXED_CHAIN"
    assert probabilities["status"] == "NOT_READY"
    assert analogues["status"] == "NOT_READY"
    assert errors["status"] == "NOT_READY"
    assert lifecycle["status"] == "NOT_READY"
    assert performance["status"] == "NOT_READY"
    assert drift["status"] == "NOT_READY"
