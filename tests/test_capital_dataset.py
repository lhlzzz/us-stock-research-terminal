from datetime import date

from capital.dataset import assemble_dataset_sample, canonical_json, dataset_stats


def _snapshot(**overrides):
    row = {
        "symbol": "ABC",
        "as_of_date": "2026-08-20",
        "research_run_id": 7,
        "data_version": "PUBLIC_OHLCV_V2",
        "model_version": "capital_behavior_v2",
        "feature_version": "capital_features_v2",
        "source_lineage": {"status": "VALID", "source": "daily_klines"},
        "features": {"price": 100.0, "volume": 1000, "liquidity_proxy": 0.8},
        "evidence": {"evidence": {"absorption": {"value": 0.7}}},
        "state": {"capital_state": "ACCUMULATION", "state_confidence": 0.8},
        "intent": {"capital_intent": "ACCUMULATE", "intent_probability": 0.6},
        "path": {"paths": {"t1": {"UP_CONTINUATION": 0.6}, "t3": {}, "t5": {}}},
    }
    row.update(overrides)
    return row


def test_dataset_sample_preserves_layers_and_split_eligibility():
    sample = assemble_dataset_sample(
        _snapshot(),
        outcome={"return_1d": 0.01, "return_3d": 0.02, "return_5d": 0.03, "return_10d": 0.04},
        split="train",
    )
    assert sample["eligibility_reason"] == "VALID"
    assert sample["eligible_for_training"] is True
    assert sample["inferred_state"]["capital_state"] == "ACCUMULATION"
    assert sample["path_distribution_t1"] == {"UP_CONTINUATION": 0.6}
    assert "future_outcome" in sample


def test_dataset_rejects_missing_lineage_and_forward_data():
    missing_lineage = assemble_dataset_sample(_snapshot(research_run_id=None))
    missing_outcome = assemble_dataset_sample(_snapshot())
    assert missing_lineage["eligibility_reason"] == "MISSING_LINEAGE"
    assert missing_outcome["eligibility_reason"] == "INSUFFICIENT_FORWARD_DATA"
    assert not missing_outcome["eligible_for_training"]


def test_dataset_payload_is_deterministic_and_stats_are_explicit():
    a = assemble_dataset_sample(_snapshot(), outcome={"return_1d": 0.01, "return_3d": 0.02, "return_5d": 0.03, "return_10d": 0.04}, split="TEST")
    b = assemble_dataset_sample(_snapshot(), outcome={"return_10d": 0.04, "return_5d": 0.03, "return_3d": 0.02, "return_1d": 0.01}, split="TEST")
    assert canonical_json(a) == canonical_json(b)
    assert dataset_stats([a]) == {
        "total_samples": 1, "valid_samples": 1, "train_samples": 0,
        "validation_samples": 0, "test_samples": 1, "trading_days": 1,
        "symbols": 1, "label_versions": ["capital_label_v1"],
        "model_versions": ["capital_behavior_v2"],
    }
