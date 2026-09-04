from datetime import date

from capital.historical_bootstrap import assemble_historical_outcome, complete_horizons, tracking_returns
from capital_test_support import ohlcv


def _tracking(horizon, value):
    return {
        "id": horizon,
        "ticket_id": 1,
        "symbol": "ABC",
        "as_of_date": date(2026, 2, 10),
        "horizon_days": horizon,
        "check_status": "completed",
        "forward_return": value,
    }


def test_existing_forward_returns_are_used_and_missing_horizons_stay_none():
    rows = [_tracking(1, 0.01), _tracking(3, 0.02), _tracking(5, 0.03)]
    outcome = tracking_returns(rows)
    assert outcome["return_1d"] == 0.01
    assert outcome["return_3d"] == 0.02
    assert outcome["return_5d"] == 0.03
    assert outcome["return_10d"] is None
    assert complete_horizons(outcome)["all"] is False
    assert complete_horizons(outcome)["t10"] is False


def test_complete_horizons_require_all_four_existing_returns():
    rows = [_tracking(1, 0.01), _tracking(3, 0.02), _tracking(5, 0.03), _tracking(10, 0.04)]
    outcome = tracking_returns(rows)
    assert complete_horizons(outcome) == {"t1": True, "t3": True, "t5": True, "t10": True, "all": True}


def test_historical_outcome_semantic_is_post_hoc_public_proxy():
    prior = ohlcv(rows=40)
    as_of = prior["date"].iloc[-1].date()
    outcome = assemble_historical_outcome(
        [_tracking(1, 0.01), _tracking(3, 0.02), _tracking(5, 0.03), _tracking(10, 0.04)],
        prior=prior,
        future=prior.iloc[0:0],
        as_of_date=as_of,
        current_state="ACCUMULATION",
    )
    assert outcome["return_10d"] == 0.04
    assert outcome["actual_intent_semantic"] == "POST_HOC_PUBLIC_DATA_INFERRED_PROXY"
    assert outcome["label_version"]


def test_historical_outcome_accepts_datetime_index_prior_and_date_column_future():
    frame = ohlcv(rows=52)
    as_of = frame["date"].iloc[39].date()
    prior = frame.iloc[:40].set_index("date")
    future = frame.iloc[40:].reset_index(drop=True)
    outcome = assemble_historical_outcome(
        [_tracking(1, 0.01), _tracking(3, 0.02), _tracking(5, 0.03), _tracking(10, 0.04)],
        prior=prior,
        future=future,
        as_of_date=as_of,
        current_state="ACCUMULATION",
    )
    assert outcome["return_10d"] == 0.04
    assert outcome["actual_intent_semantic"] == "POST_HOC_PUBLIC_DATA_INFERRED_PROXY"
