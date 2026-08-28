from datetime import date, timedelta

from capital.dataset import assign_split, purged_temporal_split


def test_temporal_split_is_ordered_and_purged():
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(30)]
    split = purged_temporal_split(dates, train_ratio=0.6, validation_ratio=0.2, horizon_days=2)
    assert split.train_dates == tuple(dates[:16])
    assert max(split.train_dates) < min(split.validation_dates)
    assert max(split.validation_dates) < min(split.test_dates)
    assert date(2026, 1, 19) in split.embargo_dates
    assert date(2026, 1, 18) in split.embargo_dates
    assert assign_split(dates[0], split) == "TRAIN"
    assert assign_split(dates[-1], split) == "TEST"
    assert assign_split(date(2025, 12, 31), split) is None


def test_temporal_split_is_deterministic_and_rejects_invalid_ratios():
    dates = ["2026-01-03", "2026-01-01", "2026-01-02"]
    assert purged_temporal_split(dates, horizon_days=0) == purged_temporal_split(dates, horizon_days=0)
    try:
        purged_temporal_split(dates, train_ratio=0.8, validation_ratio=0.3)
    except ValueError as exc:
        assert "leave a positive test partition" in str(exc)
    else:
        raise AssertionError("invalid ratios must fail")
