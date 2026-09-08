# NEXT_ACTION

## Xiaomei US-stock knowledge is a production dependency (2026-09-08)

Completion: **KNOWLEDGE_LOOP_PRODUCTION_DEPENDENCY**. Broker / live order remain
**DISABLED**. No US broker adapter exists in this repo. Authorization to
enter a live-trading stage does not create an order channel.

Per-workspace Obsidian MCP daily folders:

| workspace | daily folder |
| --- | --- |
| xiaomei | `美股/xiaomei_memory/daily` |
| xiaogu | `A股/xiaogu_memory/daily` |
| bian | `虚拟币/bian/daily` |

xiaomei 05:00 full pipeline still owns steps 6–8. Scheduler 05:20
`knowledge_loop` reruns `--knowledge`. Health check fails if the US vault
is missing. MCP remains the session read/write tool; vault absence now
fails the production knowledge loop.

Do not connect a broker. Do not emit BUY/SELL/ORDER.

## Xiaomei runtime surfaces restored (2026-09-08)

Completion: **RUNTIME_SURFACES_RESTORED**. Strategy change: **NONE**. Weight change: **NONE**.
Production ranking owner remains frozen `observable_footprint_v1`. Broker /
live order remain **DISABLED**.

Fixed the 2026-09-05 daily pipeline crash
(`ModuleNotFoundError: No module named 'scripts'`) and brought the four
runtime surfaces back up against the host PostgreSQL 5432 database:

- Daily pipeline / scheduler / daily_loop now export
  `PYTHONPATH=$PROJECT:$scripts`.
- `backfill_forward_tracking.py` imports `db.pipeline_bridge` (same as
  other scripts-dir owners). Backfill `--db` now exits 0.
- Financial OS `localhost:3000` is the public frontend. Overview no
  longer hardcodes `obsidian: null`; it reads `knowledge_assets`.
- Obsidian vaults remain mounted; knowledge search and embeddings work.

Verified this session:

- `python3 scripts/backfill_forward_tracking.py --db` exit 0
- `python3 scripts/obsidian/sync_obsidian.py` synced 2 files; embeddings 8/8
- `python3 scripts/obsidian/search_knowledge.py "美股量化" --top 3` returned hits
- `GET /api/workspaces/xiaomei/overview` = 200, source=postgresql,
  date=2026-08-27, tickets=3 (TGT/TRGP/MSTR), knowledge_assets=207,
  vectors=393 missing=0
- Browser: `/dashboard/xiaomei`, `?view=memory`, `?view=system`,
  `?view=ai-pick`, `?view=records`, `/`, `/agents` all render live data
- `PYTHONPATH=. pytest -q tests/test_pipeline_idempotency.py
  tests/test_capital_no_lookahead.py tests/test_capital_v2_no_lookahead.py
  tests/test_capital_v3_pipeline.py tests/test_ticket_research_only_contract.py
  tests/test_legacy_compatibility.py` = 33 passed
- Scheduler health OK, pid after restart = current daemon

Honest remaining gap (not converted to READY): latest ticket date is
still 2026-08-27; `daily_klines` max is 2026-07-31. Do not invent a
fresh production pick. Do not retune frozen weights.

## Xiaomei NEW MAIN FORCE STRATEGY independent profitability (2026-09-06)

Completion: **NEW_MAIN_FORCE_STRATEGY_PROFITABILITY = NOT_VALIDATED**.

`PROFITABILITY_VALIDATED = NO`. Strategy change: **NONE**. Weight change: **NONE**.
No second strategy. Production ranking owner remains frozen
`observable_footprint_v1`.

Locked identity from current source, not old tickets:

```text
NEW_STRATEGY_ID = capital_behavior_v2
NEW_STRATEGY_VERSION = capital_behavior_v2
NEW_STRATEGY_STATUS = UNVALIDATED_NO_FIXED_CHAIN
NEW_RANKING_KEY = capital_behavior_score, capital_strength, demand_persistence
```

This is Capital Brain / 主力行为, not `ticket_score`. Pipeline still does
not let capital_behavior change production ranking. Old tickets,
legacy backtest, and `observable_footprint_v1` as-of results are
LEGACY_ONLY and were not used in the core statistics.

