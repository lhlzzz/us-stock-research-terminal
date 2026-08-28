# Xiaomei Capital Behavior V2

**Goal:** Upgrade the existing public-data Capital Brain from static
rule/state mappings to a deterministic behavior, response, persistence,
transition, intent, competing-path, quality, and research-decision engine,
while retaining the regular-US-market-hours paper workflow and reusable
research/data lineage.

**Constraints:** Use only available OHLCV, realtime quote, liquidity proxy,
relative-strength, market-regime, and public-catalyst data. Preserve
`KEEP_OBSERVABLE_FOOTPRINT_RANKING_UNCHANGED`,
`NO_PRODUCTION_WEIGHT_CHANGE`, `RESEARCH_ONLY`, paper-only operation, and
`UNVALIDATED_NO_FIXED_CHAIN`. Missing data remains explicitly unavailable.
State and scoring remain deterministic and do not depend on an LLM.

**Out of scope:** Broker connectivity, live orders, live trading, hidden
participant claims, fabricated order-book/borrow/institutional-flow data, and
promotion of Capital Behavior V2 into production ranking before independent
fixed-chain, walk-forward, out-of-sample, and A/B gates pass.

## Must-Haves

- MH1: The Capital Brain exposes bounded, evidence-backed V2 absorption,
  price-response control, state transition, intent, path, strength, quality,
  distribution, and trap outputs.
- MH2: V2 predictions are deterministic, horizon-specific, competing
  probability distributions with explicit invalidation and calibration fields.
- MH3: Existing daily, intraday, ticket, tracking, lifecycle, database, and
  API surfaces carry the complete V2 capital object without changing
  observable-footprint production ranking.
- MH4: Backtest, walk-forward, A/B, no-lookahead, missing-data, and invariant
  checks preserve research-only gates and never mutate production weights.
- MH5: Documentation and `NEXT_ACTION.md` state the V2 validation status,
  data limitations, and exact evidence required before any production use.
- MH6: Regular-US-market-hours paper decisions remain freshness-gated,
  provisional intraday observations and retain daily research lineage.

### Task 1: Audit V1 and freeze the V2 contract
- [ ] Produce `research/capital_behavior_v2_gap_audit.md` from source and
  tests, covering implemented, correct, conceptual, mathematical, data,
  and required V2 corrections.
- [ ] Define V2 field names, semantic labels, bounded-value rules,
  unavailable-value rules, and production protection in the existing capital
  package.
- [ ] Verification: audit exists and current V1 tests establish a baseline.

### Task 2: Replace feature/evidence absorption math
- [ ] Extend `features.py` with normalized selling activity, actual price
  damage, expected damage from trailing pressure/activity/volatility/liquidity,
  damage efficiency, recovery, support retention, and 1d/3d/5d/10d persistence.
- [ ] Replace the V1 absorption multiplication with bounded efficiency and
  failure calculations; no missing input becomes neutral evidence.
- [ ] Verification: absorption fixtures cover heavy selling with limited
  damage, heavy selling with real damage, persistence, and failure.

### Task 3: Replace control and dynamic state transitions
- [ ] Compute upside/downside price-response efficiency, asymmetry, regime,
  collapse, pressure change, persistence, transition momentum, age, expected
  duration, percentile, and late-state risk.
- [ ] Replace static transition acceptance with a dynamic transition matrix
  and probabilities while retaining continuity and no-lookahead behavior.
- [ ] Verification: control/state tests cover bounded outputs, collapse,
  aging, fast markup-to-distribution, and deterministic transitions.

### Task 4: Replace intent and path inference
- [ ] Score the full candidate intent set and return probabilities,
  alternatives, `UNCERTAIN`, previous/current intent, and transition.
- [ ] Generate competing `UP_CONTINUATION`, `PULLBACK_CONTINUE`,
  `ACCELERATION`, `SIDEWAYS`, `DISTRIBUTION`, `BREAKDOWN`, and `TRAP`
  distributions independently for T+1/T+3/T+5.
- [ ] Include path sequence and invalidation evidence; add calibration
  interfaces for predicted probabilities and later outcomes.
- [ ] Verification: intent/path/calibration tests enforce sums, bounds,
  uncertainty, sequence, invalidation, and no fake precision.

### Task 5: Compute independent strength and research decisions
- [ ] Compute capital strength independently from direction using pressure,
  persistence, absorption, control, state/transition confidence, and
  distribution/crowding/trap/collapse penalties.
- [ ] Add capital quality, distribution probability/stage/acceleration/
  transition risk, trap probability, `STRONG_BUT_DISTRIBUTING`, and research
  ticket types/actions.
- [ ] Verification: scoring and ticket tests separate strength from direction
  and reject low-quality high-momentum cases.

### Task 6: Persist the complete V2 capital object
- [ ] Extend existing capital tables/columns rather than creating duplicate
  tables; persist V2 snapshots, evidence, transitions, intent probabilities,
  path distributions, and outcomes.
- [ ] Extend existing bridge and forward-tracking rows with V2 lineage and
  outcome-proxy fields without changing production ranking.
- [ ] Verification: migration, persistence, and tracking smoke tests return
  complete V2 rows and preserve research-only status.

### Task 7: Publish API, intraday, and lifecycle V2 context
- [ ] Extend existing API endpoints and add the requested complete capital
  object routes where absent.
- [ ] Feed daily V2 context into intraday evidence/state/intent and preserve
  regular-session, quote-freshness, provisional-observation, and daily-vs-
  intraday failure handling.
- [ ] Extend lifecycle reports and scoreboard output with V2 transitions,
  quality, warning, and path fields.
- [ ] Verification: API contract, daily pipeline, intraday paper, and
  lifecycle smokes pass.

### Task 8: Upgrade backtest, walk-forward, A/B, and calibration
- [ ] Upgrade `capital_backtest.py` for state, transition, intent, path,
  direction, warning precision, economic outcomes, state cohorts, two key
  transitions, and momentum bands top 5/10/20%.
- [ ] Extend walk-forward and optimizer gates for V2 without changing
  active weights; add calibration metrics that return
  `UNAVAILABLE_NO_FIXED_CHAIN` at zero samples.
- [ ] Verification: TRAIN -> VALIDATE -> WALK_FORWARD -> OUT_OF_SAMPLE
  artifacts preserve production protection and explicit insufficient-sample
  results.

### Task 9: Add regression tests and complete verification
- [ ] Add focused V2 tests for absorption, control, intent, state transition,
  path, calibration, no-lookahead, intraday, and ticket contracts.
- [ ] Run `pytest tests -q`, `python -m compileall -q scripts`,
  `python scripts/daily_scheduler.py --dry-run`, and all requested smoke
  checks.
- [ ] Update `NEXT_ACTION.md` with verified scope, remaining gates, and
  current V2 status.
- [ ] Verification: all available checks pass or limitations are recorded;
  final diff contains no broker/live-trade path or production ranking change.
