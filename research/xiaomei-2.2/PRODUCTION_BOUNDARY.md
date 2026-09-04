# PRODUCTION_BOUNDARY — Xiaomei 2.2

Frozen boundary:

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
- PRODUCTION_RANKING_UNCHANGED=PASS
- LEGACY_ADAPTER=PASS
- LEGACY_SINGLE_OWNER=PASS
