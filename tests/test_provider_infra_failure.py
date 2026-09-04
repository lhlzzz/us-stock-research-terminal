from __future__ import annotations

from research.providers import DATA_GAP, INFRA_FAILURE, provider_record
from research.production_gate import BLOCK, evaluate_production_gate


def test_infra_failure_is_not_data_gap():
    assert INFRA_FAILURE != DATA_GAP
    record = provider_record(symbol="NVDA", as_of="2026-09-03", source="sec", status=INFRA_FAILURE)
    assert record["status"] == INFRA_FAILURE
    gap = provider_record(symbol="NVDA", as_of="2026-09-03", source="sec", status=DATA_GAP)
    assert gap["status"] == DATA_GAP


def test_provider_infra_failure_blocks_production_gate():
    gate = evaluate_production_gate(
        session_date="2026-09-03",
        snapshot_hash="hash",
        provider_status={"sec": INFRA_FAILURE},
        start_weight_version="w1",
        finish_weight_version="w1",
    )
    assert gate["production_gate"] == BLOCK
    assert gate["checks"]["provider_integrity"] == BLOCK
