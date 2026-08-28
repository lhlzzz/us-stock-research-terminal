# Capital Behavior V3 Research Foundation

**Goal:** Add a deterministic, versioned, replayable empirical Capital Behavior dataset and research-only learning/evaluation loop on top of the existing V2 owner chain, while retaining the existing regular-US-session paper workflow and its reusable lineage.
**Constraints:** Keep `observable_footprint_v1` ranking unchanged; preserve `RESEARCH_ONLY`, `UNVALIDATED_NO_FIXED_CHAIN`, and no broker/live-trade boundaries; use as-of-only inputs; modify existing V2 owners before creating new owners.
**Out of scope:** Production weight changes, automatic model promotion, broker/execution, random time-series splits, future-data features, and claiming institution identity or intent as fact.

## Must-Haves

- MH1: Every versioned Capital snapshot can be represented as an as-of-only dataset sample with explicit eligibility and lineage.
- MH2: Future state/path/transition labels are deterministic, versioned, and unavailable when forward data is incomplete.
- MH3: Training, validation, and test partitions are chronological, purged for label horizons, and deterministic.
- MH4: Research-only empirical baselines, analogue retrieval, calibration, drift, archetype, reversal, and decay outputs never mutate production ranking.
- MH5: Daily backfill and API surfaces expose V3 dataset status and diagnostics without inventing accuracy or economic results.
- MH6: Focused tests prove no-lookahead, determinism, eligibility gates, and V2 compatibility.
- MH7: The existing paper strategy continues reacting during regular US market hours with stale-quote and session gates intact.

### Task 1: Establish the V3 gap audit and schema contract
- [x] Record the implemented V2 owners, missing V3 capabilities, data limitations, and production gates in a dated research artifact.
- [x] Add one idempotent migration for dataset samples, error attribution, and version metadata, reusing existing Capital tables where possible.
- [x] Extend SQLAlchemy models only for the new persisted V3 records.
- [ ] Verification: migration applies twice and schema constraints/indexes are inspectable.

### Task 2: Implement deterministic dataset assembly and eligibility
- [x] Add `scripts/capital/dataset.py` to assemble one sample per `symbol/as_of_date/research_run_id` from existing V2 snapshots, states, intents, paths, and linked ticket inputs.
- [x] Preserve observed/derived/inferred/predicted semantics and store feature/model/data/label versions.
- [x] Implement explicit `VALID`, `INSUFFICIENT_FORWARD_DATA`, `MISSING_LINEAGE`, `SOURCE_INVALID`, `VERSION_INVALID`, and `DATA_GAP` reasons.
- [ ] Verification: same inputs produce byte-stable sample payloads and missing lineage never becomes eligible.

### Task 3: Implement deterministic future labels and temporal splits
- [x] Add `scripts/capital/labels.py` for T+1/T+3/T+5/T+10 returns, future states, path labels, and state transitions using only bars through each due date.
- [x] Add purged chronological train/validation/test split logic with configurable embargo and no shuffle.
- [ ] Verification: synthetic bars prove future rows are excluded from current features and overlapping horizons are purged.

### Task 4: Implement research-only empirical analysis and learning baseline
- [x] Add `scripts/capital/learning.py` with interpretable empirical state/transition/intent/path conditional distributions and minimum-sample `NOT_READY` gates.
- [x] Add `scripts/capital/evaluation.py` with accuracy, macro-F1, confusion matrix, Brier, log loss, calibration error, economic metrics, and lead-time placeholders that remain unavailable without valid outcomes.
- [x] Keep rule and empirical probabilities side-by-side; do not replace V2 rule probabilities.
- [ ] Verification: deterministic baseline outputs and zero-sample gates are tested.

### Task 5: Implement archetypes and historical analogue retrieval
- [x] Add `archetypes.py` and `case_retrieval.py` using only current/as-of observable features and regime/size/liquidity metadata.
- [x] Provide successful and failed case classification without treating post-hoc labels as institutional facts.
- [ ] Verification: similarity excludes outcome fields and archetypes are deterministic.

### Task 6: Implement feature stability, decay, and reversal diagnostics
- [x] Add `feature_stability.py` for IC, rank IC, mutual information, sign stability, and bucket monotonicity without requiring positive IC.
- [x] Add `reversal.py` for bounded reversal probability and capital advantage decay from pressure/control/persistence/distribution changes.
- [ ] Verification: diagnostics are deterministic, bounded, and return explicit unavailable status for insufficient samples.

### Task 7: Integrate persistence and forward outcome attribution
- [x] Extend the existing pipeline bridge to persist dataset samples in the same research lifecycle transaction.
- [x] Extend the existing forward backfill owner to persist deterministic labels and prediction errors only after due data exists.
- [ ] Verification: mocked persistence transaction, idempotent upsert, and no production ranking diff.

### Task 8: Integrate artifacts, API, and daily research visibility
- [x] Add V3 daily JSON/Markdown artifacts and weekly review placeholders with explicit status fields.
- [x] Add the requested dataset/probability/analogue/error/lifecycle/model-performance/model-drift API routes while preserving existing routes.
- [x] Preserve the intraday paper boundary; the strategy continues reacting during regular US market hours only, with deterministic session-time and stale-quote gates.
- [ ] Verification: API contract tests, artifact smoke, and intraday session/stale-quote tests.

### Task 9: Validate the V3 research loop and production boundary
- [x] Add focused V3 tests for dataset, labels, temporal split, retrieval, archetypes, learning, calibration, drift, reversal, and pipeline integration.
- [x] Run the full Python test suite, compileall, migration idempotence, and a research-only smoke report against current database counts.
- [x] Update `NEXT_ACTION.md` with actual sample counts and explicit `NOT_READY` reasons.
- [ ] Verification: all available checks pass and final status remains `RESEARCH_ONLY`/`NOT_READY`.
