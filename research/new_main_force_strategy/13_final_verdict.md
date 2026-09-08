NEW_MAIN_FORCE_STRATEGY_PROFITABILITY = NOT_VALIDATED

PROFITABILITY_VALIDATED = NO

This is the only allowed conclusion label. No hedging language.

## Gates

- `identity_locked`: `PASS`
- `legacy_isolated`: `PASS`
- `asof_no_future_data`: `PASS`
- `top1_enough_sample`: `PASS`
- `t1_positive_expectancy`: `PASS`
- `profit_factor_gt_1`: `PASS`
- `cost_still_positive`: `FAIL`
- `holdout_positive`: `PASS`
- `top_beats_baselines`: `FAIL`
- `no_data_leak`: `PASS`
- `ranking_not_inverted`: `FAIL`

## Reasons

- `Bottom20pct_beats_Top20pct`
- `cost_still_positive`
- `top_beats_baselines`
- `ranking_not_inverted`

## What this does not do

- Does not retune weights.
- Does not invert factor signs.
- Does not create a second strategy.
- Does not promote Capital Brain into production ranking.
