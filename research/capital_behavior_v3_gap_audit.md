# Capital Behavior V3 Gap Audit

Date: 2026-08-28
Baseline: `main @ c0c2c3e`
Target: `capital_behavior_v3`
Status: `RESEARCH_ONLY`
Production protection: `KEEP_OBSERVABLE_FOOTPRINT_RANKING_UNCHANGED`,
`NO_PRODUCTION_WEIGHT_CHANGE`

## Existing Owners

- `scripts/capital/features.py` and `evidence.py`: bounded public OHLCV
  features and evidence semantics.
- `scripts/capital/state.py`: inferred state enum, continuity, transitions,
  duration, and confidence.
- `scripts/capital/intent.py`, `path.py`, and `control.py`: competing V2
  inference outputs and price-response controls.
- `scripts/db/pipeline_bridge.py`: one research-run transaction for daily
  Capital persistence.
- `scripts/backfill_forward_tracking.py`: due-date public-data outcome
  reconstruction and existing prediction outcome persistence.
- `scripts/capital/lifecycle.py`, `capital_backtest.py`, and `walk_forward.py`:
  research diagnostics with fixed-chain gates.
- `scripts/xiaomei_api.py` and `scripts/realtime_runner.py`: daily and
  intraday paper-only visibility.

## V3 Gaps Found

1. V2 snapshots are persisted, but there is no single training sample
   projection containing observed, derived, inferred, predicted, and future
   outcome layers with eligibility reasons.
2. Existing outcome persistence covers T+1/T+3/T+5 state proxies but not a
   versioned T+10/return/path label contract or deterministic transition label.
3. Existing walk-forward code is for factor scoring, not a reusable temporal
   split contract with purging and train/validation/test eligibility.
4. Existing calibration utilities calculate scalar diagnostics, but there is
   no empirical baseline, error taxonomy store, analogue retrieval, or drift
   projection for Capital V3.
5. There are no explicit V3 archetype, feature stability, capital decay, or
   reversal research objects.

## Data Boundary

Only public OHLCV, realtime quotes, liquidity proxies, relative strength,
market regime, and persisted research lineage are available. Institution
identity, signed order flow, order book, borrow, short interest, social
corpus, and hidden participant intent remain unavailable. Future public data
is allowed only in post-hoc outcome labels after the due date and is never
used to construct the as-of feature layer.

## Current Database Evidence

At the start of V3 implementation on 2026-08-28:

- `capital_daily_snapshot`: 0 rows
- `capital_prediction_outcome`: 0 rows
- `forward_tracking`: 1161 rows
- `tickets`: 458 rows

Therefore no V3 accuracy, calibration, economic result, or production-readiness
claim is valid yet. Insufficient samples must return `UNVALIDATED` or
`NOT_READY`.

## Planned V3 Shape

V3 adds one dataset projection and two audit projections. It does not create a
second Capital state engine, ticket issuer, broker path, or production scorer.
The dataset stores fielded features for SQL analysis and JSON layer snapshots
for replay. Dataset eligibility is based on lineage, source validity, complete
forward labels, and a chronological purged split.
