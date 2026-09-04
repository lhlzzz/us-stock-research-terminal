# DATA_COVERAGE — Xiaomei 2.2

As-of: **2026-09-03**
Symbols: NVDA, AAPL, MSFT
Source of truth: live SEC EDGAR + Research OS store

Rule: real data → PASS/OBSERVED. Missing source → DATA_GAP. Never mock PASS.

## Coverage matrix

| layer | NVDA | AAPL | MSFT | note |
| --- | --- | --- | --- | --- |
| SEC filings | OBSERVED (670) | OBSERVED (765) | OBSERVED (844) | EDGAR submissions |
| XBRL facts | OBSERVED | OBSERVED | OBSERVED | companyfacts |
| Revenue / NI / FCF | OBSERVED | OBSERVED | OBSERVED | XBRL-derived FCF |
| Guidance | DATA_GAP | DATA_GAP | DATA_GAP | not inferred from news |
| Segment | DATA_GAP | DATA_GAP | DATA_GAP | document parse not claimed |
| Customer concentration | DATA_GAP | DATA_GAP | DATA_GAP | absent in XBRL map |
| Earnings reported | OBSERVED | OBSERVED | OBSERVED | from SEC facts |
| Consensus EPS/rev | DATA_GAP | DATA_GAP | DATA_GAP | no validated consensus source |
| Estimate revision history | DATA_GAP | DATA_GAP | DATA_GAP | contract tested; live source absent |
| Industry SIC | OBSERVED | OBSERVED | OBSERVED | company → SIC description |
| Supply-chain graph | DATA_GAP | DATA_GAP | DATA_GAP | no independent supplier source |
| Chokepoint | DATA_GAP | DATA_GAP | DATA_GAP | empty facts stay DATA_GAP |
| Historical universe | DATA_GAP | DATA_GAP | DATA_GAP | no true membership source |
| Market OHLCV in research run | DATA_GAP | DATA_GAP | DATA_GAP | research run did not attach bars |
| Risk / catalyst / management | DATA_GAP | DATA_GAP | DATA_GAP | not invented |

## NVDA parsed XBRL (as_of 2026-09-03)

- revenue 96,221,000,000
- gross_profit 72,142,000,000
- operating_income 63,734,000,000
- net_income 59,688,000,000
- fcf 74,049,000,000 (DERIVED from OCF − |capex|)
- cash 22,443,000,000
- debt 32,366,000,000
- shares 24,100,000,000
- sbc 3,954,000,000
- buyback 39,044,000,000
- rpo 3,200,000,000
- eps_diluted 2.46

## Research readiness

Not a bool. NVDA/AAPL/MSFT readiness = **PARTIAL**
(`ready_count=4 / layer_total=10`). Reasons include market, revision,
risk, catalyst, management DATA_GAP. Classification = WATCHLIST, never
BUY/SELL.

## Provider audit

Each fetch records provider, request, symbol, as_of, attempt timestamps,
status, http_status, source, fallback, error. Cross-semantic fallback
`news → sec_filing` and `current_universe → historical_universe` is
blocked. Silent fallback is forbidden.
