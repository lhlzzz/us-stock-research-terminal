# Xiaomei Capital Behavior Gap Audit

**Baseline:** `main` at `9217e55`
**Audit date:** `2026-08-28`
**Scope:** observable public market data, derived evidence, inferred state, paper-only research

## Executive Summary

The repository already owns the statistical research pipeline, public price/volume
data transport, research lineage, forward tracking, lifecycle reporting, and a
regular-session paper runner. It does not yet have a single capital-behavior
contract that separates observed data from derived evidence, inferred state,
inferred intent, and predicted price path.

The safe implementation boundary is a parallel Capital Brain:

```text
existing observable_footprint_v1 / statistical score
            +
capital behavior evidence and state
            ->
parallel unified decision fields
```

The existing research-only and paper-only boundaries remain authoritative. No
field in this audit establishes knowledge of institutional ownership, broker
flow, or hidden participants.

## Existing Evidence

### Observable or source-backed evidence already present

- `DataProvider` is the current market-data transport owner for historical
  OHLCV and realtime quote attempts, with provider status, source attempts,
  freshness, and fallback metadata.
- Daily panels contain close/adjusted close, volume, dollar-volume quality,
  5-day and 20-day momentum, acceleration, relative strength, closing
  strength, volume trend, and volume confirmation.
- Realtime quotes contain latest price, previous close, session high/low,
  cumulative volume, timestamp, and source metadata when available.
- Catalyst and business research retain public-source evidence, relevance,
  source diversity, cluster counts, and explicit unavailable states.
- Research runs, candidates, tickets, factor snapshots, forward-tracking
  rows, paper decisions, paper positions, fills, journals, and trade traces
  provide lineage owners for current outputs.
- Market-regime classification, risk gates, optimizer gates, and short borrow
  gates already prevent unsupported production changes.

### Existing derived evidence

- Relative volume / volume trend and volume-confirmation ratios.
- Quantile or percentile-ranked relative strength, liquidity, and structured
  footprint components.
- Momentum quality, breakout acceptance, reversal quality, market breadth,
  risk penalties, and dynamic horizons.
- Candidate classification and ticket/risk outputs derived from the current
  statistical and public-evidence pipeline.

### Existing inferred or decision fields

- `observable_footprint_v1` is a derived public price-volume footprint, not
  observed institutional activity.
- `lifecycle_stage` is an existing research lifecycle label, but it is not a
  continuous capital-state machine.
- `classification`, `risk_allowed`, and paper decision statuses are policy
  decisions, not market facts.

## Reusable Fields

The following fields can be reused as inputs without changing their meaning:

| Existing field | Reuse | Semantic constraint |
|---|---|---|
| `close`, `adj_close`, `volume` | pressure and response inputs | observed only when source-backed |
| `volume_trend_20d` | volume vs baseline | derived, not buying evidence |
| `volume_confirmation_ratio` | directional confirmation candidate | requires price-direction context |
| `prior_5d_momentum`, `prior_20d_momentum` | persistence and relative response | historical return features |
| `five_day_acceleration` | persistence/late-acceleration evidence | not intent by itself |
| `relative_strength_vs_equal_weight` | demand persistence and regime alignment | statistical relative performance |
| `closing_strength_5d` | close-location and acceptance evidence | not control or ownership |
| `median_dollar_volume_20d` | liquidity and crowding proxy | public liquidity proxy |
| realtime `latest_price`, `prev_close`, `high`, `low`, `volume`, `as_of` | intraday evidence | freshness and source status required |
| market regime fields | regime alignment | current statistical context |
| catalyst evidence metadata | narrative acceptance context | public evidence only |

## Fields That Must Not Be Reused Without Renaming

These names or interpretations would overclaim knowledge:

- `fund_flow`, `main_force`, `institutional_buying`, `bank_buying`, or
  `hedge_fund_buying` as facts. Existing fund-flow data remains a public
  provider proxy and must be labeled accordingly.
- `absorption`, `accumulation`, `distribution`, `capital_intent`, and
  `capital_state` as observed facts. These are derived or inferred outputs
  and require confidence, availability, source, and lookback.
