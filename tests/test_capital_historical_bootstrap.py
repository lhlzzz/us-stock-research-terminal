from datetime import date

from capital.historical_bootstrap import bootstrap_records, funnel_from_counts
from capital.learning import MIN_SAMPLES


def test_empty_database_is_explicit_and_not_ready(tmp_path):
    payload = bootstrap_records(
        [],
        [],
        {},
        ohlcv_loader=lambda *_args: (_empty(), {}),
        artifact_root=tmp_path,
    )
    assert payload["tickets"] == 0
    assert payload["forward_tracking"] == 0
    assert payload["eligibility"]["VALID"] == 0
    assert payload["empirical"]["status"] == "NOT_READY"
    assert payload["empirical"]["min_samples"] == MIN_SAMPLES
    assert payload["production"]["production_action"] == "NO_PRODUCTION_WEIGHT_CHANGE"
    assert payload["mode"] == "dry-run"
    assert payload["lineage_block"]["complete_four_horizon_tickets"] == 0
    assert (tmp_path / "capital-learning" / "historical-bootstrap-2026-09-03.json").exists()


def test_funnel_starts_from_historical_tickets():
    funnel = funnel_from_counts(458, {
        "unique_join": 295,
        "valid_lineage": 12,
        "ohlcv_replayable": 10,
        "replay_success": 9,
        "complete_forward": 3,
        "valid": 0,
    })
    assert funnel[0]["stage"] == "Historical Tickets"
    assert funnel[-1]["stage"] == "VALID Dataset"
    assert funnel[-1]["count"] == 0


def _empty():
    import pandas as pd
    return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
