# Xiaomei Integrity And Trade Trace

**Goal:** Verify the operating US-stock research system from source, database, API, frontend, and knowledge assets; correct any broken integration; and make every research ticket traceable through one review lifecycle.

**Constraints:** Preserve the research-only and paper-trading boundary. Do not add broker, execution, live-trade, or BUY/SELL functionality. Use the current PostgreSQL database as the runtime source of truth. Use `xiaogu` only as an architectural reference, without editing it.

**Out of scope:** Changing factor weights or claiming profitability from an unvalidated causal model. Reclassifying paper trades as broker fills.

## Must-Haves

- MH1: The system's actual operating mode is evidenced from code, database, and runtime checks rather than documentation claims. A:I1
- MH2: Database, backend API, frontend data path, and knowledge retrieval have explicit passing or failing evidence, with broken paths repaired. A:I1
- MH3: Every completed or pending research ticket can be joined through one stable lifecycle from issuance to outcome and attribution. A:I1
- MH4: Profit/loss attribution is deterministic, persisted, exposed through the API, and distinguishes missing data from a real loss. A:I1
- MH5: Verification covers the affected code paths and does not add an execution or broker boundary. A:I1

### Task 1: Establish source and runtime baseline A:I1
- [ ] Inspect the current operating contracts, schemas, lifecycle code, frontend routes, and `xiaogu` reference lifecycle without modifying existing user changes.
- [ ] Query PostgreSQL for schema availability, row counts, referential gaps, lifecycle status distribution, and knowledge-asset coverage.
- [ ] Verify Python compilation and the existing research-only contract before any source edit.
- [ ] Verification: record source/runtime findings and successful baseline commands.

### Task 2: Verify public data surfaces A:I1
- [ ] Identify the active FastAPI service and Financial OS frontend route for xiaomei.
- [ ] Exercise health, overview, tickets, returns, journal, and knowledge-status endpoints against the active database.
- [ ] Identify any hardcoded, stale, or disconnected frontend path affecting the requested system surfaces.
- [ ] Verification: endpoint responses agree with database aggregates and frontend asset references.

### Task 3: Define the single research-ticket lifecycle A:I1
- [ ] Use one durable ticket identity and one lifecycle projection across `tickets`, `forward_tracking`, decision snapshots, journal, and lifecycle scoreboard.
- [ ] Adapt the relevant bounded-lifecycle and attribution concepts from `xiaogu` without copying A-share or execution behavior.
- [ ] Define deterministic attribution categories for selection evidence, outcome, data quality, and unresolved results.
- [ ] Verification: representative ticket rows produce a complete lifecycle or an explicit unresolved state.

### Task 4: Repair lineage and attribution integration A:I1
- [ ] Modify existing lifecycle, journal, database, and API modules only where evidence shows a missing join, nondeterministic reason, or unavailable lifecycle record.
- [ ] Backfill or regenerate derived records only from authoritative existing ticket and tracking data.
- [ ] Extend focused tests for lineage joins, profit/loss attribution, pending tracking, and research-only restrictions.
- [ ] Verification: database queries and API payloads expose a single coherent trace for all historical records.

### Task 5: Validate end to end and update task state A:I1
- [ ] Run focused tests, API smoke checks, database integrity queries, knowledge search, and frontend route validation.
- [ ] Run the review artifact over all available trade records and capture aggregate reasons for profits, losses, and unresolved rows.
- [ ] Update `NEXT_ACTION.md` with the verified operating mode, the lifecycle result, and any concrete remaining data-quality limitation.
- [ ] Verification: test output and runtime evidence satisfy MH1 through MH5.

## Version Closure

### Task 6: Inventory repository changes
- [ ] Separate runnable implementation, reproducible research snapshots, and generated local-only artifacts.
- [ ] Identify duplicate runtime owners without deleting unreviewed user work.
- [ ] Verification: every worktree path has an explicit version-control disposition.

### Task 7: Freeze the canonical research lifecycle
- [ ] Keep `research_trade_trace` as the only review projection and preserve unresolved source states.
- [ ] Verify pending and unresolved record counts before versioning.
- [ ] Verification: runtime API and database counts agree.

### Task 8: Create reproducible version snapshots
- [ ] Commit verified implementation and research-state changes in scoped commits.
- [ ] Leave the worktree clean without discarding source or research evidence.
- [ ] Verification: tests pass, Git status is clean, and commit identifiers are recorded.
