# SYSTEM_AUDIT — Xiaomei 2.2

Status: **XIAOMEI 2.2 RESEARCH DATA + LEARNING HARDENED**

Date: 2026-09-04
Baseline: Xiaomei 2.1.1 Hardened (`eff260b`)
Boundary: RESEARCH_ONLY / PAPER_ONLY / NO_BROKER / NO_LIVE_ORDER /
NO_PRODUCTION_PICK / NO_PRODUCTION_WEIGHT_CHANGE
Production ranking owner: `observable_footprint_v1`
Ranking: `(ticket_score, market_score, volume_confirmation_ratio)`

This version advances Research OS data, evidence, temporal isolation,
industry context, earnings facts, SEC ingestion, estimate-revision
history, historical universe gates, failure memory, and research
learning. It does **not** add a second scorer and does **not** change
production ranking.

---

## A. Architecture (unchanged owners)

```
Canonical DataProvider (scripts/data_provider.py)
        → Temporal Layer (scripts/research/temporal.py)
        → Evidence Layer (scripts/research/evidence.py)
        → Research OS (scripts/research/)
        → Research Conclusion + coverage + readiness
        → Independent outcomes T+1/3/5/10
        → Failure memory + learning patterns
```

Calendar owner remains `scripts/market_calendar.py`.
Production pipeline remains `scripts/us_profit_ticket_pipeline.py`.
Legacy `scripts/research_panel.py` remains a compatibility adapter.

## B. Evidence contract

`ResearchEvidence` requires `source` for `OBSERVED`. Missing source
promotes to `ERROR`, never READY. Status vocabulary:

OBSERVED / DERIVED / DATA_GAP / UNKNOWN / ERROR

Quality fields (`source_reliability`, `directness`, `recency`,
`temporal_validity`, `independence`, `corroboration`) are evidence
quality only. They are not production scores. RSS is LEVEL_6.
One source cannot become CORROBORATED.

## C. SEC

Live EDGAR ingest:

- `company_tickers.json` CIK lookup
- `submissions/CIK{cik}.json` filings
- `companyfacts` XBRL

Raw documents are immutable (`content_hash`). Parser emits facts only.
As-of uses filed/published/available ≤ T. Amendments keep original +
revision; selected version is latest public as_of with `supersedes`.
Concept/period conflicts retain all evidence.

Real as_of 2026-09-03:

| symbol | CIK | filings | SEC status |
| --- | --- | --- | --- |
| NVDA | 0001045810 | 670 | OBSERVED |
| AAPL | 0000320193 | 765 | OBSERVED |
| MSFT | 0000789019 | 844 | OBSERVED |

Guidance / segment / customer concentration remain DATA_GAP (not parsed
from headlines).

## D. Earnings / revisions

SEC-derived reported EPS and revenue are OBSERVED when XBRL facts exist.
Consensus EPS/revenue remain DATA_GAP (no validated consensus source).
EPS surprise and revenue surprise are stored separately.
Guidance without previous/current/source is DATA_GAP, never inferred
from a headline.

Estimate revision history contract PASSes in tests. Live consensus
history is honest **DATA_GAP**.

## E. Industry / chokepoint / universe

Industry graph from SEC SIC is OBSERVED with `graph_snapshot_id`,
`valid_from`/`valid_to`, and `content_hash`. Unsourced relations stay
UNKNOWN. Chokepoint without facts is DATA_GAP. Historical universe
membership without a true historical source is DATA_GAP. Current
universe is never backfilled into history.

## F. Failure memory and learning

Persistent SQLite store: `data/research-evidence/xiaomei22.sqlite`
(insert-only). Failure taxonomy includes TEMPORAL_LEAK, MISSING_EVIDENCE,
EARNINGS_MISREAD, UNIVERSE_SURVIVORSHIP_ERROR, DATA_PROVIDER_FAILURE.
Learning patterns do not modify `ticket_score`, `market_score`, or
`volume_confirmation_ratio`.

Seeded demo (not a ranking input):

- FailureMemory `7656eb6c-1444-455d-82fe-334e50a70b43` (NVDA EARNINGS_MISREAD)
- LearningPattern `62a04570-6a86-4650-80da-512fa9bb9beb` (`eps_beat_guidance_cut`)

## G. Production boundary

Research classification for NVDA/AAPL/MSFT = WATCHLIST.
Pipeline dry-run for each symbol = RESEARCH_ONLY SUCCESS,
`final_classification=MARKET_WATCHLIST_NEEDS_EVIDENCE`,
`paper_review_count=0`. Ranking key unchanged.

## H. Verification

- `python -m compileall -q .` PASS
- `PYTHONPATH=scripts pytest -q tests` = 238 passed
- `PYTHONPATH=scripts pytest -q tests/research` PASS
- `python scripts/xiaomei_22_audit.py` PASS
- `python scripts/db/migrate.py verify` PASS
- `python scripts/market_calendar.py` PASS