As-of replay: `daily_klines` membership + quality floors; bars with
`trade_date <= as_of`; `statistical_score=0` so footprint is not mixed
in; unadjusted close-to-close T+1/3/5/10. 394 FULL_ASOF_PANEL days;
32,060 candidate rows; Top1 T+1 n=393.

Official Top1 T+1: 53.18% / +0.12% / PF 1.17. Holdout
2026-04-08..2026-07-30 is +0.35% / PF 1.44. Cost 10 bps still +0.02%;
25/50/100 bps FAIL. Equal-weight same-day universe T+1 +0.10%. Random
Top1 T+1 +0.20%. Ranking is inverted: Bottom20% T+1 +0.16% beats
Top20% +0.07%. Pearson/Spearman of score vs T+1 are negative.

DIAGNOSTIC_FINDING only: `distribution_probability` / `trap` /
`crowding` have the largest |T+1 rank IC| and the sign is opposite the
formula's quality direction. Formula was not changed.

Command:

```bash
python scripts/new_main_force_strategy_validation.py
```

Artifacts: `research/new_main_force_strategy/`.

Do not:

- retune capital weights or invert factor signs
- promote capital_behavior_v2 into production ranking
- treat this as proof of institutional order flow
- reuse old selected tickets as the new-strategy edge

Next operational action: keep both `observable_footprint_v1` and
`capital_behavior_v2` frozen. Record the inverted ranking as a
research finding. Do not invent a second strategy this phase.

Verified this session:

- `python scripts/new_main_force_strategy_validation.py` exit 0
- `pytest -q tests/test_new_main_force_strategy_validation.py` = 7 passed

## Xiaomei 2.2.2 CURRENT STRATEGY PROFITABILITY VALIDATION (2026-09-05)

Completion: **PROFITABILITY_NOT_VALIDATED**.

Final label: **NOT_PROFITABLE**. Strategy change: **NONE**. Weight change: **NONE**.

Frozen production ranking owner remains `observable_footprint_v1`. This
phase was READ ONLY: SELECT / ANALYZE / WRITE REPORT ARTIFACT only. No
tickets, forward_tracking, factor_snapshots, scoring_config, or weights
were mutated.

Replay path (CURRENT STRATEGY, not already-selected tickets):

```
Historical Market Day
        ↓
当日真实股票宇宙 (daily_klines as-of membership; quality floors)
        ↓
当日可见数据 (trade_date <= as_of; no intraday; no live feedback)
        ↓
observable_footprint_v1  (catalyst_score = 0 as-of)
        ↓
候选排序  (ticket_score, market_score, volume_confirmation_ratio)
        ↓
模拟出票  (Top 1 / Top 3 after MIN_TICKET_SCORE)
        ↓
Forward Tracking  (kline close-to-close on calendar due date)
        ↓
真实收益验证
```

Command:

```bash
python scripts/production_profitability_validation.py
```

Artifacts: `research/production-profitability/`.

Four results must stay separate. Do not merge them.

| Series | T+1 win | T+1 avg | Note |
| --- | --- | --- | --- |
| LEGACY BACKTEST | 56.9% | +1.75% | 672 trades. LEGACY_REFERENCE only. Not CURRENT `observable_footprint_v1`. |
| LIVE/HISTORICAL REALIZED | 51.24% | -0.26% | 121 valid T+1 samples after hard exclusions. PF 0.84. Expectancy -0.26%. |
| CURRENT STRATEGY RECONSTRUCTED FULL_ASOF_PANEL Top1 | 50.00% | +0.02% | 47 FULL_ASOF_PANEL days; n=46. PF 1.014. Expectancy +0.02%. |
| CURRENT STRATEGY RECONSTRUCTED Top3 | 55.88% | +0.28% | n=136. PF 1.21. Official persist size, not the equity curve. |
| SELECTED_TICKET_ONLY Top1 | 54.17% | +0.57% | Past selected names only. Cannot prove CURRENT STRATEGY EDGE. |
| RECENT HOLDOUT (as-of Top1) | 40.00% | -0.41% | n=10. PF 0.63. Recent period is not positive expectancy. |
| EQUAL-WEIGHT ASOF PANEL T+1 | 56.52% | +0.11% | Same-day quality-filtered universe. Top1 underperforms the panel. |

