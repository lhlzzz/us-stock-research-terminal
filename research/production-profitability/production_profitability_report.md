# Production Profitability Report

READ ONLY validation of frozen `observable_footprint_v1`.

## Distinctions

- LEGACY BACKTEST RESULT: 56.9% / +1.75% (672 trades, research/historical-backtest-report.md)
- LIVE/HISTORICAL REALIZED RESULT T+1: 51.24% / -0.26%
- CURRENT STRATEGY RECONSTRUCTED Top1 T+1 (FULL_ASOF_PANEL): 50.00% / +0.02% (full_pool_days=47; universe=daily_klines_as_of_membership; catalyst=unavailable_as_of_equals_zero)
- INDEX MEMBERSHIP: DATA_GAP_NO_TRUE_HISTORICAL_MEMBERSHIP
- SELECTED_TICKET_ONLY Top1 T+1: 54.17% / +0.57% (cannot prove CURRENT STRATEGY EDGE)
- RECENT HOLDOUT T+1: 40.00% / -0.41%

## Anomalies

- missing_future_price: 3
- duplicate_ticket: 0
- duplicate_ticket_date_symbol: 93
- duplicate_sample: 0
- future_data_detected: 218
- invalid_date: 74
- price_basis_mismatch: 276
- missing_factor_snapshot: 0
- missing_ticket_score: 0
- unknown_strategy_version: 446
- adj_close_available: 0
- kline_close_available: 435447
- mixed_price_basis_in_returns: 0
- return_price_basis: forward_tracking_as_of_close_to_due_close
- asof_universe_source: daily_klines_as_of_membership
- index_universe_status: DATA_GAP_NO_TRUE_HISTORICAL_MEMBERSHIP
- asof_catalyst_policy: unavailable_as_of_equals_zero
- usable_sample_count: 468
- excluded_sample_count: 693
- exclusion_rate: 0.5968992248062015

## Verdict reasons

- historical_realized_future_data_detected
- asof_price_basis_unadjusted_close
- price_basis_mismatch_audited_not_used_in_returns
- historical_realized_high_exclusion_rate
- reconstructed_t1_expectancy=0.00021003160479685437
- reconstructed_t1_profit_factor=1.014241696598373
- reconstructed_t1_n=46
- recent_pos=False
- realized_t1_expectancy=-0.002607719008264465

```text
====================================================
XIAOMEI CURRENT STRATEGY PROFITABILITY VALIDATION
====================================================

Strategy:
observable_footprint_v1

Strategy Status:
FROZEN

Historical Tickets:
458

Unique Tickets:
458

Valid T+1 Samples:
121

----------------------------------------------------
T+1
----------------------------------------------------

Win Rate:
51.24%

Average Return:
-0.26%

Median Return:
+0.23%

Profit Factor:
0.84

Expectancy:
-0.26%

Max Drawdown (historical realized Top1):
-13.24%

----------------------------------------------------
T+3
----------------------------------------------------

Win Rate:
43.80%

Average Return:
-1.53%

Median Return:
-0.33%

Profit Factor:
0.48

Expectancy:
-1.53%

----------------------------------------------------
T+5
----------------------------------------------------

Win Rate:
45.37%

Average Return:
-2.17%

Median Return:
-0.63%

Profit Factor:
0.42

Expectancy:
-2.17%

----------------------------------------------------
T+10
----------------------------------------------------

Win Rate:
55.08%

Average Return:
+1.06%

Median Return:
+0.64%

Profit Factor:
1.34

Expectancy:
+1.06%

----------------------------------------------------
CURRENT STRATEGY RECONSTRUCTION
----------------------------------------------------

Universe source:
daily_klines_as_of_membership

Index membership:
DATA_GAP_NO_TRUE_HISTORICAL_MEMBERSHIP

Catalyst policy:
unavailable_as_of_equals_zero

FULL_ASOF_PANEL days:
47

SELECTED_TICKET_ONLY days:
58

Price basis:
kline_close_unadjusted

Top 1:
50.00% win
+0.02% avg

Top 3:
55.88% win
+0.28% avg

Max Drawdown (as-of Top1):
-28.31%

Top 1 SELECTED_TICKET_ONLY:
54.17% win
+0.57% avg
NOTE: past selected names only; not CURRENT STRATEGY EDGE

Recent Holdout:
40.00% win
-0.41% avg

----------------------------------------------------
COST STRESS
----------------------------------------------------

0 bps:
PASS

10 bps:
FAIL

25 bps:
FAIL

50 bps:
FAIL

----------------------------------------------------
RECONCILIATION
----------------------------------------------------

DB ↔ Obsidian:
53.54%

Historical ↔ Current Strategy:
2.16%

----------------------------------------------------
FINAL
----------------------------------------------------

PROFITABILITY:
NOT_PROFITABLE

PROFITABILITY_VALIDATED:
NO

PRODUCTION STRATEGY:
observable_footprint_v1

STRATEGY CHANGE:
NONE

WEIGHT CHANGE:
NONE

```
