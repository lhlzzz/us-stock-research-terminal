from datetime import date

from capital.dataset import assemble_dataset_sample, sample_fingerprint
from capital.historical_bootstrap import bootstrap_records, eligibility_for_ticket
from capital.learning import MIN_SAMPLES
from capital_test_support import ohlcv


def test_valid_requires_lineage_source_versions_and_complete_forward():
    versions = {"data_version": "PUBLIC_OHLCV_V2", "model_version": "capital_behavior_v2", "feature_version": "capital_features_v2"}
    complete = {"return_1d": 0.01, "return_3d": 0.02, "return_5d": 0.03, "return_10d": 0.04}
    assert eligibility_for_ticket(lineage_status="MISSING_LINEAGE", source_status="REPLAYABLE", versions=versions, outcome=complete) == "MISSING_LINEAGE"
    assert eligibility_for_ticket(lineage_status="VALID", source_status="SOURCE_INVALID", versions=versions, outcome=complete) == "SOURCE_INVALID"
    assert eligibility_for_ticket(lineage_status="VALID", source_status="DATA_GAP", versions=versions, outcome=complete) == "DATA_GAP"
    assert eligibility_for_ticket(lineage_status="VALID", source_status="OHLCV_UNAVAILABLE", versions=versions, outcome=complete) == "DATA_GAP"
    assert eligibility_for_ticket(lineage_status="VALID", source_status="REPLAYABLE", versions={"data_version": ""}, outcome=complete) == "VERSION_INVALID"
    assert eligibility_for_ticket(lineage_status="VALID", source_status="REPLAYABLE", versions=versions, outcome={"return_1d": 0.01}) == "INSUFFICIENT_FORWARD_DATA"
    assert eligibility_for_ticket(lineage_status="VALID", source_status="REPLAYABLE", versions=versions, outcome=complete) == "VALID"


def test_sample_fingerprint_is_stable_and_rejects_duplicates(tmp_path):
    first = sample_fingerprint(symbol="ABC", as_of_date="2026-02-10", research_run_id=7, model_version="capital_behavior_v2")
    second = sample_fingerprint(symbol="abc", as_of_date="2026-02-10", research_run_id=7, model_version="capital_behavior_v2")
    assert first == second
    sample = assemble_dataset_sample({
        "symbol": "ABC",
        "as_of_date": "2026-02-10",
        "research_run_id": 7,
        "data_version": "PUBLIC_OHLCV_V2",
        "model_version": "capital_behavior_v2",
        "feature_version": "capital_features_v2",
        "source_lineage": {"status": "VALID"},
    }, outcome={"return_1d": 0.01, "return_3d": 0.02, "return_5d": 0.03, "return_10d": 0.04})
    assert sample["sample_fingerprint"] == first


def test_empirical_baseline_stays_not_ready_below_min_samples(tmp_path):
    payload = bootstrap_records([], [], {}, ohlcv_loader=lambda *_: (ohlcv(), {"source": "fixture"}), artifact_root=tmp_path)
    assert payload["empirical"]["status"] == "NOT_READY"
    assert payload["empirical"]["min_samples"] == MIN_SAMPLES
    assert MIN_SAMPLES >= 30
