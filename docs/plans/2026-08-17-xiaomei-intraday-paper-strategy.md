# Xiaomei Intraday Paper Strategy

**Goal:** Replace the end-of-day research-ticket workflow with a US
market-hours real-time paper strategy that simulates orders, fills, fees,
slippage, positions, exits, outcomes, and reviewable knowledge assets from
reusable research and database records.

**Constraints:** Retain `DataProvider` as the sole market-data transport
owner; preserve source freshness and research lineage; use database records
as reusable research assets; do not add broker connectivity, live orders, or
claims of profitability.

**Out of scope:** Broker credentials, broker APIs, live order submission,
live short-selling, and any declaration that the strategy is profitable before
an independent completed-sample evaluation.

## Must-Haves

- MH1: The strategy reacts during regular US market hours rather than only
  after the daily close, producing source-freshness-checked intraday paper
  decisions rather than end-of-day tickets. A:I2,A:I3
- MH2: Each intraday decision retains data-source, timestamp, daily-research
  context, and lifecycle lineage. A:I2
- MH3: Paper entries and exits are risk-limited and are persisted for later
  independent outcome evaluation. A:I3
- MH4: No broker, live-order, or automatic external execution capability is
  introduced. A:I3
- MH5: The scheduler runs the paper strategy only in eligible US sessions,
  while the close workflow remains responsible for finalized daily research.
  A:I2
- MH6: The API, frontend, and knowledge assets show the complete paper
  lifecycle, including entry and outcome attribution plus the validation
  status of independent long and short paper models. A:I4,A:I5

### Task 1: Establish the intraday contract and data ownership A:I2,A:I3
- [ ] Update the existing real-time runner contract to define paper-only
  regular-session decisions, source-freshness requirements, and explicit
  non-goals.
- [ ] Query the active PostgreSQL schemas for `paper_trades`,
  `trade_journal`, `daily_candidates`, and `research_runs` before selecting
  the existing persistence surface to modify.
- [ ] Verification: deterministic session-time and stale-quote tests prove
  that a stale quote, closed session, or missing daily-research context
  cannot create a paper decision.

### Task 2: Replace ticket-driven realtime behavior with intraday signals A:I2
- [ ] Modify `scripts/realtime_runner.py` to derive a single long-only
  intraday score from realtime quote fields and the latest completed daily
  research context, without treating the in-progress day as confirmed OHLCV.
- [ ] Persist quote source, fetch timestamp, quote age, daily research run,
  score components, and a reason for every accepted or rejected decision.
- [ ] Remove the runner's `live` mode and ticket-driven automatic-order
  entrypoint so the strategy has one paper-only owner.
- [ ] Verification: fixture tests cover score formation, freshness rejection,
  duplicate-decision suppression, and absence of a live-mode CLI option.

### Task 3: Persist and manage paper lifecycle A:I3
- [ ] Modify the existing database persistence path to record intraday paper
  entries, price updates, exits, realized outcomes, and associated decision
  lineage in existing paper-trading tables where their schema supports it.
- [ ] Apply a narrowly scoped migration only if the current tables cannot
  retain decision identity, source metadata, and research-run linkage.
- [ ] Reuse the existing risk manager for per-position, exposure, and
  drawdown limits; support only long paper positions.
- [ ] Verification: transactional tests show entry, mark, exit, and rejected
  decisions retain a single lineage and do not submit external orders.

### Task 4: Integrate realistic paper execution A:I4
- [ ] Rework the existing `trading_engine` as the sole paper-execution owner
  for the intraday strategy: queued orders, limit/stop conditions, bounded
  partial fills, commissions, regulatory fees, and adverse slippage.
- [ ] Remove the engine's misleading `live` mode and unvalidated short-open
  path; retain a direction field with
  `UNAVAILABLE_NO_VALIDATED_SHORT_MODEL` for the UI and records.
- [ ] Persist orders, fills, position marks, equity snapshots, and entry/exit
  reasons with the intraday decision lineage.
- [ ] Verification: deterministic fixtures prove partial fills, fee/slippage
  math, stop/target exits, drawdown halting, and no broker call.

### Task 5: Add an independent paper short model A:I5
- [ ] Derive short eligibility from its own downside continuation, range,
  liquidity, borrow availability, borrow-cost, and squeeze-risk inputs; do
  not invert the long score.
- [ ] Extend paper orders, fills, positions, risk limits, and exit math to
  represent short paper positions and daily borrow costs.
- [ ] Persist every short rejection and acceptance reason with
  `UNVALIDATED_PAPER_SHORT` status until completed-sample gates are met.
- [ ] Verification: fixtures prove short P&L, stop/target behavior, borrow
  cost accrual, missing-borrow rejection, and no broker call.

### Task 6: Publish lifecycle, review, and knowledge assets A:I4,A:I5
- [ ] Extend the Xiaomei API and its existing frontend contract to read
  intraday positions, order/fill history, realized and unrealized outcomes,
  entry reasons, exit reasons, and strategy capability states from PostgreSQL.
- [ ] Extend the existing knowledge-asset exporter to write completed
  intraday decisions and reviews, including source state, strategy inputs,
  fill costs, outcome attribution, and reusable case text.
- [ ] Verification: API/database smoke returns lifecycle rows; the knowledge
  export includes both an entry rationale and an outcome rationale.

### Task 7: Validate the intraday paper strategy core A:I2,A:I3,A:I5
- [ ] Run focused strategy and persistence tests, Python compilation, and a
  database-backed paper-strategy smoke that cannot place live orders.
- [ ] Inspect the core-strategy diff for broker clients, credentials, and
  external order calls.
- [ ] Verification: retain the exact test and smoke outputs and confirm that
  the core strategy created no external order.

### Task 8: Implement and validate session scheduling A:I2
- [ ] Add a session-aware scheduler job in code; it is eligible at a bounded
  cadence only while the US regular session is open.
- [ ] Keep the post-close daily pipeline as finalized research input and
  remove its role as the intraday strategy entry generator.
- [ ] Run deterministic timezone tests covering Monday-Friday market hours,
  weekends, holidays, pre-market, post-market, and scheduler cadence.
- [ ] Verification: the full test suite, shell syntax validation, and a
  scheduler-backed paper-strategy smoke pass before the scheduler is enabled.

### Task 9: Inspect the complete paper-strategy surface A:I2,A:I3,A:I5
- [ ] Run focused strategy and scheduler tests, then the complete test suite,
  shell syntax validation, and a scheduler-backed paper-strategy smoke.
- [ ] Inspect the final diff for residual `live` runner modes and any broker
  client, credential, or external order call.
- [ ] Verification: retain the exact test and smoke outputs and confirm that
  the scheduled paper strategy created no external order.

### Task 10: Record the profitability gate and completion state A:I2,A:I3,A:I5
- [ ] Update `NEXT_ACTION.md` with the unvalidated-profitability gate and
  exact evidence required before any broker-integration request can be
  reconsidered.
- [ ] Verification: `NEXT_ACTION.md` cites the completed paper-strategy
  validation, states that broker integration remains out of scope, and notes
  that runtime scheduler enablement requires a separate post-verification
  restart.
