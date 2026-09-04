# SYSTEM_AUDIT — Xiaomei 2.1.1

Status: **XIAOMEI 2.1.1 HARDENED** (code + tests). Live SEC / earnings /
industry-graph ingest remain honest **DATA_GAP**.

Date: 2026-09-04
Boundary: RESEARCH_ONLY / PAPER_ONLY / NO_BROKER / NO_LIVE_ORDER /
NO_PRODUCTION_PICK / NO_PRODUCTION_WEIGHT_CHANGE
Production ranking owner: `observable_footprint_v1`
Ranking: `(ticket_score, market_score, volume_confirmation_ratio)`

---

## A. Architecture

```
Canonical DataProvider
        → Temporal Layer (published / effective / retrieved / as_of / session)
        → Evidence Layer
        → Research OS (scripts/research/)
        → Research Conclusion + coverage + DATA_GAP
        → Independent outcomes T+1/3/5/10
        → Learning / failure memory
```

Production ranking stays on `observable_footprint_v1`. Research OS never
writes weights, never emits BUY/SELL/ORDER, never creates a second pick path.

## B. Research Engine Inventory

See `research/xiaomei-2.1.1/RESEARCH_ENGINE_INVENTORY.md`.

Single research owner: `scripts/research/`.

## C. Legacy Engine Status

`scripts/research_panel.py` is a compatibility adapter.

- `canonical_owner = scripts.research`
- `compatibility_adapter = true`
- panel `method = DETERMINISTIC_PANEL_RULE`
- replay `status = UNCALIBRATED_HYPOTHESIS` with `heuristic_confidence`
- missing risk → UNKNOWN / GRAY / NEED_MORE_EVIDENCE

Callers: `us_profit_ticket_pipeline.build_candidate_record` and tests.
Not deleted because the pipeline still requires the legacy dict keys.

## D. Metric Semantics

`scripts/research/metric_semantics.py` owns MetricSpec + `value_encoding`
(`ratio_0_1`, `percent_0_100`, `decimal`, `multiple`, `absolute`, `count`,
`currency`, `text`). `normalize_metric("roe", 23)` is refused. Adapter quality
scores come from `REGISTRY`, not `roe / 0.30`.

## E. Risk Semantics

Semantic truth: LOW_RISK / MODERATE_RISK / ELEVATED_RISK / HIGH_RISK / UNKNOWN.
Display: GREEN / YELLOW / RED / GRAY.

Missing short_interest, dilution_risk, debt_covenant, earnings_quality,
insider_selling, regulatory_risk, concentration_risk →
`{value: null, status: UNKNOWN, risk_known: false, flag: GRAY}`.

Risk manager: known clean → PROCEED; known elevated → PROCEED_WITH_CAUTION;
known blocked → DO_NOT_ADVANCE; insufficient → NEED_MORE_EVIDENCE.
UNKNOWN does not PROCEED. Paper-review gate requires risk evidence.

## F. Temporal Integrity

Owner: `scripts/research/temporal.py`.

published_at ≠ retrieved_at ≠ effective_date ≠ as_of.
Historical claim requires effective_date / published_at / available_at ≤ as_of.
retrieved_at > as_of is not a violation.

Bar types: DAILY_COMPLETE / DAILY_PARTIAL / INTRADAY / SNAPSHOT /
INTRADAY_PARTIAL. Only DAILY_COMPLETE may enter daily factors, ranking,
historical daily replay, or forward outcome anchors.

## G. Market Calendar

Owner: `scripts/market_calendar.py` `USMarketCalendar`.

Used by `data_provider.py`, `xiaomei_scheduler.py`, `realtime_runner.py`,
`us_profit_ticket_pipeline.bday_date`, `historical_replay_baseline.output_date_string`,
`backfill_forward_tracking.py`.

Monday 05:00 BJT → last completed US session (Friday 2026-09-04).
Independence Day observed 2026-07-03 → 2026-07-02.
Holidays are generated (NYSE observed + early close), not a 2026/2027 list.

Pipeline artifacts emit `target_session`, `actual_previous_trading_session`,
`pipeline_execution_time`, `session_status`.

## H. Provider Integrity

`company_fundamentals(symbol, as_of, provider)`, `sec_filing(...)`,
`earnings_intelligence(...)` take explicit symbol + as_of.
Empty dict does not invent a ticker.

