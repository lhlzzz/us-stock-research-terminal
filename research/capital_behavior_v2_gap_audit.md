# Capital Behavior V2 Gap Audit

Date: 2026-08-28
Baseline: `main @ 255996c`
Status: `RESEARCH_ONLY`
Production protection: `KEEP_OBSERVABLE_FOOTPRINT_RANKING_UNCHANGED`,
`NO_PRODUCTION_WEIGHT_CHANGE`
Capital validation: `UNVALIDATED_NO_FIXED_CHAIN`

## Scope and Data Boundary

The audit covers the existing owners in `scripts/capital/`, the daily
pipeline and persistence bridge, realtime paper context, lifecycle/backtest,
walk-forward, optimizer, and the current Capital API. The model is limited to
public OHLCV, realtime quote, liquidity proxies, relative strength, market
regime, and public-catalyst evidence. It cannot identify institutions,
principal participants, signed trades, borrow, short interest, order book, or
hidden flow. Unavailable inputs must remain unavailable.

## V1 Implemented

- `features.py` normalizes/deduplicates OHLCV, bounds values, and limits
  features to the final observed row.
- `evidence.py` emits public-data evidence with `OBSERVED`/`DERIVED`/
  `INFERRED`/`PREDICTED` semantics and availability metadata.
- `state.py` provides the named capital-state enum, a static adjacency map,
  duration, confidence, and a continuity hold for weak non-adjacent changes.
- `intent.py` emits an inferred intent, expected direction, continuation
  condition, and invalidation condition.
- `control.py` emits upside/downside control values and a dominant direction.
- `path.py` emits one state-selected path with three scalar horizon values.
- `scoring.py` emits parallel capital, combined, strength, distribution, and
  trap values while marking the model unvalidated.
- Existing PostgreSQL tables are extended to persist complete V2 daily
  snapshots, evidence, state history, intent, path distributions, and
  prediction outcomes without duplicate Capital tables.
- Daily pipeline, ticket/tracking bridge, lifecycle report, intraday context,
  API routes, and research-only A/B/walk-forward hooks are present.

## V1 Correct Parts

- Production observable-footprint ranking is not changed by Capital output.
- Capital outputs are parallel research metadata and are not broker/execution
  instructions.
- OHLCV is bounded by the requested as-of frame and does not forward-fill
  missing history.
- Evidence names do not claim verified institutional identity.
- Existing fixed-chain gates correctly return
  `UNVALIDATED_NO_FIXED_CHAIN` when samples are insufficient.
- The daily and intraday contexts are explicitly separated.
- Existing no-lookahead coverage verifies future bars are excluded from
  bounded OHLCV input.

## Conceptual Problems

- The pipeline is still primarily `price features -> handcrafted score ->
  state`; pressure and price response are not modeled as a relationship.
- Absorption is treated as a single daily score rather than pressure damage
  versus expected damage over persistent windows.
- Intent is effectively `state -> INTENT_BY_STATE`; current evidence does not
  compete among candidate behaviors.
- Path is effectively `state -> PATH_BY_STATE`; alternatives do not compete.
- State continuity is an adjacency gate, not a dynamic transition model.
- Capital strength is conflated with `dominant_pressure`, so strength is not
  independent of direction or health.
- Intraday V1 consumes daily context but has no V2 response/control/
  transition representation.

## Mathematical Problems

- V1 absorption includes
  `volume_pressure * (1 - downward_pressure)`. Lower downward pressure can
  mechanically increase the score even though the definition requires
  meaningful selling pressure. This is the primary known defect.
- V1 control mixes pressure, price impact, and close position; it does not
  estimate response per normalized activity or separate directional
  elasticity.
- V1 `price_impact` uses fixed return/volume denominators rather than
  volatility/liquidity-normalized response.
- V1 path probabilities are three scalar scores, not a probability simplex.
  T+3/T+5 are copied adjustments from one base value.
- V1 confidence is asymmetric: it multiplies candidate strength by upward
  confidence even for downside states.
- V1 distribution/trap are penalties but do not form a transition risk model.
- V1 state age is only an integer duration and has no expected-duration or
  aging calculation.

## Data Deficiencies

- Only public OHLCV and quote data are available for the capital engine.
- Signed order flow, order book depth, borrow availability/cost, short
  interest, institutional flow, and participant identity are unavailable.
- Historical records without unique versioned research lineage cannot be used
  as fixed-chain training or validation samples.
- There are currently no independent completed V2 outcome samples, so learned
  weights, thresholds, transition probabilities, and calibrated precision
  cannot be claimed.
- MFE/MAE and some intraday outcome fields are not yet persisted.

## V2 Required Corrections

1. Add selling activity, actual/expected price damage, damage efficiency,
   recovery, support retention, persistence, and absorption failure.
2. Define pressure-response efficiency with volatility and liquidity
   normalization; expose directional control, asymmetry, regime, and collapse.
3. Add persistence-aware state momentum, dynamic transition probabilities,
   state aging, expected duration, and late-state risk.
4. Score competing intents with explicit uncertainty and intent transitions.
5. Generate competing horizon-specific path distributions with sequences and
   invalidation; enforce probability simplex invariants.
6. Separate direction, strength, quality, distribution probability/stage, and
   trap probability.
7. Extend existing database/API/pipeline/intraday/tracking/lifecycle owners
   with V2 fields without duplicate tables or production ranking changes.
8. Add calibration interfaces and V2 backtest/walk-forward/A-F artifacts that
   remain blocked until independent fixed-chain samples exist.
9. Add focused tests for all invariants and every no-lookahead input boundary.

## Acceptance Interpretation

V2 completion means the deterministic research engine and its evidence chain
exist and are verified. It does not mean the model is profitable or
production-ready. Promotion remains blocked until independent versioned
completed samples, walk-forward, out-of-sample, and A/B gates satisfy the
repository's production criteria.