Why NOT_PROFITABLE (not PROFITABLE / WEAK_EDGE / DATA_INVALID):

- FULL_ASOF_PANEL days = 47. Reconstruction exists. Duplicate samples = 0.
  Mixed price bases in returns = 0. This is an honest strategy result, not
  a missing-universe DATA_INVALID.
- As-of Top1 T+1 n=46: 50% win / +0.02% / PF 1.014. Barely positive before
  cost. Holdout is negative. Cost 10/25/50 bps all FAIL. Realized T+1 is
  also negative (expectancy -0.26%, PF 0.84).
- Ranking is inverted: Bottom 20% T+1 avg +0.17% beats Top1 +0.02%. Top1
  is worse than Top5. Score does not sort return.
- Monthly: 2026-05 −0.05%; 2026-06 +0.07%; 2026-07 −0.01%. One of three
  months profitable.
- As-of Top1 equity: cumulative −2.78%, max drawdown −28.31%.
- Nasdaq100/S&P500 membership history remains DATA_GAP. Universe =
  `daily_klines_as_of_membership` with production quality floors
  (history≥200, price≥5, median dollar volume ≥5e6). Current-index
  backfill was not used.
- Catalyst evidence is unavailable as-of, so `catalyst_score=0` on the
  frozen formula (`unavailable_as_of_equals_zero`). This is missing
  catalyst on CURRENT STRATEGY, not a new selector.
- Price basis is unadjusted kline close (`adj_close` all NULL). Declared,
  not mixed with adjusted or forward_tracking prices on the as-of path.
- Historical tickets still have 218 future-asof rows and 59.7% exclusion.
  Those remain labels on LIVE/HISTORICAL REALIZED. They do not rewrite
  as-of returns and no longer force DATA_INVALID for CURRENT STRATEGY.
- Historical ↔ current score agreement = 2.16%. Top1 same rate = 36.4%.
- UNKNOWN_VERSION tickets = 446 / 458. CURRENT_VERSION tickets = 9.

Do not:

- invent a second strategy
- retune `ticket_score` / weights / ranking
- write validation results into production weights
- connect Broker / Live Order
- treat the legacy +1.75% backtest as CURRENT STRATEGY
- treat SELECTED_TICKET_ONLY +0.57% as CURRENT STRATEGY EDGE
- treat T+3/T+5 as a substitute for failed T+1 holdout / cost gates

Next operational action: keep `observable_footprint_v1` FROZEN. Do not
change the frozen formula to make the numbers look better. A true
historical index-membership source and as-of catalyst evidence remain
honest DATA_GAP; they are not required to reverse this NOT_PROFITABLE
label on the recoverable as-of panel.

Verified this session:

- `python scripts/production_profitability_validation.py` exit 0
- `pytest -q` = 294 passed, 1 skipped
- `python scripts/xiaomei_production_release_audit.py` = strategy / weights /
  broker / live-order / production-apply all PASS; RELEASE BLOCKED only on
  `git_clean` because this validation's uncommitted artifacts exist.

## Xiaomei 2.2.1 PRODUCTION_RUNTIME_READY (2026-09-05)

Completion: **XIAOMEI 2.2.1 PRODUCTION_RUNTIME_READY**.

- Strategy `observable_footprint_v1` remains **FROZEN**. Weights remain
  **FROZEN**. Research / Replay / Learning remain **LIVE**.
- Production weight mutation owner is
  `research.weight_mutation.request_weight_change`. Frozen runtime
  never persists. Pipeline upgrade is RESEARCH_PROPOSAL only.
- Daily loop uses canonical US session + fail-fast quality gate +
  production gate PASS/BLOCK + run_manifest.json.
- Score semantics: ticket_score is candidate ranking composite;
  alpha_status = NOT_VALIDATED. Risk pass is not BUY.
- Replay sample identity is ticket + horizon + replay_date.
- Audit: `python scripts/xiaomei_production_release_audit.py`
- Weight surface: `python scripts/audit_weight_mutation_surface.py`
- Forbidden this phase: new Alpha, ranking formula change, broker,
  live order, production weight apply, expanding universe.

Next operational action: ingest a validated consensus/revision source
and a true historical universe membership source if one becomes
available. Do not invent those sources. Do not add scoring modules.
Do not change production weights or live-trade boundary.

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
