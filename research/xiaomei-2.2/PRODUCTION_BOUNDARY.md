# PRODUCTION_BOUNDARY — Xiaomei 2.2

Status: **PRODUCTION_RESEARCH_READY**

| surface | state |
| --- | --- |
| strategy `observable_footprint_v1` | **FROZEN** |
| research | **LIVE** |
| replay | **LIVE** |
| learning | **LIVE** |
| production ranking | `(ticket_score, market_score, volume_confirmation_ratio)` |
| Research → Alpha | **FORBIDDEN** |
| Research → BUY/SELL | **FORBIDDEN** |
| Learning → auto weight change | **FORBIDDEN** |
| Broker | **NO_BROKER** |
| Live Order | **NO_LIVE_ORDER** |

Operating classification remains **RESEARCH_ONLY**. Readiness does not
open a live-order or production-pick path.

Frozen flags:

- RESEARCH_ONLY
- PAPER_ONLY
- NO_BROKER
- NO_LIVE_ORDER
- NO_PRODUCTION_PICK
- NO_PRODUCTION_WEIGHT_CHANGE

Production ranking owner: **observable_footprint_v1**
Sort key: `(ticket_score, market_score, volume_confirmation_ratio)`
Owner file: `scripts/us_profit_ticket_pipeline.py`

## What 2.2 did not change

- No new quality / risk / panel / replay / production scorer
- Research OS cannot emit BUY / SELL / ORDER
- Failure memory cannot write ranking weights
- Estimate revision and earnings do not enter production ranking
- Chokepoint is research context only
- Legacy `research_panel.py` remains compatibility adapter
  (`canonical_owner=scripts.research`)

## Pipeline dry-run 2026-09-03

| symbol | status | classification | paper_review | ranking owner |
| --- | --- | --- | --- | --- |
| NVDA | RESEARCH_ONLY SUCCESS | MARKET_WATCHLIST_NEEDS_EVIDENCE | 0 | observable_footprint_v1 |
| AAPL | RESEARCH_ONLY SUCCESS | MARKET_WATCHLIST_NEEDS_EVIDENCE | 0 | observable_footprint_v1 |
| MSFT | RESEARCH_ONLY SUCCESS | MARKET_WATCHLIST_NEEDS_EVIDENCE | 0 | observable_footprint_v1 |

`as_of_date` / `target_session` / `actual_previous_trading_session` =
2026-09-03 for all three.

## Audit

`scripts/xiaomei_22_audit.py`:

- PRODUCTION_BOUNDARY=PASS
- PRODUCTION_RESEARCH_READY=PASS
- STRATEGY_FROZEN=PASS
- RESEARCH_LIVE=PASS
- REPLAY_LIVE=PASS
- LEARNING_LIVE=PASS
- LEARNING_NO_AUTO_WEIGHT=PASS
- RESEARCH_NO_ALPHA=PASS
- RESEARCH_NO_BUY_SELL=PASS
- NO_BROKER=PASS
- NO_LIVE_ORDER=PASS
- PRODUCTION_RANKING_UNCHANGED=PASS
- LEGACY_ADAPTER=PASS
- LEGACY_SINGLE_OWNER=PASS