- `price_control` as “control by a dominant participant”. The contract must
  use `Price Control` / `Price Response Efficiency` and explicitly mean
  pressure-to-price response efficiency.
- A volume spike as absorption. Absorption requires activity plus limited
  adverse price progress plus support/recovery evidence.
- A positive return or high momentum as demand persistence. Persistence
  requires repeated observations and follow-through over a declared lookback.

## Missing or Unavailable Data

- There is no validated order-book, queue, signed trade, broker flow, short
  locate, or participant-identity feed. The model cannot legally or
  technically claim to know who traded.
- Public fund-flow fields have uncertain provider semantics and cannot be
  upgraded to institutional-flow facts.
- Intraday history is limited compared with daily history. A current quote is
  not a complete intraday OHLCV series and cannot be treated as one.
- Social sentiment is explicitly unavailable when no validated corpus/source
  exists. It may not be filled with a neutral score.
- State accuracy, intent accuracy, path accuracy, distribution avoidance, and
  trap avoidance have no independent versioned capital-label sample yet.
- State normalization, thresholds, and weights must not be fitted using future
  prices, future volume, future labels, or same-sample outcomes.

## Current Intraday Gaps

`intraday_paper_v1` currently combines:

```text
latest completed daily research context
session momentum
session range position
```

It already enforces regular US-session and quote-freshness gates, persists
paper decisions and positions, records realistic fees/slippage, and keeps the
short model independently gated by borrow availability.

From a capital-behavior perspective it is missing:

- daily capital state/strength carried into the session;
- fresh intraday evidence with explicit observed/derived semantics;
- a distinct intraday capital state and inferred intent;
- distribution and trap rejection independent of raw momentum;
- daily/intraday state lineage in the decision record.

## Current Ticket Gaps

Tickets retain statistical scores, observable footprint metadata, catalyst
evidence, risk outputs, classification, and forward dates. They do not yet
carry capital score/state/intent/path fields, an explicit distribution risk
field, a trap risk field, or a machine-readable capital thesis and invalidation
condition.

The first integration should add nullable parallel fields or a JSON evidence
payload while preserving existing ticket classification and research-only
wording.

## Current Lifecycle Gaps

The current lifecycle scoreboard groups research/ticket outcomes and supports
completed-only gates. It does not model a continuous capital state history,
state duration, transition evidence, state-at-entry, or state correctness at
future horizons.

The capital lifecycle therefore needs a separate versioned projection linked
to the same symbol, date, research run, model version, and data version. It
must not overwrite the existing lifecycle labels.

## Current Forward-Tracking Gaps

Forward tracking currently stores future prices/returns, status, outcome
classification, reasons, and ticket lineage. It does not store capital state,
intent, strength, predicted path, or state/intent/path outcomes. These fields
can be added only for new versioned predictions; historical rows without
unique lineage must remain unavailable rather than reconstructed.

## Architecture Decision

Implement one Capital Behavior Engine under `scripts/capital/` with:

- a structured evidence contract;
- daily and intraday feature derivation from public OHLCV/quote inputs;
- a confidence-aware, continuity-constrained state transition function;
- explicit `INFERRED` intent and `PREDICTED` path outputs;
- a parallel capital score and unified score;
- reusable serialization helpers for tickets, paper decisions, tracking, and
  reports.

The existing statistical engine remains the owner of the current production
score and classification. Capital outputs remain parallel until independent
fixed-chain walk-forward evidence demonstrates improvement.

## Validation Boundary

Required before production-gate consideration:

1. deterministic unit tests for missing, NaN, zero-volume, flat-price,
   duplicate, stale, gap, and outlier inputs;
2. no-lookahead tests proving feature windows end at `as_of_date`;
3. versioned state/intent/path outcome samples;
4. train/validation/test or walk-forward replay;
5. A/B results for baseline, capital-only, blended, distribution gate, trap
   gate, and intraday capital variants;
6. explicit `UNVALIDATED` / `NOT_READY` output when sample gates fail.

Until those conditions hold, Capital Brain is research metadata and a
paper-review assist, not a production hard gate.
