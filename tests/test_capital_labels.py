import pandas as pd

from capital.labels import label_future_outcomes, outcome_is_complete


def _bars(periods=40, extra_gain=0.0):
    dates = pd.date_range("2026-08-01", periods=periods, freq="D")
    close = [100.0] * 20 + [100.0 + i * (1.0 + extra_gain) for i in range(periods - 20)]
    return pd.DataFrame({
        "date": dates,
        "open": close,
        "high": [value + 1.0 for value in close],
        "low": [value - 1.0 for value in close],
        "close": close,
        "volume": [1000] * periods,
    })


def test_labels_are_post_hoc_and_complete_only_with_all_horizons():
    frame = _bars(40)
    outcome = label_future_outcomes(frame, as_of_date="2026-08-20", current_state="ACCUMULATION")
    assert outcome["label_version"] == "capital_label_v1"
    assert outcome["return_1d"] is not None
    assert outcome["return_10d"] is not None
    assert outcome["actual_intent_semantic"] == "POST_HOC_PUBLIC_DATA_INFERRED_PROXY"
    assert outcome_is_complete(outcome)


def test_future_bars_after_horizon_do_not_change_label():
    base = _bars(40)
    extended = pd.concat([
        base,
        pd.DataFrame({
            "date": pd.date_range("2026-09-10", periods=5, freq="D"),
            "open": [1000.0] * 5,
            "high": [1010.0] * 5,
            "low": [990.0] * 5,
            "close": [1000.0] * 5,
            "volume": [100000] * 5,
        }),
    ], ignore_index=True)
    first = label_future_outcomes(base, as_of_date="2026-08-20")
    second = label_future_outcomes(extended, as_of_date="2026-08-20")
    for key in ("return_1d", "return_3d", "return_5d", "return_10d", "path_after_10d"):
        assert first[key] == second[key]


def test_missing_forward_bars_stay_unavailable():
    outcome = label_future_outcomes(_bars(23), as_of_date="2026-08-20")
    assert outcome["available"] is True
    assert outcome["return_10d"] is None
    assert not outcome_is_complete(outcome)