Return contract: symbol / as_of / published_at / effective_date /
retrieved_at / source / source_type / status OBSERVED|DATA_GAP|ERROR / facts.

Cache stores `_cache_time`, `data_as_of`, `source_timestamp`, `session_date`.
Historical as_of refuses cache without `data_as_of`. Realtime cache metadata
is not treated as a historical bar. Fallback attempts stay on
`source_attempts`.

## I. Universe Integrity

`UniverseSnapshot` fields: universe_name, symbol, effective_from, effective_to,
source, source_url, snapshot_date, version.

`universe(as_of)` hides names that were not in the universe at that date.
True historical universe snapshots without source rows stay DATA_GAP.
Production universe remains `nasdaq100_sp500_union`.

## J. Historical Leakage

Claims with effective_date or published_at after as_of are blocked.
Obsidian notes without effective_date are `DO_NOT_USE_IN_HISTORICAL_REPLAY`.
Realtime / INTRADAY_PARTIAL bars cannot enter daily replay.
`_enrich_panels_with_realtime` is display-only and does not mutate canonical
daily panels. `_build_realtime_intraday_fallback` is unused by `choose_universe`.

## K. Portfolio Semantics

ALREADY_OWNED / WATCHING / OVERWEIGHT / UNDERWEIGHT / CONCENTRATION_RISK /
SAME_THEME / SAME_VALUE_CHAIN / UNKNOWN.

already_owned is not overweight. Missing weights → concentration_status
INCOMPLETE, not 0. Portfolio never changes market alpha
(`market_alpha_adjustment=0`).

## L. Pipeline Idempotency

`daily_pipeline.sh` has a single-flight lock (`run/daily-pipeline.lock`) and
per-step state (`run_id`, `step_id`, `step_status`, started/completed,
`artifact_hash`). `create_ticket` aliases `upsert_ticket` on
output_date + symbol + as_of_date. Forward tracking already upserts.

## M. Database Integrity

Ticket and forward_tracking writes are upserts. Duplicate rerun of the same
run/symbol/as_of must update, not insert a second identity. Legacy unversioned
tickets remain unversioned; lineage is not invented.

## N. Failure Memory

Persistent classified failure library is still empty / DATA_GAP.
Failure lifecycle remains warning and evidence only. Do not fake READY.

## O. Industry Graph

Schema exists in `scripts/research/industry.py`. Live entities = 0.
Status = DATA_GAP. Chokepoint ingest = DATA_GAP.

## P. Production Boundary

Unchanged:

```
RESEARCH_ONLY
PAPER_ONLY
NO_BROKER
NO_LIVE_ORDER
NO_PRODUCTION_PICK
NO_PRODUCTION_WEIGHT_CHANGE
ranking_owner = observable_footprint_v1
```

Capital Behavior V2/V3 formulas were not modified.
Company / Industry / Buffett / Serenity / Statistical research are not
production signals.

## Q. Test Results

See test run in this task. Required 2.1.1 cases live in
`tests/test_xiaomei_211_hardening.py`:

- adapter / DETERMINISTIC_PANEL_RULE / UNCALIBRATED_HYPOTHESIS
- missing risk UNKNOWN not GREEN
- metric registry encodings
- Monday BJT → Friday session
- realtime does not pollute daily bars
- historical claim as_of
- provider symbol + as_of
- universe survivorship
- same-session quote cross-check
- already_owned ≠ overweight
- composite coverage
- independent outcomes per horizon
- pipeline lock
- forward dates use USMarketCalendar

## R. Known Data Gaps

Do not convert these to READY:

- SEC ingestion
- Earnings ingestion
- Estimate revision ingestion
- Industry graph ingestion
- Chokepoint ingestion
- True historical universe snapshots (no sourced membership history)
- Persistent failure memory

---

## Integrity gates

| Gate | Result |
| --- | --- |
| Legacy Research Engine = SINGLE OWNER | PASS |
| Risk Missing = UNKNOWN | PASS |
| Realtime != Daily | PASS |
| Intraday != Daily | PASS |
| Calendar = SINGLE OWNER | PASS |
| Temporal = SINGLE OWNER | PASS |
| Provider receives symbol/as_of | PASS |
| Universe is temporal | PASS |
| Cross-check is same-session | PASS |
| Portfolio UNKNOWN != 0 | PASS |
| Composite exposes coverage | PASS |
| Pipeline idempotent | PASS |

Completion: **XIAOMEI 2.1.1 HARDENED**
