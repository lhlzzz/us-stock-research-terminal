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

### Task 9: Archive and remove untraceable records
- [ ] Preserve every record lacking `ticket_id` in one archive table with a reason and original JSON payload.
- [ ] Remove the archived rows from active tracking, paper-trade, and journal tables.
- [ ] Verify no active lifecycle row remains without a ticket source.

### Task 10: Restore scheduled US-market lifecycle execution
- [x] Derive the just-closed US session date from the Beijing-time execution time instead of treating the Beijing calendar date as the market date.
- [x] Schedule the 05:00 Beijing pipeline for Tuesday through Saturday so Friday's US close is processed on Saturday morning.
- [x] Make the existing infrastructure startup path launch one scheduler process without duplicate daemons.
- [x] Verification: scheduler session-date tests pass, one daemon is running, and frontend/API data remains available.

### Task 11: Version and complete research-decision records
- [x] Persist the source code revision, scoring configuration snapshot, data-as-of timestamp, and evidence availability for every research run.
- [x] Backfill only derivable decision metadata from authoritative ticket, candidate, and runtime-decision records; preserve unavailable evidence as unavailable.
- [x] Verification: every new run is reproducibly versioned and the API exposes the version fields.

### Task 12: Make the research thesis evidence truthful
- [x] Replace unsupported "main fund" and "social sentiment" labels with explicit observable proxies or unavailable states.
- [x] Expose news, capital-flow proxy, price-volume, and risk evidence separately so a ticket can explain why it exists and what evidence is absent.
- [x] Verification: no frontend/API field describes a proxy as verified institutional flow or social sentiment.

### Task 13: Publish one direct-database research dashboard contract
- [x] Make the overview API read paper positions, trade journals, tickets, factors, outcomes, and version metadata from PostgreSQL.
- [x] Publish ticket-level research-detail rows that join evidence, selection factors, forward outcomes, and attribution by `ticket_id`.
- [x] Verification: the contract has no filesystem engine-state dependency for xiaomei paper data.

### Task 14: Bind every xiaomei frontend module to the dashboard contract
- [x] Replace placeholder research, intelligence, performance, and lifecycle content with contract fields and explicit unavailable states.
- [x] Display selection evidence, factor contribution, horizon outcomes, loss/win attribution, and research version for each ticket.
- [x] Verification: lint/build pass and the page renders data from the direct-database endpoint.

### Task 15: Define the paper-only long/short research boundary
- [x] Keep no broker or execution path.
- [x] Do not emit a short candidate until a separately measured short-side model exists; show the missing validation explicitly.
- [x] Define ranking as historical expected return and downside-aware evidence, never a profit guarantee.

## Observable Footprint Closure

### Task 16: Make market-data transport auditable and single-owner
- [x] Route the existing `DataProvider` API requests through one Scrapy-owned transport with bounded retries, timeouts, per-domain concurrency, request deduplication, and response audit records.
- [x] Use the Yahoo Finance chart API only as an optional historical source; preserve explicit rate-limit or unavailable status and then use the existing approved fallbacks.
- [x] Remove direct market-data requests from the profit-ticket pipeline and retain source, freshness, and fallback-attempt metadata with every provider result.
- [x] Verification: a local API fixture proves Scrapy transport deduplication and HTTP-status recording; provider tests prove rate-limited Yahoo falls back explicitly.

### Task 17: Replace unsupported main-force claims with an observable footprint strategy
- [x] Replace “main fund,” “institutional interest,” and social-sentiment defaults with a deterministic public-observation model.
- [x] Rank only from price-volume footprint, liquidity, relative strength, breakout acceptance, close strength, independently observed catalyst evidence, market participation, and explicit risk penalties.
- [x] Treat unavailable inputs as unavailable and confidence-reducing; never assign a neutral score merely because data is missing.
- [x] Persist factor values, contributions, coverage, risk penalties, source availability, and ranking version for every candidate and ticket.
- [x] Verification: focused strategy tests prove missing evidence cannot create an official paper-review candidate and that factor contributions survive the database payload.

### Task 18: Export full lifecycle records as reusable research cases
- [x] Extend the existing knowledge exporter with research-run revision/configuration, source layers, factor/ranking snapshots, full tracking horizons, and deterministic outcome attribution.
- [x] Generate concise reusable case text for selection thesis, evidence availability, observable footprint, win/loss/pending outcome, and reason.
- [x] Upsert the existing `pick_case_embeddings` store only; do not create a parallel knowledge store or fabricate unavailable historical evidence.
- [x] Verification: export one controlled historical date, inspect the JSON content, and verify its case vector upsert.
