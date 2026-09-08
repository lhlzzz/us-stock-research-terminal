# Historical As-Of Replay

```text
Historical Trading Day
        ↓
as-of daily_klines universe + quality floors
        ↓
bars with trade_date <= as_of only
        ↓
capital_behavior_v2 (statistical_score=0)
        ↓
full candidate pool saved
        ↓
sort (capital_behavior_score, capital_strength, demand_persistence)
        ↓
simulate Top1 / Top3 / Top5
        ↓
forward unadjusted close-to-close
```

- full_asof_days: `394`
- incomplete_days: `0`
- candidate_rows: `32060`
- future_data_in_features: `False`
- price_basis: `kline_close_unadjusted`
- universe: `daily_klines_as_of_membership`
- index membership: `DATA_GAP_NO_TRUE_HISTORICAL_MEMBERSHIP`

No future ranking. No post-hoc winner selection. No manual replacement.

## Daily status counts

- `FULL_ASOF_PANEL`: `394`
