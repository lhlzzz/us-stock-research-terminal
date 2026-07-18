# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-10-open
- as_of_date: 2026-06-10
- universe_source: nasdaq100_sp500_union
- source_mode: cached_local
- universe_key: union
- universe_total_symbols: 513
- universe_included_symbols: 488
- period_used: 1y
- classification: MARKET_WATCHLIST_NEEDS_EVIDENCE
- candidate_pool_size: 5
- top_k: 5
- paper_review_count: 0
- market_watchlist_count: 5
- zero_paper_review_is_valid_output: True
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening-guard-smoke/summary-2026-06-10-open.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening-guard-smoke/metrics-2026-06-10-open.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening-guard-smoke/candidates-2026-06-10-open.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening-guard-smoke/forward-tracking-2026-06-10-open.csv

## Methodology References
- UZI-Skill: risk checklist and multi-dimensional review
- TradingAgents: role-based research synthesis
- Serenity Skill: theme and supply-chain catalyst mapping
- Buffett Skills: quality, margin-of-safety, bear-case framing
- QuantDinger: replay discipline and data-health guardrails

## Price-Volume Summary
- equal_weight_20d_benchmark: 0.07279369837937971
- median_20d_momentum: 0.07279369837937971
- median_5d_acceleration: -0.08817522180133164
- median_volume_confirmation: 0.3093604277463087
- median_relative_strength: 0.0
- top_market_score_p90: 0.7979999999999999

## Paper Review Candidates
- none

## Market Watchlist Needs Evidence
|rank|symbol|company|raw_market_score|market_score|rule|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|
|1|AMD|Advanced Micro Devices, Inc.|None|None||None|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
|2|ADBE|Adobe Inc.|None|None||None|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
|3|ABNB|ABNB|None|None||None|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
|4|KLAC|KLAC|0.8999999999999999|0.82|momentum_exhaustion_guard|0.82|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
|5|HUBB|Hubbell Inc|0.6|0.6||0.6|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|

## Catalyst Summary
- candidates_with_narrative_relevant: 0
- candidates_with_business_relevant: 0
- top_shared_titles: []

## Evidence Gaps
### 1. AMD
- company: Advanced Micro Devices, Inc. (yfinance)
- narrative query: AMD advanced micro devices stock catalyst earnings news
- business query: AMD advanced micro devices orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 124
- business ranked candidates: 0 | status: missing | returncode: 124
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 2. ADBE
- company: Adobe Inc. (yfinance)
- narrative query: ADBE adobe stock catalyst earnings news
- business query: ADBE adobe orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 124
- business ranked candidates: 0 | status: missing | returncode: 124
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 3. ABNB
- company: ABNB (symbol)
- narrative query: ABNB abnb stock catalyst earnings news
- business query: ABNB abnb orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 124
- business ranked candidates: 0 | status: missing | returncode: 124
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 4. KLAC
- company: KLAC (symbol)
- narrative query: KLAC klac stock catalyst earnings news
- business query: KLAC klac orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 124
- business ranked candidates: 0 | status: missing | returncode: 124
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 5. HUBB
- company: Hubbell Inc (yfinance)
- narrative query: HUBB hubbell stock catalyst earnings news
- business query: HUBB hubbell orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 124
- business ranked candidates: 0 | status: missing | returncode: 124
- evidence gap reason: last30days_returned_zero_ranked_candidates

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|AMD|1|1d|2026-06-11|pending|
|AMD|1|3d|2026-06-15|pending|
|AMD|1|5d|2026-06-17|pending|
|AMD|1|10d|2026-06-24|pending|
|ADBE|2|1d|2026-06-11|pending|
|ADBE|2|3d|2026-06-15|pending|
|ADBE|2|5d|2026-06-17|pending|
|ADBE|2|10d|2026-06-24|pending|
|ABNB|3|1d|2026-06-11|pending|
|ABNB|3|3d|2026-06-15|pending|
|ABNB|3|5d|2026-06-17|pending|
|ABNB|3|10d|2026-06-24|pending|
|KLAC|4|1d|2026-06-11|pending|
|KLAC|4|3d|2026-06-15|pending|
|KLAC|4|5d|2026-06-17|pending|
|KLAC|4|10d|2026-06-24|pending|
|HUBB|5|1d|2026-06-11|pending|
|HUBB|5|3d|2026-06-15|pending|
|HUBB|5|5d|2026-06-17|pending|
|HUBB|5|10d|2026-06-24|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.15
- momentum_exhaustion_guard_adjustment: -0.08
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|rs_vs_equal_weight|
|---|---|---|---|---|---|---|---|---|
|1|KLAC|0.8999999999999999|0.82|momentum_exhaustion_guard|0.18053702162208274|-0.17558208534867492|0.6079804333943457|0.10774332324270303|
|2|HUBB|0.6|0.6||-0.034949624863323314|-0.0007683582539883549|0.01074042209827164|-0.10774332324270303|
|3|ADBE|None|None||None|None|None|None|
|4|AMD|None|None||None|None|None|None|
|5|ABNB|None|None||None|None|None|None|
|6|ALNY|None|None||None|None|None|None|
|7|GOOGL|None|None||None|None|None|None|
|8|GOOG|None|None||None|None|None|None|
|9|AMZN|None|None||None|None|None|None|
|10|AEP|None|None||None|None|None|None|

## Final Classification
- MARKET_WATCHLIST_NEEDS_EVIDENCE
