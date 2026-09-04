# NEXT_ACTION

## Xiaomei 2.2 PRODUCTION_RESEARCH_READY (2026-09-04)

Completion: **XIAOMEI 2.2 PRODUCTION_RESEARCH_READY**.

- Strategy `observable_footprint_v1` is **FROZEN**. Research / Replay /
  Learning are **LIVE**. Operating classification remains RESEARCH_ONLY.
- Production ranking owner remains `observable_footprint_v1` with sort
  `(ticket_score, market_score, volume_confirmation_ratio)`.
- Forbidden: Research → Alpha; Research → BUY/SELL; Learning → auto
  weight change; Broker connect; Live Order enable.
- Research OS owner remains `scripts/research/`. Legacy `research_panel.py`
  is a compatibility adapter.
- Live SEC EDGAR ingest (submissions + XBRL companyfacts) for NVDA/AAPL/MSFT
  as_of 2026-09-03 is OBSERVED. Raw documents are immutable. Amendments and
  fact conflicts keep all evidence and record `supersedes`.
- Earnings reported facts come from SEC. Consensus / estimate-revision live
  history / chokepoint / true historical universe membership remain honest
  **DATA_GAP**. DATA_GAP is not converted to READY.
- Persistent FailureMemory + LearningPattern live in SQLite
  (`data/research-evidence/xiaomei22.sqlite`). They do not mutate ranking.
- CLI: `python scripts/research_cli.py research company NVDA --as-of 2026-09-03`
- Audit: `python scripts/xiaomei_22_audit.py`
- Tests: `python -m compileall -q .` pass; `PYTHONPATH=scripts pytest -q tests`
  = **238 passed**. Audit: `python scripts/xiaomei_22_audit.py` =
  **XIAOMEI_2.2_AUDIT=PASS** including PRODUCTION_RESEARCH_READY /
  STRATEGY_FROZEN / RESEARCH_LIVE / REPLAY_LIVE / LEARNING_LIVE.
- Reports: `research/xiaomei-2.2/SYSTEM_AUDIT.md`, `DATA_COVERAGE.md`,
  `REPLAY_AUDIT.md`, `LEARNING_AUDIT.md`, `PRODUCTION_BOUNDARY.md`.

Next operational action: ingest a validated consensus/revision source and a
true historical universe membership source if one becomes available. Do not
invent those sources. Do not add scoring modules. Do not change production
weights or live-trade boundary.

## Xiaomei 2.1.1 full-system integration hardening (2026-09-04)

Completion: **XIAOMEI 2.1.1 HARDENED**.

- Single Research OS owner: `scripts/research/`. Legacy `research_panel.py` is a
  compatibility adapter (`canonical_owner=scripts.research`). No second quality /
  risk / panel / replay scoring engine.
- Missing risk is UNKNOWN/GRAY, never GREEN. Risk manager maps insufficient data
  to NEED_MORE_EVIDENCE, not PROCEED. Paper-review gate now requires market +
  research + risk + completeness + temporal validity. RSS cannot auto-pass.
- Realtime quotes do not mutate canonical daily bars. Intraday fallback is
  INTRADAY_PARTIAL / is_complete=false and is unused by `choose_universe`.
- `USMarketCalendar` is the only US session/holiday owner. Monday 05:00 BJT maps
  to Friday. Pipeline artifacts emit `target_session` /
  `actual_previous_trading_session` / `pipeline_execution_time`.
- Temporal model in `scripts/research/temporal.py`. Providers take explicit
  `symbol` + `as_of`. MetricSpec has `value_encoding`. Composite exposes
  coverage/readiness. Portfolio already_owned ≠ overweight. Universe is
  temporal. Outcomes are per-horizon T+1/3/5/10. Tickets upsert. Daily pipeline
  has a single-flight lock + `skip_if_completed`.
- Inventory: `research/xiaomei-2.1.1/RESEARCH_ENGINE_INVENTORY.md`
- Audit: `research/xiaomei-2.1.1/SYSTEM_AUDIT.md`
- Tests: `python -m compileall -q .` pass; `PYTHONPATH=. pytest -q tests` =
  **218 passed**. Named 2.1.1 files:
  `test_xiaomei_211_hardening.py`, `test_legacy_compatibility.py`,
  `test_market_calendar.py`, `test_temporal_integrity.py`,
  `test_provider_contracts.py`, `test_universe_survivorship.py`,
  `test_pipeline_idempotency.py`, `test_research_gate.py`,
  `test_research_integration.py`.
- Dry-run NVDA `--universe-source explicit --universe NVDA --skip-last30days
  --top-k 1` = RESEARCH_ONLY SUCCESS, `as_of_date`/`target_session`
  `2026-09-03`, classification MARKET_WATCHLIST_NEEDS_EVIDENCE, paper_review=0.
  Production ranking owner unchanged: `observable_footprint_v1`.
- Remaining honest DATA_GAP (do not fake READY): SEC, earnings, estimate
  revision, industry graph, chokepoint, true historical universe snapshots,
  persistent failure memory.

Next operational action: Xiaomei 2.2 real SEC + earnings + industry-graph
ingestion. Do not add more scoring modules. Do not change production weights
or live-trade boundary.
