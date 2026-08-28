import pandas as pd

from backfill_forward_tracking import _capital_outcome
from capital.features import build_feature_set
from capital_test_support import ohlcv


def test_feature_set_is_bounded_to_supplied_as_of_frame():
    bounded = ohlcv()
    extended = bounded.copy()
    future = pd.DataFrame([{
        "date": pd.Timestamp("2027-01-01"), "open": 1_000, "high": 1_010,
        "low": 990, "close": 1_005, "volume": 99_000_000,
    }])
    extended = pd.concat([extended, future], ignore_index=True)
    first = build_feature_set(bounded)
    second = build_feature_set(extended.loc[extended["date"] <= bounded["date"].max()])
    assert first == second


def test_actual_intent_outcome_is_explicitly_post_hoc_proxy(monkeypatch):
    bars = ohlcv()
    monkeypatch.setattr("backfill_forward_tracking.fetch_bounded_ohlcv", lambda *_args, **_kwargs: bars)
    outcome = _capital_outcome(
        symbol="NVDA",
        as_of_date=bars["date"].iloc[-2].date(),
        due_date=bars["date"].iloc[-1].date(),
        horizon_days=1,
        entry_state="ACTIVE_MARKUP",
        entry_intent="PUSH_HIGHER",
        predicted_path="UP_CONTINUATION",
        forward_return=0.01,
    )
    assert outcome["actual_intent_proxy"]
    assert outcome["actual_intent_semantic"] == "POST_HOC_INFERRED_PROXY"
